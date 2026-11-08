import json
import re
import sys
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import networkx as nx
import numpy as np

LAB = Path(__file__).parent
SCHEMA = LAB / "inputs/12-schema.json"
GLOSSARY = LAB / "inputs/12-glossary.json"
STRUCTURE = LAB / "inputs/12-structure.json"
LINKS = LAB / "inputs/12-links.json"
CACHE = LAB / "runs/13-cache"
NEW_DOC = "doc-parsing-chunking"
NUM_CTX = 8192
STAGES = ["entity_relation", "event_entity", "event_relation"]


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kgd = load("kg_vs_dense", LAB / "12_kg_vs_dense.py")


def surface_key(name):
    return re.sub(r"\s+", " ", str(name).strip().strip("`'\"“”‘’").casefold())


def read_glossary():
    entries = json.loads(GLOSSARY.read_text())
    canonical_of = {}
    for entry in entries:
        for form in [entry["canonical"], *entry["aliases"]]:
            canonical_of[surface_key(form)] = entry["canonical"]
    return entries, canonical_of


def glossary_in(text, entries):
    folded = text.casefold()
    return [e for e in entries if any(form.casefold() in folded for form in [e["canonical"], *e["aliases"]])]


def ordered_chunks():
    chunks = kgd.read_chunks()
    return [c for c in chunks if not c["id"].startswith(NEW_DOC)] + [c for c in chunks if c["id"].startswith(NEW_DOC)]


def relation_prompt(schema, terms, text):
    types = "\n".join(f"- {t['name']}: {t['description']}" for t in schema["entity_types"])
    relations = "\n".join(f"- {r['name']} ({'/'.join(r['head'])} → {'/'.join(r['tail'])}): {r['description']}"
                          for r in schema["relations"])
    glossary = "\n".join(f"- {e['canonical']} [{e['type']}] = {', '.join(e['aliases']) or '-'}" for e in terms) or "- (none)"
    return f"""Extract facts between named entities from the passage, using only this schema.

Entity types:
{types}

Relations:
{relations}

Glossary terms that appear in this passage (canonical name [type] = other spellings):
{glossary}

Rules:
1. Head and Tail are named entities of the listed types. Sentence fragments, numbers and generic words are not entities.
2. If an entity is a glossary term or one of its other spellings, write the canonical name exactly.
3. Otherwise write the name as it appears in the passage, in its original language.
4. Use only the listed relations, in the listed direction. If no listed relation fits a fact, leave that fact out.

Passage:
{text}"""


def relation_output_schema(schema):
    types = [t["name"] for t in schema["entity_types"]]
    triple = {"type": "object", "required": ["Head", "HeadType", "Relation", "Tail", "TailType"], "properties": {
        "Head": {"type": "string"}, "HeadType": {"enum": types},
        "Relation": {"enum": [r["name"] for r in schema["relations"]]},
        "Tail": {"type": "string"}, "TailType": {"enum": types}}}
    return {"type": "object", "required": ["triples"], "properties": {"triples": {"type": "array", "items": triple}}}


def event_prompt(terms, text):
    official = kgd.three_stages.TRIPLE_INSTRUCTIONS["en"]["event_entity"]
    glossary = "\n".join(f"- {e['canonical']} = {', '.join(e['aliases']) or '-'}" for e in terms)
    if not glossary:
        return official + "\n" + text
    return f"{official}\nWhen an entity is one of these glossary terms or their other spellings, write the canonical name exactly:\n{glossary}\n{text}"


