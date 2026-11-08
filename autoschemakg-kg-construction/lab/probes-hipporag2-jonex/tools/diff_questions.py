import json, sys
from collections import Counter
a = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1])}
b = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2])}
variants_a = [k for k in next(iter(a.values())) if k not in ("id","type","gold")]
variants_b = [k for k in next(iter(b.values())) if k not in ("id","type","gold")]
print("variants", variants_a, variants_b)
for qid in a:
    row = {**a[qid], **{k: v for k, v in b.get(qid, {}).items() if k in variants_b}}
    hits = {v: row[v]["hits"] for v in variants_a + variants_b}
    if len(set(hits.values())) > 1:
        print(qid, row["type"], hits)
overlap = Counter()
for qid in a:
    s = set(a[qid]["A"]["found"]); t = set(a[qid]["B1"]["found"])
    overlap[len(s & t)] += 1
print("A∩B1 top5 overlap", sorted(overlap.items()))
for v in variants_a + variants_b:
    rows = [{**a[q], **b.get(q, {})} for q in a]
    for kind in ("single", "bridge"):
        sub = [r for r in rows if r["type"] == kind]
        print(v, kind, round(sum(r[v]["recall"] for r in sub)/len(sub), 3), sum(r[v]["all"] for r in sub))
    if v.startswith("B"):
        print(v, "start_nodes", Counter(r[v]["start_nodes"] for r in rows).most_common())
