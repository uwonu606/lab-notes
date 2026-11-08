import sys, xml.etree.ElementTree as ET
from collections import Counter
ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
root = ET.parse(sys.argv[1]).getroot()
keys = {k.get("id"): k.get("attr.name") for k in root.findall("g:key", ns)}
graph = root.find("g:graph", ns)
print("edgedefault", graph.get("edgedefault"))
ntype = {}
for n in graph.findall("g:node", ns):
    for d in n.findall("g:data", ns):
        if keys.get(d.get("key")) == "type":
            ntype[n.get("id")] = d.text
out = Counter(); inn = Counter(); etypes = Counter()
for e in graph.findall("g:edge", ns):
    s, t = e.get("source"), e.get("target")
    out[s] += 1; inn[t] += 1
    etypes[(ntype.get(s), ntype.get(t))] += 1
print("edge (src type, dst type)", etypes.most_common())
for ty in sorted(set(ntype.values())):
    nodes = [n for n, v in ntype.items() if v == ty]
    print(ty, len(nodes), "out-degree 0:", sum(out[n] == 0 for n in nodes), "in-degree 0:", sum(inn[n] == 0 for n in nodes))
