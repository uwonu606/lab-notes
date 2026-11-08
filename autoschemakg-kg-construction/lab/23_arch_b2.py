import importlib
import json
import time

import numpy as np

import embed_client

arch = importlib.import_module("23_arch_common")

DEPTH = 400
RRF_VARIANTS = {"mix-claim-fixed": ("claim", "fixed"), "mix-section-fixed": ("section", "fixed")}
CTX_FIRST_CHARS = 2500
RUN_DIR = arch.RUNS / "23-arch-b2-mix"
CTX_VECTORS = RUN_DIR / "idx/emb-claim-ctx.npy"


def claim_context_text(claim, section_of):
    title = arch.read_docs()[claim["doc_id"]]["title"]
    return f"{title}\n[{section_of[claim['parent_section']]['section_type']}] {claim['text']}"


def claim_ctx_units():
    claims = arch.load_units("claim")
    ids_path = CTX_VECTORS.with_suffix(".ids.json")
    if CTX_VECTORS.exists() and json.loads(ids_path.read_text()) == claims.ids:
        return arch.Units("claim", claims.rows, np.load(CTX_VECTORS)), None
    section_of = {r["unit_id"]: r for r in arch.load_units("section").rows}
    started = time.monotonic()
    matrix = np.asarray(embed_client.embed([claim_context_text(c, section_of) for c in claims.rows]), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    CTX_VECTORS.parent.mkdir(parents=True, exist_ok=True)
    np.save(CTX_VECTORS, matrix)
    ids_path.write_text(json.dumps(claims.ids, ensure_ascii=False))
    return arch.Units("claim", claims.rows, matrix), round(time.monotonic() - started, 1)


def ctx_then_fixed(ctx_ranked, fixed_ranked):
    first = arch.fill_budget(ctx_ranked, budget=CTX_FIRST_CHARS, min_units=1)
    return arch.fill_budget(first + fixed_ranked), len(first)


def main():
    questions = arch.read_questions()
    qvecs = arch.embed_questions(questions)
    run = arch.Run("b2-mix")
    for variant, kinds in RRF_VARIANTS.items():
        sources = [arch.load_units(kind) for kind in kinds]
        for q, qvec in zip(questions, qvecs):
            rankings = [units.dense_units(qvec, path_stages=(f"dense={units.kind}",), top=DEPTH) for units in sources]
            fused = arch.rrf(*rankings)
            kept = arch.fill_budget(arch.without_overlaps(fused))
            run.add(q.qid, variant, kept, stage_counts={f"dense={u.kind}": DEPTH for u in sources} | {"rrf": len(fused)},
                    empty_stages=[], llm={"calls": 0},
                    unit_kinds={kind: sum(arch.unit_kind(u["path"]) == kind for u in kept) for kind in kinds})

    ctx, embed_seconds = claim_ctx_units()
    fixed = arch.load_units("fixed")
    for q, qvec in zip(questions, qvecs):
        ctx_ranked = ctx.dense_units(qvec, path_stages=("dense=claim-ctx",), top=DEPTH)
        kept = arch.fill_budget(ctx_ranked)
        run.add(q.qid, "claim-ctx", kept, stage_counts={"dense=claim-ctx": DEPTH}, empty_stages=[], llm={"calls": 0})
        filled, ctx_count = ctx_then_fixed(ctx_ranked, fixed.dense_units(qvec, path_stages=("dense=fixed",), top=DEPTH))
        run.add(q.qid, "claim-ctx-fill", filled, stage_counts={"dense=claim-ctx": ctx_count, "dense=fixed": len(filled) - ctx_count},
                empty_stages=[], llm={"calls": 0})
    run.write()
    print(run.score())
    (RUN_DIR / "run-report.json").write_text(json.dumps({"claim_ctx_embed_seconds": embed_seconds, "embed_stats": embed_client.stats,
                                                          "gold_sha256": arch.sha256_of(arch.GOLD)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
