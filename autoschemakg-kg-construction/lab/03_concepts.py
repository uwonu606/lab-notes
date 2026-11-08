import json
import random
import sys
import urllib.request
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

spec = spec_from_file_location("three_stages", Path(__file__).parent / "01_three_stages.py")
three_stages = module_from_spec(spec)
spec.loader.exec_module(three_stages)

CONCEPT_INSTRUCTIONS = three_stages.load_literal("CONCEPT_INSTRUCTIONS")
SEED = three_stages.SEED
OLLAMA_CHAT = three_stages.OLLAMA_CHAT


def ask(model, prompt):
    body = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.7, "seed": SEED},
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(OLLAMA_CHAT, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())["message"]["content"]


def load_graph(run_path):
    record = json.loads(Path(run_path).read_text())
    kind, edges = {}, []
    for stage in record["stages"].values():
        for head_kind, head, relation, tail_kind, tail in stage["triples"]:
            kind.setdefault(head, head_kind)
            kind.setdefault(tail, tail_kind)
            edges.append((head, relation, tail))
    return kind, edges


def entity_context(node, edges, rng):
    predecessors = [(h, r) for h, r, t in edges if t == node]
    successors = [(r, t) for h, r, t in edges if h == node]
    context = ""
    if predecessors:
        context += ", ".join(f"{h} {r}" for h, r in rng.sample(predecessors, 1))
    if successors:
        context += ", ".join(f"{r} {t}" for r, t in rng.sample(successors, 1))
    return context


def concepts_of(model, node, node_kind, edges, rng):
    template = CONCEPT_INSTRUCTIONS["en"][node_kind]
    if node_kind == "entity":
        context = entity_context(node, edges, rng)
        prompt = template.replace("[ENTITY]", node).replace("[CONTEXT]", context)
    else:
        context = None
        prompt = template.replace("[EVENT]", node)
    raw = ask(model, prompt)
    labels = [x.strip().lower() for x in raw.split(",")]
    return context, raw, [label for label in labels if label]


def components(nodes, links):
    parent = {n: n for n in nodes}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for a, b in links:
        parent[find(a)] = find(b)
    groups = defaultdict(list)
    for n in nodes:
        groups[find(n)].append(n)
    return sorted(groups.values(), key=len, reverse=True)


def main(run_path, model, out_path):
    rng = random.Random(SEED)
    kind, edges = load_graph(run_path)
    node_concepts = {}
    print("=== 노드마다 붙은 개념 이름표 (소문자, 쉼표로 자름)")
    for node in sorted(kind, key=lambda n: (kind[n], n)):
        context, raw, labels = concepts_of(model, node, kind[node], edges, rng)
        node_concepts[node] = labels
        shown_context = f"  CONTEXT='{context}'" if context is not None else ""
        print(f"  [{kind[node]}] {node}{shown_context}\n      -> {labels}")

    concept_nodes = defaultdict(list)
    for node, labels in node_concepts.items():
        for label in labels:
            concept_nodes[label].append(node)
    print(f"\n=== 개념 문자열 집합: {len(concept_nodes)}개. 둘 이상의 노드가 같은 문자열을 낸 개념")
    for label, members in sorted(concept_nodes.items(), key=lambda kv: -len(kv[1])):
        if len(members) > 1:
            print(f"  '{label}' <- {members}")

    events = [n for n in kind if kind[n] == "event"]
    print("\n=== 이벤트 쌍마다 겹친 이름표")
    for a, b in combinations(sorted(events), 2):
        shared = sorted(set(node_concepts[a]) & set(node_concepts[b]))
        if shared:
            print(f"  {a}\n  {b}\n      겹침 {shared}")

    before = components(list(kind), [(h, t) for h, _, t in edges])
    concept_links = [(n, "concept:" + c) for n, labels in node_concepts.items() for c in labels]
    after = components(list(kind) + ["concept:" + c for c in concept_nodes], [(h, t) for h, _, t in edges] + concept_links)
    print("\n=== 연결 덩어리 (방향 무시)")
    print(f"  개념 전: {len(before)}덩어리")
    for group in before:
        print(f"    {group}")
    print(f"  개념 후: {len(after)}덩어리 (개념 노드 {len(concept_nodes)}개 포함)")
    print(f"  원래 노드 수는 그대로 {len(kind)}개. 개념은 노드를 합치지 않고 has_concept 선만 더한다")

    Path(out_path).write_text(json.dumps(
        {"model": model, "seed": SEED, "run": run_path, "node_concepts": node_concepts,
         "concept_nodes": concept_nodes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
