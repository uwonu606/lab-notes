import sys, runpy, json
from collections import Counter
import numpy as np
sys.argv = ["hr2_pilot.py", sys.argv[1], sys.argv[2]]
src = open("hr2_pilot.py").read().split('print("triples"')[0]
ns = {}
exec(compile(src, "hr2_pilot.py", "exec"), ns)
chunks, questions, units, offset, cid_index = ns["chunks"], ns["questions"], ns["units"], ns["offset"], ns["cid_index"]
encode, recall, records, build, retrieve = ns["encode"], ns["recall"], ns["records"], ns["build"], ns["retrieve"]
nC = len(chunks)
cv = encode([c["text"] for c in chunks])
rv = encode([r["text"] for r in records])
rec_by_chunk = {}
for i, r in enumerate(records):
    rec_by_chunk.setdefault(r["chunk"], []).append(i)

G = build(tau=0.8, use_records=False, grounded_only=False)
top1 = Counter()
deg = (G["A"] > 0).sum(1)[G["P"]:]
for q in questions:
    s, _ = retrieve(G, q["question"], 0.05)
    top1[chunks[int(np.argmax(s[:nC]))]["id"]] += 1
print("PPR pw=0.05 top-1 chunk counts (top 5):", top1.most_common(5))
print("passage degree of those:", {k: int(deg[cid_index[k]]) for k, _ in top1.most_common(5)}, "median passage degree", int(np.median(deg)))

def chunk_piece(i):
    c = chunks[i]; return (c["id"].split("#")[0], offset[c["id"]], offset[c["id"]] + len(c["text"]))
def rec_piece(j):
    r = records[j]; return (r["chunk"].split("#")[0], offset[r["chunk"]] + r["start"], offset[r["chunk"]] + r["end"])

def fill(seq, B):
    out, left, taken = [], B, []
    for p in seq:
        if left <= 0: break
        d, s, e = p
        if any(d == d2 and a <= s and e <= b for d2, a, b in taken): continue
        out.append((d, s, min(e, s + left))); left -= e - s; taken.append(p)
    return out

rows = {k: {B: [] for B in (1000, 2500, 5000)} for k in ("dense", "pack5", "pack5_thr", "maxsim")}
at5 = {"dense": [], "maxsim": []}
for q in questions:
    qv = encode([q["question"]])[0]
    cs = cv @ qv; rs = rv @ qv
    order = list(np.argsort(-cs))
    ms = cs.copy()
    for cid, idx in rec_by_chunk.items():
        ms[cid_index[cid]] = max(ms[cid_index[cid]], rs[idx].max())
    morder = list(np.argsort(-ms))
    gold = set(q["gold"])
    at5["dense"].append(len(gold & {chunks[i]["id"] for i in order[:5]}) / len(gold))
    at5["maxsim"].append(len(gold & {chunks[i]["id"] for i in morder[:5]}) / len(gold))
    top5 = order[:5]
    recs = sorted([j for i in top5 for j in rec_by_chunk.get(chunks[i]["id"], [])], key=lambda j: -rs[j])
    pack = [rec_piece(j) for j in recs] + [chunk_piece(i) for i in order]
    thr = [rec_piece(j) for j in recs if rs[j] >= cs[top5[0]] - 0.05]
    pack_thr = thr + [chunk_piece(i) for i in order]
    for B in (1000, 2500, 5000):
        rows["dense"][B].append(recall(fill([chunk_piece(i) for i in order], B), units[q["id"]]))
        rows["pack5"][B].append(recall(fill(pack, B), units[q["id"]]))
        rows["pack5_thr"][B].append(recall(fill(pack_thr, B), units[q["id"]]))
        rows["maxsim"][B].append(recall(fill([chunk_piece(i) for i in morder], B), units[q["id"]]))
for k, v in rows.items():
    print(f"{k:10s}", " ".join(f"{B}자 {np.mean(x):.3f}" for B, x in v.items()), (f"@5 {np.mean(at5[k]):.3f}" if k in at5 else ""))
