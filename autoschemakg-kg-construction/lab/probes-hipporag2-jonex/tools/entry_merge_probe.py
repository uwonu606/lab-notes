import json, re, sys

GLOSSARY, VECTOR_CACHE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
KNOWN_SAME = [("git rebase", "rebase"), ("git commit --amend", "amend"),
              ("Choi 2018", "UFET"), ("Choi 2018", "ultra-fine typing")]
THRESHOLDS = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85]


def normalize(text):
    lowered = text.casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()


entries = json.load(open(GLOSSARY, encoding="utf-8"))
vectors = json.load(open(VECTOR_CACHE, encoding="utf-8"))["vectors"]
names = [[normalize(n) for n in [e["canonical"], *e.get("aliases", [])] if normalize(n) in vectors] for e in entries]
canon = [e["canonical"] for e in entries]
index = {c: i for i, c in enumerate(canon)}


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def entry_similarity(i, j):
    return max(dot(vectors[a], vectors[b]) for a in names[i] for b in names[j])


n = len(entries)
sim = [[entry_similarity(i, j) if i != j else -1.0 for j in range(n)] for i in range(n)]

lines = [f"entries {n}, entry pairs {n * (n - 1) // 2}"]
lines.append("\n=== known same-target entry pairs (round 22 answer-seen merges)")
for a, b in KNOWN_SAME:
    i, j = index[a], index[b]
    row = sorted(range(n), key=lambda k: sim[i][k], reverse=True)
    lines.append(f"  {a!r} ~ {b!r}: cosine {sim[i][j]:.3f}, rank of {b!r} among neighbours of {a!r}: {row.index(j) + 1}/{n - 1}; "
                 f"top3 = {[(canon[k], round(sim[i][k], 3)) for k in row[:3]]}")

pairs = sorted(((sim[i][j], canon[i], canon[j]) for i in range(n) for j in range(i + 1, n)), reverse=True)
known = {frozenset(p) for p in KNOWN_SAME}
lines.append("\n=== review queue (entry pairs with cosine >= t)")
for t in THRESHOLDS:
    queued = [p for p in pairs if p[0] >= t]
    hits = sum(1 for _, a, b in queued if frozenset((a, b)) in known)
    lines.append(f"  t={t}: queued pairs {len(queued)}, known same found {hits}/{len(KNOWN_SAME)}")
lines.append("\n=== top 30 entry pairs")
for s, a, b in pairs[:30]:
    mark = " <known>" if frozenset((a, b)) in known else ""
    lines.append(f"  {s:.3f}  {a} ~ {b}{mark}")

open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
