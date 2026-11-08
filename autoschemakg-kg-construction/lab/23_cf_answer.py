"""9단계 답 판 S-orig·S0~S4: 작은 모델(qwen3:8b)이 검색 결과(+ 연결된 카드)로 답하고, Opus 가 이름 표·카드와 함께 채점한다.

    P=.venv-hr2/bin/python
    $P 23_cf_answer.py answer S1          # runs/23-cf-answer/S1/answers.jsonl (scope.txt 80문항)
    $P 23_cf_answer.py grade S1           # grades.jsonl
    $P 23_cf_answer.py table              # 판마다 score.md, runs/23-cf-answer/SUMMARY.md

판마다 말뭉치가 달라서(S-orig 는 원래, 나머지는 사내화) 23_arch_common 을 읽기 전에 NET_CORPUS·NET_GOLD 를 정한다.
그래서 answer·grade 는 판 하나씩 따로 띄운다. answer 는 질문 글과 검색 단위·카드만 본다. 정답은 grade·table 만 읽는다.
"""
import argparse
import importlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

LAB = Path(__file__).parent
CF_GOLD = "inputs/net-corpus-cf/gold/questions-cf.jsonl"
ORIG_GOLD = "inputs/net-corpus-cf/gold/questions-orig.jsonl"
SCOPE = LAB / "inputs/net-corpus-cf/gold/scope.txt"
LINKS = [LAB / "runs/23-cf-link/questions-alias.jsonl", LAB / "runs/23-cf-link/questions-fact.jsonl"]
OUT_ROOT = LAB / "runs/23-cf-answer"
ANSWER_PROMPT = LAB / "prompts/cf-answer.txt"
GRADE_PROMPT = LAB / "prompts/cf-answer-grade.txt"
ANSWER_TOKENS = 768
ANSWER_CONTEXT = 16384
BUDGET_MODE = "5000자"
NO_CARDS = "(없음)"
CARD_HANDLE = re.compile(r"\[G(\d+)\]")
CARD_SOURCES_HEAD = re.compile(r"^\s*\**근거\s*카드\**\s*[:：]\s*(.*)$")


@dataclass(frozen=True)
class AnswerRun:
    retrieval_dir: str
    variant: str
    corpus: str
    cards_from: str = ""

    @property
    def with_cards(self):
        return bool(self.cards_from)

    def card_ids(self, linked):
        """hubs = 작은 모델 선택(주된 판), union = 글자 매칭 ∪ 작은 모델(사후 판 S1-union)."""
        return linked["hubs"] if self.cards_from == "hubs" else list(dict.fromkeys(linked["text_hubs"] + linked["hubs"]))

    @property
    def gold(self):
        return ORIG_GOLD if self.corpus == "orig" else CF_GOLD


RUNS = {
    "S-orig": AnswerRun("runs/23-cf-orig", "cf-orig", "orig"),
    "S0": AnswerRun("runs/23-cf-claimctx", "cf-claimctx", "cf"),
    "S1": AnswerRun("runs/23-cf-claimctx", "cf-claimctx", "cf", "hubs"),
    "S1-union": AnswerRun("runs/23-cf-claimctx", "cf-claimctx", "cf", "union"),
    "S2": AnswerRun("runs/23-cf-rewrite", "cf-rewrite", "cf", "hubs"),
    "S3": AnswerRun("runs/23-cf-relgraph", "cf-relgraph", "cf", "hubs"),
    "S4": AnswerRun("runs/23-cf-table", "cf-table", "cf", "hubs"),
}
POST_HOC = {"S1-union": "link=union: 연결 80 의 정확도를 본 뒤 더한 판(team-lead 결정)"}
COMPARISONS = [("S-orig", "S0"), ("S0", "S1"), ("S1", "S1-union"), ("S1", "S2"), ("S1", "S3"), ("S1", "S4")]


def configure(spec):
    os.environ["NET_CORPUS"] = spec.corpus
    os.environ["NET_GOLD"] = spec.gold
    sys.path.insert(0, str(LAB))
    global arch, ans, link
    arch = importlib.import_module("23_arch_common")
    ans = importlib.import_module("23_answer")
    link = importlib.import_module("23_cf_link")


