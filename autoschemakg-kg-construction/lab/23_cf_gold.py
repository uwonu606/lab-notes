"""9단계 사내화 정답: pub(원래 질문 글, 근거 구간만 옮김)·alias(질문의 공개 이름을 사내 별칭으로)·fact(Opus 가 새로 씀).

    python3 23_cf_gold.py pub-alias          # questions-pub.jsonl, questions-alias.jsonl
    python3 23_cf_gold.py fact               # Opus 가 fact 문항을 쓰고 코드·Opus 가 검사 → questions-fact.jsonl, fact/
    python3 23_cf_gold.py combine            # questions-cf.jsonl(사내화 위치) + questions-orig.jsonl(원래 위치, cf-orig 채점용)
    python3 23_cf_gold.py freeze             # sha256 → gold/SHA256SUMS. 이미 있으면 다르게 다시 쓰지 않는다
    python3 23_cf_gold.py labels             # 고정 정답 옆 표시 labels.jsonl (trace_hint, rewritten). 고정 파일은 쓰지 않는다

출력은 inputs/net-corpus-cf/gold/. 원래 정답(inputs/net-corpus/gold/questions.jsonl)은 읽기만 한다.
qid: pub 은 원래 그대로(S01-sg01), alias 는 뒤에 .alias, fact 는 F01 … 이다.
"""
import argparse
import copy
import hashlib
import importlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

cf = importlib.import_module("23_cf_layer")
gold_build = importlib.import_module("23_gold_build")

LAB = cf.LAB
ORIG_GOLD = cf.CORPUS / "gold/questions.jsonl"
GOLD_DIR = cf.CF_CORPUS / "gold"
FACT_DIR = GOLD_DIR / "fact"
FROZEN = GOLD_DIR / "SHA256SUMS"
GOLD_FILES = ("questions-pub.jsonl", "questions-alias.jsonl", "questions-fact.jsonl", "questions-cf.jsonl", "questions-orig.jsonl")
ALIAS_SUFFIX = ".alias"

FACT_TARGETS = 50
FACT_DOC_CHARS = 9000
FACT_EN_SHARE = 5
FACT_BUDGET_USD = 15.0
FACT_REVISE_COST_GUESS = 0.18


def move_spans(value, mover):
    """{"doc_id","start","end"} 꼴 dict 를 어디에 있든 mover(doc_id, start, end) → (doc_id, start, end) 로 옮긴다."""
    if isinstance(value, list):
        return [move_spans(v, mover) for v in value]
    if isinstance(value, dict):
        if {"doc_id", "start", "end"} <= value.keys():
            doc_id, start, end = mover(value["doc_id"], value["start"], value["end"])
            return {**value, "doc_id": doc_id, "start": start, "end": end}
        return {k: move_spans(v, mover) for k, v in value.items()}
    return value


def span_docs(row):
    spans = [s for item in row.get("evidence", []) for s in item.get("spans", [item])] + list(row.get("near", []))
    return list(dict.fromkeys(s["doc_id"] for s in spans)), spans


def doc_id_pattern(ids):
    return re.compile(r"(?<![A-Za-z0-9-])(" + "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True)) + r")(?![A-Za-z0-9])")


def touch_fields(row, question_hubs, layer):
    """원래 위치의 정답 행에서 hub_touch(질문 글이나 근거·near 문서에 구심점), hub_in_evidence(근거 구간 안)를 센다."""
    docs, spans = span_docs(row)
    doc_hubs = sorted({h for d in docs for h in layer.hubs_in(d)})
    span_hubs = sorted({h for s in spans for h in layer.hubs_in(s["doc_id"], s["start"], s["end"])})
    return {"gold_hubs": question_hubs, "hub_touch": bool(question_hubs or doc_hubs), "evidence_doc_hubs": doc_hubs,
            "evidence_span_hubs": span_hubs}


