import sys
import numpy as np
sys.argv = ["hr2_pilot.py", sys.argv[1], sys.argv[2]]
src = open("hr2_pilot.py").read().split('print("triples"')[0]
ns = {}; exec(compile(src, "hr2_pilot.py", "exec"), ns)
chunks, questions, units, offset, cid_index = ns["chunks"], ns["questions"], ns["units"], ns["offset"], ns["cid_index"]
encode, recall, records, text_processing, triples = ns["encode"], ns["recall"], ns["records"], ns["text_processing"], ns["triples"]
surf = {}
for _, h, _, t in triples:
    for x in (h, t): surf.setdefault(text_processing(x), x)
keys = list(surf); pv = encode([surf[k] for k in keys]); S = pv @ pv.T
iu = np.triu_indices(len(keys), 1); vals = S[iu]
for lo, hi in ((0.7, 0.8), (0.75, 0.8), (0.8, 2), (0.85, 2), (0.9, 2)):
    print(f"phrase pairs cos in [{lo},{hi}):", int(((vals >= lo) & (vals < hi)).sum()), "of", len(vals), "phrases", len(keys))
nC = len(chunks); cv = encode([c["text"] for c in chunks]); rv = encode([r["text"] for r in records])
rec_by_chunk = {}
for i, r in enumerate(records): rec_by_chunk.setdefault(r["chunk"], []).append(i)
cp = lambda i: (chunks[i]["id"].split("#")[0], offset[chunks[i]["id"]], offset[chunks[i]["id"]] + len(chunks[i]["text"]))
rp = lambda j: (records[j]["chunk"].split("#")[0], offset[records[j]["chunk"]] + records[j]["start"], offset[records[j]["chunk"]] + records[j]["end"])
def fill(seq, B):
    out, left, taken = [], B, []
    for p in seq:
        if left <= 0: break
        d, s, e = p
        if any(d == d2 and a <= s and e <= b for d2, a, b in taken): continue
        out.append((d, s, min(e, s + left))); left -= e - s; taken.append(p)
    return out
halves = {"all": questions, "odd": questions[1::2], "even": questions[0::2]}
for delta in (0.0, 0.03, 0.05, 0.08, 0.1, 0.15):
    line = []
    for name, qs in halves.items():
        r1 = []; r25 = []
        for q in qs:
            qv = encode([q["question"]])[0]; cs = cv @ qv; rs = rv @ qv
            order = list(np.argsort(-cs)); top5 = order[:5]
            recs = sorted([j for i in top5 for j in rec_by_chunk.get(chunks[i]["id"], [])], key=lambda j: -rs[j])
            seq = [rp(j) for j in recs if rs[j] >= cs[top5[0]] - delta] + [cp(i) for i in order]
            r1.append(recall(fill(seq, 1000), units[q["id"]])); r25.append(recall(fill(seq, 2500), units[q["id"]]))
        line.append(f"{name} 1000자 {np.mean(r1):.3f} 2500자 {np.mean(r25):.3f}")
    print(f"delta {delta:.2f}: " + " | ".join(line))
