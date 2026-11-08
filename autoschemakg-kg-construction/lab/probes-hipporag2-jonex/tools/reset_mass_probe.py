import json, sys, math, urllib.request

CHUNKS, QUESTIONS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PASSAGE_NODE_WEIGHT = {"official HippoRAG 2": 0.05, "AutoSchemaKG default": 1.0}

def embed(texts):
    body = json.dumps({"model": "bge-m3", "input": texts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.load(resp)["embeddings"]

def unit(v):
    n = math.sqrt(sum(x * x for x in v)); return [x / n for x in v]

chunks = [json.loads(line) for line in open(CHUNKS, encoding="utf-8") if line.strip()]
questions = json.load(open(QUESTIONS, encoding="utf-8"))
chunk_vecs = []
for i in range(0, len(chunks), 8):
    chunk_vecs += [unit(v) for v in embed([c["text"] for c in chunks[i:i + 8]])]
question_vecs = [unit(v) for v in embed([q["question"] for q in questions])]

sums = []
for qv in question_vecs:
    scores = [sum(a * b for a, b in zip(qv, cv)) for cv in chunk_vecs]
    lo, hi = min(scores), max(scores)
    sums.append(sum((s - lo) / (hi - lo) for s in scores))
mean_sum = sum(sums) / len(sums)
lines = [f"chunks {len(chunks)}, questions {len(questions)}",
         f"sum of min-max normalized dense scores per question: mean {mean_sum:.2f}, min {min(sums):.2f}, max {max(sums):.2f}"]
for label, w in PASSAGE_NODE_WEIGHT.items():
    passage_mass = w * mean_sum
    for phrase_mass in (1.0, 2.5, 5.0):
        share = passage_mass / (passage_mass + phrase_mass)
        lines.append(f"{label} weight {w}: passage reset mass {passage_mass:.2f}; if phrase seed mass {phrase_mass} -> passage share after normalization {share:.2f}")
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