def pub_row(row, layer, ids):
    question_hubs = list(dict.fromkeys(f.hub for f in layer.rewriter.matcher.find(row["question"])))
    moved = move_spans(copy.deepcopy(row), layer.map_span)
    if "out_of_range_docs" in moved:
        moved["out_of_range_docs"] = [layer.cf_doc_id(d) for d in row["out_of_range_docs"]]
    moved["answer_path"] = ids.sub(lambda m: layer.cf_doc_id(m.group(1)), row["answer_path"])
    return {**moved, "set": "pub", **touch_fields(row, question_hubs, layer)}


def alias_question(row, layer):
    """질문 속 공개 이름을 사내 이름으로. 근거 문서들이 가장 많이 쓴 사내 이름은 피한다(다른 것이 있으면)."""
    docs, _ = span_docs(row)

    def choose(hub):
        used = Counter()
        for d in docs:
            used.update(layer.internal_used(d, hub.id))
        avoid = {used.most_common(1)[0][0]} if used else set()
        return cf.pick_internal(hub, row["qid"] + ALIAS_SUFFIX, avoid)

    return layer.rewriter.replace(row["question"], row["qid"], choose)


def build_pub_alias(layer):
    rows = cf.read_jsonl(ORIG_GOLD)
    ids = doc_id_pattern(layer.to_cf)
    pub, alias = [], []
    for row in rows:
        p = pub_row(row, layer, ids)
        pub.append(p)
        if p["gold_hubs"]:
            question = alias_question(row, layer)
            alias.append({**p, "qid": row["qid"] + ALIAS_SUFFIX, "pub_qid": row["qid"], "set": "alias", "question": question})
    leaks = [(r["qid"], [l.form for l in layer.leaks(r["question"])]) for r in alias if layer.leaks(r["question"])]
    if leaks:
        raise RuntimeError(f"alias 질문에 공개 이름이 남았다: {leaks[:10]}")
    cf.write_jsonl(GOLD_DIR / "questions-pub.jsonl", pub)
    cf.write_jsonl(GOLD_DIR / "questions-alias.jsonl", alias)
    return {"pub": len(pub), "alias": len(alias), "pub_hub_touch": sum(r["hub_touch"] for r in pub),
            "pub_question_hubs": sum(bool(r["gold_hubs"]) for r in pub)}


def check_moved_evidence(layer):
    """옮긴 근거 구간의 글이 원래 구간의 글을 바꾼 것과 같은지 센다(같지 않으면 이름 경계에서 넓어진 것)."""
    orig_docs = cf.read_jsonl(cf.DOCS)
    orig_text = {d["doc_id"]: d["text"] for d in orig_docs}
    cf_text = {d["doc_id"]: d["text"] for d in cf.read_jsonl(cf.CF_DOCS)}
    same = widened = 0
    examples = []
    for orig, moved in zip(cf.read_jsonl(ORIG_GOLD), cf.read_jsonl(GOLD_DIR / "questions-pub.jsonl")):
        for a, b in zip(span_docs(orig)[1], span_docs(moved)[1]):
            before = layer.replace_text(orig_text[a["doc_id"]][a["start"]:a["end"]], a["doc_id"])
            after = cf_text[b["doc_id"]][b["start"]:b["end"]]
            if before == after:
                same += 1
            else:
                widened += 1
                if len(examples) < 5:
                    examples.append({"qid": orig["qid"], "replaced": before[:120], "moved": after[:120]})
            back = layer.orig_span(b["doc_id"], b["start"], b["end"])
            if back != (a["doc_id"], a["start"], a["end"]) and len(examples) < 10:
                examples.append({"qid": orig["qid"], "roundtrip": [a, back]})
    return {"spans_same_text": same, "spans_widened": widened, "examples": examples}


FACT_SYSTEM = ("You write retrieval benchmark questions for an internal knowledge base of a Korean network verification department. "
               "Reply with one JSON object only.")

