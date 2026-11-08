"""답 단계: 판의 검색 결과로 Haiku 가 답하고, Opus 가 정답·근거 구간과 견주어 채점한다.

    P=.venv-hr2/bin/python
    $P 23_answer.py answer runs/23-arch-b0-dense dense            # free·eref 두 형식, runs/23-answer/<판>-<형식>/answers.jsonl
    $P 23_answer.py grade  runs/23-arch-b0-dense dense            # grades.jsonl
    $P 23_answer.py table                                          # 폴더마다 score.md, runs/23-answer/SUMMARY.md

답 단계는 질문과 검색 단위만 본다. 정답 answer·evidence·type 은 grade·table 만 읽는다.
"""
import argparse
import importlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from llm_cache import ClaudeClient, LLMCallFailed

arch = importlib.import_module("23_arch_common")

PROMPTS = arch.LAB / "prompts"
OUT_ROOT = arch.RUNS / "23-answer"
FORMATS = ("free", "eref", "eref-fix")
FIRST_PASS_FORMATS = ("free", "eref")
REFUSAL = "근거 없음"
BUDGET_MODE = "5000자"
TYPE_ORDER = ("single", "multihop", "aggregation", "diffterm", "temporal", "overview", "noevidence")
ANSWER_WIDER_THAN_EVIDENCE = frozenset({  # inputs/net-corpus/gold/GOLD.md 재판정 절: 3회차 뒤에도 "일부만" 인 14문항
    "S01-ag03", "S02-ag02", "S03-ag02", "S03-ag03", "S07-ag02", "S08-ag03", "S09-ag03", "S10-ag02", "S10-ag03",
    "S01-mh03", "S01-ov03", "S02-mh03", "S04-dt01", "S05-ov02"})

HANDLE = re.compile(r"\[E(\d+)\]")
SENTENCE_BREAK = re.compile(r"(?<=[.!?。])(?<!\b[A-Z]\.)\s+")
LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
FREE_ANSWER_HEAD = re.compile(r"^\s*\**답\**\s*[:：]\s*")
FREE_SOURCES_HEAD = re.compile(r"^\s*\**근거\s*문서\**\s*[:：]\s*(.*)$")


def prompt_text(name):
    return (PROMPTS / name).read_text(encoding="utf-8")


def doc_header(doc_id):
    doc = arch.read_docs()[doc_id]
    return f"{doc_id} ({doc['kind']}, {doc['date'][:10]}, 제목: {doc['title']})"


def unit_text(unit):
    return arch.span_text(unit["doc_id"], unit["start"], unit["end"])


def lab_relative(run_dir):
    return str(Path(run_dir).resolve().relative_to(arch.LAB))


def run_label(run_dir, variant):
    short = Path(run_dir).name.removeprefix("23-arch-")
    return short if variant in short else f"{short}.{variant}"


def shown_units_by_question(run_dir, variant):
    rows = [r for r in arch.read_jsonl(Path(run_dir) / "retrieval.jsonl") if r["variant"] == variant]
    if not rows:
        raise SystemExit(f"{run_dir}/retrieval.jsonl 에 variant {variant} 가 없다")
    return {r["qid"]: arch.fill_budget(r["units"]) for r in rows}


def materials(units, form):
    if form == "eref":
        return "\n\n".join(f"[E{n}] {doc_header(u['doc_id'])}\n{unit_text(u)}" for n, u in enumerate(units, start=1))
    return "\n\n".join(f"--- {doc_header(u['doc_id'])}\n{unit_text(u)}" for u in units)


def answer_prompt(question, units, form):
    return f"[질문]\n{question}\n\n[자료]\n{materials(units, form)}"


@dataclass
class Sentence:
    text: str
    handles: list = field(default_factory=list)

    @property
    def states_absence(self):
        return REFUSAL in self.text


def has_words(text):
    return re.search(r"\w", HANDLE.sub("", text)) is not None


