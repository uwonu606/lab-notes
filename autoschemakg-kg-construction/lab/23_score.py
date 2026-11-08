"""검색 단위 종류와 상관없이 근거 구간 덮기로 채점한다.

검색 결과 jsonl 한 줄: {"qid", "variant", "units": [{"doc_id", "start", "end", "score", "path"}, ...]} (순위 순).
  start/end 는 docs.jsonl 의 text 기준 문자 위치다. path 는 단계를 ">" 로 잇고 단계마다 "<종류>" 또는 "<종류>=<세부>" 다.
  경로 집계는 첫 단계 종류, 마지막 단계 종류, unit 단계의 세부(unit=claim → claim) 셋으로 낸다.
정답 jsonl 한 줄: {"qid", "type"?, "evidence": [근거 묶음, ...]}.
  근거 묶음은 {"label"?, "spans": [{"doc_id", "start", "end"}, ...]} 이고, 묶음 안 구간 하나라도 덮이면 그 묶음을 찾은 것이다.
  {"doc_id", "start", "end"} 하나만 써도 구간 하나짜리 묶음으로 읽는다.
덮기: 가져온 단위들(겹치면 합집합)이 구간 길이의 50% 이상과 겹치면 덮은 것이다.
"""
import argparse
import json
from collections import Counter
from math import comb
from pathlib import Path

from statistics import mean

TOP_K = 5
CHAR_BUDGETS = (1000, 2500, 5000)
COVER_SHARE = 0.5


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def read_gold(path):
    gold = {}
    for row in read_jsonl(path):
        items = []
        for number, item in enumerate(row.get("evidence") or []):
            spans = item.get("spans", [item])
            items.append({"label": item.get("label", str(number)), "spans": [(s["doc_id"], s["start"], s["end"]) for s in spans]})
        gold[str(row["qid"])] = {"type": row.get("type"), "items": items}
    return gold


def taken(units, budget=None):
    pieces, left = [], budget
    for unit in units:
        if left is not None and left <= 0:
            break
        length = unit["end"] - unit["start"]
        end = unit["end"] if left is None else unit["start"] + min(length, left)
        pieces.append((unit["doc_id"], unit["start"], end, unit.get("path", "")))
        if left is not None:
            left -= length
    return pieces


def overlap_with_union(span, pieces):
    doc, start, end = span
    intervals = sorted((max(s, start), min(e, end)) for d, s, e, _ in pieces if d == doc and min(e, end) > max(s, start))
    covered, reach = 0, start
    for s, e in intervals:
        if e > reach:
            covered += e - max(s, reach)
            reach = e
    return covered


def judge(pieces, items):
    found, missed = [], []
    for item in items:
        hit_spans = [span for span in item["spans"] if overlap_with_union(span, pieces) >= COVER_SHARE * (span[2] - span[1])]
        if not hit_spans:
            missed.append(item["label"])
            continue
        paths = sorted({p for d, s, e, p in pieces for doc, start, end in hit_spans if d == doc and min(e, end) > max(s, start)})
        found.append({"label": item["label"], "paths": paths})
    return {"recall": len(found) / len(items), "all": not missed, "found": found, "missed": missed}


def modes(top_k):
    return [(f"@{top_k}", lambda units: taken(units[:top_k]))] + [(f"{b}자", lambda units, b=b: taken(units, b)) for b in CHAR_BUDGETS]


def stages(path):
    return [stage.split("=", 1) + [""] * ("=" not in stage) for stage in path.split(">")]


PATH_VIEWS = {
    "첫 단계": lambda path: stages(path)[0][0],
    "마지막 단계": lambda path: stages(path)[-1][0],
    "unit 종류": lambda path: next((detail for kind, detail in stages(path) if kind == "unit"), "(표기 없음)"),
}


def sign_test(wins, losses):
    n = wins + losses
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n)