FACT_PROMPT = """사내 용어집 카드 하나와, 그 카드가 가리키는 대상을 다룬 사내 문서 하나를 준다. 사내 문서에서는 제품·업체·통신사·행사·기관을 사내 이름으로만 쓴다.

검색 평가용 질문 하나를 써라. 이 질문은 카드의 대상을 이름 대신 카드에 박아 둔 사실로 가리킨다. 그래서 카드를 읽은 사람만 어느 대상인지 알고, 문서를 찾아 답할 수 있다.

[카드] id={hub_id}
사내 이름: {names}
박아 둔 사실:
{facts}

[다른 카드의 사내 이름 (id: 이름들)]
{other_names}

[문서] {doc_id} ({doc_kind}) {title}
{doc_text}

규칙:
- 질문 언어: {lang_rule}
- 카드 대상을 가리킬 때는 위 사실 가운데 "kind=identity" 가 아닌 것 하나를 골라 그 내용을 풀어 쓴다. "kind=invented" 사실이 있으면 그것을 먼저 고른다. 고른 사실 원문을 fact_used 에 그대로 옮긴다.
- 질문에 카드 대상의 사내 이름·별칭·코드({forbidden})와 공개 이름을 쓰지 않는다. 공개 정체(제품 종류·만든 곳)를 풀어 써서 짐작하게 하지도 않는다.
- 다른 대상은 위 표의 사내 이름으로만 가리킬 수 있다. 공개 이름(실제 제품·업체·통신사·행사 이름)은 어떤 것도 쓰지 않는다.
- 질문이 묻는 것(증상의 원인, 고친 방법, 설정 값, 버전, 시험 결과 같은 것)은 문서 안에 답이 있어야 한다. 카드 사실만으로 답이 나오면 안 된다.
- 질문은 한 문장이나 두 문장, 실무자가 묻는 말투. 답은 짧게.
- quotes: 답의 근거가 되는 문서 원문을 글자 그대로 1~3개 옮긴다(한 개는 300자 이하). 고치거나 줄이지 않는다.
- gold_hubs: 질문이 가리키는 카드 id(사실로 가리킨 이 카드 + 사내 이름으로 쓴 다른 카드). needs_hubs: 풀이에 카드가 필요한 id(사실로 가리킨 카드).

답 형식: {{"question": "...", "answer": "...", "answer_path": "어떤 사실로 카드를 찾고 문서의 어느 내용에 닿는지 한 문장", "fact_used": "...", "quotes": ["..."], "gold_hubs": ["..."], "needs_hubs": ["..."]}}"""

FACT_REPAIR = "\n\n앞의 답에 문제가 있었다: {problems}\n규칙을 지켜 JSON 하나로 다시 답한다."

FACT_REVISE = """

앞서 쓴 질문:
{previous}

작성 맥락 없는 검토자가 이 질문을 받지 않았다. 판정: support={support}, needs_card={needs_card}, resolves_to={resolves}
검토 의견: {note}

이 의견을 반영해 다시 쓴다. 정답에는 인용한 원문이 모두 뒷받침하는 내용만 넣는다(원문에 없는 세부를 덧붙이지 않는다). 질문 글에 공개 제품을 짐작하게 하는 단서(공개 오류 문구 그대로, 그 제품에만 있는 파일·함수·명령 이름, 공개 정체의 묘사)를 넣지 않는다. 고른 사실이 다른 카드에도 맞으면 이 카드에만 맞는 사실을 고른다. 규칙과 답 형식은 위와 같다."""

FACT_JUDGE_SYSTEM = "You are an independent reviewer of a retrieval benchmark. You have not seen how it was made. Reply with one JSON object only."

