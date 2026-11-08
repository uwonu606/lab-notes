import json, re, sys
from pathlib import Path

import numpy as np

LAB = Path(sys.argv[1])
GLOSSARY = Path(sys.argv[2])
OUT = Path(sys.argv[3])
TOP_N = 5
LINK_TOP_K = 5
DAMPING = 0.5
PASSAGE_WEIGHTS = [0.01, 0.05, 0.2, 1.0]


def mentions(form, text):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(form) + r"(?![A-Za-z0-9])", text, re.I) is not None


def min_max(x):
    span = x.max() - x.min()
    return (x - x.min()) / span if span > 0 else np.ones_like(x)


def personalized_pagerank(adjacency, reset, damping, iterations=200):
    degree = adjacency.sum(axis=1)
    transition = np.divide(adjacency, degree[:, None], out=np.zeros_like(adjacency), where=degree[:, None] > 0)
    reset = reset / reset.sum()
    score = reset.copy()
    for _ in range(iterations):
        dangling = score[degree == 0].sum()
        score = (1 - damping) * reset + damping * (score @ transition + dangling * reset)
    return score


chunks = [json.loads(line) for line in (LAB / "inputs/12-chunks.jsonl").read_text().splitlines()]
questions = json.loads((LAB / "inputs/12-questions.json").read_text())
entries = json.loads(GLOSSARY.read_text())
vectors = json.loads((LAB / "runs/12-cache/embeddings.json").read_text())


def unit_matrix(texts):
    missing = [t for t in texts if t not in vectors]
    if missing:
        raise SystemExit(f"not in embedding cache: {missing[:3]}")
    m = np.array([vectors[t] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


chunk_vectors = unit_matrix([c["text"] for c in chunks])
question_vectors = unit_matrix([q["question"] for q in questions])

entry_chunks = []
for e in entries:
    forms = [e["canonical"], *e["aliases"]]
    entry_chunks.append({i for i, c in enumerate(chunks) if any(mentions(f, c["text"]) for f in forms)})
live = [k for k, s in enumerate(entry_chunks) if s]
n_chunks, n_entries = len(chunks), len(live)
size = n_chunks + n_entries
adjacency = np.zeros((size, size))
for col, k in enumerate(live):
    for i in entry_chunks[k]:
        adjacency[i, n_chunks + col] = adjacency[n_chunks + col, i] = 1.0


def recall_at(ranked_ids, gold):
    return sum(g in ranked_ids[:TOP_N] for g in gold) / len(gold)


def run(passage_weight, divide_by_df):
    per_question, fallback = [], 0
    for q, qv in zip(questions, question_vectors):
        dense = chunk_vectors @ qv
        seeds = np.zeros(size)
        for col, k in enumerate(live):
            e = entries[k]
            if any(mentions(f, q["question"]) for f in [e["canonical"], *e["aliases"]]):
                seeds[n_chunks + col] = 1.0 / len(entry_chunks[k]) if divide_by_df else 1.0
        if LINK_TOP_K and np.count_nonzero(seeds) > LINK_TOP_K:
            keep = np.argsort(-seeds)[:LINK_TOP_K]
            trimmed = np.zeros(size)
            trimmed[keep] = seeds[keep]
            seeds = trimmed
        if not seeds.any():
            fallback += 1
            order = np.argsort(-dense)
        else:
            reset = seeds.copy()
            reset[:n_chunks] += min_max(dense) * passage_weight
            score = personalized_pagerank(adjacency, reset, DAMPING)[:n_chunks]
            order = np.argsort(-score)
        ranked = [chunks[i]["id"] for i in order]
        per_question.append((q["id"], q["type"], recall_at(ranked, q["gold"]), all(g in ranked[:TOP_N] for g in q["gold"]), set(ranked[:TOP_N])))
    return per_question, fallback


def summary(rows):
    out = []
    for kind in ("single", "bridge", None):
        sel = [r for r in rows if kind is None or r[1] == kind]
        out.append(f"{kind or 'all'} {np.mean([r[2] for r in sel]):.3f} ({sum(r[3] for r in sel)}/{len(sel)})")
    return " · ".join(out)


dense_rows = []
for q, qv in zip(questions, question_vectors):
    ranked = [chunks[i]["id"] for i in np.argsort(-(chunk_vectors @ qv))]
    dense_rows.append((q["id"], q["type"], recall_at(ranked, q["gold"]), all(g in ranked[:TOP_N] for g in q["gold"]), set(ranked[:TOP_N])))

lines = [f"chunks {n_chunks}, glossary entries with >=1 chunk {n_entries}, chunk-entry edges {int(adjacency.sum() // 2)}, damping {DAMPING}, undirected",
         f"dense (A) recall@5: {summary(dense_rows)}"]
for divide in (True, False):
    for w in PASSAGE_WEIGHTS:
        rows, fallback = run(w, divide)
        changed = [r[0] for r, d in zip(rows, dense_rows) if r[2] != d[2]]
        overlap = np.mean([len(r[4] & d[4]) for r, d in zip(rows, dense_rows)])
        lines.append(f"PPR seeds=query-matched entries{' /df' if divide else ''} passage_weight {w}: {summary(rows)} · dense fallback {fallback}/40 · "
                     f"top5 overlap with dense {overlap:.2f} · questions differing from dense {changed}")
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
