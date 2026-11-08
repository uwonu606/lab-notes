import json, re, sys, urllib.request, itertools, math

GLOSSARY = sys.argv[1]
OUT = sys.argv[2]
THRESHOLDS = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]

def hipporag_text_processing(text):
    lowered = text.casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()

def passes_hipporag_synonym_query_gate(phrase):
    return len(re.sub('[^A-Za-z0-9]', '', phrase)) > 2

def embed(texts):
    body = json.dumps({"model": "bge-m3", "input": texts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)["embeddings"]

def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))

entries = json.load(open(GLOSSARY, encoding="utf-8"))
name_to_entry = {}
for idx, entry in enumerate(entries):
    for raw in [entry["canonical"], *entry.get("aliases", [])]:
        name = hipporag_text_processing(raw)
        if name:
            name_to_entry.setdefault(name, set()).add(idx)

names = sorted(name_to_entry)
vectors = {}
for start in range(0, len(names), 64):
    batch = names[start:start + 64]
    for name, vec in zip(batch, embed(batch)):
        vectors[name] = unit(vec)

same, diff = [], []
for a, b in itertools.combinations(names, 2):
    s = cosine(vectors[a], vectors[b])
    if name_to_entry[a] & name_to_entry[b]:
        same.append((s, a, b))
    else:
        diff.append((s, a, b))

def quantiles(values):
    v = sorted(values)
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1)))]
    return {q: round(pick(q), 3) for q in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)}

lines = []
lines.append(f"glossary entries {len(entries)}, distinct normalized names {len(names)}")
lines.append(f"same-entry pairs {len(same)}, different-entry pairs {len(diff)}")
lines.append(f"same quantiles {quantiles([s for s, _, _ in same])}")
lines.append(f"diff quantiles {quantiles([s for s, _, _ in diff])}")
for t in THRESHOLDS:
    tp = sum(1 for s, _, _ in same if s >= t)
    fp = sum(1 for s, _, _ in diff if s >= t)
    prec = tp / (tp + fp) if tp + fp else float('nan')
    lines.append(f"threshold {t}: same>=t {tp}/{len(same)} ({tp/len(same):.3f}), diff>=t {fp}/{len(diff)}, precision {prec:.3f}")

def gate_pair(a, b):
    return passes_hipporag_synonym_query_gate(a) or passes_hipporag_synonym_query_gate(b)
same_gate = [p for p in same if gate_pair(p[1], p[2])]
lines.append(f"same-entry pairs where at least one side passes the ASCII>2 gate: {len(same_gate)}/{len(same)}")
same_ge08 = [p for p in same if p[0] >= 0.8]
lines.append(f"same-entry pairs >=0.8 that the official gate would keep: {sum(1 for p in same_ge08 if gate_pair(p[1], p[2]))}/{len(same_ge08)}")
hangul = re.compile(r"[가-힣]")
def kind(p):
    ka, kb = bool(hangul.search(p[1])), bool(hangul.search(p[2]))
    return "ko-ko" if ka and kb else ("en-en" if not ka and not kb else "ko-en")
for k in ("ko-ko", "ko-en", "en-en"):
    sub = [s for s, a, b in same if kind((s, a, b)) == k]
    subd = [s for s, a, b in diff if kind((s, a, b)) == k]
    if sub:
        lines.append(f"{k}: same n={len(sub)} median {quantiles(sub)[0.5]} share>=0.8 {sum(1 for s in sub if s>=0.8)/len(sub):.3f}; diff n={len(subd)} share>=0.8 {sum(1 for s in subd if s>=0.8)/max(1,len(subd)):.4f}")
lines.append("top 15 different-entry pairs:")
for s, a, b in sorted(diff, reverse=True)[:15]:
    lines.append(f"  {s:.3f}  {a} | {b}  entries {sorted(name_to_entry[a])} {sorted(name_to_entry[b])}")
lines.append("lowest 10 same-entry pairs:")
for s, a, b in sorted(same)[:10]:
    lines.append(f"  {s:.3f}  {a} | {b}")
extra = [("매출", "수익"), ("품질팀", "품질 관리팀"), ("배포 파이프라인", "ci 파이프라인"), ("회의록", "미팅 노트"), ("2024년 매출", "2025년 매출"), ("초안", "최종본")]
ev = embed([x for pair in extra for x in pair])
lines.append("hand-picked pairs (not from the glossary):")
for i, (a, b) in enumerate(extra):
    lines.append(f"  {cosine(unit(ev[2*i]), unit(ev[2*i+1])):.3f}  {a} | {b}")
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