def split_sentences(body):
    sentences = []
    for line in body.splitlines():
        line = LIST_MARKER.sub("", line.replace("**", "")).strip()
        for piece in SENTENCE_BREAK.split(line):
            piece = piece.strip()
            if not piece:
                continue
            handles = [int(n) for n in HANDLE.findall(piece)]
            if has_words(piece):
                sentences.append(Sentence(piece, handles))
            elif handles and sentences:
                sentences[-1].handles += handles
                sentences[-1].text += " " + piece
    return sentences


def parse_eref(reply, units):
    sentences = split_sentences(reply)
    known = range(1, len(units) + 1)
    cited = sorted({h for s in sentences for h in s.handles})
    uncited = [s.text for s in sentences if not s.handles and not s.states_absence]
    unknown = [h for h in cited if h not in known]
    refused = opens_with_absence(sentences) and not cited
    return {"sentences": [{"text": s.text, "handles": s.handles, "states_absence": s.states_absence} for s in sentences],
            "cited": [{"handle": f"E{h}", **span_of(units[h - 1])} for h in cited if h in known],
            "unknown_handles": [f"E{h}" for h in unknown], "uncited_sentences": [] if refused else uncited,
            "incomplete": not refused and bool(unknown or uncited), "refused_by_code": refused}


def opens_with_absence(sentences):
    return bool(sentences) and sentences[0].states_absence


def span_of(unit):
    return {"doc_id": unit["doc_id"], "start": unit["start"], "end": unit["end"]}


def parse_free(reply, units):
    shown_docs = list(dict.fromkeys(u["doc_id"] for u in units))
    corpus_ids = arch.read_docs().keys()
    body_lines, listed, has_sources_line = [], [], False
    for line in reply.splitlines():
        sources = FREE_SOURCES_HEAD.match(line)
        if sources:
            has_sources_line = True
            listed += [t.strip(" `*[]()") for t in re.split(r"[,\s]+", sources.group(1)) if t.strip(" `*[]()")]
        else:
            body_lines.append(FREE_ANSWER_HEAD.sub("", line))
    body = "\n".join(body_lines)
    mentioned = [d for d in shown_docs if d in body]
    cited = list(dict.fromkeys([d for d in listed if d in shown_docs] if has_sources_line else mentioned))
    unknown = [t for t in listed if t not in shown_docs and (t in corpus_ids or re.search(r"\w-\w", t))]
    sentences = split_sentences(body)
    content = [s for s in sentences if not s.states_absence]
    refused = opens_with_absence(sentences) and not cited
    uncited = [s.text for s in content] if not cited and not refused else []
    return {"sentences": [{"text": s.text, "handles": [], "states_absence": s.states_absence} for s in sentences],
            "cited_docs": cited, "unknown_docs": unknown, "uncited_sentences": uncited,
            "incomplete": bool(unknown or uncited), "refused_by_code": refused}


def out_dir(label, form):
    return OUT_ROOT / f"{label}-{form}"


def answer_run(run_dir, variant, label, forms, qids):
    questions = [q for q in arch.read_questions() if not qids or q.qid in qids]
    shown = shown_units_by_question(run_dir, variant)
    client = ClaudeClient("haiku")
    for form in forms:
        if form == "eref-fix":
            write_answers(label, form, run_dir, variant, fix_rows(label, questions, shown, client))
            continue
        system = prompt_text(f"answer-{form}.txt")
        prompts = [answer_prompt(q.question, shown[q.qid], form) for q in questions]
        replies = client.ask_many(prompts, system=system, tag=f"answer-{form}")
        rows = []
        for q, prompt, reply in zip(questions, prompts, replies):
            units = shown[q.qid]
            row = {"qid": q.qid, "format": form, "run_dir": lab_relative(run_dir), "variant": variant,
                   "shown": [{"handle": f"E{n}", **span_of(u), "path": u["path"]} for n, u in enumerate(units, start=1)],
                   "shown_chars": arch.chars_of(units), "llm": arch.llm_record(client, prompt, system)}
            if isinstance(reply, LLMCallFailed):
                rows.append({**row, "answer": None, "error": str(reply)})
                continue
            parsed = parse_eref(reply.text, units) if form == "eref" else parse_free(reply.text, units)
            rows.append({**row, "answer": reply.text, **parsed})
        write_answers(label, form, run_dir, variant, rows)
    print("haiku", client.usage_line(), flush=True)