def extract():
    CACHE.mkdir(parents=True, exist_ok=True)
    schema = json.loads(SCHEMA.read_text())
    entries, _ = read_glossary()
    system = kgd.three_stages.TRIPLE_INSTRUCTIONS["en"]["system"]
    for item in ordered_chunks():
        path = CACHE / kgd.cache_path(item["id"]).name
        if path.exists():
            continue
        terms = glossary_in(item["text"], entries)
        b1 = json.loads(kgd.cache_path(item["id"]).read_text())
        record = {"id": item["id"], "original_text": item["text"], "metadata": {}, "glossary_terms": [e["canonical"] for e in terms],
                  "usage": {}, "event_relation_dict": b1["event_relation_dict"], "event_relation_output": b1["event_relation_output"]}
        raw, record["usage"]["entity_relation"] = kgd.chat(
            [{"role": "user", "content": relation_prompt(schema, terms, item["text"])}],
            output_schema=relation_output_schema(schema), num_ctx=NUM_CTX)
        record["entity_relation_output"] = raw
        try:
            record["entity_relation_dict"] = json.loads(raw)["triples"]
        except (ValueError, KeyError, TypeError):
            record["entity_relation_dict"] = []
        raw, record["usage"]["event_entity"] = kgd.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": event_prompt(terms, item["text"])}], num_ctx=NUM_CTX)
        record["event_entity_output"] = raw
        record["event_entity_dict"], _ = kgd.three_stages.parse_or_empty(raw)
        path.write_text(json.dumps(record, ensure_ascii=False))
        seconds = sum(u["seconds"] for u in record["usage"].values())
        print(f"{item['id']}  용어 {len(terms)}개  트리플 {len(record['entity_relation_dict'])}  {seconds:.0f}s", flush=True)


def normalized(name, canonical_of):
    return canonical_of.get(surface_key(name), str(name).strip())


def records(kind):
    """kind: b1 = 자유 추출(12-cache), b3 = schema·용어집 추출 + 용어집 정규화(13-cache). 순서는 기존 문서 → 새 문서."""
    _, canonical_of = read_glossary()
    result, types = [], {}
    for item in ordered_chunks():
        if kind == "b1":
            raw = json.loads(kgd.cache_path(item["id"]).read_text())
        else:
            raw = json.loads((CACHE / kgd.cache_path(item["id"]).name).read_text())
        record = {"id": item["id"], "original_text": item["text"], "metadata": {}, "event_relation_dict": raw["event_relation_dict"]}
        triples, events = [], []
        for t in raw["entity_relation_dict"]:
            if not isinstance(t, dict) or not t.get("Head") or not t.get("Tail") or not t.get("Relation"):
                continue
            head, tail = t["Head"], t["Tail"]
            if kind == "b3":
                head, tail = normalized(head, canonical_of), normalized(tail, canonical_of)
                types.setdefault(head, t.get("HeadType"))
                types.setdefault(tail, t.get("TailType"))
            triples.append({"Head": head, "Relation": t["Relation"], "Tail": tail})
        for e in raw["event_entity_dict"]:
            if not isinstance(e, dict):
                continue
            entities = [str(x) for x in (e.get("Entity") or [])]
            if kind == "b3":
                entities = [normalized(x, canonical_of) for x in entities]
            events.append({"Event": e.get("Event", ""), "Entity": entities})
        record["entity_relation_dict"], record["event_entity_dict"] = triples, events
        result.append(record)
    return result, types


def mentions_by_record(recs):
    mentions = defaultdict(set)
    for r in recs:
        for name in kgd.distractor.names_in(r):
            if name:
                mentions[r["id"]].add(name)
    return mentions


def add_all_source_edges(graph, recs):
    """공식 json2csv 는 이름을 처음 본 청크에만 Source 선을 쓴다(json_to_csv.py:376-385). 나오는 청크마다 쓰는 판."""
    node_of = {d["id"]: n for n, d in graph.nodes(data=True) if d["type"] in ("entity", "event")}
    passage_of = {re.sub(r"\s+", " ", d["id"]).strip(): n for n, d in graph.nodes(data=True) if d["type"] == "passage"}
    added = 0
    for r in recs:
        passage = passage_of[re.sub(r"\s+", " ", r["original_text"]).strip()]
        for name in mentions_by_record([r])[r["id"]]:
            node = node_of.get(name)
            if node and not graph.has_edge(node, passage):
                graph.add_edge(node, passage, relation="mention in", type="Source")
                added += 1
    return added


