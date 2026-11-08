import json
import sys
from collections import defaultdict

PPR_ALPHA = 0.99
PPR_MAX_ITER = 2000
PPR_TOL = 1e-7
PASSAGE = "원문 청크"


def build_graph(extraction_path, concept_path):
    extraction = json.load(open(extraction_path))
    concepts = json.load(open(concept_path))["node_concepts"]
    edges = set()
    for stage in extraction["stages"].values():
        for _, head, _, _, tail in stage["triples"]:
            edges.add((head, tail))
            edges.add((head, PASSAGE))
            edges.add((tail, PASSAGE))
    for node, labels in concepts.items():
        for label in labels:
            edges.add((node, "개념:" + label))
    return edges


def pagerank(edges, personalization, directed):
    """networkx.pagerank 와 같은 식: 나가는 선으로만 걷고, 나가는 선이 없는 점의 몫은 출발 분포로 돌려보낸다."""
    if not directed:
        edges = edges | {(b, a) for a, b in edges}
    nodes = sorted({n for edge in edges for n in edge})
    out = defaultdict(list)
    for a, b in edges:
        out[a].append(b)
    total = sum(personalization.values())
    p = {n: personalization.get(n, 0) / total for n in nodes}
    x = {n: 1 / len(nodes) for n in nodes}
    for _ in range(PPR_MAX_ITER):
        dangling = sum(x[n] for n in nodes if not out[n])
        nxt = {n: (PPR_ALPHA * dangling + 1 - PPR_ALPHA) * p[n] for n in nodes}
        for a in nodes:
            for b in out[a]:
                nxt[b] += PPR_ALPHA * x[a] / len(out[a])
        if sum(abs(nxt[n] - x[n]) for n in nodes) < len(nodes) * PPR_TOL:
            return nxt
        x = nxt
    return x


def main(extraction_path, concept_path, *start_nodes):
    edges = build_graph(extraction_path, concept_path)
    personalization = {n: 1 for n in start_nodes}
    watched = [n for n in sorted({n for e in edges for n in e}) if not n.startswith("개념:")]
    concept_nodes = sorted({n for e in edges for n in e if n.startswith("개념:")})
    for directed in (True, False):
        scores = pagerank(edges, personalization, directed)
        print(f"\n=== {'방향 있음 (공식 nx.DiGraph)' if directed else '방향 없음 (비교용)'}  출발: {start_nodes}")
        for n in sorted(watched, key=lambda n: -scores[n]):
            print(f"  {scores[n]:.4f}  {n}")
        print(f"  개념 점 {len(concept_nodes)}개 합계 {sum(scores[n] for n in concept_nodes):.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
