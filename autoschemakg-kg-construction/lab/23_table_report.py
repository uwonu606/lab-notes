"""안 4 보고용 분석: 대조 판 대비 승패, 근거 없음 신호, 추출이 정답 근거를 덮는 상한과 누락 표본, 템플릿·fallback 이유별 결과. 정답은 여기서만 읽는다."""
import argparse
import importlib
import json
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

arch = importlib.import_module("23_arch_common")

TABLE_DIR = arch.RUNS / "23-arch-a4-table"
FOCUS_MODES = ("2500자", "5000자")


def gold_rows():
    return {str(r["qid"]): r for r in arch.read_jsonl(arch.GOLD)}


def record_spans_by_doc(table_path):
    db = sqlite3.connect(table_path)
    spans = defaultdict(list)
    for doc_id, start, end in db.execute("SELECT r.doc_id, s.start, s.end FROM cell_spans s JOIN records r USING (record_id)"):
        spans[doc_id].append((doc_id, start, end, ""))
    db.close()
    return spans


def covered(span, pieces):
    doc, start, end = span
    return arch._scorer().overlap_with_union(span, pieces) >= arch._scorer().COVER_SHARE * (end - start)


def extraction_ceiling(gold, spans_by_doc, seed=23, samples=6):
    """정답 근거 묶음 가운데 표의 어떤 칸 발췌라도 50% 이상 덮는 묶음의 비율(유형별), 그리고 못 덮은 묶음 표본."""
    by_type, misses = defaultdict(lambda: [0, 0]), defaultdict(list)
    for qid, row in gold.items():
        for item in row.get("evidence") or []:
            spans = [(s["doc_id"], s["start"], s["end"]) for s in item.get("spans", [item])]
            hit = any(covered(s, spans_by_doc.get(s[0], [])) for s in spans)
            by_type[row["type"]][0] += hit
            by_type[row["type"]][1] += 1
            if not hit:
                misses[row["type"]].append((qid, spans[0]))
    rng = random.Random(seed)
    picked = [m for t in ("aggregation", "temporal", "single") for m in rng.sample(misses[t], min(2, len(misses[t])))][:samples]
    return by_type, picked


def no_evidence_table(trace_rows, gold):
    counts = Counter()
    for t in trace_rows:
        is_none = gold[t["qid"]]["type"] == "noevidence"
        counts[("noevidence" if is_none else "answerable", bool(t.get("no_evidence_signal")))] += 1
    return counts


def by_reason(trace_rows, detail, gold, mode):
    rows = defaultdict(list)
    for t in trace_rows:
        if gold[t["qid"]]["type"] == "noevidence":
            continue
        rows[t.get("fallback_reason") or "table_only"].append(detail[t["qid"], mode]["recall"])
    return {k: (len(v), mean(v)) for k, v in rows.items()}


def by_template(trace_rows, detail, gold, mode):
    rows = defaultdict(list)
    for t in trace_rows:
        if gold[t["qid"]]["type"] == "noevidence":
            continue
        template = (t.get("parsed") or {}).get("template", "슬롯 실패")
        rows[template].append(detail[t["qid"], mode]["recall"])
    return {k: (len(v), mean(v)) for k, v in rows.items()}


def reason_by_type(trace_rows, gold):
    table = defaultdict(Counter)
    for t in trace_rows:
        table[gold[t["qid"]]["type"]][t.get("fallback_reason") or "table_only"] += 1
    return table


def main():
    parser = argparse.ArgumentParser(description="안 4 판 하나의 보고용 표를 markdown 으로 낸다")
    parser.add_argument("run_dir")
    parser.add_argument("variant")
    parser.add_argument("--control-dir", default=str(arch.RUNS / "23-arch-a4-table-records-dense"))
    parser.add_argument("--control-variant", default="a4-table-records-dense")
    parser.add_argument("--table", default=str(TABLE_DIR / "table.sqlite"))
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    gold = gold_rows()
    traces = [t for t in arch.read_jsonl(run_dir / "trace.jsonl") if t["variant"] == args.variant]
    detail = arch.read_detail(run_dir, args.variant)

    print(f"### {args.variant} 대 대조 판 `{args.control_variant}` 문항 승패\n")
    print(arch.compare_table(run_dir, args.variant, Path(args.control_dir), args.control_variant))

    print("\n### fallback 이유 × 유형 (문항 수)\n")
    table = reason_by_type(traces, gold)
    reasons = sorted({r for c in table.values() for r in c})
    print("| 유형 | " + " | ".join(reasons) + " |\n|---|" + "---|" * len(reasons))
    for t in sorted(table):
        print(f"| {t} | " + " | ".join(str(table[t][r]) for r in reasons) + " |")

    for mode in FOCUS_MODES:
        print(f"\n### {mode} 재현율: fallback 이유별 · 템플릿별 (근거 있는 문항)\n")
        print("| 묶음 | 문항 | 재현율 |\n|---|---|---|")
        for k, (n, r) in sorted(by_reason(traces, detail, gold, mode).items()):
            print(f"| 이유 {k} | {n} | {r:.3f} |")
        for k, (n, r) in sorted(by_template(traces, detail, gold, mode).items()):
            print(f"| 템플릿 {k} | {n} | {r:.3f} |")

    counts = no_evidence_table(traces, gold)
    print("\n### 근거 없음 신호 (슬롯을 채워 실행했고 0행)\n")
    print("| 문항 | 신호 켜짐 | 신호 꺼짐 |\n|---|---|---|")
    for kind in ("noevidence", "answerable"):
        print(f"| {kind} | {counts[kind, True]} | {counts[kind, False]} |")

    ceiling, misses = extraction_ceiling(gold, record_spans_by_doc(args.table))
    print("\n### 표가 정답 근거를 덮는 상한 (칸 발췌 전체의 합집합이 근거 묶음을 50% 이상 덮음)\n")
    print("| 유형 | 덮은 묶음 / 전체 |\n|---|---|")
    for t, (hit, total) in sorted(ceiling.items()):
        if total:
            print(f"| {t} | {hit}/{total} ({hit / total:.3f}) |")
    total_hit, total_all = sum(v[0] for v in ceiling.values()), sum(v[1] for v in ceiling.values())
    print(f"| 전체 | {total_hit}/{total_all} ({total_hit / total_all:.3f}) |")
    print("\n### 추출 누락 표본\n")
    for qid, (doc_id, start, end) in misses:
        text = arch.span_text(doc_id, start, end).replace("\n", " ")[:220]
        print(f"- `{qid}` `{doc_id}` {start}-{end}: \"{text}\"")


if __name__ == "__main__":
    main()
