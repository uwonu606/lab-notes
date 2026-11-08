import json, re, sys, math, urllib.request, urllib.error

GLOSSARY, CANDIDATE_TSV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
KNOWN_MISSING = [("git rebase", "rebase"), ("git commit --amend", "amend"),
                 ("Choi 2018", "UFET"), ("Choi 2018", "ultra-fine typing")]
THRESHOLDS = [0.6, 0.65, 0.7, 0.75, 0.8]


def normalize(text):
    lowered = text.casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()


def embed(texts):
    body = json.dumps({"model": "bge-m3", "input": texts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)["embeddings"]


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def embed_all(names):
    vectors, failed = {}, []
    for start in range(0, len(names), 16):
        batch = names[start:start + 16]
        try:
            pairs = list(zip(batch, embed(batch)))
        except urllib.error.HTTPError:
            pairs = []
            for name in batch:
                try:
                    pairs.append((name, embed([name])[0]))
                except urllib.error.HTTPError:
                    failed.append(name)
        for name, vec in pairs:
            vectors[name] = unit(vec)
    return vectors, failed


entries = json.load(open(GLOSSARY, encoding="utf-8"))
entry_names = [[normalize(n) for n in [e["canonical"], *e.get("aliases", [])] if normalize(n)] for e in entries]
covered = {n for names in entry_names for n in names}

candidates = set()
with open(CANDIDATE_TSV, encoding="utf-8") as f:
    next(f)
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and normalize(parts[1]):
            candidates.add(normalize(parts[1]))
for _, alias in KNOWN_MISSING:
    candidates.add(normalize(alias))
candidates -= covered
candidates = sorted(candidates)

import os
CACHE = OUT + ".vectors.json"
if os.path.exists(CACHE):
    cached = json.load(open(CACHE, encoding="utf-8"))
    vectors, failed_names = cached["vectors"], cached["failed"]
else:
    vectors, failed_names = embed_all(sorted(covered | set(candidates)))
    json.dump({"vectors": vectors, "failed": failed_names}, open(CACHE, "w", encoding="utf-8"))
candidates = [c for c in candidates if c in vectors]
entry_names = [[n for n in names if n in vectors] or names[:0] for names in entry_names]

def entry_score(idx, cand):
    cv = vectors[cand]
    return max((sum(a * b for a, b in zip(vectors[n], cv)) for n in entry_names[idx]), default=-1.0)

scores = [[entry_score(i, c) for c in candidates] for i in range(len(entries))]

lines = [f"embedding failed for {len(failed_names)} names: {failed_names[:10]}", f"glossary entries {len(entries)}, glossary names {len(covered)}, candidate names not in glossary {len(candidates)}"]
canon_index = {e["canonical"]: i for i, e in enumerate(entries)}
lines.append("\n=== known missing short forms (from round 22 answer-seen glossary)")
for canon, alias in KNOWN_MISSING:
    i = canon_index[canon]
    cand = normalize(alias)
    if cand not in candidates:
        lines.append(f"  {canon!r} <- {alias!r}: not embeddable or not a candidate")
        continue
    in_b1 = "yes" if cand in candidates else "no"
    row = sorted(zip(scores[i], candidates), reverse=True)
    rank = [c for _, c in row].index(cand) + 1
    best_entry = max(range(len(entries)), key=lambda j: scores[j][candidates.index(cand)])
    lines.append(f"  {canon!r} <- {alias!r}: cosine {scores[i][candidates.index(cand)]:.3f}, rank {rank}/{len(candidates)} within entry, "
                 f"best entry for this candidate = {entries[best_entry]['canonical']!r}, top3 of entry = {[(c, round(s, 3)) for s, c in row[:3]]}")

lines.append("\n=== review queue size if each candidate goes only to its best entry and cosine >= t")
best = [max(range(len(entries)), key=lambda j: scores[j][k]) for k in range(len(candidates))]
for t in THRESHOLDS:
    queued = [(candidates[k], entries[best[k]]["canonical"], scores[best[k]][k]) for k in range(len(candidates)) if scores[best[k]][k] >= t]
    hits = sum(1 for canon, alias in KNOWN_MISSING
               if any(c == normalize(alias) and e == canon for c, e, _ in queued))
    lines.append(f"  t={t}: queued pairs {len(queued)}, known missing found {hits}/{len(KNOWN_MISSING)}")

lines.append("\n=== review queue size if top-k candidates per entry")
for k in [1, 3, 5, 10]:
    hits = 0
    for canon, alias in KNOWN_MISSING:
        i = canon_index[canon]
        row = [c for _, c in sorted(zip(scores[i], candidates), reverse=True)[:k]]
        hits += normalize(alias) in row
    lines.append(f"  k={k}: queued pairs {k * len(entries)}, known missing found {hits}/{len(KNOWN_MISSING)}")

open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
