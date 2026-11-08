import json, sys
qs = json.load(open(sys.argv[1]))
a = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2])}
b = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[3])}
def kind(q):
    g = q["gold"]
    if len(g) == 1: return "single"
    d = [x.split("#") for x in g]
    if d[0][0] != d[1][0]: return "bridge-crossdoc"
    if abs(int(d[0][1]) - int(d[1][1])) == 1: return "bridge-adjacent"
    return "bridge-samedoc"
groups = {}
for q in qs:
    groups.setdefault(kind(q), []).append(q["id"])
for k, ids in groups.items():
    line = [k, len(ids)]
    for v in ("A","B1","B2"):
        line.append(f"{v} {sum(a[i][v]['recall'] for i in ids)/len(ids):.3f}")
    for v in ("B3","B3m"):
        line.append(f"{v} {sum(b[i][v]['recall'] for i in ids)/len(ids):.3f}")
    print(*line, ids)