def build(variant):
    kind, all_sources = {"B1": ("b1", False), "B1m": ("b1", True), "B3": ("b3", False), "B3m": ("b3", True)}[variant]
    recs, types = records(kind)
    graph = kgd.build_without_concepts(recs, LAB / f"runs/13g-{variant}")
    added = add_all_source_edges(graph, recs) if all_sources else 0
    return graph, recs, types, added


def chunk_of_passage(graph):
    by_text = kgd.chunk_ids_by_text()
    return {n: kgd.to_chunk_id(d["id"], by_text) for n, d in graph.nodes(data=True) if d["type"] == "passage"}


def chunks_reached(graph, node, passage_chunk):
    return {passage_chunk[p] for p in graph.successors(node) if p in passage_chunk}


def graph_state(graph, recs):
    entities = [d["id"] for _, d in graph.nodes(data=True) if d["type"] == "entity"]
    groups = Counter(surface_key(e) for e in entities)
    relation_names = Counter(d["relation"] for u, v, d in graph.edges(data=True)
                             if d.get("type") == "Relation" and graph.nodes[u]["type"] == "entity" and graph.nodes[v]["type"] == "entity")
    chunk_count = Counter(name for names in mentions_by_record(recs).values() for name in names)
    shared = sum(1 for e in entities if chunk_count[e] >= 2)
    return (f"엔티티 {len(entities)} (두 청크 이상에 나온 것 {shared}) · 대소문자·공백만 다른 묶음 {sum(1 for c in groups.values() if c > 1)} · "
            f"엔티티 사이 관계 이름 {len(relation_names)}종 (한 번만 쓰인 것 {sum(1 for c in relation_names.values() if c == 1)})")


def short_name(target):
    return target.split(" (")[0].strip()


def lookup_node(graph, encoder, name, node_vectors, node_ids, canonical_of=None):
    """canonical_of 가 있으면(B3 계열) 질문의 이름도 용어집으로 정식 이름으로 바꿔 그 점을 먼저 찾는다."""
    if canonical_of is not None:
        wanted = canonical_of.get(surface_key(name))
        exact = [n for n in node_ids if graph.nodes[n]["id"] == wanted]
        if exact:
            return exact[0]
    order = np.argsort(-(node_vectors @ encoder.encode([name])[0]))
    return node_ids[order[0]]


def precision_recall(found, gold):
    hit = len(found & gold)
    return (hit / len(found) if found else 0.0), hit / len(gold)


def structure_eval(name, graph, encoder, targets, canonical_of=None):
    passage_chunk = chunk_of_passage(graph)
    node_ids = [n for n, d in graph.nodes(data=True) if d["type"] == "entity"]
    node_vectors = encoder.encode([graph.nodes[n]["id"] for n in node_ids])
    rows = []
    for t in targets:
        node = lookup_node(graph, encoder, short_name(t["target"]), node_vectors, node_ids, canonical_of)
        found = chunks_reached(graph, node, passage_chunk)
        rows.append((t, graph.nodes[node]["id"], found))
    return rows