def write_answers(label, form, run_dir, variant, rows):
    target = out_dir(label, form)
    target.mkdir(parents=True, exist_ok=True)
    arch.write_jsonl(target / "answers.jsonl", rows)
    prompts = ["prompts/answer-eref.txt", "prompts/answer-eref-fix.txt"] if form == "eref-fix" else [f"prompts/answer-{form}.txt"]
    (target / "RUN.json").write_text(json.dumps({
        "run_dir": lab_relative(run_dir), "variant": variant, "format": form, "questions": len(rows),
        "answer_prompt": prompts, "answer_model": "haiku", "budget": [arch.MIN_BUDGET, arch.MIN_UNITS],
        "gold_sha256": arch.sha256_of(arch.GOLD), "docs_sha256": arch.sha256_of(arch.DOCS)}, ensure_ascii=False, indent=1))
    failed = sum(r.get("answer") is None for r in rows)
    print(f"{target.name}: 답 {len(rows) - failed}, 실패 {failed}", flush=True)


def fix_problems(first):
    lines = [f"- 표식이 없는 문장: {text}" for text in first["uncited_sentences"]]
    lines += [f"- [자료] 에 없는 표식: [{h}]" for h in first["unknown_handles"]]
    return "\n".join(lines)


def fix_rows(label, questions, shown, client):
    """eref 답 가운데 incomplete 인 것만 고칠 곳을 짚어 한 번 더 부른다. 고친 답이 또 incomplete 면 그대로 incomplete 다."""
    first_rows = {r["qid"]: r for r in arch.read_jsonl(out_dir(label, "eref") / "answers.jsonl")}
    system, template = prompt_text("answer-eref.txt"), prompt_text("answer-eref-fix.txt")
    needs_fix = [q for q in questions if first_rows[q.qid].get("incomplete")]
    prompts = [answer_prompt(q.question, shown[q.qid], "eref") + "\n\n" + template.replace("<<PREVIOUS>>", first_rows[q.qid]["answer"])
               .replace("<<PROBLEMS>>", fix_problems(first_rows[q.qid])) for q in needs_fix]
    fixed = dict(zip((q.qid for q in needs_fix), zip(prompts, client.ask_many(prompts, system=system, tag="answer-eref-fix"))))
    rows = []
    for q in questions:
        first = first_rows[q.qid]
        row = {**first, "format": "eref-fix", "fix_turn": q.qid in fixed,
               "first_pass": {k: first.get(k) for k in ("incomplete", "unknown_handles", "uncited_sentences", "refused_by_code")}}
        if q.qid in fixed:
            prompt, reply = fixed[q.qid]
            second = arch.llm_record(client, prompt, system)
            row["llm"] = {"seconds": first["llm"]["seconds"] + second["seconds"], "cost_usd": first["llm"]["cost_usd"] + second["cost_usd"],
                          "cached": second["cached"], "calls": 2}
            if isinstance(reply, LLMCallFailed):
                row["fix_error"] = str(reply)
            else:
                row.update(answer=reply.text, **parse_eref(reply.text, shown[q.qid]))
        rows.append(row)
    return rows


def gold_rows():
    return {str(r["qid"]): r for r in arch.read_jsonl(arch.GOLD)}