def main():
    parser = argparse.ArgumentParser(description="검색 결과를 근거 구간 덮기로 채점한다 (단위 종류 무관).")
    parser.add_argument("retrieval", help="{qid, variant, units} jsonl")
    parser.add_argument("gold", help="{qid, evidence} jsonl")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--baseline", default="dense")
    parser.add_argument("--detail", help="질문·변형·방식마다 찾은 근거와 그 path 를 적을 jsonl")
    args = parser.parse_args()

    all_gold = read_gold(args.gold)
    gold = {q: g for q, g in all_gold.items() if g["items"]}
    no_evidence = Counter(g["type"] or "(유형 없음)" for q, g in all_gold.items() if not g["items"])
    results = [r for r in read_jsonl(args.retrieval) if str(r["qid"]) in gold]
    variants = list(dict.fromkeys(r["variant"] for r in results))
    mode_list = modes(args.top_k)
    scored = {v: {} for v in variants}
    for r in results:
        scored[r["variant"]][str(r["qid"])] = {name: judge(cut(r["units"]), gold[str(r["qid"])]["items"]) for name, cut in mode_list}

    types = sorted({g["type"] for g in gold.values() if g["type"]})
    names = [name for name, _ in mode_list]
    print(f"=== 정답 질문 {len(all_gold)}개 중 근거가 있는 {len(gold)}개를 채점한다 · 근거 묶음 {sum(len(g['items']) for g in gold.values())}개 · "
          f"근거 없음이라 뺀 질문 {sum(no_evidence.values())}개 {dict(no_evidence)}")
    print(f"=== 칸은 근거 묶음 재현율 평균, 괄호는 묶음을 다 찾은 질문 수")
    print(f"=== 덮기: 가져온 단위의 합집합이 구간 하나의 {int(COVER_SHARE * 100)}% 이상. @{args.top_k} 는 상위 {args.top_k}단위, N자 는 순위대로 N자까지 (마지막 단위는 앞에서 자름)")

    def table_row(label, qids, rows):
        cells = " ".join(f"{mean([rows[q][n]['recall'] for q in qids]):.3f} ({sum(rows[q][n]['all'] for q in qids):>2})" if qids else f"{'-':>11}" for n in names)
        return f"{label:22} {cells}   {len(qids):>6}"

    print(f"\n{'변형':22} " + " ".join(f"{n:>11}" for n in names) + "   질문 수")
    for v in variants:
        print(table_row(v, list(scored[v]), scored[v]))
    if types:
        print(f"\n=== 유형별")
        for t in types:
            print(f"--- {t}")
            for v in variants:
                print(table_row(f"  {v}", [q for q in scored[v] if gold[q]["type"] == t], scored[v]))

    for view, kind_of in PATH_VIEWS.items():
        print(f"\n=== 찾은 근거 묶음을 가져온 단위의 path — {view} (@{args.top_k}, {names[1]}). path 는 단계를 > 로 잇고 단계마다 종류=세부. 한 묶음을 여러 종류가 덮으면 종류마다 센다")
        for v in variants:
            for n in names[:2]:
                kinds = Counter(k for q in scored[v] for f in scored[v][q][n]["found"] for k in {kind_of(x) for x in f["paths"]})
                print(f"  {v:22} {n:>6}  " + " · ".join(f"{k} {c}" for k, c in kinds.most_common()))

    if args.baseline in scored:
        for n in names[:2]:
            print(f"\n=== {args.baseline} 와 {n} 재현율이 갈린 질문 (+ 는 변형이 더 찾음). p 는 갈린 질문만 본 양측 부호 검정")
            base = scored[args.baseline]
            for v in variants:
                if v == args.baseline:
                    continue
                diffs = {q: scored[v][q][n]["recall"] - base[q][n]["recall"] for q in base if q in scored[v]}
                diffs = {q: d for q, d in diffs.items() if d}
                wins, losses = sum(d > 0 for d in diffs.values()), sum(d < 0 for d in diffs.values())
                print(f"  {v:22} 이김 {wins} · 짐 {losses} · p={sign_test(wins, losses):.2f}   " + " ".join(f"{q}{d:+.2g}" for q, d in sorted(diffs.items())))

    if args.detail:
        Path(args.detail).write_text("".join(json.dumps({"qid": q, "variant": v, "mode": n, **scored[v][q][n]}, ensure_ascii=False) + "\n"
                                             for v in variants for q in scored[v] for n in names))


if __name__ == "__main__":
    main()