FACT_JUDGE_PROMPT = """검색 평가용 질문을 판정한다. 질문은 사내 용어집 카드의 대상을 이름 대신 박아 둔 사실로 가리킨다. 아래 카드 목록 전체와 질문, 정답, 근거 구간을 준다.

[카드 목록 (id | 사내 이름 | 박아 둔 사실)]
{cards}

질문: {question}
정답: {answer}
근거 구간:
{spans}

판정:
- resolves_to: 카드 목록만 보고 질문이 가리키는 카드 id 를 고른다(여럿이면 모두). 사실이 여러 카드에 맞아 하나로 정할 수 없으면 맞는 것을 모두 적는다.
- support: 근거 구간이 정답을 모두 뒷받침하면 "full", 일부만이면 "partial", 아니면 "none".
- needs_card: 카드 없이 질문 글만으로 대상을 알 수 있으면 false(공개 이름이나 공개 정체를 짐작할 단서가 있음).
- note: 한두 문장.

답 형식: {{"resolves_to": ["..."], "support": "full|partial|none", "needs_card": true|false, "note": "..."}}"""


def window(text, ops_starts, limit=FACT_DOC_CHARS):
    if len(text) <= limit:
        return text, 0
    best = max(range(0, len(text) - limit + 1, 500), key=lambda s: sum(s <= p < s + limit for p in ops_starts))
    return text[best:best + limit], best


def fact_targets(layer, hubs, cf_docs, limit=FACT_TARGETS):
    """구심점마다 문서 하나: 그 구심점을 산문(사내 이름)으로 가장 많이 쓴 문서, 이미 고른 문서는 피한다. 문서 수가 많은 구심점부터."""
    prose_count = {h.id: Counter() for h in hubs}
    for orig_id, doc_map in layer.doc_maps.items():
        for op in doc_map.ops:
            if op.text != layer.hubs[op.hub].slug:
                prose_count[op.hub][orig_id] += 1
    order = sorted(hubs, key=lambda h: (-len(prose_count[h.id]), h.id))
    used, targets = set(), []
    for hub in order:
        candidates = [(c, d) for d, c in prose_count[hub.id].items() if d not in used and c >= 2]
        if not candidates:
            continue
        _, doc = max(candidates, key=lambda cd: (cd[0], hashlib.sha256(cd[1].encode()).hexdigest()))
        used.add(doc)
        targets.append((hub.id, doc))
        if len(targets) == limit:
            break
    return targets


def fact_prompt(card, hub, layer, doc, others, lang):
    starts = [op.new_start for op in layer.doc_maps[layer.orig_doc_id(doc["doc_id"])].ops if op.hub == hub.id]
    text, offset = window(doc["text"], starts)
    facts = "\n".join(f"- (kind={f.get('kind', 'corpus')}) {f['text']}" for f in card.get("facts", []))
    lang_rule = "영어로 쓴다." if lang == "en" else "한국어로 쓴다(로그 문구·설정 키 같은 영어 낱말은 섞어도 된다)."
    forbidden = ", ".join([*hub.internal_names, hub.slug])
    prompt = FACT_PROMPT.format(hub_id=hub.id, names=", ".join(hub.internal_names), facts=facts, other_names=others,
                                doc_id=doc["doc_id"], doc_kind=doc["kind"], title=doc["title"], doc_text=text,
                                lang_rule=lang_rule, forbidden=forbidden)
    return prompt, offset


