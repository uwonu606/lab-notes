import ast
import csv
import json
import logging
import random
import sys
import types
import urllib.request
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import networkx as nx
import numpy as np

LAB = Path(__file__).parent
ATLAS = LAB / "repos/AutoSchemaKG/atlas_rag"
OLLAMA = "http://localhost:11434"
MODEL = "llama3.1:8b"
EMBEDDER = "bge-m3"
DATASET = "distract"
QUESTION = "민수는 왜 편의점에서 우산을 샀나?"
STORY = "10-umbrella"
NEEDED = ["아침에 민수는 우산을 집에 두고 출근했다.", "점심 무렵 비가 쏟아졌다.", "민수는 편의점에서 우산을 샀다."]
TOP_N = 5


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def stub(name, **attributes):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    for key, value in attributes.items():
        setattr(module, key, value)


three_stages = load("three_stages", LAB / "01_three_stages.py")
concept_lab = load("concept_lab", LAB / "03_concepts.py")
official_graph = load("official_graph", LAB / "09_official_graph.py")


def load_official_retriever():
    """atlas_rag 패키지 __init__ 은 무거운 의존성을 끌어오므로, 검색에 필요한 파일만 경로로 불러온다."""
    for package in ("atlas_rag", "atlas_rag.retriever", "atlas_rag.vectorstore", "atlas_rag.llm_generator"):
        stub(package)
    stub("atlas_rag.vectorstore.embedding_model", BaseEmbeddingModel=object)
    stub("atlas_rag.llm_generator.llm_generator", LLMGenerator=object)
    load("atlas_rag.retriever.base", ATLAS / "retriever/base.py")
    config = load("atlas_rag.retriever.inference_config", ATLAS / "retriever/inference_config.py")
    hipporag2 = load("atlas_rag.retriever.hipporag2", ATLAS / "retriever/hipporag2.py")
    return hipporag2.HippoRAG2Retriever, config.InferenceConfig


def post(path, body):
    request = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())


def extract(passages_file, cache_dir):
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    for number, passage in enumerate(Path(passages_file).read_text().splitlines()):
        path = cache / f"{Path(passages_file).stem}_{number:03d}.json"
        if path.exists():
            continue
        record = {"id": path.stem, "original_text": passage, "metadata": {}}
        for stage in three_stages.STAGES:
            record[f"{stage}_dict"], _ = three_stages.parse_or_empty(three_stages.ask(MODEL, stage, passage))
        path.write_text(json.dumps(record, ensure_ascii=False))
        print(path.name, flush=True)


class OllamaEncoder:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path)
        self.vectors = json.loads(self.cache_path.read_text()) if self.cache_path.exists() else {}

    def encode(self, texts, query_type=None, **kwargs):
        texts = [texts] if isinstance(texts, str) else list(texts)
        missing = sorted({t for t in texts if t not in self.vectors})
        for start in range(0, len(missing), 64):
            batch = missing[start : start + 64]
            self.vectors.update(zip(batch, post("/api/embed", {"model": EMBEDDER, "input": batch})["embeddings"]))
        if missing:
            self.cache_path.write_text(json.dumps(self.vectors))
        matrix = np.array([self.vectors[t] for t in texts], dtype=np.float32)
        return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


class ExactInnerProductIndex:
    def __init__(self, vectors):
        self.vectors = vectors

    def search(self, queries, k):
        scores = queries @ self.vectors.T
        order = np.argsort(-scores, axis=1)[:, :k]
        return np.take_along_axis(scores, order, axis=1), order


class OllamaEdgeFilter:
    def __init__(self):
        self.messages = load("rag_prompt", ATLAS / "llm_generator/prompt/rag_prompt.py").filter_triple_messages
        self.fix = load("validate_json_output", ATLAS / "llm_generator/format/validate_json_output.py").fix_filter_triplets
        self.answers = {}

    def filter_triples_with_entity_event(self, question, triples):
        if (question, triples) not in self.answers:
            self.answers[question, triples] = self.ask(question, triples)
        return self.answers[question, triples]

    def ask(self, question, triples):
        messages = deepcopy(self.messages)
        messages.append(
            {"role": "user", "content": f"""[ ## question ## ]]
        {question}

        [[ ## fact_before_filter ## ]]
        {triples}"""})
        body = {"model": MODEL, "stream": False, "format": "json", "options": {"temperature": 0.0}, "messages": messages}
        try:
            return json.dumps(self.fix(post("/api/chat", body)["message"]["content"]), ensure_ascii=False)
        except Exception:
            return triples


