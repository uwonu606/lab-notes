import argparse
import json
from pathlib import Path


def cost_header(index_reports, retrieve_report, estimate_chunks):
    lines = []
    main = None
    for path in index_reports:
        report = json.loads(Path(path).read_text())
        main = main or report
        llm = report["llm_by_purpose"]
        calls = sum(llm[p].get("unique_prompts", 0) for p in llm)
        seconds = sum(llm[p].get("recorded_seconds", 0) for p in llm)
        cost = sum(llm[p].get("recorded_cost_usd", 0) for p in llm)
        failures = report["openie_json_failures"]
        edges = report["graph"]["edges_by_kind"]
        lines.append(f"=== 색인 {path}: 청크 {report['chunks']} · OpenIE 호출 {calls:.0f}번 · 호출당 초 합 {seconds:.0f}초 · ${cost:.3f} · "
                     f"첫 실행 추출 {report['first_full_run']['extract_seconds']}초 + 색인 {report['first_full_run']['build_seconds']}초(동시 {report['settings']['workers']})")
        lines.append(f"    OpenIE JSON 실패 {len(failures)}건 {[(f['stage'], f['chunk_id']) for f in failures]} · 트리플 0개 청크 {len(report['openie']['chunks_without_triples'])}개 · "
                     f"phrase {report['phrase_nodes']}개 중 한글 포함 {report['phrase_nodes_with_hangul']}개 · ASCII 조건 통과 {report['phrases_passing_ascii_gate']} / 유니코드 조건 통과 {report['phrases_passing_unicode_gate']} · "
                     f"fact {report['fact_nodes']}개 · 선 {edges}")
    if retrieve_report:
        report = json.loads(Path(retrieve_report).read_text())
        for key, llm in report["llm_by_index"].items():
            filt = llm.get("filter", {})
            calls = filt.get("unique_prompts", 0)
            lines.append(f"=== 검색 필터 LLM ({key} 색인): 호출 {calls:.0f}번 (이번 실행 {filt.get('calls', 0):.0f}) · 호출당 초 합 {filt.get('recorded_seconds', 0):.0f}초 · "
                         f"${filt.get('recorded_cost_usd', 0):.3f} · 실패한 시도 {filt.get('failed_attempts', 0):.0f}")
        for name, v in report["variants"].items():
            share = "-" if v["passage_share_mean"] is None else f"{v['passage_share_mean']:.3f}"
            lines.append(f"    {name:20} 필터가 비어 dense 로 간 질의 {v['dense_fallback']} · 필터 답 해석 실패 {v['filter_parse_failed']} · 남긴 트리플 평균 {v['filter_kept_mean']:.2f} · "
                         f"후보에 없던 트리플(difflib 로 후보에 붙음) {v['filter_invented']} · PPR reset 중 passage 몫 평균 {share} · phrase 시작점 평균 {v['phrase_seeds_mean'] or 0:.1f}개, 무게 합 평균 {v['phrase_mass_mean'] or 0:.2f}")
    if main and estimate_chunks:
        llm = main["llm_by_purpose"]
        per_chunk_seconds = sum(llm[p].get("recorded_seconds", 0) for p in ("ner", "triples") if p in llm) / main["chunks"]
        per_chunk_cost = sum(llm[p].get("recorded_cost_usd", 0) for p in ("ner", "triples") if p in llm) / main["chunks"]
        wall = main["first_full_run"]["extract_seconds"] / main["chunks"] * estimate_chunks
        build = main["first_full_run"]["build_seconds"] / main["chunks"] * estimate_chunks
        lines.insert(0, f"=== {estimate_chunks:,}청크 색인 추정 (57청크 실측을 청크 수에 비례해 늘림, 청크 길이가 같다고 봄): OpenIE 호출 {2 * estimate_chunks:,}번 · "
                     f"${per_chunk_cost * estimate_chunks:.2f} · 호출 시간 합 {per_chunk_seconds * estimate_chunks / 60:.0f}분 → 동시 {main['settings']['workers']} 로 약 {wall / 60:.0f}분 + 임베딩·그래프 약 {build / 60:.0f}분")
    return lines


def main():
    parser = argparse.ArgumentParser(description="23_hr2_index·retrieve 보고서에서 호출 수·비용·실패를 모으고 큰 말뭉치 색인 비용을 추정한다.")
    parser.add_argument("--index-report", action="append", default=[])
    parser.add_argument("--retrieve-report")
    parser.add_argument("--estimate-chunks", type=int)
    args = parser.parse_args()
    print("\n".join(cost_header(args.index_report, args.retrieve_report, args.estimate_chunks)))


if __name__ == "__main__":
    main()
