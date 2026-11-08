import argparse
import json
import re
import sys
import time
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(__file__).parent
CALL_RETRY_ROUNDS = 2


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = load("hr2_common", LAB / "23_hr2_common.py")
from hipporag.utils.misc_utils import compute_mdhash_id


def call_failures(openie):
    return [f for f in openie.failures if f["error"].startswith("claude -p failed")]


def extract_until_calls_succeed(openie, rows):
    for round_number in range(CALL_RETRY_ROUNDS + 1):
        openie.failures = []
        openie.batch_openie(rows)
        unanswered = call_failures(openie)
        if not unanswered:
            return
        print(f"  claude -p 가 끝내 답하지 않은 OpenIE 호출 {len(unanswered)}개 — 다시 돈다 ({round_number + 1}/{CALL_RETRY_ROUNDS})", flush=True)
    raise SystemExit(f"OpenIE 호출 {len(unanswered)}개가 재시도 뒤에도 실패했다. 성공한 호출은 캐시에 있으니 다시 돌리면 이어진다: {unanswered[:3]}")


def ascii_gate(phrase):
    return len(re.sub("[^A-Za-z0-9]", "", phrase)) > 2


def unicode_gate(phrase):
    return sum(c.isalnum() for c in phrase) > 2


def describe_index(hipporag, chunks, id_of_hash):
    info = hipporag._openie_info or hipporag.load_existing_openie([])[0]
    phrases = hipporag.entity_embedding_store.get_all_texts()
    hangul = [p for p in phrases if re.search("[가-힣]", p)]
    kinds = Counter(hipporag.graph.es["edge_kind"]) if hipporag.graph.ecount() else Counter()
    return {
        "chunks": len(chunks),
        "unique_chunk_texts": len(id_of_hash),
        "openie": {
            "entities_raw": sum(len(d["extracted_entities"]) for d in info),
            "triples_raw": sum(len(d["extracted_triples"]) for d in info),
            "chunks_without_triples": sorted(id_of_hash[d["idx"]] for d in info if not d["extracted_triples"]),
        },
        "phrase_nodes": len(phrases),
        "phrase_nodes_with_hangul": len(hangul),
        "phrases_passing_ascii_gate": sum(map(ascii_gate, phrases)),
        "phrases_passing_unicode_gate": sum(map(unicode_gate, phrases)),
        "hangul_phrases_passing_ascii_gate": sum(map(ascii_gate, hangul)),
        "fact_nodes": len(hipporag.fact_embedding_store.get_all_ids()),
        "graph": {"vertices": hipporag.graph.vcount(), "edges": hipporag.graph.ecount(), "edges_by_kind": dict(kinds)},
    }


def main():
    parser = argparse.ArgumentParser(description="청크를 공식 HippoRAG 2 OpenIE(claude -p) → 공식 색인으로 만든다.")
    parser.add_argument("chunks", help="한 줄에 {id, text} 하나인 jsonl")
    parser.add_argument("out_dir")
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--ascii-gate", action="store_true", help="동의어 선 후보 조건을 공식 ASCII 3자 규칙으로 둔다")
    parser.add_argument("--synonym-threshold", type=float, default=0.8)
    parser.add_argument("--limit", type=int, help="앞의 N개 청크만 쓴다 (시험용)")
    parser.add_argument("--prompt-style", choices=("roles", "transcript"), default="roles",
                        help="roles: 공식 system 메시지를 system 쪽에, 예시·입력을 태그로 나눠 user 쪽에. transcript: 대화록 한 덩어리(첫 57청크 판)")
    parser.add_argument("--embed-backend", choices=sorted(common.embed_client.BACKENDS), help="기본은 embed_client.DEFAULT_BACKEND. 옛 색인을 다시 지을 때는 그 색인의 값")
    args = parser.parse_args()

    chunks = common.read_chunks(args.chunks)[: args.limit]
    id_of_hash = {}
    for c in chunks:
        id_of_hash.setdefault(compute_mdhash_id(c["text"], prefix="chunk-"), c["id"])
    if len(id_of_hash) < len(chunks):
        print(f"  본문이 같은 청크 {len(chunks) - len(id_of_hash)}개는 HippoRAG 가 하나로 합친다 (첫 id 만 남는다)")

    out = Path(args.out_dir)
    settings = common.default_settings(args.model, not args.ascii_gate, args.synonym_threshold, args.workers, args.prompt_style, args.embed_backend)
    common.save_settings(out, settings)
    (out / "chunk_ids.json").write_text(json.dumps(id_of_hash, ensure_ascii=False, indent=0))
    hipporag, llm, _ = common.open_hipporag(out, settings, rebuild_graph=True)

    started = time.monotonic()
    rows = {key: {"content": c["text"]} for c in chunks for key in [compute_mdhash_id(c["text"], prefix="chunk-")] if id_of_hash[key] == c["id"]}
    extract_until_calls_succeed(hipporag.openie, rows)
    json_failures = [{**f, "chunk_id": id_of_hash[f["chunk_id"]]} for f in hipporag.openie.failures]
    extracted = time.monotonic()
    stats = llm.stats.snapshot()
    hipporag.index(common.as_documents(chunks))
    finished = time.monotonic()

    live_calls = sum(s.get("calls", 0) for s in stats.values())
    report_path = out / "index-report.json"
    previous = json.loads(report_path.read_text()) if report_path.exists() else {}
    report = {
        "settings": settings,
        **describe_index(hipporag, chunks, id_of_hash),
        "openie_json_failures": [{k: v for k, v in f.items() if k != "response"} | {"response_head": (f["response"] or "")[:300]} for f in json_failures],
        "llm_by_purpose": stats,
        "this_run": {"live_llm_calls": live_calls, "embedded_texts": common.embed_client.stats["requested_texts"],
                     "extract_seconds": round(extracted - started, 1), "build_seconds": round(finished - extracted, 1)},
    }
    report["first_full_run"] = report["this_run"] if live_calls else previous.get("first_full_run", report["this_run"])
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))

    print(f"=== {args.chunks} → {out}  (동의어 후보 조건: {'ASCII 3자(공식)' if args.ascii_gate else '유니코드 3자(패치)'})")
    print(f"  LLM {common.usage_line(stats)}")
    print(f"  OpenIE JSON 실패 {len(json_failures)}건 {[(f['stage'], f['chunk_id']) for f in json_failures]} · 트리플 0개 청크 {len(report['openie']['chunks_without_triples'])}개")
    print(f"  phrase {report['phrase_nodes']}개 (한글 포함 {report['phrase_nodes_with_hangul']}) · fact {report['fact_nodes']}개 · 그래프 점 {report['graph']['vertices']} 선 {report['graph']['edges']} {report['graph']['edges_by_kind']}")
    print(f"  이번 실행: 추출 {report['this_run']['extract_seconds']}초 · 색인 {report['this_run']['build_seconds']}초 · 새 LLM 호출 {live_calls:.0f} · 새 임베딩 {common.embed_client.stats['requested_texts']}개")


if __name__ == "__main__":
    main()