def parse_json(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("JSON 이 없다")
    return json.loads(match.group(0))


def fact_problems(reply, hub, card, layer, docs_by_id, doc_id):
    problems, located = [], []
    question = reply.get("question", "")
    if not question:
        return ["question 이 비었다"], []
    if layer.leaks(question):
        problems.append(f"질문에 공개 이름 {[l.form for l in layer.leaks(question)]} 이 있다")
    named = [n for n in (*hub.internal_names, hub.slug) if n.casefold() in question.casefold()]
    if named:
        problems.append(f"질문에 카드 대상의 사내 이름 {named} 이 있다")
    facts = {f["text"]: f.get("kind", "corpus") for f in card.get("facts", [])}
    if facts.get(reply.get("fact_used")) in (None, "identity"):
        problems.append("fact_used 가 identity 가 아닌 카드 사실의 원문 그대로가 아니다")
    if hub.id not in reply.get("needs_hubs", []) or hub.id not in reply.get("gold_hubs", []):
        problems.append(f"needs_hubs·gold_hubs 에 {hub.id} 가 없다")
    unknown = [h for h in [*reply.get("needs_hubs", []), *reply.get("gold_hubs", [])] if h not in layer.hubs]
    if unknown:
        problems.append(f"없는 카드 id {unknown}")
    for quote in reply.get("quotes", []):
        span = gold_build.locate(docs_by_id, doc_id, quote)
        if span is None:
            problems.append(f"인용을 문서에서 찾지 못했다: {quote[:80]!r}")
        else:
            located.append(span)
    if not reply.get("quotes"):
        problems.append("quotes 가 비었다")
    return problems, located


def read_cards_raw():
    data = json.loads(cf.HUBS.read_text(encoding="utf-8"))
    return {row["id"]: row for row in (data["hubs"] if isinstance(data, dict) else data)}


def write_fact(layer, limit=FACT_TARGETS):
    from llm_cache import ClaudeClient, LLMCallFailed

    FACT_DIR.mkdir(parents=True, exist_ok=True)
    cards = read_cards_raw()
    hubs = list(layer.hubs.values())
    cf_docs = {d["doc_id"]: d for d in cf.read_jsonl(cf.CF_DOCS)}
    targets = fact_targets(layer, hubs, cf_docs, limit)
    others = "\n".join(f"{h.id}: {', '.join(h.internal_names)}" for h in hubs)
    client = ClaudeClient("opus", max_concurrency=5)
    jobs = []
    for n, (hub_id, orig_doc) in enumerate(targets, start=1):
        hub, doc = layer.hubs[hub_id], cf_docs[layer.cf_doc_id(orig_doc)]
        lang = "en" if n % FACT_EN_SHARE == 0 else "ko"
        prompt, offset = fact_prompt(cards[hub_id], hub, layer, doc, "\n".join(l for l in others.splitlines() if not l.startswith(hub_id + ":")), lang)
        jobs.append({"qid": f"F{n:02d}", "hub": hub_id, "doc_id": doc["doc_id"], "lang": lang, "prompt": prompt, "offset": offset})
    replies = client.ask_many([j["prompt"] for j in jobs], system=FACT_SYSTEM, tag="cf-fact")
    drafts = []
    for job, reply in zip(jobs, replies):
        hub, card = layer.hubs[job["hub"]], cards[job["hub"]]
        record = {k: job[k] for k in ("qid", "hub", "doc_id", "lang", "prompt")}
        rounds = []
        prompt = job["prompt"]
        for attempt in range(2):
            if isinstance(reply, LLMCallFailed):
                rounds.append({"error": str(reply)})
                break
            try:
                parsed = parse_json(reply.text)
                problems, located = fact_problems(parsed, hub, card, layer, cf_docs, job["doc_id"])
            except (ValueError, json.JSONDecodeError) as error:
                parsed, problems, located = None, [f"JSON 을 읽지 못했다: {error}"], []
            rounds.append({"reply": reply.text, "problems": problems})
            if not problems:
                record.update(parsed=parsed, located=located)
                break
            if attempt == 0:
                prompt = job["prompt"] + FACT_REPAIR.format(problems="; ".join(problems))
                try:
                    reply = client.ask(prompt, system=FACT_SYSTEM, tag="cf-fact-repair")
                except LLMCallFailed as error:
                    reply = error
        record["rounds"] = rounds
        drafts.append(record)
    return drafts, client


def judge_facts(layer, drafts, client, tag="cf-fact-judge"):
    cards = read_cards_raw()
    listing = "\n".join(f"{cid} | {', '.join(layer.hubs[cid].internal_names)} | "
                        + " / ".join(f["text"] for f in card.get("facts", []) if f.get("kind") != "identity")
                        for cid, card in cards.items())
    cf_text = {d["doc_id"]: d["text"] for d in cf.read_jsonl(cf.CF_DOCS)}
    passed = [d for d in drafts if "parsed" in d]
    prompts = [FACT_JUDGE_PROMPT.format(cards=listing, question=d["parsed"]["question"], answer=d["parsed"]["answer"],
                                        spans="\n".join(f"[{n}] {cf_text[s['doc_id']][s['start']:s['end']]}" for n, s in enumerate(d["located"], 1)))
               for d in passed]
    replies = client.ask_many(prompts, system=FACT_JUDGE_SYSTEM, tag=tag)
    judged = []
    for draft, reply in zip(passed, replies):
        try:
            verdict = parse_json(reply.text)
        except (AttributeError, ValueError, json.JSONDecodeError):
            verdict = {"error": str(reply)[:300]}
        resolved = set(verdict.get("resolves_to", []))
        keep = (verdict.get("support") == "full" and verdict.get("needs_card") is True
                and draft["hub"] in resolved and resolved <= set(draft["parsed"]["gold_hubs"]))
        judged.append({"qid": draft["qid"], "hub": draft["hub"], "verdict": verdict, "keep": keep})
    return judged


def spent(client):
    return sum(s.get("recorded_cost_usd", 0) for s in client.stats.snapshot().values())


def revise_dropped(layer, drafts, judged, client):
    """판정에서 떨어진 문항마다 판정 메모를 붙여 한 번 다시 쓰게 하고, 코드 검사·판정을 다시 한다. 붙은 것만 초안을 바꾼다."""
    cards = read_cards_raw()
    cf_docs = {d["doc_id"]: d for d in cf.read_jsonl(cf.CF_DOCS)}
    dropped = {j["qid"]: j for j in judged if not j["keep"]}
    targets = [d for d in drafts if d["qid"] in dropped and "parsed" in d]
    if spent(client) + len(targets) * FACT_REVISE_COST_GUESS > FACT_BUDGET_USD:
        raise RuntimeError(f"다시 쓰기를 하면 예산 ${FACT_BUDGET_USD} 를 넘는다(지금 ${spent(client):.2f}, {len(targets)}문항)")
    prompts = []
    for d in targets:
        v = dropped[d["qid"]]["verdict"]
        previous = {k: d["parsed"][k] for k in ("question", "answer", "fact_used", "quotes")}
        prompts.append(d["prompt"] + FACT_REVISE.format(previous=json.dumps(previous, ensure_ascii=False), note=v.get("note", ""),
                                                        support=v.get("support"), needs_card=v.get("needs_card"),
                                                        resolves=v.get("resolves_to")))
    replies = client.ask_many(prompts, system=FACT_SYSTEM, tag="cf-fact-revise")
    revised = []
    for d, reply in zip(targets, replies):
        try:
            parsed = parse_json(reply.text)
            problems, located = fact_problems(parsed, layer.hubs[d["hub"]], cards[d["hub"]], layer, cf_docs, d["doc_id"])
        except (AttributeError, ValueError, json.JSONDecodeError) as error:
            parsed, problems, located = None, [f"답을 읽지 못했다: {error}"], []
        d["rounds"].append({"revise_reply": getattr(reply, "text", str(reply)), "problems": problems})
        if not problems:
            revised.append({**d, "parsed": parsed, "located": located})
    rejudged = {j["qid"]: j for j in judge_facts(layer, revised, client, tag="cf-fact-rejudge")}
    for d in drafts:
        j = rejudged.get(d["qid"])
        if j and j["keep"]:
            new = next(r for r in revised if r["qid"] == d["qid"])
            d.update(parsed=new["parsed"], located=new["located"], revised=True)
    return [rejudged.get(j["qid"], j) if not j["keep"] else j for j in judged], len(targets)


def fact_rows(layer, drafts, judged):
    keep = {j["qid"] for j in judged if j["keep"]}
    cf_kind = {d["doc_id"]: d["kind"] for d in cf.read_jsonl(cf.CF_DOCS)}
    rows = []
    for d in drafts:
        if d["qid"] not in keep:
            continue
        p = d["parsed"]
        spans = [{"doc_id": s["doc_id"], "start": s["start"], "end": s["end"]} for s in d["located"]]
        rows.append({"qid": d["qid"], "type": "fact", "lang": d["lang"], "question": p["question"],
                     "answer": p["answer"], "answer_path": f"{d['doc_id']}: {p['answer_path']}",
                     "evidence": [{"label": "근거", "spans": spans}], "doc_kinds": [cf_kind[d["doc_id"]]],
                     "set": "fact", "gold_hubs": list(dict.fromkeys(p["gold_hubs"])), "needs_hubs": list(dict.fromkeys(p["needs_hubs"])),
                     "fact_used": p["fact_used"], "hub_touch": True,
                     "evidence_doc_hubs": layer.hubs_in(layer.orig_doc_id(d["doc_id"])),
                     "evidence_span_hubs": sorted({h for s in spans for h in layer.hubs_in(layer.orig_doc_id(s["doc_id"]),
                                                                                          *layer.orig_span(s["doc_id"], s["start"], s["end"])[1:])})})
    return rows


def build_fact(layer, limit=FACT_TARGETS):
    drafts, client = write_fact(layer, limit)
    first = judge_facts(layer, drafts, client)
    judged, revise_tried = revise_dropped(layer, drafts, first, client)
    cf.write_jsonl(FACT_DIR / "judge.jsonl", [{**j, "first_verdict": f["verdict"]} for j, f in zip(judged, first)])
    cf.write_jsonl(FACT_DIR / "drafts.jsonl", [{k: v for k, v in d.items() if k != "prompt"} for d in drafts])
    rows = fact_rows(layer, drafts, judged)
    cf.write_jsonl(GOLD_DIR / "questions-fact.jsonl", rows)
    usage = client.stats.snapshot()
    cost = sum(s.get("recorded_cost_usd", 0) for s in usage.values())
    report = {"targets": len(drafts), "code_passed": sum("parsed" in d for d in drafts),
              "first_judge_kept": sum(j["keep"] for j in first), "revise_tried": revise_tried,
              "revise_kept": sum(bool(d.get("revised")) for d in drafts), "judge_kept": len(rows),
              "repaired": sum(len(d["rounds"]) > 1 and "parsed" in d for d in drafts),
              "dropped_by_judge": [{"qid": j["qid"], "verdict": j["verdict"]} for j in judged if not j["keep"]],
              "failed_code": [{"qid": d["qid"], "problems": d["rounds"][-1].get("problems") or d["rounds"][-1].get("error")}
                              for d in drafts if "parsed" not in d],
              "cost_usd": round(cost, 3), "usage": client.usage_line()}
    (FACT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if cost > FACT_BUDGET_USD:
        print(f"주의: fact 문항 Opus 비용 ${cost:.2f} 가 예산 ${FACT_BUDGET_USD} 를 넘었다", file=sys.stderr)
    return report


def combine(layer):
    pub = cf.read_jsonl(GOLD_DIR / "questions-pub.jsonl")
    alias = cf.read_jsonl(GOLD_DIR / "questions-alias.jsonl")
    fact = cf.read_jsonl(GOLD_DIR / "questions-fact.jsonl")
    cf.write_jsonl(GOLD_DIR / "questions-cf.jsonl", pub + alias + fact)
    orig = {r["qid"]: r for r in cf.read_jsonl(ORIG_GOLD)}
    orig_rows = [{**orig[r["qid"]], **{k: r[k] for k in ("set", "gold_hubs", "hub_touch", "evidence_doc_hubs", "evidence_span_hubs")}}
                 for r in pub]
    orig_rows += [{**move_spans(copy.deepcopy(r), layer.orig_span),
                   "answer_path": doc_id_pattern(layer.to_orig).sub(lambda m: layer.orig_doc_id(m.group(1)), r["answer_path"])}
                  for r in fact]
    cf.write_jsonl(GOLD_DIR / "questions-orig.jsonl", orig_rows)
    return {"cf": len(pub) + len(alias) + len(fact), "orig": len(orig_rows)}


TRACE_PATTERNS = {"ogs-prefix": r"(?<![A-Za-z0-9])ogs[_-]", "acetcom": r"acetcom", "srs-prefix": r"(?<![A-Za-z0-9])srs[A-Za-z]{2,}"}
LABELS = GOLD_DIR / "labels.jsonl"


def trace_kinds(text):
    return sorted(kind for kind, pattern in TRACE_PATTERNS.items() if re.search(pattern, text, re.I))


def build_labels():
    """고정 정답 옆 표시: trace_hint(근거·near 문서에 남은 정체 흔적 종류), rewritten(fact 를 판정 메모를 본 뒤 고쳐 씀)."""
    cf_text = {d["doc_id"]: d["text"] for d in cf.read_jsonl(cf.CF_DOCS)}
    revised = {d["qid"] for d in cf.read_jsonl(FACT_DIR / "drafts.jsonl") if d.get("revised")}
    rows = []
    for r in cf.read_jsonl(GOLD_DIR / "questions-cf.jsonl"):
        docs, _ = span_docs(r)
        by_doc = {d: trace_kinds(cf_text[d]) for d in docs}
        kinds = sorted({k for ks in by_doc.values() for k in ks})
        rows.append({"qid": r["qid"], "set": r["set"], "trace_hint": bool(kinds), "trace_kinds": kinds,
                     "trace_docs": sorted(d for d, ks in by_doc.items() if ks), "rewritten": r["qid"] in revised})
    cf.write_jsonl(LABELS, rows)
    return {"rows": len(rows), "trace_hint": {f"{k[0]}:{k[1]}": v for k, v in Counter((r["set"], r["trace_hint"]) for r in rows).items()},
            "rewritten": sum(r["rewritten"] for r in rows),
            "docs_with_trace": sum(bool(trace_kinds(t)) for t in cf_text.values()), "labels_sha256": cf.sha256_of(LABELS)}


def freeze():
    lines = [f"{cf.sha256_of(GOLD_DIR / name)}  {name}" for name in GOLD_FILES]
    text = "\n".join(lines) + "\n"
    if FROZEN.exists() and FROZEN.read_text() != text:
        raise RuntimeError(f"{FROZEN} 와 지금 파일이 다르다. 고정한 정답은 바꾸지 않는다")
    FROZEN.write_text(text)
    return text


def main():
    parser = argparse.ArgumentParser(description="9단계 사내화 정답 세 묶음을 만든다.")
    parser.add_argument("command", choices=["pub-alias", "check", "fact", "combine", "freeze", "labels"])
    parser.add_argument("--limit", type=int, default=FACT_TARGETS, help="fact 대상 수 (비용 재기용)")
    args = parser.parse_args()
    if args.command == "freeze":
        print(freeze())
        return
    if args.command == "labels":
        print(json.dumps(build_labels(), ensure_ascii=False, indent=1))
        return
    if FROZEN.exists() and args.command != "check":
        raise RuntimeError(f"정답을 이미 고정했다({FROZEN}). 다시 만들지 않는다")
    layer = cf.Layer.load()
    if args.command == "fact":
        result = build_fact(layer, args.limit)
    else:
        result = {"pub-alias": build_pub_alias, "check": check_moved_evidence, "combine": combine}[args.command](layer)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
