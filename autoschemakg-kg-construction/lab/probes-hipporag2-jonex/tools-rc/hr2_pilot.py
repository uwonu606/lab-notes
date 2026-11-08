import json, os, re, sys, urllib.request
from collections import defaultdict
import numpy as np

LAB, EMB_CACHE = sys.argv[1], sys.argv[2]
CACHE_DIR = os.path.join(LAB, "runs/12-cache")
COVER, TOP_N, BUDGETS = 0.5, 5, (1000, 2500, 5000)

vectors = json.load(open(EMB_CACHE))
def post(path, payload):
    req = urllib.request.Request("http://localhost:11434" + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))
def encode(texts):
    missing = sorted({t for t in texts if t not in vectors})
    for i in range(0, len(missing), 64):
        b = missing[i:i + 64]
        vectors.update(zip(b, post("/api/embed", {"model": "bge-m3", "input": b})["embeddings"]))
    if missing:
        json.dump(vectors, open(EMB_CACHE, "w"))
    m = np.array([vectors[t] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)

def text_processing(s):
    return re.sub(r"\s+", " ", "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s.lower())).strip()

chunks = [json.loads(l) for l in open(os.path.join(LAB, "inputs/12-chunks.jsonl"))]
questions = json.load(open(os.path.join(LAB, "inputs/12-questions.json")))
evidence = json.load(open(os.path.join(LAB, "inputs/14-evidence.json")))["questions"]
cid_index = {c["id"]: i for i, c in enumerate(chunks)}
offset, pos = {}, defaultdict(int)
for c in chunks:
    slug = c["id"].split("#")[0]
    offset[c["id"]] = pos[slug]; pos[slug] += len(c["text"]) + 1

units = {}
for qid, per_chunk in evidence.items():
    units[qid] = []
    for cid, excerpts in per_chunk.items():
        spans = []
        for ex in excerpts:
            at = chunks[cid_index[cid]]["text"].find(ex)
            spans.append((offset[cid] + at, offset[cid] + at + len(ex)))
        units[qid].append({"doc": cid.split("#")[0], "spans": spans})

def covers(doc, s, e, u):
    return doc == u["doc"] and any(min(e, b) - max(s, a) >= COVER * (b - a) for a, b in u["spans"])

# --- extraction from cache (llama3.1:8b, round 13)
triples, records = [], []
for c in chunks:
    d = json.load(open(os.path.join(CACHE_DIR, c["id"].replace("#", "_") + ".json")))
    for t in d.get("entity_relation_dict") or []:
        h, r, tl = (t.get("Head") or "").strip(), (t.get("Relation") or "").strip(), (t.get("Tail") or "").strip()
        if text_processing(h) and text_processing(tl):
            triples.append((c["id"], h, r, tl))
    for ev in d.get("event_entity_dict") or []:
        e = (ev.get("Event") or "").strip()
        at = c["text"].find(e) if e else -1
        if at >= 0:
            records.append({"chunk": c["id"], "start": at, "end": at + len(e), "text": e,
                            "names": [n for n in (ev.get("Entity") or []) if isinstance(n, str) and text_processing(n)]})

def build(tau, use_records, grounded_only):
    phrase_ids, phrase_surface = {}, {}
    def phrase(raw):
        k = text_processing(raw)
        if k not in phrase_ids:
            phrase_ids[k] = len(phrase_ids); phrase_surface[k] = raw
        return phrase_ids[k]
    facts, fact_edges, ctx = [], defaultdict(float), defaultdict(set)
    for cid, h, r, tl in triples:
        if grounded_only:
            low = chunks[cid_index[cid]]["text"].casefold()
            if h.casefold() not in low or tl.casefold() not in low:
                continue
        a, b = phrase(h), phrase(tl)
        facts.append((cid, a, b, f"{h} {r} {tl}"))
        fact_edges[tuple(sorted((a, b)))] += 1.0
        ctx[("c", cid)].update((a, b))
    recs = []
    if use_records:
        for r in records:
            ids = [phrase(n) for n in r["names"] if n.casefold() in r["text"].casefold()]
            if not ids:
                continue
            recs.append(r); ctx[("r", len(recs) - 1)].update(ids)
            ctx[("c", r["chunk"])].update(ids)
    P = len(phrase_ids)
    keys = list(phrase_ids)
    pv = encode([phrase_surface[k] for k in keys])
    syn = {}
    if tau <= 1.0:
        sims = pv @ pv.T
        for i in range(P):
            for j in np.where(sims[i] >= tau)[0]:
                if j > i:
                    syn[(i, int(j))] = float(sims[i, j])
    passages = [("c", c["id"]) for c in chunks] + [("r", i) for i in range(len(recs))]
    N = P + len(passages)
    W = defaultdict(float)
    for (a, b), w in fact_edges.items():
        W[(a, b)] = max(W[(a, b)], w)
    for (a, b), w in syn.items():
        W[(a, b)] = max(W[(a, b)], w)
    for pi, key in enumerate(passages):
        for ph in ctx.get(key, ()):
            k = tuple(sorted((ph, P + pi)))
            W[k] = max(W[k], 1.0)
    if use_records:
        for ri, r in enumerate(recs):
            k = (P + cid_index[r["chunk"]], P + len(chunks) + ri)
            W[k] = max(W[k], 1.0)
    A = np.zeros((N, N))
    for (a, b), w in W.items():
        A[a, b] = A[b, a] = w
    ph_chunks = defaultdict(set)
    for (kind, ref), ids in ctx.items():
        if kind == "c":
            for ph in ids:
                ph_chunks[ph].add(ref)
    texts = [chunks[cid_index[ref]]["text"] if k == "c" else recs[ref]["text"] for k, ref in passages]
    return dict(P=P, N=N, A=A, facts=facts, fv=encode([f[3] for f in facts]), passages=passages, recs=recs,
                pvec=encode(texts), ph_chunks=ph_chunks, n_syn=len(syn), n_fact=len(fact_edges))

def ppr(A, reset, damping=0.5, iters=200):
    deg = A.sum(1)
    T = np.divide(A, deg[:, None], out=np.zeros_like(A), where=deg[:, None] > 0)
    r = reset / reset.sum(); p = r.copy()
    for _ in range(iters):
        dangling = p[deg == 0].sum()
        p = (1 - damping) * r + damping * (T.T @ p + dangling * r)
    return p

def minmax(x):
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo) if hi > lo else np.ones_like(x)

def retrieve(G, q, pw, link_k=5):
    qv = encode([q])[0]
    fs = minmax(G["fv"] @ qv)
    top = np.argsort(-fs)[:link_k]
    phrase_scores = defaultdict(list)
    for i in top:
        _, a, b, _ = G["facts"][i]
        for ph in (a, b):
            phrase_scores[ph].append(fs[i] / max(1, len(G["ph_chunks"].get(ph, ()))))
    reset = np.zeros(G["N"])
    for ph, vals in sorted(phrase_scores.items(), key=lambda kv: -np.mean(kv[1]))[:link_k]:
        reset[ph] = np.mean(vals)
    ds = G["pvec"] @ qv
    reset[G["P"]:] = minmax(ds) * pw
    scores = ppr(G["A"], reset)[G["P"]:]
    return scores, ds

def pieces_of(G, order, budget=None, top=None):
    out, left, taken = [], budget, []
    for idx in order:
        kind, ref = G["passages"][idx]
        if kind == "c":
            cid = ref; s0, e0 = offset[cid], offset[cid] + len(chunks[cid_index[cid]]["text"])
        else:
            r = G["recs"][ref]; cid = r["chunk"]; s0, e0 = offset[cid] + r["start"], offset[cid] + r["end"]
        doc = cid.split("#")[0]
        if any(d == doc and a <= s0 and e0 <= b for d, a, b in taken):
            continue
        if budget is not None:
            if left <= 0: break
            e1 = min(e0, s0 + left); left -= e0 - s0
            out.append((doc, s0, e1))
        else:
            out.append((doc, s0, e0))
        taken.append((doc, s0, e0))
        if top is not None and len(out) >= top: break
    return out

def recall(pieces, us):
    hit = [any(covers(*p, u) for p in pieces) for u in us]
    return sum(hit) / len(us)

def evaluate(name, G, pw, mode):
    rows = defaultdict(list)
    nchunks = len(chunks)
    for q in questions:
        scores, ds = retrieve(G, q["question"], pw) if mode != "dense" else (None, G["pvec"] @ encode([q["question"]])[0])
        s = ds if mode == "dense" else scores
        chunk_order = list(np.argsort(-s[:nchunks]))
        gold = set(q["gold"])
        top5 = [chunks[i]["id"] for i in chunk_order[:TOP_N]]
        rows["@5"].append(len(gold & set(top5)) / len(gold))
        mixed = list(np.argsort(-s)) if mode == "mixed" else chunk_order
        for B in BUDGETS:
            rows[B].append(recall(pieces_of(G, mixed, budget=B), units[q["id"]]))
        rows["type_" + q["type"]].append(len(gold & set(top5)) / len(gold))
    m = {k: round(float(np.mean(v)), 3) for k, v in rows.items()}
    print(f"{name:42s} @5 {m['@5']:.3f} (single {m['type_single']:.3f} / bridge {m['type_bridge']:.3f}) | 1000자 {m[1000]:.3f} 2500자 {m[2500]:.3f} 5000자 {m[5000]:.3f}")

print("triples", len(triples), "records(verbatim events)", len(records))
G0 = build(tau=2.0, use_records=False, grounded_only=False)
evaluate("A dense (chunk)", G0, 0, "dense")
for tau in (0.8, 0.9, 2.0):
    G = build(tau=tau, use_records=False, grounded_only=False)
    print(f"  graph tau={tau}: phrases {G['P']} fact edges {G['n_fact']} synonym edges {G['n_syn']}")
    for pw in (0.05, 0.3, 1.0):
        evaluate(f"HR2 official-like tau={tau} pw={pw}", G, pw, "chunk")
Gg = build(tau=0.8, use_records=False, grounded_only=True)
print(f"  grounded-only facts {len(Gg['facts'])}")
for pw in (0.05, 0.3):
    evaluate(f"HR2 grounded triples tau=0.8 pw={pw}", Gg, pw, "chunk")
Gr = build(tau=0.8, use_records=True, grounded_only=True)
print(f"  records as passage nodes {len(Gr['recs'])}, phrases {Gr['P']}, synonym edges {Gr['n_syn']}")
for pw in (0.05, 0.3):
    evaluate(f"HR2+records chunk-rank pw={pw}", Gr, pw, "chunk")
    evaluate(f"HR2+records mixed-rank pw={pw}", Gr, pw, "mixed")
evaluate("dense mixed (records+chunks)", Gr, 0, "dense_mixed_placeholder") if False else None
