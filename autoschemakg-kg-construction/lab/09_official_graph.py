import csv
import json
import sys
import types
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import networkx as nx

LAB = Path(__file__).parent
OFFICIAL = LAB / "repos/AutoSchemaKG/atlas_rag/kg_construction"
PATTERN = "umbrella"


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_official_converters():
    """atlas_rag 패키지 __init__ 은 무거운 의존성을 끌어오므로, 변환에 필요한 파일만 경로로 불러온다."""
    for package in ("atlas_rag", "atlas_rag.kg_construction"):
        sys.modules.setdefault(package, types.ModuleType(package))
    load("atlas_rag.kg_construction.triple_config", OFFICIAL / "triple_config.py")
    json_to_csv = load("json_to_csv", OFFICIAL / "utils/json_processing/json_to_csv.py")
    concept_to_csv = load("concept_to_csv", OFFICIAL / "concept_to_csv.py")
    csv_to_graphml = load("csv_to_graphml", OFFICIAL / "utils/csv_processing/csv_to_graphml.py")
    return json_to_csv, concept_to_csv, csv_to_graphml


def parsed(raw):
    start, end = raw.find("["), raw.rfind("]")
    return json.loads(raw[start : end + 1])


def write_extraction_json(extraction, out):
    folder = out / "kg_extraction"
    folder.mkdir(parents=True, exist_ok=True)
    stages = extraction["stages"]
    record = {
        "id": PATTERN,
        "original_text": extraction["passage"],
        "metadata": {},
        "entity_relation_dict": parsed(stages["entity_relation"]["raw"]),
        "event_entity_dict": parsed(stages["event_entity"]["raw"]),
        "event_relation_dict": parsed(stages["event_relation"]["raw"]),
    }
    (folder / f"{PATTERN}_1.json").write_text(json.dumps(record, ensure_ascii=False) + "\n")
    return folder


def node_kinds(triple_nodes_csv):
    with open(triple_nodes_csv, encoding="utf-8") as f:
        return {row["name:ID"]: row["type"] for row in csv.DictReader(f)}


def relations_of(triple_edges_csv):
    with open(triple_edges_csv, encoding="utf-8") as f:
        return sorted({row["relation"] for row in csv.DictReader(f)})


def write_concepts_csv(node_concepts, kinds, relation_concepts, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["node", "conceptualized_node", "node_type"])
        for node, labels in node_concepts.items():
            writer.writerow([node, ", ".join(labels), kinds[node]])
        for relation, labels in relation_concepts.items():
            writer.writerow([relation, ", ".join(labels), "relation"])


def conceptualize_relations(relations, model):
    concepts = load("concepts_lab", LAB / "03_concepts.py")
    template = concepts.CONCEPT_INSTRUCTIONS["en"]["relation"]
    result = {}
    for relation in relations:
        raw = concepts.ask(model, template.replace("[RELATION]", relation))
        result[relation] = [label.strip().lower() for label in raw.split(",") if label.strip()]
    return result


def report(graphml_path):
    graph = nx.read_graphml(graphml_path)
    print(f"=== 그래프 종류: {type(graph).__name__}, 점 {graph.number_of_nodes()}개, 선 {graph.number_of_edges()}개")
    print("\n=== 점 종류 (type)")
    for kind, count in Counter(data.get("type") for _, data in graph.nodes(data=True)).most_common():
        examples = [data.get("id") for _, data in graph.nodes(data=True) if data.get("type") == kind][:3]
        print(f"  {kind:10} {count:3}개  예: {examples}")
    print("\n=== 선 종류 (type) 와 관계 이름 (relation)")
    for kind, count in Counter(data.get("type") for *_, data in graph.edges(data=True)).most_common():
        relations = Counter(data.get("relation") for *_, data in graph.edges(data=True) if data.get("type") == kind)
        print(f"  {kind:10} {count:3}개  관계 이름: {dict(relations)}")
    print("\n=== 관계 선에 붙은 concepts 속성 (관계 개념)")
    for head, tail, data in graph.edges(data=True):
        if data.get("type") == "Relation" and data.get("concepts"):
            print(f"  {graph.nodes[head]['id']} ―{data['relation']}→ {graph.nodes[tail]['id']}  concepts={data['concepts']}")
    print("\n=== 민수 → 우산 선")
    for head, tail, data in graph.edges(data=True):
        if graph.nodes[head].get("id") == "민수" and graph.nodes[tail].get("id") == "우산":
            print(f"  relation={data.get('relation')}")


def main(extraction_path, concept_path, model, out_dir):
    out = Path(out_dir)
    json_to_csv, concept_to_csv, csv_to_graphml = load_official_converters()
    extraction = json.load(open(extraction_path))
    data_dir = write_extraction_json(extraction, out)
    triples = out / "triples_csv"
    json_to_csv.json2csv(dataset=PATTERN, data_dir=str(data_dir), output_dir=str(triples), schema=None, custom=False)

    nodes_csv = triples / f"triple_nodes_{PATTERN}_from_json_without_emb.csv"
    edges_csv = triples / f"triple_edges_{PATTERN}_from_json_without_emb.csv"
    node_concepts = json.load(open(concept_path))["node_concepts"]
    relation_concepts = conceptualize_relations(relations_of(edges_csv), model)
    concepts_csv = triples / f"{PATTERN}_from_json_with_concept.csv"
    write_concepts_csv(node_concepts, node_kinds(nodes_csv), relation_concepts, concepts_csv)

    concept_dir = out / "concept_csv"
    concept_dir.mkdir(exist_ok=True)
    concept_to_csv.all_concept_triples_csv_to_csv(
        node_file=str(nodes_csv),
        edge_file=str(edges_csv),
        concepts_file=str(concepts_csv),
        output_node_file=str(concept_dir / f"concept_nodes_{PATTERN}_from_json_with_concept.csv"),
        output_edge_file=str(concept_dir / f"concept_edges_{PATTERN}_from_json_with_concept.csv"),
        output_full_concept_triple_edges=str(concept_dir / f"triple_edges_{PATTERN}_from_json_with_concept.csv"),
    )
    graphml = out / "kg_graphml" / f"{PATTERN}_graph.graphml"
    csv_to_graphml.csvs_to_graphml(
        triple_node_file=str(nodes_csv),
        text_node_file=str(triples / f"text_nodes_{PATTERN}_from_json.csv"),
        triple_edge_file=str(concept_dir / f"triple_edges_{PATTERN}_from_json_with_concept.csv"),
        text_edge_file=str(triples / f"text_edges_{PATTERN}_from_json.csv"),
        concept_node_file=str(concept_dir / f"concept_nodes_{PATTERN}_from_json_with_concept.csv"),
        concept_edge_file=str(concept_dir / f"concept_edges_{PATTERN}_from_json_with_concept.csv"),
        output_file=str(graphml),
        include_concept=True,
    )
    report(graphml)


if __name__ == "__main__":
    main(*sys.argv[1:5])