def evaluate(*variants):
    variants = variants or ("B1", "B1m", "B3", "B3m")
    targets = json.loads(STRUCTURE.read_text())
    links = json.loads(LINKS.read_text())
    chunks = kgd.read_chunks()
    encoder = kgd.distractor.OllamaEncoder(kgd.CACHE / "embeddings.json")
    usage = [u for c in chunks for u in json.loads((CACHE / kgd.cache_path(c["id"]).name).read_text())["usage"].values()]
    entries, _ = read_glossary()
    schema = json.loads(SCHEMA.read_text())
    print(f"=== schema: 엔티티 종류 {len(schema['entity_types'])} · 관계 {len(schema['relations'])} · 용어집 {len(entries)}개 (기존 문서만 보고 씀)")
    print(f"=== B3 추출 비용 (질문 1·2, 질문 3 은 B1 재사용): {kgd.usage_summary(usage)}")

    chunk_vectors = encoder.encode([c["text"] for c in chunks])
    print("\n=== 구조 질문: 대상의 짧은 이름(괄호 앞)으로 찾은 청크 — 정밀도 / 재현율 (A 는 질문 임베딩 상위 gold 수만큼, grep 은 짧은 이름 글자 그대로, B3 계열은 용어집으로 정식 이름을 찾고 없으면 임베딩)")
    struct_scores = defaultdict(list)
    for t in targets:
        gold = set(t["gold"])
        dense = {chunks[i]["id"] for i in np.argsort(-(chunk_vectors @ encoder.encode([t["question"]])[0]))[:len(gold)]}
        grep = {c["id"] for c in chunks if short_name(t["target"]).casefold() in c["text"].casefold()}
        struct_scores["A"].append(precision_recall(dense, gold))
        struct_scores["grep"].append(precision_recall(grep, gold))

    built = {}
    for v in variants:
        graph, recs, types, added = build(v)
        built[v] = (graph, recs)
        print(f"\n=== {v} 그래프: {kgd.graph_summary(graph)}" + (f" · 더한 Source 선 {added}" if added else ""))
        print(f"    {graph_state(graph, recs)}")
        uses_glossary = v.startswith("B3")
        for t, node_name, found in structure_eval(v, graph, encoder, targets, read_glossary()[1] if uses_glossary else None):
            struct_scores[v].append(precision_recall(found, set(t["gold"])))

    print("\n=== 구조 질문 대상별 재현율")
    names = ["A", "grep", *variants]
    for i, t in enumerate(targets):
        cells = "  ".join(f"{n} {struct_scores[n][i][1]:.2f}" for n in names)
        print(f"  {t['id']} {t['target'][:24]:24} gold {len(t['gold']):2}  {cells}")
    print("  평균  " + "  |  ".join(f"{n} P {np.mean([s[0] for s in struct_scores[n]]):.2f} R {np.mean([s[1] for s in struct_scores[n]]):.2f}" for n in names))

    print("\n=== 새 문서 → 기존 문서 연결: 새 청크와 같은 엔티티 점을 공유하는 기존 청크 (Source 선 기준)")
    gold_pairs = {(l["new"], x["old"]) for l in links for x in l["links"]}
    print(f"  정답 연결 {len(gold_pairs)}쌍")
    for v in variants:
        graph, _ = built[v]
        passage_chunk = chunk_of_passage(graph)
        found_pairs, via = set(), defaultdict(set)
        for n, d in graph.nodes(data=True):
            if d["type"] != "entity":
                continue
            reached = chunks_reached(graph, n, passage_chunk)
            for new in (c for c in reached if c.startswith(NEW_DOC)):
                for old in (c for c in reached if not c.startswith(NEW_DOC)):
                    found_pairs.add((new, old))
                    via[new, old].add(d["id"])
        p, r = precision_recall(found_pairs, gold_pairs)
        print(f"  {v}: 찾은 쌍 {len(found_pairs)} · 정답과 겹침 {len(found_pairs & gold_pairs)} · 정밀도 {p:.2f} · 재현율 {r:.2f}")
        for pair in sorted(found_pairs & gold_pairs):
            print(f"      ✓ {pair[0]} ↔ {pair[1]}  via {sorted(via[pair])[:4]}")
        wrong = sorted(found_pairs - gold_pairs)
        for pair in wrong[:6]:
            print(f"      ✗ {pair[0]} ↔ {pair[1]}  via {sorted(via[pair])[:4]}")
        if len(wrong) > 6:
            print(f"      … 정답 밖 {len(wrong) - 6}쌍 더")

    _, canonical_of = read_glossary()
    new_terms = Counter()
    for r in records("b3")[0]:
        if r["id"].startswith(NEW_DOC):
            new_terms.update(n for n in mentions_by_record([r])[r["id"]] if surface_key(n) not in canonical_of)
    (LAB / "runs/13-new-terms.tsv").write_text("count\tname\n" + "\n".join(f"{c}\t{n}" for n, c in new_terms.most_common()) + "\n")
    print(f"\n=== 새 문서에서 나온 용어집 밖 이름 {len(new_terms)}개 → runs/13-new-terms.tsv (사람이 고를 후보). 예: {[n for n, _ in new_terms.most_common(8)]}")


