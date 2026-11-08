"""재판정 뒤 고침(patch)을 정답 초안에 반영한다.

patch 한 줄: {"qid", "action": "trim"|"widen"|"keep", "answer"?, "evidence"?, "reason"}
  trim  은 answer 만 바꾼다(검색 채점에 영향 없음). widen 은 evidence 를 통째로 바꾼다(초안 형식, quotes 는 원문 그대로).
  aggregation 의 answer 를 바꾸면 "answer_source": "draft" 를 붙여 판정 결과의 answer 대신 쓰게 한다.
  keep 은 고치지 않고 이유만 남긴다.
초안마다 revisions 에 날짜·action·reason 을 덧붙인다.

    python3 23_gold_patch.py <drafts_dir> <patch.jsonl...> --note "2026-10-13 전수 재판정 1회차"
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="재판정 고침을 정답 초안에 반영한다.")
    parser.add_argument("drafts_dir")
    parser.add_argument("patches", nargs="+")
    parser.add_argument("--note", required=True)
    args = parser.parse_args()

    patches = {}
    for path in args.patches:
        for line in Path(path).read_text().splitlines():
            if line.strip():
                patch = json.loads(line)
                patches[patch["qid"]] = patch
    applied = set()
    for path in sorted(Path(args.drafts_dir).glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        for row in rows:
            patch = patches.get(row["draft_id"])
            if not patch:
                continue
            if patch["action"] in ("trim", "widen") and "answer" in patch:
                row["answer"] = patch["answer"]
                if row["type"] == "aggregation":
                    row["answer_source"] = "draft"
            if patch["action"] == "widen":
                row["evidence"] = patch["evidence"]
            row.setdefault("revisions", []).append(f"{args.note}: {patch['action']} — {patch['reason']}")
            applied.add(row["draft_id"])
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    missing = sorted(set(patches) - applied)
    print(f"반영 {len(applied)} · 초안에 없는 qid {missing}")


if __name__ == "__main__":
    main()
