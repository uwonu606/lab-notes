import json, re, sys, math, operator, itertools, urllib.request
from collections import defaultdict
from pathlib import Path

LAB = Path(sys.argv[1])
OUT = Path(sys.argv[2])
NEW_DOC = "doc-parsing-chunking"
BANDS = [(0.9, 1.01), (0.8, 0.9), (0.7, 0.8), (0.6, 0.7)]
SYNONYM_EDGE_THRESHOLD = 0.8
DAMPING = 0.5


def hipporag_text_processing(text):
    lowered = str(text).casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()


def mentions(form, text):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(form) + r"(?![A-Za-z0-9])", text, re.I) is not None


def embed(texts):
    vectors = []
    for start in range(0, len(texts), 64):
        body = json.dumps({"model": "bge-m3", "input": texts[start:start + 64]}).encode()
        req = urllib.request.Request("http://localhost:11434/api/embed", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                vectors.extend(json.load(resp)["embeddings"])
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"batch {start}: {err.read()[:300]!r} sample {texts[start:start+3]!r} maxlen {max(len(t) for t in texts[start:start+64])}")
    return vectors


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def cosine(a, b):
    return sum(map(operator.mul, a, b))


chunks = [json.loads(l) for l in (LAB / "inputs/12-chunks.jsonl").read_text().splitlines() if l.strip()]
chunk_text = {c["id"]: c["text"] for c in chunks}
new_ids = [c for c in chunk_text if c.startswith(NEW_DOC)]
old_ids = [c for c in chunk_text if not c.startswith(NEW_DOC)]
glossary = json.loads((LAB / "inputs/12-glossary.json").read_text())
gold = {(l["new"], x["old"]) for l in json.loads((LAB / "inputs/12-links.json").read_text()) for x in l["links"]}

terms_in_chunk = {cid: {e["canonical"] for e in glossary
                        if any(mentions(f, t) for f in [e["canonical"], *e["aliases"]])}
                  for cid, t in chunk_text.items()}
glossary_pairs = {(n, o) for n in new_ids for o in old_ids if terms_in_chunk[n] & terms_in_chunk[o]}

phrase_chunks = defaultdict(set)
fact_edges = defaultdict(int)
for cid in chunk_text:
    cache = json.loads((LAB / "runs/12-cache" / (cid.replace("#", "_") + ".json")).read_text())
    for t in cache.get("entity_relation_dict") or []:
        h, tl = hipporag_text_processing(t.get("Head", "")), hipporag_text_processing(t.get("Tail", ""))
        if not h or not tl:
            continue
        phrase_chunks[h].add(cid)
        phrase_chunks[tl].add(cid)
        if h != tl:
            fact_edges[tuple(sorted((h, tl)))] += 1

glossary_name_entry = defaultdict(set)
for idx, e in enumerate(glossary):
    for f in [e["canonical"], *e["aliases"]]:
        n = hipporag_text_processing(f)
        if n:
            glossary_name_entry[n].add(idx)

phrases = sorted(phrase_chunks)
names_to_embed = sorted(set(phrases) | set(glossary_name_entry))
vec = {n: unit(v) for n, v in zip(names_to_embed, embed(names_to_embed))}

lines = []
lines.append(f"chunks {len(chunk_text)} new {len(new_ids)} old {len(old_ids)} gold pairs {len(gold)}")
lines.append(f"glossary word-boundary pairs {len(glossary_pairs)} correct {len(glossary_pairs & gold)}")
lines.append(f"phrases (llama3.1:8b entity_relation, normalized) {len(phrases)}; glossary names {len(glossary_name_entry)}")

new_phrases = sorted({p for p in phrases if phrase_chunks[p] & set(new_ids)})
new_only = [p for p in new_phrases if not (phrase_chunks[p] & set(old_ids))]
lines.append(f"new-doc phrases {len(new_phrases)}; of which appear only in new doc {len(new_only)}; already a glossary name {sum(1 for p in new_phrases if p in glossary_name_entry)}")