def evidence_block(gold):
    if not gold.get("evidence"):
        near = "\n\n".join(f"[가까운 대상 {n}] {doc_header(s['doc_id'])}\n{arch.span_text(s['doc_id'], s['start'], s['end'])}"
                           for n, s in enumerate(gold.get("near") or [], start=1))
        return "없음 — 이 질문은 말뭉치에 답이 없게 만든 문항이다." + (f"\n\n질문과 가까운 대상의 구간(답이 아니다):\n{near}" if near else "")
    pieces, n = [], 0
    for item in gold["evidence"]:
        for s in item.get("spans", [item]):
            n += 1
            pieces.append(f"[{n}] {item.get('label', '')} · {doc_header(s['doc_id'])}\n{arch.span_text(s['doc_id'], s['start'], s['end'])}")
    return "\n\n".join(pieces)


def citation_block(answer):
    if answer["format"].startswith("eref"):
        return "\n\n".join(f"[{c['handle']}] {doc_header(c['doc_id'])}\n{arch.span_text(c['doc_id'], c['start'], c['end'])}"
                           for c in answer["cited"])
    by_doc = defaultdict(list)
    for u in answer["shown"]:
        by_doc[u["doc_id"]].append(arch.span_text(u["doc_id"], u["start"], u["end"]))
    return "\n\n".join(f"[문서 {d}] {doc_header(d)}\n" + "\n…\n".join(by_doc[d]) for d in answer["cited_docs"])


def judged_sentences(answer):
    """(id, 문장, 인용 표시) — 인용이 있고 '근거 없음' 문장이 아닌 것만 Opus 가 판정한다."""
    picked = []
    for n, s in enumerate(answer["sentences"], start=1):
        if s["states_absence"]:
            continue
        if answer["format"].startswith("eref") and s["handles"]:
            known = [f"E{h}" for h in s["handles"] if f"E{h}" not in answer["unknown_handles"]]
            if known:
                picked.append((f"S{n}", s["text"], "인용: " + ", ".join(dict.fromkeys(known))))
        elif answer["format"] == "free" and answer["cited_docs"]:
            picked.append((f"S{n}", s["text"], "인용: 모델이 적은 근거 문서 전부"))
    return picked


def grade_prompt(gold, answer):
    sentences = "\n".join(f"{sid} ({tag}): {text}" for sid, text, tag in judged_sentences(answer)) or "(없음)"
    cited = citation_block(answer) or "(인용 없음)"
    return (f"질문: {gold['question']}\n정답: {gold['answer']}\n\n정답 근거 구간:\n{evidence_block(gold)}\n\n"
            f"모델 답:\n{answer['answer']}\n\n모델이 인용한 자료:\n{cited}\n\n판정할 문장:\n{sentences}")


