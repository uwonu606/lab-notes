"""정답 초안(원문 인용)을 문자 위치로 고정하고 유형별 조건을 코드로 검사해 정답 jsonl 을 낸다.

초안 한 줄 (gold/drafts/*.jsonl):
  {"draft_id", "type", "question", "answer", "answer_path",
   "evidence": [{"label", "quotes": [{"doc_id", "quote"}]}],
   diffterm:   "absent_terms": [근거 구간에 글자로 없어야 할 질문 용어], "evidence_terms": [근거 쪽 표현]
   temporal:   "time_range": {"from": "YYYY[-MM[-DD]]", "to": "..."}, "out_of_range_docs": [같은 주제, 범위 밖 doc_id]
   multihop:   "bridge": 다리 종류 (명시 링크 | 같은 대상 | 같은 장비)
   noevidence: "near": [{"doc_id", "quote"}], "absent_check": [[한 문서에 함께 나오면 안 되는 낱말, ...], ...]
   aggregation: 근거는 23_gold_pool.py 판정 결과(--agg)에서 온다. 초안의 evidence 는 씨앗일 뿐 정답에 넣지 않는다.
                answer 는 판정 결과에서 만든 것을 쓰고, "answer_source": "draft" 면 초안의 answer 를 쓴다}
인용은 docs 의 text 에서 글자 그대로 찾는다. 없으면 공백 연속을 하나로 본 비교로 한 번 더 찾고, 그래도 없으면 버린다.
"""
import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

TYPES = ("single", "multihop", "aggregation", "diffterm", "temporal", "overview", "noevidence")
HANGUL = re.compile(r"[가-힣]")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def read_docs(paths):
    docs = {}
    for path in paths:
        for doc in read_jsonl(path):
            docs[doc["doc_id"]] = doc
    return docs


def squeeze_with_map(text):
    kept, origin, in_space = [], [], False
    for position, char in enumerate(text):
        if char.isspace():
            if not in_space:
                kept.append(" ")
                origin.append(position)
            in_space = True
        else:
            kept.append(char)
            origin.append(position)
            in_space = False
    return "".join(kept), origin


def locate(docs, doc_id, quote):
    doc = docs.get(doc_id)
    quote = quote.strip()
    if doc is None or not quote:
        return None
    text = doc["text"]
    start = text.find(quote)
    if start >= 0:
        return {"doc_id": doc_id, "start": start, "end": start + len(quote), "match": "exact", "occurrences": text.count(quote)}
    squeezed, origin = squeeze_with_map(text)
    target = re.sub(r"\s+", " ", quote)
    at = squeezed.find(target)
    if at < 0:
        return None
    last = origin[at + len(target) - 1] + 1
    return {"doc_id": doc_id, "start": origin[at], "end": last, "match": "whitespace", "occurrences": squeezed.count(target)}


def question_lang(question):
    return "ko" if len(HANGUL.findall(question)) >= 2 else "en"


def in_range(date, time_range):
    lower = time_range.get("from", "0000")
    upper = time_range.get("to", "9999")
    return lower <= date[:len(lower)] and date[:len(upper)] <= upper


def locate_groups(docs, groups, problems):
    located = []
    for group in groups:
        spans = []
        for quote in group.get("quotes", []):
            span = locate(docs, quote["doc_id"], quote["quote"])
            if span is None:
                problems.append(f"인용 못 찾음 {quote['doc_id']}: {quote['quote'][:80]!r}")
            else:
                spans.append(span)
        located.append({"label": group.get("label", str(len(located))), "spans": spans})
    return located


def span_text(docs, span):
    return docs[span["doc_id"]]["text"][span["start"]:span["end"]]


