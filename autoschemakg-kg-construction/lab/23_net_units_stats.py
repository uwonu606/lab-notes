import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

LAB = Path(__file__).parent
UNITS = LAB / "runs/23-net-units"
KINDS = ("fixed", "section", "claim", "doc")


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def quantiles(values):
    ordered = sorted(values)
    pick = lambda q: ordered[round(q * (len(ordered) - 1))]
    return [ordered[0], pick(0.1), pick(0.5), pick(0.9), ordered[-1], round(sum(ordered) / len(ordered))] if ordered else [0] * 6


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows])


def main():
    parser = argparse.ArgumentParser(description="runs/23-net-units 의 단위 수·길이 분포·LLM 비용을 markdown 표로 낸다.")
    parser.add_argument("--units", default=str(UNITS))
    parser.add_argument("--hr2-report", default=str(LAB / "runs/23-net-hr2/idx/index-report.json"))
    args = parser.parse_args()
    units = Path(args.units)

    rows = {kind: read(units / f"{kind}.jsonl") for kind in KINDS}
    doc_kind = {r["doc_id"]: r["doc_kind"] for r in rows["doc"]}
    print("## 단위 수와 길이 (글자)\n")
    print(table(["단위", "수", "문서당", "최소", "p10", "중앙", "p90", "최대", "평균"],
                [[k, len(v), round(len(v) / max(len(rows["doc"]), 1), 1), *quantiles([r["end"] - r["start"] for r in v])] for k, v in rows.items()]))

    print("\n## 문서 종류별 단위 수\n")
    kinds = sorted(Counter(doc_kind.values()), key=lambda k: -Counter(doc_kind.values())[k])
    print(table(["단위"] + kinds, [[k] + [sum(doc_kind[r["doc_id"]] == dk for r in v) for dk in kinds] for k, v in rows.items()]))

    print("\n## 절 종류\n")
    by_type = defaultdict(list)
    for r in rows["section"]:
        by_type[(doc_kind[r["doc_id"]] == "report", r["section_type"])].append(r["end"] - r["start"])
    claims_of = Counter(r["parent_section"] for r in rows["claim"])
    claim_rows = []
    for (is_report, kind), lengths in sorted(by_type.items(), key=lambda x: (x[0][0], -len(x[1]))):
        sections = [r for r in rows["section"] if (doc_kind[r["doc_id"]] == "report") == is_report and r["section_type"] == kind]
        claim_rows.append(["보고서" if is_report else "이슈·토론·메일·블로그", kind, len(lengths), quantiles(lengths)[2],
                           round(sum(claims_of[s["unit_id"]] for s in sections) / len(sections), 2)])
    print(table(["문서", "절 종류", "수", "중앙 길이", "절당 claim"], claim_rows))

    trees = read(units / "section-tree.jsonl")
    if trees:
        blocks = [len(t["blocks"]) for t in trees]
        print(f"\n트리: 문서 {len(trees)}개, 덩어리 {sum(blocks)}개 (문서당 중앙 {quantiles(blocks)[2]}), 코드가 자른 덩어리 {sum(t['code_blocks'] for t in trees)}개")

    covered = defaultdict(set)
    for r in rows["claim"]:
        covered[r["doc_id"]].update(range(r["start"], r["end"]))
    total = sum(r["end"] - r["start"] for r in rows["doc"])
    print(f"claim 이 덮는 원문 글자: {sum(map(len, covered.values()))} / {total} ({sum(map(len, covered.values())) / max(total, 1):.1%}), claim 0개 절 {sum(claims_of[s['unit_id']] == 0 for s in rows['section'])}/{len(rows['section'])}")

    stats_path = units / "build-stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())
        print("\n## LLM 호출 (Haiku, 처음 부를 때의 값)\n")
        print(table(["tag", "서로 다른 프롬프트", "비용 $", "호출 초 합"],
                    [[tag, int(s.get("unique_prompts", 0)), round(s.get("recorded_cost_usd", 0), 3), round(s.get("recorded_seconds", 0))]
                     for tag, s in stats["llm_by_tag"].items()]))
        print("\n## 실패와 보정 횟수\n")
        print(table(["단계", "항목", "수"], [[stage, k, v] for stage, counts in stats["counts_by_stage"].items() for k, v in sorted(counts.items())]))

    embed_path = units / "idx/embed-report.json"
    if embed_path.exists():
        print("\n## 임베딩\n")
        report = json.loads(embed_path.read_text())
        print(table(["단위", "수", "캐시", "새로", "초", "잠금 대기 초"],
                    [[k, s["units"], s["cached_texts"], s["requested_texts"], s["seconds"], s["lock_wait_seconds"]] for k, s in report.items()]))

    hr2 = Path(args.hr2_report)
    if hr2.exists():
        r = json.loads(hr2.read_text())
        llm = r["llm_by_purpose"]
        print("\n## HippoRAG 2 색인\n")
        print(table(["항목", "값"], [
            ["청크", r["chunks"]], ["본문이 같아 합친 청크", r["chunks"] - r["unique_chunk_texts"]],
            ["OpenIE 프롬프트", sum(int(s.get("unique_prompts", 0)) for s in llm.values())],
            ["OpenIE 비용 $", round(sum(s.get("recorded_cost_usd", 0) for s in llm.values()), 3)],
            ["OpenIE JSON 실패", len(r["openie_json_failures"])], ["트리플 0개 청크", len(r["openie"]["chunks_without_triples"])],
            ["트리플", r["openie"]["triples_raw"]], ["phrase (한글 포함)", f"{r['phrase_nodes']} ({r['phrase_nodes_with_hangul']})"],
            ["fact", r["fact_nodes"]], ["그래프 점·선", f"{r['graph']['vertices']} · {r['graph']['edges']} {r['graph']['edges_by_kind']}"],
            ["첫 실행 추출·색인 초", f"{r['first_full_run']['extract_seconds']} · {r['first_full_run']['build_seconds']}"]]))


if __name__ == "__main__":
    main()