def parse_grade(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        grade = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if grade.get("correctness") not in (0, 0.5, 1) or not isinstance(grade.get("refused"), bool):
        return None
    return grade


SUPPORT_VALUE = {"full": 1.0, "partial": 0.5, "none": 0.0}


def support_score(answer, grade):
    """판정 대상 문장(근거 없음 문장 제외)마다 full 1·partial 0.5·none 0, 인용 없는 문장은 0. 대상이 없으면 None."""
    verdicts = {s.get("id"): SUPPORT_VALUE.get(s.get("support")) for s in grade.get("sentences", [])}
    judged = {sid for sid, _, _ in judged_sentences(answer)}
    values = []
    for n, s in enumerate(answer["sentences"], start=1):
        if s["states_absence"]:
            continue
        sid = f"S{n}"
        values.append((verdicts.get(sid) or 0.0) if sid in judged else 0.0)
    return mean(values) if values else None


def retrieval_recall(run_dir, variant):
    return {qid: r["recall"] for (qid, mode), r in arch.read_detail(run_dir, variant).items() if mode == BUDGET_MODE}


def shown_recall(answer, gold_items):
    scorer = arch._scorer()
    pieces = scorer.taken([{**u, "path": u.get("path", "")} for u in answer["shown"]])
    return scorer.judge(pieces, gold_items)["recall"] if gold_items else None


def grade_run(label, forms):
    golds = gold_rows()
    scorer = arch._scorer()
    gold_items = scorer.read_gold(arch.GOLD)
    client = ClaudeClient("opus")
    system = prompt_text("answer-grade.txt")
    for form in forms:
        target = out_dir(label, form)
        answers = [a for a in arch.read_jsonl(target / "answers.jsonl") if a.get("answer") is not None]
        run_info = json.loads((target / "RUN.json").read_text())
        recall = retrieval_recall(arch.LAB / run_info["run_dir"], run_info["variant"])
        prompts = [grade_prompt(golds[a["qid"]], a) for a in answers]
        replies = client.ask_many(prompts, system=system, tag=f"grade-{form}")
        rows = []
        for a, prompt, reply in zip(answers, prompts, replies):
            gold = golds[a["qid"]]
            row = {"qid": a["qid"], "type": gold["type"], "answer_wider_than_evidence": a["qid"] in ANSWER_WIDER_THAN_EVIDENCE,
                   "retrieval_recall_5000": recall.get(a["qid"]), "shown_recall": shown_recall(a, gold_items[a["qid"]]["items"]),
                   "incomplete": a["incomplete"], "refused_by_code": a["refused_by_code"], "llm": arch.llm_record(client, prompt, system)}
            grade = None if isinstance(reply, LLMCallFailed) else parse_grade(reply.text)
            if grade is None:
                rows.append({**row, "grade": None, "error": str(reply) if isinstance(reply, LLMCallFailed) else reply.text[:500]})
                continue
            rows.append({**row, "correctness": grade["correctness"], "refused": grade["refused"],
                         "support": support_score(a, grade), "sentence_support": grade.get("sentences", []), "note": grade.get("note", "")})
        arch.write_jsonl(target / "grades.jsonl", rows)
        failed = sum("correctness" not in r for r in rows)
        print(f"{target.name}: 채점 {len(rows) - failed}, 실패 {failed}", flush=True)
    print("opus", client.usage_line(), flush=True)


def fmt(value, digits=3):
    return "-" if value is None else f"{value:.{digits}f}"


def mean_or_none(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def uncited_sentence_share(answers):
    answered = [a for a in answers if a.get("answer") is not None]
    content = sum(sum(not s["states_absence"] for s in a["sentences"]) for a in answered)
    return sum(len(a["uncited_sentences"]) for a in answered) / content if content else None


def folder_metrics(target, golds):
    answers = {a["qid"]: a for a in arch.read_jsonl(target / "answers.jsonl")}
    grades = [g for g in arch.read_jsonl(target / "grades.jsonl") if "correctness" in g]
    with_evidence = [g for g in grades if g["type"] != "noevidence"]
    no_evidence = [g for g in grades if g["type"] == "noevidence"]
    by_type = {t: mean_or_none(g["correctness"] for g in grades if g["type"] == t) for t in TYPE_ORDER}
    lang_of = {qid: golds[qid].get("lang", "") for qid in answers}
    by_lang = {lang: {"with_evidence": mean_or_none(g["correctness"] for g in with_evidence if lang_of[g["qid"]] == lang),
                      "refusal_recall": mean_or_none(g["refused"] for g in no_evidence if lang_of[g["qid"]] == lang),
                      "questions": sum(lang_of[g["qid"]] == lang for g in grades)}
               for lang in sorted(set(lang_of.values()))}
    relation = Counter()
    for g in with_evidence:
        r = g["retrieval_recall_5000"]
        bucket = "0" if r == 0 else "1" if r == 1 else "일부"
        relation[bucket, g["correctness"]] += 1
    return {
        "name": target.name, "graded": len(grades), "answered": sum(a.get("answer") is not None for a in answers.values()),
        "by_type": by_type, "by_lang": by_lang,
        "fix_turns": sum(bool(a.get("fix_turn")) for a in answers.values()),
        "first_pass_incomplete": mean_or_none(a["first_pass"]["incomplete"] for a in answers.values() if "first_pass" in a),
        "with_evidence": mean_or_none(g["correctness"] for g in with_evidence),
        "with_evidence_without_wide": mean_or_none(g["correctness"] for g in with_evidence if not g["answer_wider_than_evidence"]),
        "wide": {g["qid"]: g["correctness"] for g in with_evidence if g["answer_wider_than_evidence"]},
        "support": mean_or_none(g["support"] for g in grades if not g["refused"]),
        "support_questions": sum(g["support"] is not None and not g["refused"] for g in grades),
        "incomplete": mean(a["incomplete"] for a in answers.values() if a.get("answer") is not None),
        "unknown_citations": sum(bool(a.get("unknown_handles") or a.get("unknown_docs")) for a in answers.values() if a.get("answer") is not None),
        "uncited_answers": sum(bool(a.get("uncited_sentences")) for a in answers.values() if a.get("answer") is not None),
        "uncited_sentence_share": uncited_sentence_share(answers.values()),
        "refusal_recall": mean_or_none(g["refused"] for g in no_evidence),
        "false_refusal": mean_or_none(g["refused"] for g in with_evidence),
        "false_refusal_found": sum(g["refused"] and g["retrieval_recall_5000"] > 0 for g in with_evidence),
        "false_refusal_missed": sum(g["refused"] and g["retrieval_recall_5000"] == 0 for g in with_evidence),
        "code_vs_grader_refusal": sum(g["refused"] != g["refused_by_code"] for g in grades),
        "retrieval_recall": mean_or_none(g["retrieval_recall_5000"] for g in with_evidence),
        "shown_vs_budget_recall_differ": sum(g["shown_recall"] != g["retrieval_recall_5000"] for g in with_evidence),
        "relation": relation,
        "found_but_wrong": relation["1", 0], "missed_but_right": relation["0", 1],
        "cost": sum(a["llm"]["cost_usd"] for a in answers.values()) + sum(g["llm"]["cost_usd"] for g in grades),
    }


def folder_table(m):
    lines = [f"# {m['name']}", "",
             f"답 {m['answered']} · 채점 {m['graded']} · 답+채점 비용 ${m['cost']:.2f}", "",
             "| 유형 | 정답성 평균 |", "|---|---:|"]
    lines += [f"| {t} | {fmt(m['by_type'][t])} |" for t in TYPE_ORDER]
    lines += ["", "| 항목 | 값 |", "|---|---:|",
              f"| 근거 있는 문항 정답성 | {fmt(m['with_evidence'])} |",
              f"| 같은 값, 정답이 근거보다 넓은 14문항 뺌 | {fmt(m['with_evidence_without_wide'])} |",
              f"| 인용 지지율 (거절 아닌 답 {m['support_questions']}개) | {fmt(m['support'])} |",
              f"| incomplete 비율 | {fmt(m['incomplete'])} |",
              *([f"| 교정 턴을 받은 답 / 교정 전 incomplete 비율 | {m['fix_turns']} / {fmt(m['first_pass_incomplete'])} |"] if m["first_pass_incomplete"] is not None else []),
              f"| 모르는 인용이 있는 답 | {m['unknown_citations']} |",
              f"| 인용 없는 문장이 있는 답 | {m['uncited_answers']} |",
              f"| 내용 문장 가운데 인용 없는 문장 비율 | {fmt(m['uncited_sentence_share'])} |",
              f"| 근거 없음 거절 재현율 | {fmt(m['refusal_recall'])} |",
              f"| 오거절률 (근거 있는 문항) | {fmt(m['false_refusal'])} |",
              f"| 오거절 중 검색이 근거를 일부라도 가져온 것 / 못 가져온 것 | {m['false_refusal_found']} / {m['false_refusal_missed']} |",
              f"| 코드 판정과 Opus 판정의 거절이 갈린 답 | {m['code_vs_grader_refusal']} |",
              f"| 검색 재현율 5000자 | {fmt(m['retrieval_recall'])} |",
              f"| 보인 단위 재현율이 5000자 재현율과 다른 문항 | {m['shown_vs_budget_recall_differ']} |",
              "", "검색 재현율(5000자) × 정답성, 근거 있는 문항 수:", "",
              "| 재현율 \\ 정답성 | 0 | 0.5 | 1 |", "|---|---:|---:|---:|"]
    lines += [f"| {b} | " + " | ".join(str(m["relation"][b, c]) for c in (0, 0.5, 1)) + " |" for b in ("0", "일부", "1")]
    lines += ["", "| 언어 | 문항 | 근거 있는 문항 정답성 | 근거 없음 거절 재현율 |", "|---|---:|---:|---:|"]
    lines += [f"| {lang} | {v['questions']} | {fmt(v['with_evidence'])} | {fmt(v['refusal_recall'])} |" for lang, v in m["by_lang"].items()]
    lines += ["", "정답이 근거 구간보다 넓은 14문항의 정답성: " + ", ".join(f"{q} {c}" for q, c in sorted(m["wide"].items()))]
    return "\n".join(lines) + "\n"


def summary_table(metrics):
    head = ["판·형식", *TYPE_ORDER, "근거 있음", "ko", "en", "넓은 14 뺌", "인용 지지", "incomplete", "거절 재현", "오거절", "검색 5000자", "찾았는데 0", "못 찾았는데 1"]
    lines = ["| " + " | ".join(head) + " |", "|---|" + "---:|" * (len(head) - 1)]
    for m in metrics:
        cells = [fmt(m["by_type"][t], 2) for t in TYPE_ORDER] + [
            fmt(m["with_evidence"]), *(fmt(m["by_lang"].get(lang, {}).get("with_evidence"), 2) for lang in ("ko", "en")),
            fmt(m["with_evidence_without_wide"]), fmt(m["support"]), fmt(m["incomplete"]),
            fmt(m["refusal_recall"]), fmt(m["false_refusal"]), fmt(m["retrieval_recall"]),
            str(m["found_but_wrong"]), str(m["missed_but_right"])]
        lines.append(f"| {m['name']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def table_all(names):
    folders = [OUT_ROOT / n for n in names] if names else sorted(p for p in OUT_ROOT.iterdir() if (p / "grades.jsonl").exists())
    metrics, golds = [], gold_rows()
    for target in folders:
        m = folder_metrics(target, golds)
        (target / "score.md").write_text(folder_table(m))
        metrics.append(m)
    summary = ("# 답 단계 요약\n\n정답성은 Opus 채점 0/0.5/1 의 평균이다. noevidence 칸은 거절했으면 1 이다. "
               "찾았는데 0 은 5000자 재현율 1 인데 정답성 0, 못 찾았는데 1 은 재현율 0 인데 정답성 1 인 문항 수다.\n\n"
               + summary_table(metrics) + "\n")
    (OUT_ROOT / "SUMMARY.md").write_text(summary)
    print(summary)


def main():
    parser = argparse.ArgumentParser(description="판의 검색 결과로 Haiku 답(free·eref)을 내고 Opus 로 채점한다.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("answer", "grade"):
        command = commands.add_parser(name)
        command.add_argument("run_dir")
        command.add_argument("variant")
        command.add_argument("--label", help="runs/23-answer/<label>-<형식>/. 기본은 판 폴더 이름(variant 가 다르면 .variant)")
        command.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FIRST_PASS_FORMATS),
                             help="eref-fix 는 같은 label 의 eref 답이 먼저 있어야 한다")
        if name == "answer":
            command.add_argument("--qids", nargs="+", help="이 문항만 (시험용). 비우면 250문항")
    table = commands.add_parser("table")
    table.add_argument("names", nargs="*", help="runs/23-answer/ 아래 폴더 이름. 비우면 grades.jsonl 이 있는 모든 폴더")
    args = parser.parse_args()
    if args.command == "table":
        return table_all(args.names)
    label = args.label or run_label(args.run_dir, args.variant)
    if args.command == "answer":
        answer_run(args.run_dir, args.variant, label, args.formats, args.qids)
    else:
        grade_run(label, args.formats)


if __name__ == "__main__":
    main()
