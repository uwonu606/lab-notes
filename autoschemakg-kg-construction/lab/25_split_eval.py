"""쪼개기 결과를 절 정답(gold/*.json)과 견준다. 검색과 상관없는 쪼개기 자체의 품질이다.

    .venv-25/bin/python 25_split_eval.py runs/25-split/haiku/chunks-harness.jsonl --decisions runs/25-split/haiku/decisions.jsonl
    .venv-25/bin/python 25_split_eval.py runs/25-split/base/chunks-mdheader.jsonl

칸 정확도: 문서 종류를 맞힌 문서에서, 공백이 아닌 글자 가운데 청크의 칸이 정답 칸(합친 절은 둘 중 하나)에 드는 비율. 종류를 틀린 문서는 0 이다.
경계: 정답 절의 시작 줄과 청크 경계(칸이나 제목 경로가 바뀌는 청크의 시작)가 같은 줄이면 맞다. 재현율·정밀도를 낸다.
조용한 실패: 검증을 넘어 규칙으로 쪼갰는데(reuse·new·repair) 칸 정확도가 SILENT_BELOW 미만인 문서.
--corpus 는 md/ 를 담은 말뭉치 폴더, --gold-sections 는 25_degrade.py 가 낸 절 위치(gold-sections.jsonl)다.
주면 제목 줄을 찾지 않고 그 위치를 절 정답으로 쓴다(열화 문서는 제목이 문단에 붙어 줄로 찾을 수 없다).
    .venv-25/bin/python 25_split_eval.py runs/25-split-messy/L2/haiku-line/chunks-harness.jsonl --decisions runs/25-split-messy/L2/haiku-line/decisions.jsonl \
        --corpus inputs/parser-corpus-messy/L2 --gold-sections inputs/parser-corpus-messy/L2/gold-sections.jsonl
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/parser-corpus"
SCHEMA_TYPES = {p.stem for p in (LAB / "inputs/parser-schemas").glob("*.yaml")}
SILENT_BELOW = 0.8


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_line(line):
    line = re.sub(r"^\s*#+\s*", "", line.strip())
    line = re.sub(r"^\*\*(.*)\*\*$", r"\1", line.strip())
    return re.sub(r"\s+", " ", line).strip()


def gold_sections(text, gold):
    line_starts, cursor = [], 0
    for line in text.split("\n"):
        line_starts.append((cursor, normalize_line(line)))
        cursor += len(line) + 1
    starts, position = [], 0
    for section in gold["sections"]:
        if section["heading"] is None:
            starts.append((0, set(section["fields"])))
            continue
        wanted = normalize_line(section["heading"])
        while position < len(line_starts) and line_starts[position][1] != wanted:
            position += 1
        if position < len(line_starts):
            starts.append((line_starts[position][0], set(section["fields"])))
            position += 1
    return [(start, starts[i + 1][0] if i + 1 < len(starts) else len(text), fields) for i, (start, fields) in enumerate(starts)]


def line_of(text, offset):
    return text.count("\n", 0, offset)


def evaluate(chunks, decisions, corpus=CORPUS, placed=None):
    by_doc = defaultdict(list)
    for chunk in chunks:
        by_doc[chunk["doc_id"]].append(chunk)
    rows = []
    for doc_id, doc_chunks in sorted(by_doc.items()):
        text = (Path(corpus) / "md" / f"{doc_id}.md").read_text(encoding="utf-8")
        if placed:
            gold = placed[doc_id]
            sections = [(s["start"], s["end"], set(s["fields"])) for s in gold["sections"]]
        else:
            gold = json.loads((CORPUS / "gold" / f"{doc_id}.json").read_text(encoding="utf-8"))
            sections = gold_sections(text, gold)
        decision = decisions.get(doc_id, {})
        predicted_type = decision.get("doc_type")
        row = {"doc_id": doc_id, "doc_type": gold["doc_type"], "drift": gold.get("drift"), "route": decision.get("route", "-"),
               "predicted_type": predicted_type}

        if gold["doc_type"] in SCHEMA_TYPES and predicted_type is not None:
            hit = total = 0
            for chunk in doc_chunks:
                for start, end, fields in sections:
                    lo, hi = max(start, chunk["start"]), min(end, chunk["end"])
                    if lo >= hi:
                        continue
                    chars = sum(1 for ch in text[lo:hi] if not ch.isspace())
                    total += chars
                    hit += chars if predicted_type == gold["doc_type"] and chunk.get("field") in fields else 0
            row["field_accuracy"] = hit / total if total else None

        gold_lines = {line_of(text, start) for start, _, _ in sections[1:]}
        predicted_lines, previous = set(), None
        for chunk in sorted(doc_chunks, key=lambda c: c["start"]):
            key = (chunk.get("field"), tuple(chunk.get("heading_path") or []))
            if previous is not None and key != previous:
                predicted_lines.add(line_of(text, chunk["start"]))
            previous = key
        row["boundary_gold"], row["boundary_pred"], row["boundary_hit"] = len(gold_lines), len(predicted_lines), len(gold_lines & predicted_lines)
        rows.append(row)
    return rows


def summarize(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    print(f"\n{key:16} {'문서':>4} {'칸 정확도':>9} {'경계 재현율':>10} {'경계 정밀도':>10}")
    for name, group in sorted(groups.items(), key=lambda g: str(g[0])):
        accuracies = [r["field_accuracy"] for r in group if r.get("field_accuracy") is not None]
        gold_total, pred_total, hit_total = (sum(r[k] for r in group) for k in ("boundary_gold", "boundary_pred", "boundary_hit"))
        accuracy = f"{sum(accuracies) / len(accuracies):.3f}" if accuracies else "-"
        recall = f"{hit_total / gold_total:.3f}" if gold_total else "-"
        precision = f"{hit_total / pred_total:.3f}" if pred_total else "-"
        print(f"{str(name):16} {len(group):>4} {accuracy:>9} {recall:>10} {precision:>10}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("chunks")
    parser.add_argument("--decisions")
    parser.add_argument("--out", help="문서별 결과 jsonl")
    parser.add_argument("--corpus", default=CORPUS)
    parser.add_argument("--gold-sections")
    args = parser.parse_args()
    decisions = {d["doc_id"]: d for d in read_jsonl(args.decisions)} if args.decisions else {}
    placed = {r["doc_id"]: r for r in read_jsonl(args.gold_sections)} if args.gold_sections else None
    rows = evaluate(read_jsonl(args.chunks), decisions, args.corpus, placed)
    for key in ("doc_type", "drift", "route"):
        summarize(rows, key)
    everything = [{**r, "all": "전체"} for r in rows]
    summarize(everything, "all")
    silent = [r for r in rows if r["route"] in ("reuse", "new", "repair") and r.get("field_accuracy") is not None and r["field_accuracy"] < SILENT_BELOW]
    print(f"\n조용한 실패 {len(silent)}건: " + ", ".join(f"{r['doc_id']}({r['route']}, {r['predicted_type']}, {r['field_accuracy']:.2f})" for r in silent))
    if args.out:
        Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