def check_type(draft, evidence, near, docs, problems):
    kind = draft["type"]
    spans = [s for g in evidence for s in g["spans"]]
    if kind != "noevidence" and kind != "aggregation" and any(not g["spans"] for g in evidence):
        problems.append("근거 묶음 중 구간이 하나도 안 남은 것이 있다")
    if kind not in ("noevidence",) and not spans:
        problems.append("근거 구간이 없다")
    if kind == "multihop" and len({s["doc_id"] for s in spans}) < 2:
        problems.append("multihop 인데 근거 문서가 둘 미만")
    if kind == "overview" and (len(evidence) < 3 or len({s["doc_id"] for s in spans}) < 2):
        problems.append("overview 인데 요점 3개 미만이거나 문서가 둘 미만")
    if kind == "diffterm":
        terms = draft.get("absent_terms") or []
        if not terms:
            problems.append("diffterm 인데 absent_terms 가 없다")
        if not any(t.casefold() in draft["question"].casefold() for t in terms):
            problems.append("absent_terms 가운데 질문에 나오는 것이 없다")
        for span in spans:
            body = span_text(docs, span).casefold()
            leaked = [t for t in terms if t.casefold() in body]
            if leaked:
                problems.append(f"diffterm 근거 구간 {span['doc_id']} 에 질문 용어가 있다: {leaked}")
    if kind == "temporal":
        time_range = draft.get("time_range") or {}
        if not time_range:
            problems.append("temporal 인데 time_range 가 없다")
        for doc_id in {s["doc_id"] for s in spans}:
            if not in_range(docs[doc_id]["date"], time_range):
                problems.append(f"근거 문서 {doc_id} ({docs[doc_id]['date'][:10]}) 가 범위 밖")
        outside = [d for d in draft.get("out_of_range_docs", []) if d in docs and not in_range(docs[d]["date"], time_range)]
        if not outside:
            problems.append("범위 밖 같은 주제 문서(out_of_range_docs)가 확인되지 않는다")
    if kind == "noevidence":
        if spans:
            problems.append("noevidence 인데 evidence 가 있다")
        if not near:
            problems.append("noevidence 인데 near 구간이 없다")
        for words in draft.get("absent_check", []):
            hits = [d for d, doc in docs.items() if all(w.casefold() in (doc["title"] + "\n" + doc["text"]).casefold() for w in words)]
            if hits:
                problems.append(f"absent_check {words} 가 함께 나오는 문서: {hits[:5]}")
        if not draft.get("absent_check"):
            problems.append("noevidence 인데 absent_check 가 없다")


def public_span(span):
    return {"doc_id": span["doc_id"], "start": span["start"], "end": span["end"]}


def build(draft, docs, aggregated):
    problems = []
    if draft.get("type") not in TYPES:
        return None, [f"모르는 유형 {draft.get('type')}"]
    if draft["type"] == "aggregation":
        result = aggregated.get(draft["draft_id"])
        if result is None:
            return None, ["집계 판정 결과가 없다 (23_gold_pool.py 를 먼저 돌린다)"]
        evidence = [{"label": i["label"], "spans": [s for s in (locate(docs, q["doc_id"], q["quote"]) for q in i["quotes"]) if s]}
                    for i in result["instances"]]
        lost = [g["label"] for g in evidence if not g["spans"]]
        if lost:
            problems.append(f"인용을 못 찾아 뺀 instance: {lost}")
        evidence = [g for g in evidence if g["spans"]]
    else:
        evidence = locate_groups(docs, draft.get("evidence", []), problems)
    near = [s for s in (locate(docs, q["doc_id"], q["quote"]) for q in draft.get("near", [])) if s]
    if len(near) < len(draft.get("near", [])):
        problems.append("near 인용 일부를 못 찾았다")
    hard = []
    check_type(draft, evidence, near, docs, hard)
    if hard:
        return None, problems + hard
    row = {"qid": draft["draft_id"], "type": draft["type"], "lang": question_lang(draft["question"]), "question": draft["question"],
           "answer": aggregated[draft["draft_id"]]["answer"] if draft["type"] == "aggregation" and draft.get("answer_source") != "draft" else draft["answer"],
           "answer_path": draft["answer_path"],
           "evidence": [{"label": g["label"], "spans": [public_span(s) for s in g["spans"]]} for g in evidence],
           "doc_kinds": sorted({docs[s["doc_id"]]["kind"] for g in evidence for s in g["spans"]} | {docs[s["doc_id"]]["kind"] for s in near})}
    for key in ("absent_terms", "evidence_terms", "time_range", "out_of_range_docs", "bridge", "criterion"):
        if key in draft:
            row[key] = draft[key]
    if near:
        row["near"] = [public_span(s) for s in near]
    if draft["type"] == "aggregation":
        row["instance_count"] = len(evidence)
    return row, problems