def retrieval(*variants):
    variants = variants or ("B3", "B3m")
    questions = json.loads(kgd.QUESTIONS.read_text())
    by_text = kgd.chunk_ids_by_text()
    encoder = kgd.distractor.OllamaEncoder(kgd.CACHE / "embeddings.json")
    rows = [{"id": q["id"], "type": q["type"]} for q in questions]
    for v in variants:
        graph, _, _, _ = build(v)
        retriever, config = kgd.kg_retriever(graph, encoder, ("entity", "event"), v)
        for row, q in zip(rows, questions):
            found, state = kgd.kg_search(retriever, config, q["question"], by_text)
            row[v] = {**kgd.score(found, q["gold"]), "found": found, **state}
        print(f"  {v}: LLM 거름 실패로 거르지 않은 선을 쓴 호출 {retriever.edge_filter.failures}번")
    (LAB / "runs/13-retrieval.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    kgd.print_scores(rows, list(variants))


def combine():
    targets = json.loads(STRUCTURE.read_text())
    chunks = kgd.read_chunks()
    encoder = kgd.distractor.OllamaEncoder(kgd.CACHE / "embeddings.json")
    chunk_vectors = encoder.encode([c["text"] for c in chunks])
    graph, _, _, _ = build("B3m")
    thread_rows = structure_eval("B3m", graph, encoder, targets, read_glossary()[1])
    threads = {t["id"]: found for t, _, found in thread_rows}
    ranked = {t["id"]: [chunks[i]["id"] for i in np.argsort(-(chunk_vectors @ encoder.encode([t["question"]])[0]))] for t in targets}

    conditions = {"실": lambda t: threads[t["id"]]}
    for k in TOP_KS:
        conditions[f"임베딩@{k}"] = lambda t, k=k: set(ranked[t["id"]][:k])
        conditions[f"실+임베딩@{k}"] = lambda t, k=k: threads[t["id"]] | set(ranked[t["id"]][:k])

    print("\n=== 구조 질문: 실(B3m) · 임베딩 상위 k(정답 수를 모름) · 둘의 합집합")
    print("    대상이 고른 점: " + " · ".join(f"{t['id']}→{node}" for t, node, _ in thread_rows))
    scores = {name: [(precision_recall(pick(t), set(t["gold"])), len(pick(t))) for t in targets] for name, pick in conditions.items()}
    for name, rows in scores.items():
        print(f"  {name:14} 정밀도 {np.mean([s[0][0] for s in rows]):.2f}  재현율 {np.mean([s[0][1] for s in rows]):.2f}  평균 찾은 조각 {np.mean([s[1] for s in rows]):.1f}")

    print("\n=== 대상별 재현율")
    for i, t in enumerate(targets):
        cells = "  ".join(f"{name} {scores[name][i][0][1]:.2f}" for name in conditions)
        print(f"  {t['id']} gold {len(t['gold']):2}  {cells}")

    print("\n=== 임베딩@5 가 실에 더한 조각 (✓ 정답 · ✗ 정답 밖)")
    for t in targets:
        added = [c for c in ranked[t["id"]][:5] if c not in threads[t["id"]]]
        marks = " ".join(f"{'✓' if c in t['gold'] else '✗'}{c}" for c in added)
        print(f"  {t['id']} {short_name(t['target'])[:20]:20} {marks or '(없음)'}")


TOP_KS = (3, 5, 10)


if __name__ == "__main__":
    {"extract": extract, "evaluate": evaluate, "retrieval": retrieval, "combine": combine}[sys.argv[1]](*sys.argv[2:])
