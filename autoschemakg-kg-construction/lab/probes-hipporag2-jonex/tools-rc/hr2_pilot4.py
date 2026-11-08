import sys
import numpy as np
sys.argv = ["hr2_pilot.py", sys.argv[1], sys.argv[2]]
src = open("hr2_pilot.py").read().split('print("triples"')[0]
ns = {}; exec(compile(src, "hr2_pilot.py", "exec"), ns)
chunks, questions, units, offset = ns["chunks"], ns["questions"], ns["units"], ns["offset"]
encode, recall, records, build, retrieve = ns["encode"], ns["recall"], ns["records"], ns["build"], ns["retrieve"]
nC = len(chunks); rv = encode([r["text"] for r in records])
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
G = build(tau=0.8, use_records=False, grounded_only=False)
for pw in (0.05, 0.3, 1.0):
    r1, r25, r5, at5 = [], [], [], []
    for q in questions:
        s, ds = retrieve(G, q["question"], pw)
        order = list(np.argsort(-s[:nC])); top5 = order[:5]
        qv = encode([q["question"]])[0]; rs = rv @ qv
        best = max(ds[i] for i in top5)
        recs = sorted([j for i in top5 for j in rec_by_chunk.get(chunks[i]["id"], [])], key=lambda j: -rs[j])
        seq = [rp(j) for j in recs if rs[j] >= best - 0.05] + [cp(i) for i in order]
        r1.append(recall(fill(seq, 1000), units[q["id"]])); r25.append(recall(fill(seq, 2500), units[q["id"]])); r5.append(recall(fill(seq, 5000), units[q["id"]]))
        gold = set(q["gold"]); at5.append(len(gold & {chunks[i]["id"] for i in top5}) / len(gold))
    print(f"PPR pw={pw} + record packing: @5 {np.mean(at5):.3f} 1000자 {np.mean(r1):.3f} 2500자 {np.mean(r25):.3f} 5000자 {np.mean(r5):.3f}")