def contained(a, b):
    return a in b or b in a


lines.append("")
lines.append("== term-pair review items: new-doc phrase (not a glossary name) x glossary entry, best name cosine per entry")
term_items = []
for p in new_phrases:
    if p in glossary_name_entry:
        continue
    best = {}
    for name, entries in glossary_name_entry.items():
        s = cosine(vec[p], vec[name])
        for idx in entries:
            if s > best.get(idx, (-1, None))[0]:
                best[idx] = (s, name)
    for idx, (s, name) in best.items():
        if s >= BANDS[-1][0]:
            term_items.append((s, p, glossary[idx]["canonical"], name, contained(p, name)))
for lo, hi in BANDS:
    band = [t for t in term_items if lo <= t[0] < hi]
    lines.append(f"  band [{lo},{min(hi,1.0)}): items {len(band)}  containment {sum(1 for t in band if t[4])}  distinct phrases {len({t[1] for t in band})}")
lines.append("  items >= 0.7 (cos, new phrase, glossary canonical, matched name, containment):")
for t in sorted(term_items, reverse=True):
    if t[0] >= 0.7:
        lines.append(f"    {t[0]:.3f}  {t[1]} | {t[2]} ({t[3]}) {'C' if t[4] else ''}")


def new_pairs_from_item(p, canonical):
    entry = next(e for e in glossary if e["canonical"] == canonical)
    olds = {o for o in old_ids if canonical in terms_in_chunk[o]}
    return {(n, o) for n in phrase_chunks[p] if n in new_ids for o in olds}


lines.append("")
lines.append("== chunk pairs that approving term items would add (beyond glossary pairs), per band")
for lo, hi in BANDS:
    added = set()
    for t in term_items:
        if lo <= t[0] < hi:
            added |= new_pairs_from_item(t[1], t[2]) - glossary_pairs
    lines.append(f"  band [{lo},{min(hi,1.0)}): new chunk pairs {len(added)}  in old gold {len(added & gold)}")

lines.append("")
lines.append("== HippoRAG-style synonym edges among all phrases (cos >= 0.8), new<->old crossing")
syn = {}
for a, b in itertools.combinations(phrases, 2):
    if len(a) < 2 or len(b) < 2:
        continue
    s = cosine(vec[a], vec[b])
    if s >= 0.6:
        syn[(a, b)] = s
crossing = {k: s for k, s in syn.items()
            if (phrase_chunks[k[0]] & set(new_ids) and phrase_chunks[k[1]] & set(old_ids))
            or (phrase_chunks[k[1]] & set(new_ids) and phrase_chunks[k[0]] & set(old_ids))}
for lo, hi in BANDS:
    lines.append(f"  all-phrase pairs in [{lo},{min(hi,1.0)}): {sum(1 for s in syn.values() if lo <= s < hi)}   new<->old crossing: {sum(1 for s in crossing.values() if lo <= s < hi)}")
lines.append("  crossing pairs >= 0.8:")
for (a, b), s in sorted(crossing.items(), key=lambda kv: -kv[1]):
    if s >= 0.8:
        lines.append(f"    {s:.3f}  {a} | {b}")


def build_graph(with_synonyms):
    adj = defaultdict(dict)
    def add(u, v, w):
        adj[u][v] = max(adj[u].get(v, 0.0), w)
        adj[v][u] = max(adj[v].get(u, 0.0), w)
    for (a, b), c in fact_edges.items():
        add(("p", a), ("p", b), float(c))
    for p, cs in phrase_chunks.items():
        for c in cs:
            add(("c", c), ("p", p), 1.0)
    if with_synonyms:
        for (a, b), s in syn.items():
            if s >= SYNONYM_EDGE_THRESHOLD:
                add(("p", a), ("p", b), s)
    return adj