def main():
    parser = argparse.ArgumentParser(description="정답 초안의 인용을 문자 위치로 고정하고 유형 조건을 검사한다.")
    parser.add_argument("drafts", nargs="+", help="초안 jsonl (여럿)")
    parser.add_argument("--docs", nargs="+", required=True, help="{doc_id, text, date, kind, title} jsonl (여럿)")
    parser.add_argument("--agg", help="23_gold_pool.py 가 낸 집계 판정 jsonl")
    parser.add_argument("--out", help="정답 jsonl. 없으면 검사만 한다")
    parser.add_argument("--report", help="버린 것과 경고를 적을 json")
    parser.add_argument("--cap", nargs="*", default=[], help="유형=최대 문항 수 (예: single=40). 넘는 것은 seed 로 뽑아 --reserve 로 보낸다")
    parser.add_argument("--reserve", help="--cap 으로 뺀 문항을 적을 jsonl")
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    docs = read_docs(args.docs)
    aggregated = {r["draft_id"]: r for r in read_jsonl(args.agg)} if args.agg else {}
    rows, report = [], {}
    drafts = [d for path in args.drafts for d in read_jsonl(path)]
    duplicated = [d for d, n in Counter(d["draft_id"] for d in drafts).items() if n > 1]
    if duplicated:
        raise SystemExit(f"draft_id 가 겹친다: {duplicated}")
    for draft in drafts:
        if draft["type"] == "aggregation" and not args.agg:
            continue
        row, problems = build(draft, docs, aggregated)
        if problems:
            report[draft["draft_id"]] = {"kept": row is not None, "problems": problems}
            print(f"{'경고' if row else '버림'} {draft['draft_id']} ({draft['type']}): " + " | ".join(problems))
        if row:
            rows.append(row)
    reserve = []
    for kind, cap in (c.split("=") for c in args.cap):
        of_kind = [r for r in rows if r["type"] == kind]
        moved = {r["qid"] for r in random.Random(args.seed).sample(of_kind, max(0, len(of_kind) - int(cap)))}
        reserve += [r for r in rows if r["qid"] in moved]
        rows = [r for r in rows if r["qid"] not in moved]
    if reserve:
        print(f"예비로 뺀 문항 {len(reserve)}: {sorted(r['qid'] for r in reserve)}")
        Path(args.reserve).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reserve))
    kinds = Counter(r["type"] for r in rows)
    print(f"남은 질문 {len(rows)}/{len(drafts)} · " + " · ".join(f"{t} {kinds[t]}" for t in TYPES)
          + f" · 한국어 {sum(r['lang'] == 'ko' for r in rows)}")
    if args.out:
        Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    if args.report:
        Path(args.report).write_text(json.dumps({"stats": stats(rows, docs), "problems": report}, ensure_ascii=False, indent=1))


def stats(rows, docs):
    def evidence_docs(row):
        return {s["doc_id"] for g in row["evidence"] for s in g["spans"]} | {s["doc_id"] for s in row.get("near", [])}
    return {
        "questions": len(rows),
        "by_type": {t: {"questions": sum(r["type"] == t for r in rows), "ko": sum(r["type"] == t and r["lang"] == "ko" for r in rows),
                        "evidence_groups": sum(len(r["evidence"]) for r in rows if r["type"] == t),
                        "evidence_spans": sum(len(g["spans"]) for r in rows if r["type"] == t for g in r["evidence"])} for t in TYPES},
        "ko_share": round(sum(r["lang"] == "ko" for r in rows) / len(rows), 3),
        "questions_touching_kind": dict(Counter(k for r in rows for k in r["doc_kinds"]).most_common()),
        "evidence_docs_by_kind": dict(Counter(docs[d]["kind"] for d in {d for r in rows for d in evidence_docs(r)}).most_common()),
        "evidence_docs_by_lang": dict(Counter(docs[d]["lang"] for d in {d for r in rows for d in evidence_docs(r)}).most_common()),
        "distinct_evidence_docs": len({d for r in rows for d in evidence_docs(r)}),
    }


if __name__ == "__main__":
    main()
