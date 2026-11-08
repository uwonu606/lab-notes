import argparse
import importlib
import json
import time

import embed_client

arch = importlib.import_module("23_arch_common")

VARIANT_OF_KIND = {"fixed": "dense", "section": "dense-section", "claim": "dense-claim", "doc": "dense-doc"}


def main():
    parser = argparse.ArgumentParser(description="B0: 단위 종류마다 bge-m3 dense 순위를 글자 예산만큼 runs/23-arch-b0-dense/ 에 낸다.")
    parser.add_argument("--kinds", default=",".join(VARIANT_OF_KIND))
    args = parser.parse_args()

    questions = arch.read_questions()
    started = time.monotonic()
    qvecs = arch.embed_questions(questions)
    question_seconds = time.monotonic() - started
    run = arch.Run("b0-dense")
    checks = {}
    for kind in args.kinds.split(","):
        units = arch.load_units(kind)
        checks[kind] = dict(zip(("min_cosine_vs_cache", "newly_embedded"), arch.stored_vectors_match_cache(kind)))
        for q, qvec in zip(questions, qvecs):
            ranked = units.dense_units(qvec, top=400)
            kept = arch.fill_budget(ranked)
            run.add(q.qid, VARIANT_OF_KIND[kind], kept, stage_counts={"dense": len(units)}, empty_stages=[], llm={"calls": 0})
        print(f"{kind}: 단위 {len(units)} · 저장 벡터와 캐시 cosine 최소 {checks[kind]['min_cosine_vs_cache']:.4f}", flush=True)
    run.write()
    print(run.score())
    (run.dir / "run-report.json").write_text(json.dumps({
        "questions": len(questions), "question_embed_seconds": round(question_seconds, 1),
        "embed_backend": embed_client.stats["backend"], "embed_stats": embed_client.stats, "vector_checks": checks,
        "docs_sha256": arch.sha256_of(arch.DOCS), "gold_sha256": arch.sha256_of(arch.GOLD)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