def ppr(adj, reset, iters=60):
    total = sum(reset.values())
    reset = {k: v / total for k, v in reset.items()}
    out_w = {u: sum(nb.values()) for u, nb in adj.items()}
    score = dict(reset)
    for _ in range(iters):
        nxt = defaultdict(float)
        for u, s in score.items():
            if out_w.get(u):
                for v, w in adj[u].items():
                    nxt[v] += DAMPING * s * w / out_w[u]
            else:
                nxt[u] += DAMPING * s
        for k, v in reset.items():
            nxt[k] += (1 - DAMPING) * v
        score = nxt
    return score


emb_cache = json.loads((LAB / "runs/12-cache/embeddings.json").read_text())
chunk_vec = {cid: unit(emb_cache[t]) for cid, t in chunk_text.items() if t in emb_cache}
lines.append("")
lines.append(f"chunk vectors found in 12-cache/embeddings.json: {len(chunk_vec)}/{len(chunk_text)}")


def rank_old_by_ppr(adj, n):
    reset = {("p", p): 1.0 / len(phrase_chunks[p]) for p in phrase_chunks if n in phrase_chunks[p]}
    reset[("c", n)] = reset.get(("c", n), 0.0) + 0.0
    sc = ppr(adj, reset)
    return sorted(old_ids, key=lambda o: -sc.get(("c", o), 0.0))


def rank_old_by_dense(n):
    return sorted(old_ids, key=lambda o: -cosine(chunk_vec[n], chunk_vec[o]))


def report(label, ranker):
    lines.append(f"== {label}")
    for k in (3, 5, 10):
        found = {(n, o) for n in new_ids for o in ranker(n)[:k]}
        outside = found - glossary_pairs
        lines.append(f"  top-{k}/new chunk: candidates {len(found)} correct {len(found & gold)} R {len(found & gold)/len(gold):.2f} P {len(found & gold)/len(found):.2f}  | not sharing a glossary term {len(outside)}")


g_syn = build_graph(True)
g_nosyn = build_graph(False)
report("PPR (undirected, damping 0.5, node specificity, synonym edges >=0.8)", lambda n: rank_old_by_ppr(g_syn, n))
report("PPR without synonym edges", lambda n: rank_old_by_ppr(g_nosyn, n))
if len(chunk_vec) == len(chunk_text):
    report("dense chunk cosine (bge-m3 cache)", rank_old_by_dense)

lines.append("")
lines.append("== top-5 PPR candidates per new chunk that share no glossary term (review-log chunk items)")
for n in new_ids:
    picks = [o for o in rank_old_by_ppr(g_syn, n)[:5] if (n, o) not in glossary_pairs]
    lines.append(f"  {n}: {picks}")

OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))

diag = []
diag.append("== reachability: old chunks with PPR score > 1e-9 per new chunk, and gold among them")
for label, g in (("with synonyms", g_syn), ("no synonyms", g_nosyn)):
    tot_reach, tot_gold = 0, 0
    for n in new_ids:
        reset = {("p", p): 1.0 / len(phrase_chunks[p]) for p in phrase_chunks if n in phrase_chunks[p]}
        sc = ppr(g, reset)
        reach = [o for o in old_ids if sc.get(("c", o), 0.0) > 1e-9]
        hit = [o for o in reach if (n, o) in gold]
        tot_reach += len(reach); tot_gold += len(hit)
        diag.append(f"  {label} {n}: seeds {len(reset)} reachable old {len(reach)} gold reachable {len(hit)}/{sum(1 for x in gold if x[0]==n)}")
    diag.append(f"  {label} total reachable pairs {tot_reach}, gold reachable {tot_gold}/25")
diag.append("== new-doc phrases that also appear in old chunks: " + repr([p for p in new_phrases if phrase_chunks[p] & set(old_ids)]))
diag.append("== does any new-doc phrase contain 'autoschemakg': " + repr([p for p in new_phrases if 'autoschema' in p]))
with OUT.open("a") as f:
    f.write("\n".join(diag) + "\n")
print("\n".join(diag))