class LogLines(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def records_for(cache_dir, kind, count):
    cache = Path(cache_dir)
    story = sorted(cache.glob(f"{STORY}_*.json"))
    distractors = sorted(cache.glob(f"10-{kind}_*.json"))[:count]
    assert len(story) == 5 and len(distractors) == count, (len(story), len(distractors))
    return [json.loads(p.read_text()) for p in story + distractors]


def names_in(record):
    for item in record["entity_relation_dict"] + record["event_relation_dict"]:
        if isinstance(item, dict):
            yield from (str(item.get("Head", "")).strip(), str(item.get("Tail", "")).strip())
    for item in record["event_entity_dict"]:
        if isinstance(item, dict):
            yield str(item.get("Event", "")).strip()
            yield from (str(entity).strip() for entity in item.get("Entity", []) or [])


def mentioning_records(records):
    mentions = {}
    for record in records:
        for name in names_in(record):
            mentions.setdefault(name, set()).add(record["id"])
    return mentions


def build_graph(records, out, with_concepts):
    data_dir = out / "kg_extraction"
    data_dir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    (data_dir / f"{DATASET}_1.json").write_text("\n".join(lines) + "\n")
    json_to_csv, concept_to_csv, csv_to_graphml = official_graph.load_official_converters()
    triples = out / "triples_csv"
    json_to_csv.json2csv(dataset=DATASET, data_dir=str(data_dir), output_dir=str(triples), schema=None, custom=False)
    nodes_csv = triples / f"triple_nodes_{DATASET}_from_json_without_emb.csv"
    edges_csv = triples / f"triple_edges_{DATASET}_from_json_without_emb.csv"
    graph_files = {
        "triple_node_file": str(nodes_csv),
        "text_node_file": str(triples / f"text_nodes_{DATASET}_from_json.csv"),
        "triple_edge_file": str(edges_csv),
        "text_edge_file": str(triples / f"text_edges_{DATASET}_from_json.csv"),
    }
    if with_concepts:
        concept_dir = out / "concept_csv"
        concept_dir.mkdir(exist_ok=True)
        concepts_csv = triples / f"{DATASET}_from_json_with_concept.csv"
        write_concepts(nodes_csv, edges_csv, concepts_csv, out / "concepts.json")
        concept_to_csv.all_concept_triples_csv_to_csv(
            node_file=str(nodes_csv),
            edge_file=str(edges_csv),
            concepts_file=str(concepts_csv),
            output_node_file=str(concept_dir / "concept_nodes.csv"),
            output_edge_file=str(concept_dir / "concept_edges.csv"),
            output_full_concept_triple_edges=str(concept_dir / "triple_edges_with_concept.csv"),
        )
        graph_files.update(
            triple_edge_file=str(concept_dir / "triple_edges_with_concept.csv"),
            concept_node_file=str(concept_dir / "concept_nodes.csv"),
            concept_edge_file=str(concept_dir / "concept_edges.csv"),
        )
    graphml = out / "graph.graphml"
    csv_to_graphml.csvs_to_graphml(**graph_files, output_file=str(graphml), include_concept=with_concepts)
    return nx.read_graphml(graphml)


def write_concepts(nodes_csv, edges_csv, concepts_csv, cache_path):
    kinds = official_graph.node_kinds(nodes_csv)
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
    else:
        with open(edges_csv, encoding="utf-8") as f:
            edges = [(row[":START_ID"], row["relation"], row[":END_ID"]) for row in csv.DictReader(f)]
        rng = random.Random(three_stages.SEED)
        cached = {
            "node_concepts": {n: concept_lab.concepts_of(MODEL, n, kinds[n], edges, rng)[2] for n in sorted(kinds)},
            "relation_concepts": official_graph.conceptualize_relations(official_graph.relations_of(edges_csv), MODEL),
        }
        cache_path.write_text(json.dumps(cached, ensure_ascii=False, indent=1))
    official_graph.write_concepts_csv(cached["node_concepts"], kinds, cached["relation_concepts"], concepts_csv)


def retriever_data(graph, encoder, node_types):
    """공식 create_embeddings_and_index 의 include_events=True 경로와 같은 목록을 만든다. 개념을 켜면 concept 점도 넣는다."""
    node_list = [n for n, d in graph.nodes(data=True) if d["type"] in node_types]
    node_set = set(node_list)
    edge_list = [e for e in graph.edges if e[0] in node_set and e[1] in node_set]
    edge_strings = [f"{graph.nodes[h]['id']} {graph.edges[h, t]['relation']} {graph.nodes[t]['id']}" for h, t in edge_list]
    text_dict = {n: d["id"].strip() for n, d in graph.nodes(data=True) if d["type"] == "passage"}
    edge_embeddings = encoder.encode(edge_strings)
    return {
        "node_list": node_list,
        "edge_list": edge_list,
        "node_embeddings": encoder.encode([graph.nodes[n]["id"] for n in node_list]),
        "edge_embeddings": edge_embeddings,
        "text_embeddings": encoder.encode(list(text_dict.values())),
        "edge_faiss_index": ExactInnerProductIndex(edge_embeddings),
        "text_dict": text_dict,
        "KG": graph,
    }


def retrieve(cache_dir, kind, count, out_dir, concepts="no-concepts"):
    out = Path(out_dir)
    with_concepts = concepts == "concepts"
    node_types = ("entity", "event", "concept") if with_concepts else ("entity", "event")
    records = records_for(cache_dir, kind, int(count))
    mentions = mentioning_records(records)
    graph = build_graph(records, out, with_concepts)
    encoder = OllamaEncoder(Path(cache_dir) / "embeddings.json")
    HippoRAG2Retriever, InferenceConfig = load_official_retriever()
    config = InferenceConfig()
    log = LogLines()
    logger = logging.getLogger(f"hipporag2-{out.name}")
    logger.setLevel(logging.INFO)
    logger.addHandler(log)
    retriever = HippoRAG2Retriever(llm_generator=OllamaEdgeFilter(), sentence_encoder=encoder,
                                   data=retriever_data(graph, encoder, node_types), inference_config=config, logger=logger)

    official_top, _ = retriever.retrieve(QUESTION, topN=TOP_N)
    node_scores, passage_scores = retriever.retrieve_personalization_dict(QUESTION, topN=config.topk_edges,
                                                                         weight_adjust=config.weight_adjust)
    kg = retriever.KG
    story = {n for n, text in retriever.passage_dict.items() if text in Path(LAB / f"inputs/{STORY}.txt").read_text()}

    def origin(*nodes):
        if any(kg.nodes[n]["type"] == "concept" for n in nodes):
            return "개념"
        record_ids = set().union(*(mentions.get(kg.nodes[n]["id"], set()) for n in nodes))
        return "+".join(sorted({"우산" if r.startswith(STORY) else "붙임" for r in record_ids})) or "?"

    def source_edges(node):
        return sum(1 for p in kg.successors(node) if p in retriever.passage_dict)

    print(f"=== 질문: {QUESTION}")
    print(f"=== 개념 단계: {'켬' if with_concepts else '끔'}")
    print(f"=== 붙인 문서: {kind} {count}개 | 원문 {len(retriever.passage_dict)}개, 점 {kg.number_of_nodes()}개, 선 {kg.number_of_edges()}개")
    shared = sorted((n for n in retriever.node_list if origin(n) == "붙임+우산"), key=lambda n: kg.nodes[n]["id"])
    print(f"\n=== 우산 이야기와 붙인 문서가 함께 쓰는 점 {len(shared)}개 — 이름이 나온 원문 수 → 그 점에서 원문으로 가는 Source 선 수")
    for n in shared:
        print(f"  {kg.nodes[n]['id']}: 원문 {len(mentions[kg.nodes[n]['id']])}개 → Source 선 {source_edges(n)}개")

    print_candidate_edges(log.lines, kg, origin)

    print(f"\n=== 3) PageRank 출발 점수: 점 {len(node_scores)}개 (LLM 이 거른 선의 양 끝)")
    for node, score in sorted(node_scores.items(), key=lambda x: -x[1]):
        print(f"  {score:.3f}  [{origin(node)}] {kg.nodes[node]['id']}")
    story_mass = sum(s for p, s in passage_scores.items() if p in story)
    other_mass = sum(s for p, s in passage_scores.items() if p not in story)
    print(f"  원문 출발 점수 합: 우산 문장 5개 {story_mass:.2f} / 붙인 문서 {count}개 {other_mass:.2f}")
    print("  우산 문장마다 원문 출발 점수 (질문-원문 유사도를 최솟값 0, 최댓값 1 로 늘인 값):")
    for p in sorted(story, key=lambda p: -passage_scores[p]):
        print(f"    {passage_scores[p]:.3f}  {retriever.passage_dict[p]}")

    ranked = ranking(kg, node_scores, passage_scores, config)
    dense = [p for p, _ in sorted(passage_scores.items(), key=lambda x: -x[1])]
    assert [retriever.passage_dict[p] for p in ranked[:TOP_N]] == official_top
    print_ranking("4) 원문 순위 — 공식 HippoRAG2 (PageRank)", ranked, retriever.passage_dict, story)
    print_ranking("5) 비교: PageRank 없이 질문-원문 유사도만", dense, retriever.passage_dict, story)
    for label, order in (("PageRank", ranked), ("유사도만", dense)):
        hits = [retriever.passage_dict[p] in NEEDED for p in order[:TOP_N]].count(True)
        print(f"=== 결과 ({label}): 필요한 세 문장 중 상위 {TOP_N}개 안 {hits}/3")


def print_candidate_edges(log_lines, kg, origin):
    before = next(ast.literal_eval(l.split(": ", 1)[1]) for l in log_lines if "Before Filter Edge" in l)
    after = next((l.split(": ", 1)[1] for l in log_lines if "Filtered edges" in l), "[]")
    by_name = {}
    for h, t in kg.edges:
        by_name.setdefault((kg.nodes[h]["id"], kg.edges[h, t]["relation"], kg.nodes[t]["id"]), (h, t))
    origins = [origin(*by_name[tuple(f)]) for f in before]
    counts = {o: origins.count(o) for o in sorted(set(origins))}
    print(f"\n=== 1) 질문과 가까운 선 {len(before)}개의 출처: {counts}")
    for fact, o in list(zip(before, origins))[:10]:
        print(f"  [{o}] {' / '.join(fact)}")
    print(f"\n=== 2) LLM 거름 뒤 남은 선: {after}")


def ranking(kg, node_scores, passage_scores, config):
    if not node_scores:
        return [p for p, _ in sorted(passage_scores.items(), key=lambda x: -x[1])]
    pr = nx.pagerank(kg, personalization={**node_scores, **passage_scores}, alpha=config.ppr_alpha,
                     max_iter=config.ppr_max_iter, tol=config.ppr_tol)
    return [p for p in sorted(passage_scores, key=lambda p: -pr[p]) if pr[p] > 0.0]


def print_ranking(title, order, passage_dict, story):
    print(f"\n=== {title}")
    for rank, p in enumerate(order[:8], 1):
        text = passage_dict[p]
        mark = "★" if text in NEEDED else ("·" if p in story else " ")
        print(f"  {rank:3}. {mark} {text}")
    ranks = [order.index(p) + 1 for p in order if passage_dict[p] in NEEDED]
    print(f"  필요한 세 문장(★)의 순위: {ranks}")


if __name__ == "__main__":
    {"extract": extract, "retrieve": retrieve}[sys.argv[1]](*sys.argv[2:])