def scope_qids():
    return [line.split("\t", 1)[0] for line in SCOPE.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_qid(qid, spec):
    """S-orig 는 원래 말뭉치 판이라 alias 문항을 원래 qid(pub 글)로 묻는다. fact 문항은 qid 가 같다."""
    return qid.removesuffix(".alias") if spec.corpus == "orig" else qid


def read_links():
    return {row["qid"]: row for path in LINKS for row in arch.read_jsonl(path)}


def answer_prompt(question, cards, units):
    card_block = link.render_cards(cards) if cards else NO_CARDS
    return f"[질문]\n{question}\n\n[카드]\n{card_block}\n\n[자료]\n{ans.materials(units, 'free')}"


def parse_answer(reply, units, cards):
    body_lines, listed = [], []
    for line in reply.splitlines():
        sources = CARD_SOURCES_HEAD.match(line)
        if sources:
            listed += [int(n) for n in re.findall(r"G?(\d+)", sources.group(1))]
        else:
            body_lines.append(line)
    parsed = ans.parse_free("\n".join(body_lines), units)
    for s in parsed["sentences"]:
        s["cards"] = [int(n) for n in CARD_HANDLE.findall(s["text"])]
    inline = [n for s in parsed["sentences"] for n in s["cards"]]
    numbers = list(dict.fromkeys(listed + inline))
    known = range(1, len(cards) + 1)
    return {**parsed, "cited_cards": [cards[n - 1].id for n in numbers if n in known],
            "unknown_cards": [f"G{n}" for n in numbers if n not in known]}


def answer_run(label):
    spec = RUNS[label]
    qids = scope_qids()
    questions = {q.qid: q.question for q in arch.read_questions()}
    retrieval = {r["qid"]: r["units"] for r in arch.read_jsonl(LAB / spec.retrieval_dir / "retrieval.jsonl") if r["variant"] == spec.variant}
    links = read_links() if spec.with_cards else {}
    cards_by_id = {c.id: c for c in link.read_cards()}
    from ollama_cache import OllamaClient
    from llm_cache import LLMCallFailed
    client = OllamaClient("qwen3:8b", num_ctx=ANSWER_CONTEXT, num_predict=ANSWER_TOKENS)
    system = ANSWER_PROMPT.read_text(encoding="utf-8")
    jobs = []
    for qid in qids:
        source = source_qid(qid, spec)
        units = arch.fill_budget(retrieval[source])
        cards = [cards_by_id[h] for h in spec.card_ids(links[qid])] if spec.with_cards else []
        jobs.append((qid, source, units, cards, answer_prompt(questions[source], cards, units)))
    replies = client.ask_many([job[-1] for job in jobs], system=system, tag=f"cf-answer-{label}")
    rows = []
    for (qid, source, units, cards, prompt), reply in zip(jobs, replies):
        row = {"qid": qid, "source_qid": source, "label": label, "cards_shown": [c.id for c in cards],
               "shown": [{**ans.span_of(u), "path": u["path"]} for u in units], "shown_chars": arch.chars_of(units),
               "llm": arch.llm_record(client, prompt, system)}
        if isinstance(reply, LLMCallFailed):
            rows.append({**row, "answer": None, "error": str(reply)})
            continue
        rows.append({**row, "answer": reply.text, "truncated": reply.metadata.get("finish_reason") == "length",
                     "tokens": [reply.metadata.get("prompt_tokens"), reply.metadata.get("completion_tokens")],
                     **parse_answer(reply.text, units, cards)})
    target = OUT_ROOT / label
    target.mkdir(parents=True, exist_ok=True)
    arch.write_jsonl(target / "answers.jsonl", rows)
    (target / "RUN.json").write_text(json.dumps({
        "label": label, **spec.__dict__, "post_hoc": POST_HOC.get(label, ""), "questions": len(rows), "answer_prompt": str(ANSWER_PROMPT.relative_to(LAB)),
        "model": "qwen3:8b", "options": client.options, "scope_sha256": arch.sha256_of(SCOPE), "hubs_sha256": arch.sha256_of(link.HUBS),
        "docs_sha256": arch.sha256_of(arch.DOCS), "gold_sha256": arch.sha256_of(arch.GOLD), "ollama": client.usage_line()},
        ensure_ascii=False, indent=1))
    print(f"{label}: 답 {sum(r['answer'] is not None for r in rows)}/{len(rows)} · 끊김 {sum(bool(r.get('truncated')) for r in rows)} · {client.usage_line()}", flush=True)


def name_table(text, extra_ids, cards, slugs):
    """질문·정답·근거·답에 글자로 나오는 구심점과 extra_ids 의 '공개 이름 = 사내 이름 / 별칭 / 식별자 slug' 줄."""
    ids = list(dict.fromkeys(list(extra_ids) + link.text_match(text, cards)))
    by_id = {c.id: c for c in cards}
    return "\n".join(f"- {', '.join(by_id[i].public_names)} = {by_id[i].name} / {', '.join(by_id[i].aliases)} / 식별자 안에서는 {slugs[i]}"
                     for i in ids) or "(없음)"


def hub_slugs():
    return {h.id: h.slug for h in importlib.import_module("23_cf_layer").read_hubs()}


def cited_material(answer):
    by_doc = defaultdict(list)
    for u in answer["shown"]:
        by_doc[u["doc_id"]].append(arch.span_text(u["doc_id"], u["start"], u["end"]))
    return "\n\n".join(f"[문서 {d}] {ans.doc_header(d)}\n" + "\n…\n".join(by_doc[d]) for d in answer["cited_docs"]) or "(인용 없음)"


def judged_sentences(answer):
    picked = []
    for n, s in enumerate(answer["sentences"], start=1):
        if s["states_absence"]:
            continue
        tags = (["모델이 적은 근거 문서 전부"] if answer["cited_docs"] else []) + [f"G{c}" for c in s["cards"] if f"G{c}" not in answer["unknown_cards"]]
        if tags:
            picked.append((f"S{n}", s["text"], "인용: " + ", ".join(tags)))
    return picked


def grade_prompt(gold, answer, cards_by_id, slugs):
    shown = [cards_by_id[i] for i in answer["cards_shown"]]
    hidden = [cards_by_id[i] for i in gold.get("gold_hubs") or [] if i not in answer["cards_shown"] and i in cards_by_id]
    evidence = ans.evidence_block(gold)
    names = name_table("\n".join([gold["question"], gold["answer"], evidence, answer["answer"]]),
                       answer["cards_shown"] + [c.id for c in hidden], list(cards_by_id.values()), slugs)
    sentences = "\n".join(f"{sid} ({tag}): {text}" for sid, text, tag in judged_sentences(answer)) or "(없음)"
    return (f"질문: {gold['question']}\n정답: {gold['answer']}\n\n정답 근거 구간:\n{evidence}\n\n"
            f"이름 표:\n{names}\n\n모델에게 보인 카드:\n{link.render_cards(shown) if shown else NO_CARDS}\n\n"
            f"채점용 카드:\n{link.render_cards(hidden, prefix='K') if hidden else NO_CARDS}\n\n"
            f"모델 답:\n{answer['answer']}\n\n모델이 인용한 자료:\n{cited_material(answer)}\n\n판정할 문장:\n{sentences}")


def support_score(answer, grade):
    verdicts = {s.get("id"): ans.SUPPORT_VALUE.get(s.get("support")) for s in grade.get("sentences", [])}
    judged = {sid for sid, _, _ in judged_sentences(answer)}
    values = [(verdicts.get(f"S{n}") or 0.0) if f"S{n}" in judged else 0.0
              for n, s in enumerate(answer["sentences"], start=1) if not s["states_absence"]]
    return mean(values) if values else None


def grade_run(label):
    spec = RUNS[label]
    target = OUT_ROOT / label
    golds = {str(r["qid"]): r for r in arch.read_jsonl(arch.GOLD)}
    cf_golds = {str(r["qid"]): r for r in arch.read_jsonl(LAB / CF_GOLD)}
    cards_by_id = {c.id: c for c in link.read_cards()}
    recall = {qid: r["recall"] for (qid, mode), r in arch.read_detail(LAB / spec.retrieval_dir, spec.variant).items() if mode == BUDGET_MODE}
    answers = [a for a in arch.read_jsonl(target / "answers.jsonl") if a.get("answer") is not None]
    from llm_cache import ClaudeClient, LLMCallFailed
    client = ClaudeClient("opus")
    system = GRADE_PROMPT.read_text(encoding="utf-8")
    slugs = hub_slugs()
    prompts = [grade_prompt(golds[a["source_qid"]], a, cards_by_id, slugs) for a in answers]
    rows = []
    for a, prompt, reply in zip(answers, prompts, client.ask_many(prompts, system=system, tag=f"cf-grade-{label}")):
        gold, cf_gold = golds[a["source_qid"]], cf_golds[a["qid"]]
        row = {"qid": a["qid"], "type": gold["type"], "set": cf_gold.get("set"), "lang": gold.get("lang"),
               "gold_hubs": cf_gold.get("gold_hubs", []), "cards_shown": a["cards_shown"], "cited_cards": a["cited_cards"],
               "retrieval_recall_5000": recall.get(a["source_qid"]), "incomplete": a["incomplete"], "refused_by_code": a["refused_by_code"],
               "truncated": a.get("truncated", False), "answer_seconds": a["llm"]["seconds"], "llm": arch.llm_record(client, prompt, system)}
        grade = None if isinstance(reply, LLMCallFailed) else ans.parse_grade(reply.text)
        if grade is None:
            rows.append({**row, "error": str(reply) if isinstance(reply, LLMCallFailed) else reply.text[:500]})
            continue
        rows.append({**row, "correctness": grade["correctness"], "refused": grade["refused"], "support": support_score(a, grade),
                     "sentence_support": grade.get("sentences", []), "note": grade.get("note", "")})
    arch.write_jsonl(target / "grades.jsonl", rows)
    print(f"{label}: 채점 {sum('correctness' in r for r in rows)}/{len(rows)} · opus {client.usage_line()}", flush=True)


def mean_or_none(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def fmt(value, digits=3):
    return "-" if value is None else f"{value:.{digits}f}"


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def label_metrics(label):
    grades = [g for g in read_rows(OUT_ROOT / label / "grades.jsonl") if "correctness" in g]
    evid = [g for g in grades if g["type"] != "noevidence"]
    buckets = defaultdict(list)
    for g in evid:
        r = g["retrieval_recall_5000"]
        buckets["0" if r == 0 else "1" if r == 1 else "일부"].append(g["correctness"])
    return {"label": label, "graded": len(grades), "all": mean_or_none(g["correctness"] for g in grades),
            "by_set": {s: mean_or_none(g["correctness"] for g in grades if g["set"] == s) for s in ("alias", "fact")},
            "by_type": {t: mean_or_none(g["correctness"] for g in grades if g["type"] == t) for t in sorted({g["type"] for g in grades})},
            "support": mean_or_none(g["support"] for g in grades if not g["refused"]),
            "refused_with_evidence": sum(g["refused"] for g in evid), "noevidence_refused": [sum(g["refused"] for g in grades if g["type"] == "noevidence"),
                                                                                         sum(g["type"] == "noevidence" for g in grades)],
            "card_cited": sum(bool(g["cited_cards"]) for g in grades), "cards_shown": sum(bool(g["cards_shown"]) for g in grades),
            "truncated": sum(g["truncated"] for g in grades), "answer_seconds": mean_or_none(g["answer_seconds"] for g in grades),
            "truncated_correct": mean_or_none(g["correctness"] for g in grades if g["truncated"]),
            "untruncated_correct": mean_or_none(g["correctness"] for g in grades if not g["truncated"]),
            "recall": mean_or_none(g["retrieval_recall_5000"] for g in evid),
            "by_recall": {b: (mean(v), len(v)) for b, v in buckets.items()},
            "opus_cost": sum(g["llm"]["cost_usd"] for g in grades), "correct": {g["qid"]: g["correctness"] for g in grades}}


def sign_test(wins, losses):
    from math import comb
    n = wins + losses
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n)


def table_all():
    labels = [l for l in RUNS if (OUT_ROOT / l / "grades.jsonl").exists()]
    metrics = {l: label_metrics(l) for l in labels}
    lines = ["# 9단계 답 판 요약", "", "정답성은 Opus 0/0.5/1 평균이다(noevidence 는 거절이면 1). 문항은 `scope.txt` 80문항이다.", "",
             "| 판 | 채점 | 전체 | alias | fact | 인용 지지 | 카드 인용한 답 / 카드 받은 답 | 근거 있는데 거절 | 근거 없음 거절 | 검색 5000자 | 답 평균 초 | 끊김 | Opus |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for l, m in metrics.items():
        lines.append(f"| {l}{' (사후)' if l in POST_HOC else ''} | {m['graded']} | {fmt(m['all'])} | {fmt(m['by_set']['alias'])} | {fmt(m['by_set']['fact'])} | {fmt(m['support'])} | "
                     f"{m['card_cited']} / {m['cards_shown']} | {m['refused_with_evidence']} | {m['noevidence_refused'][0]}/{m['noevidence_refused'][1]} | "
                     f"{fmt(m['recall'])} | {fmt(m['answer_seconds'], 1)} | {m['truncated']} | ${m['opus_cost']:.2f} |")
    lines += ["", "끊긴 답(출력이 num_predict 768 에서 끊김). 원인은 주로 \"근거 문서:\" 줄의 문서 번호 되풀이이고, 생성 옵션은 바꾸지 않았다(사용자 결정). 파서는 되풀이된 번호를 한 번으로 센다:", "",
              "| 판 | 끊김 | 끊긴 답 정답성 | 끊기지 않은 답 정답성 |", "|---|---:|---:|---:|"]
    lines += [f"| {l} | {m['truncated']} | {fmt(m['truncated_correct'])} | {fmt(m['untruncated_correct'])} |" for l, m in metrics.items()]
    lines += ["", "검색 재현율(5000자) 묶음별 정답성(문항 수):", "", "| 판 | 0 | 일부 | 1 |", "|---|---:|---:|---:|"]
    for l, m in metrics.items():
        lines.append(f"| {l} | " + " | ".join(f"{m['by_recall'][b][0]:.3f} ({m['by_recall'][b][1]})" if b in m["by_recall"] else "-" for b in ("0", "일부", "1")) + " |")
    lines += ["", "같은 문항 승패:", "", "| 비교 | 이김 | 짐 | 같음 | p |", "|---|---:|---:|---:|---:|"]
    for a, b in COMPARISONS:
        if a in metrics and b in metrics:
            ca, cb = metrics[a]["correct"], metrics[b]["correct"]
            common = ca.keys() & cb.keys()
            win, loss = sum(cb[q] > ca[q] for q in common), sum(cb[q] < ca[q] for q in common)
            lines.append(f"| {b} 대 {a} | {win} | {loss} | {len(common) - win - loss} | {sign_test(win, loss):.2f} |")
    types = sorted({t for m in metrics.values() for t in m["by_type"]})
    lines += ["", "유형별 정답성:", "", "| 판 | " + " | ".join(types) + " |", "|---|" + "---:|" * len(types)]
    for l, m in metrics.items():
        lines.append(f"| {l} | " + " | ".join(fmt(m["by_type"].get(t), 2) for t in types) + " |")
    (OUT_ROOT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="9단계 답 판: qwen3:8b 답, Opus 채점, 요약 표.")
    parser.add_argument("command", choices=["answer", "grade", "table"])
    parser.add_argument("label", nargs="?", choices=list(RUNS))
    args = parser.parse_args()
    if args.command == "table":
        return table_all()
    if not args.label:
        parser.error("answer·grade 는 판 이름이 필요하다")
    configure(RUNS[args.label])
    (answer_run if args.command == "answer" else grade_run)(args.label)


if __name__ == "__main__":
    main()
