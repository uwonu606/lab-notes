import json, math, re, sys, urllib.error, urllib.request
from pathlib import Path

import numpy as np

LAB = Path(sys.argv[1])
VECTOR_CACHE = Path(sys.argv[2])
OUT = Path(sys.argv[3])
TOP_N = 5
LINK_TOP_K = 5
DAMPING = 0.5
SYNONYM_THRESHOLD = 0.8
PASSAGE_WEIGHTS = [0.05, 0.2, 1.0]


def text_processing(text):
    lowered = str(text).casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()


def embed(texts):
    body = json.dumps({"model": "bge-m3", "input": texts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)["embeddings"]


cache = json.loads(VECTOR_CACHE.read_text()) if VECTOR_CACHE.exists() else {}


def vectors_for(texts):
    missing = sorted({t for t in texts if t not in cache})
    for start in range(0, len(missing), 16):
        batch = missing[start:start + 16]
        try:
            cache.update(zip(batch, embed(batch)))
        except urllib.error.HTTPError:
            for t in batch:
                try:
                    cache[t] = embed([t])[0]
                except urllib.error.HTTPError:
                    cache[t] = None
    if missing:
        VECTOR_CACHE.write_text(json.dumps(cache))
    return texts


def unit_matrix(texts, source):
    m = np.array([source[t] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


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
lab_vectors = json.loads((LAB / "runs/12-cache/embeddings.json").read_text())

facts, fact_chunks, phrase_chunks = [], {}, {}
for ci, c in enumerate(chunks):
    record = json.loads((LAB / "runs/12-cache" / (c["id"].replace("#", "_") + ".json")).read_text())
    for t in record["entity_relation_dict"]:
        triple = (text_processing(t.get("Head", "")), text_processing(t.get("Relation", "")), text_processing(t.get("Tail", "")))
        if not triple[0] or not triple[2]:
            continue
        if triple not in fact_chunks:
            facts.append(triple)
            fact_chunks[triple] = set()
        fact_chunks[triple].add(ci)
        for p in (triple[0], triple[2]):
            phrase_chunks.setdefault(p, set()).add(ci)

phrases = sorted(phrase_chunks)
fact_texts = [str(f) for f in facts]
vectors_for(fact_texts + phrases)
usable_facts = [i for i, t in enumerate(fact_texts) if cache.get(t) is not None]
fact_matrix = unit_matrix([fact_texts[i] for i in usable_facts], cache)
chunk_vectors = unit_matrix([c["text"] for c in chunks], lab_vectors)
question_vectors = unit_matrix([q["question"] for q in questions], lab_vectors)

n_chunks = len(chunks)
phrase_index = {p: n_chunks + k for k, p in enumerate(phrases)}
size = n_chunks + len(phrases)
base = np.zeros((size, size))
for f in facts:
    a, b = phrase_index[f[0]], phrase_index[f[2]]
    if a != b:
        base[a, b] += len(fact_chunks[f])
        base[b, a] += len(fact_chunks[f])
for p, cs in phrase_chunks.items():
    for ci in cs:
        base[ci, phrase_index[p]] = max(base[ci, phrase_index[p]], 1.0)
        base[phrase_index[p], ci] = base[ci, phrase_index[p]]

usable_phrases = [p for p in phrases if cache.get(p) is not None]
phrase_matrix = unit_matrix(usable_phrases, cache)
similarity = phrase_matrix @ phrase_matrix.T
with_synonyms = base.copy()
synonym_edges = 0
for i, p in enumerate(usable_phrases):
    if len(re.sub("[^A-Za-z0-9]", "", p)) <= 2:
        continue
    order = np.argsort(-similarity[i])
    taken = 0
    for j in order:
        if j == i:
            continue
        if similarity[i, j] < SYNONYM_THRESHOLD or taken >= 100:
            break
        a, b = phrase_index[p], phrase_index[usable_phrases[j]]
        if with_synonyms[a, b] < similarity[i, j]:
            if with_synonyms[a, b] == 0:
                synonym_edges += 1
            with_synonyms[a, b] = with_synonyms[b, a] = max(with_synonyms[a, b], similarity[i, j])
        taken += 1


def recall_at(ranked, gold):
    return sum(g in ranked[:TOP_N] for g in gold) / len(gold)


def search(adjacency, qv, passage_weight, divide_by_df):
    dense = chunk_vectors @ qv
    fact_scores = min_max(fact_matrix @ qv)
    top = np.argsort(-fact_scores)[:LINK_TOP_K]
    weights, counts = np.zeros(size), np.zeros(size)
    for rank in top:
        f = facts[usable_facts[rank]]
        for p in (f[0], f[2]):
            node = phrase_index[p]
            score = fact_scores[rank] / len(phrase_chunks[p]) if divide_by_df else fact_scores[rank]
            weights[node] += score
            counts[node] += 1
    weights = np.divide(weights, counts, out=np.zeros_like(weights), where=counts > 0)
    if np.count_nonzero(weights) > LINK_TOP_K:
        keep = np.argsort(-weights)[:LINK_TOP_K]
        trimmed = np.zeros(size)
        trimmed[keep] = weights[keep]
        weights = trimmed
    if not weights.any():
        return [chunks[i]["id"] for i in np.argsort(-dense)]
    reset = weights.copy()
    reset[:n_chunks] += min_max(dense) * passage_weight
    score = personalized_pagerank(adjacency, reset, DAMPING)[:n_chunks]
    return [chunks[i]["id"] for i in np.argsort(-score)]


def summary(rows):
    parts = []
    for kind in ("single", "bridge", None):
        sel = [r for r in rows if kind is None or r[1] == kind]
        parts.append(f"{kind or 'all'} {np.mean([r[2] for r in sel]):.3f} ({sum(r[3] for r in sel)}/{len(sel)})")
    return " · ".join(parts)


dense_rows = []
for q, qv in zip(questions, question_vectors):
    ranked = [chunks[i]["id"] for i in np.argsort(-(chunk_vectors @ qv))]
    dense_rows.append((q["id"], q["type"], recall_at(ranked, q["gold"]), all(g in ranked[:TOP_N] for g in q["gold"]), set(ranked[:TOP_N])))

lines = [f"llama3.1:8b entity triples from runs/12-cache: facts {len(facts)} (embedded {len(usable_facts)}), phrases {len(phrases)}, "
         f"passage-phrase edges {sum(len(v) for v in phrase_chunks.values())}, synonym edges at {SYNONYM_THRESHOLD} (ASCII>2 gate) {synonym_edges}",
         "settings: undirected, damping 0.5, query-to-fact top-5, NO recognition-memory filter, phrase seed top-5",
         f"dense (A) recall@5: {summary(dense_rows)}"]
for graph_name, adjacency in (("no synonym", base), ("synonym 0.8", with_synonyms)):
    for divide in (True, False):
        for w in PASSAGE_WEIGHTS:
            rows = []
            for q, qv in zip(questions, question_vectors):
                ranked = search(adjacency, qv, w, divide)
                rows.append((q["id"], q["type"], recall_at(ranked, q["gold"]), all(g in ranked[:TOP_N] for g in q["gold"]), set(ranked[:TOP_N])))
            changed = [r[0] for r, d in zip(rows, dense_rows) if r[2] != d[2]]
            better = [r[0] for r, d in zip(rows, dense_rows) if r[2] > d[2]]
            overlap = np.mean([len(r[4] & d[4]) for r, d in zip(rows, dense_rows)])
            lines.append(f"{graph_name}{' /df' if divide else ''} w={w}: {summary(rows)} · overlap {overlap:.2f} · better {better} · worse {[c for c in changed if c not in better]}")
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
