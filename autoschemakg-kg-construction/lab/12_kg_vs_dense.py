import ast
import csv
import json
import logging
import random
import re
import sys
import time
import types
import urllib.error
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import List

import networkx as nx
import numpy as np

LAB = Path(__file__).parent
NOTES_HOME = LAB.parent.parent
ATLAS = LAB / "repos/AutoSchemaKG/atlas_rag"
CORPUS = ["commit-pr-workflow/notes.md", "doc-parsing-chunking/notes.md", "concept-extraction-papers/research.md"]
CHUNK_SIZE = 1000
CHUNKS = LAB / "inputs/12-chunks.jsonl"
QUESTIONS = LAB / "inputs/12-questions.json"
CACHE = LAB / "runs/12-cache"
CONCEPTS = CACHE / "concepts.json"
DATASET = "notes"
TOP_N = 5
COPY_SPAN = 4
STAGES = ["entity_relation", "event_entity", "event_relation"]


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


distractor = load("distractor", LAB / "10_distractor_retrieval.py")
three_stages = distractor.three_stages
official_graph = distractor.official_graph
concepts_lab = load("concepts_lab", LAB / "03_concepts.py")
single_post = distractor.post


def retrying_post(path, body, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            return single_post(path, body)
        except urllib.error.HTTPError as error:
            print(f"  Ollama {path} HTTP {error.code} — 모델을 내렸다 올려 다시 보낸다 ({attempt}/{attempts})", flush=True)
            if attempt == attempts:
                raise
            single_post("/api/generate", {"model": body["model"], "keep_alive": 0})


distractor.post = retrying_post


def official_chunker():
    """triple_extraction.py 는 torch·datasets 를 끌어오므로 TextChunker 클래스만 떼어 실행한다."""
    tree = ast.parse((ATLAS / "kg_construction/triple_extraction.py").read_text())
    chunker = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TextChunker")
    namespace = {"List": List, "ProcessingConfig": object}
    exec(compile(ast.Module([chunker], type_ignores=[]), "triple_extraction.py", "exec"), namespace)
    return namespace["TextChunker"](types.SimpleNamespace(chunk_size=CHUNK_SIZE, chunk_overlap=0))


def read_chunks():
    return [json.loads(line) for line in CHUNKS.read_text().splitlines()]


def chunk():
    chunker = official_chunker()
    lines = []
    for doc in CORPUS:
        slug = doc.split("/")[0]
        for number, text in enumerate(chunker.split_text((NOTES_HOME / doc).read_text())):
            lines.append(json.dumps({"id": f"{slug}#{number:02d}", "doc": doc, "text": text}, ensure_ascii=False))
    CHUNKS.write_text("\n".join(lines) + "\n")
    lengths = [len(json.loads(line)["text"]) for line in lines]
    for doc in CORPUS:
        count = sum(1 for line in lines if json.loads(line)["doc"] == doc)
        print(f"{doc}: 청크 {count}개")
    print(f"합계 {len(lines)}개, 글자 수 최소 {min(lengths)} / 평균 {sum(lengths) // len(lengths)} / 최대 {max(lengths)}")


def chat(messages, attempts=3, output_schema=None, num_ctx=None):
    options = {"temperature": 0.7, "seed": three_stages.SEED} | ({"num_ctx": num_ctx} if num_ctx else {})
    body = {"model": distractor.MODEL, "stream": False, "options": options, "messages": messages}
    if output_schema:
        body["format"] = output_schema
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            response = distractor.post("/api/chat", body)
        except urllib.error.HTTPError as error:
            problem = f"HTTP {error.code}"
        else:
            usage = {"prompt_tokens": response.get("prompt_eval_count", 0), "completion_tokens": response.get("eval_count", 0),
                     "seconds": round(time.monotonic() - started, 2)}
            content = response["message"]["content"]
            if usage["completion_tokens"] and content.strip("? \n"):
                return content, usage
            problem = f"깨진 답 {content[:20]!r}"
        print(f"  Ollama {problem} — 모델을 내렸다 올려 다시 묻는다 ({attempt}/{attempts})", flush=True)
        single_post("/api/generate", {"model": distractor.MODEL, "keep_alive": 0})
    raise RuntimeError(f"Ollama 가 {attempts}번 모두 실패했다: {problem}")


def cache_path(chunk_id):
    return CACHE / f"{chunk_id.replace('#', '_')}.json"


def extract():
    CACHE.mkdir(parents=True, exist_ok=True)
    instructions = three_stages.TRIPLE_INSTRUCTIONS["en"]
    for item in read_chunks():
        path = cache_path(item["id"])
        if path.exists():
            continue
        record = {"id": item["id"], "original_text": item["text"], "metadata": {}, "usage": {}}
        for stage in STAGES:
            raw, usage = chat([{"role": "system", "content": instructions["system"]},
                               {"role": "user", "content": instructions[stage] + "\n" + item["text"]}])
            record[f"{stage}_dict"], _ = three_stages.parse_or_empty(raw)
            record[f"{stage}_output"] = raw
            record["usage"][stage] = usage
        path.write_text(json.dumps(record, ensure_ascii=False))
        seconds = sum(u["seconds"] for u in record["usage"].values())
        print(f"{item['id']}  {seconds:.0f}s", flush=True)


def read_records():
    keep = ("id", "original_text", "metadata", *(f"{stage}_dict" for stage in STAGES))
    records = []
    for item in read_chunks():
        record = json.loads(cache_path(item["id"]).read_text())
        records.append({key: record[key] for key in keep})
    return records


def write_triples(records, out):
    data_dir = out / "kg_extraction"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / f"{DATASET}_1.json").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")
    json_to_csv, concept_to_csv, csv_to_graphml = official_graph.load_official_converters()
    triples = out / "triples_csv"
    json_to_csv.json2csv(dataset=DATASET, data_dir=str(data_dir), output_dir=str(triples), schema=None, custom=False)
    return triples, concept_to_csv, csv_to_graphml


def triple_file(triples, kind):
    return triples / f"{kind}_{DATASET}_from_json_without_emb.csv"


def build_without_concepts(records, out):
    triples, _, csv_to_graphml = write_triples(records, out)
    graphml = out / "graph.graphml"
    csv_to_graphml.csvs_to_graphml(
        triple_node_file=str(triple_file(triples, "triple_nodes")),
        text_node_file=str(triples / f"text_nodes_{DATASET}_from_json.csv"),
        triple_edge_file=str(triple_file(triples, "triple_edges")),
        text_edge_file=str(triples / f"text_edges_{DATASET}_from_json.csv"),
        output_file=str(graphml),
        include_concept=False,
    )
    return nx.read_graphml(graphml)


def build_with_concepts(records, out):
    triples, concept_to_csv, csv_to_graphml = write_triples(records, out)
    saved = json.loads(CONCEPTS.read_text())
    concepts_csv = triples / f"{DATASET}_from_json_with_concept.csv"
    official_graph.write_concepts_csv(saved["node_concepts"], official_graph.node_kinds(triple_file(triples, "triple_nodes")),
                                      saved["relation_concepts"], concepts_csv)
    concept_dir = out / "concept_csv"
    concept_dir.mkdir(exist_ok=True)
    concept_to_csv.all_concept_triples_csv_to_csv(
        node_file=str(triple_file(triples, "triple_nodes")),
        edge_file=str(triple_file(triples, "triple_edges")),
        concepts_file=str(concepts_csv),
        output_node_file=str(concept_dir / f"concept_nodes_{DATASET}_from_json_with_concept.csv"),
        output_edge_file=str(concept_dir / f"concept_edges_{DATASET}_from_json_with_concept.csv"),
        output_full_concept_triple_edges=str(concept_dir / f"triple_edges_{DATASET}_from_json_with_concept.csv"),
    )
    graphml = out / "graph.graphml"
    csv_to_graphml.csvs_to_graphml(
        triple_node_file=str(triple_file(triples, "triple_nodes")),
        text_node_file=str(triples / f"text_nodes_{DATASET}_from_json.csv"),
        triple_edge_file=str(concept_dir / f"triple_edges_{DATASET}_from_json_with_concept.csv"),
        text_edge_file=str(triples / f"text_edges_{DATASET}_from_json.csv"),
        concept_node_file=str(concept_dir / f"concept_nodes_{DATASET}_from_json_with_concept.csv"),
        concept_edge_file=str(concept_dir / f"concept_edges_{DATASET}_from_json_with_concept.csv"),
        output_file=str(graphml),
        include_concept=True,
    )
    return nx.read_graphml(graphml)


def conceptualize():
    triples, _, _ = write_triples(read_records(), LAB / "runs/12g-concept-input")
    kinds = official_graph.node_kinds(triple_file(triples, "triple_nodes"))
    with open(triple_file(triples, "triple_edges"), encoding="utf-8") as f:
        edges = [(row[":START_ID"], row["relation"], row[":END_ID"]) for row in csv.DictReader(f)]
    saved = json.loads(CONCEPTS.read_text()) if CONCEPTS.exists() else {"node_concepts": {}, "relation_concepts": {}, "usage": []}
    usage = saved["usage"]

    def recording_ask(model, prompt):
        content, used = chat([{"role": "system", "content": "You are a helpful AI assistant."},
                              {"role": "user", "content": prompt}])
        usage.append(used)
        return content

    concepts_lab.ask = recording_ask
    rng = random.Random(0)
    pending = [node for node in kinds if node not in saved["node_concepts"]]
    for number, node in enumerate(pending, 1):
        _, _, labels = concepts_lab.concepts_of(distractor.MODEL, node, kinds[node], edges, rng)
        saved["node_concepts"][node] = labels
        if number % 25 == 0 or number == len(pending):
            CONCEPTS.write_text(json.dumps(saved, ensure_ascii=False))
            print(f"점 {len(saved['node_concepts'])}/{len(kinds)}", flush=True)
    template = concepts_lab.CONCEPT_INSTRUCTIONS["en"]["relation"]
    for relation in sorted({r for _, r, _ in edges} - set(saved["relation_concepts"])):
        raw = recording_ask(distractor.MODEL, template.replace("[RELATION]", relation))
        saved["relation_concepts"][relation] = [label.strip().lower() for label in raw.split(",") if label.strip()]
    CONCEPTS.write_text(json.dumps(saved, ensure_ascii=False))
    print(f"관계 {len(saved['relation_concepts'])}개 끝")


def words(text):
    return re.findall(r"\S+", text)


def copied_spans(question, text):
    tokens = words(question)
    spans = (" ".join(tokens[i : i + COPY_SPAN]) for i in range(len(tokens) - COPY_SPAN + 1))
    return [span for span in spans if span in " ".join(words(text))]


def check_questions():
    chunks = {c["id"]: c["text"] for c in read_chunks()}
    questions = json.loads(QUESTIONS.read_text())
    print(f"질문 {len(questions)}개: {dict(Counter(q['type'] for q in questions))}")
    for q in questions:
        unknown = [g for g in q["gold"] if g not in chunks]
        copied = [span for g in q["gold"] if g in chunks for span in copied_spans(q["question"], chunks[g])]
        if unknown or copied or (q["type"] == "bridge") != (len(q["gold"]) == 2):
            print(f"  {q['id']}: 없는 청크 {unknown} / 어절 {COPY_SPAN}개 이상 그대로 {copied} / gold {len(q['gold'])}개")
    print(f"정답 청크가 걸친 문서: {dict(Counter(g.split('#')[0] for q in questions for g in q['gold']))}")


def retriever_data(graph, encoder, node_types):
    """공식 create_embeddings_and_index 와 같은 목록을 만든다. node_types 가 include_events·include_concept 를 대신한다."""
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
        "edge_faiss_index": distractor.ExactInnerProductIndex(edge_embeddings),
        "text_dict": text_dict,
        "KG": graph,
    }


def chunk_ids_by_text():
    return {re.sub(r"\s+", " ", c["text"]).strip(): c["id"] for c in read_chunks()}


def to_chunk_id(text, by_text):
    return by_text[re.sub(r"\s+", " ", text).strip()]


def graph_summary(graph):
    nodes = Counter(d["type"] for _, d in graph.nodes(data=True))
    edges = Counter(d.get("type") for *_, d in graph.edges(data=True))
    return f"점 {graph.number_of_nodes()} {dict(nodes)} · 선 {graph.number_of_edges()} {dict(edges)}"


def usage_summary(entries):
    return (f"호출 {len(entries)}번, 입력 토큰 {sum(u['prompt_tokens'] for u in entries):,}, "
            f"출력 토큰 {sum(u['completion_tokens'] for u in entries):,}, {sum(u['seconds'] for u in entries) / 60:.1f}분")


class CountingEdgeFilter(distractor.OllamaEdgeFilter):
    """부모는 Ollama 가 실패하면 거르지 않은 선을 조용히 돌려준다. 그 횟수를 센다."""

    def __init__(self):
        super().__init__()
        self.failures = 0

    def ask(self, question, triples):
        original_post = distractor.post

        def checked_post(path, body, attempts=3):
            for _ in range(attempts):
                response = original_post(path, body)
                if response.get("eval_count") and response["message"]["content"].strip("? \n"):
                    return response
                single_post("/api/generate", {"model": body["model"], "keep_alive": 0})
            raise RuntimeError("broken answer")

        distractor.post = checked_post
        try:
            answer = super().ask(question, triples)
        finally:
            distractor.post = original_post
        if answer is triples:
            self.failures += 1
        return answer


def kg_retriever(graph, encoder, node_types, name):
    HippoRAG2Retriever, InferenceConfig = distractor.load_official_retriever()
    config = InferenceConfig()
    logger = logging.getLogger(f"hipporag2-{name}")
    logger.addHandler(distractor.LogLines())
    edge_filter = CountingEdgeFilter()
    retriever = HippoRAG2Retriever(llm_generator=edge_filter, sentence_encoder=encoder,
                                   data=retriever_data(graph, encoder, node_types), inference_config=config, logger=logger)
    retriever.edge_filter = edge_filter
    return retriever, config


def kg_search(retriever, config, question, by_text):
    top, _ = retriever.retrieve(question, topN=TOP_N)
    node_scores, _ = retriever.retrieve_personalization_dict(question, topN=config.topk_edges, weight_adjust=config.weight_adjust)
    return [to_chunk_id(t, by_text) for t in top], {"start_nodes": len(node_scores), "returned": len(top)}


def score(found, gold):
    hits = len(set(found[:TOP_N]) & set(gold))
    return {"hits": hits, "recall": hits / len(gold), "all": hits == len(gold)}


def print_scores(rows, variants):
    print(f"\n=== 결과: 정답 청크가 상위 {TOP_N}개 안에 든 비율 (recall@{TOP_N}) / 정답 청크가 모두 든 질문 수")
    for kind in ("single", "bridge", "전체"):
        subset = [r for r in rows if kind == "전체" or r["type"] == kind]
        cells = []
        for v in variants:
            recall = sum(r[v]["recall"] for r in subset) / len(subset)
            complete = sum(r[v]["all"] for r in subset)
            cells.append(f"{v} {recall:.3f} ({complete}/{len(subset)})")
        print(f"  {kind:6} n={len(subset):2}  " + "  |  ".join(cells))


def evaluate(*variants):
    variants = variants or ("A", "B1")
    chunks = read_chunks()
    questions = json.loads(QUESTIONS.read_text())
    records = read_records()
    by_text = chunk_ids_by_text()
    encoder = distractor.OllamaEncoder(CACHE / "embeddings.json")
    extraction_usage = [u for item in chunks for u in json.loads(cache_path(item["id"]).read_text())["usage"].values()]
    print(f"=== 문서 {len(CORPUS)}개 → 청크 {len(chunks)}개 (chunk_size {CHUNK_SIZE}자) · 질문 {len(questions)}개")
    print(f"=== 구축 비용 — 추출: {usage_summary(extraction_usage)}")
    if CONCEPTS.exists():
        print(f"=== 구축 비용 — 개념: {usage_summary(json.loads(CONCEPTS.read_text())['usage'])}")

    searchers, edge_filters = {}, {}
    chunk_texts = [c["text"] for c in chunks]
    chunk_vectors = encoder.encode(chunk_texts)
    if "A" in variants:
        def dense(question):
            order = np.argsort(-(chunk_vectors @ encoder.encode([question])[0]))[:TOP_N]
            return [chunks[i]["id"] for i in order], {}
        searchers["A"] = dense
    if "B1" in variants:
        graph = build_without_concepts(records, LAB / "runs/12g-noconcept")
        print(f"=== B1 그래프: {graph_summary(graph)}")
        retriever, config = kg_retriever(graph, encoder, ("entity", "event"), "B1")
        searchers["B1"] = lambda q, r=retriever, c=config: kg_search(r, c, q, by_text)
        edge_filters["B1"] = retriever.edge_filter
    if "B2" in variants:
        graph = build_with_concepts(records, LAB / "runs/12g-concept")
        print(f"=== B2 그래프: {graph_summary(graph)}")
        retriever, config = kg_retriever(graph, encoder, ("entity", "event", "concept"), "B2")
        searchers["B2"] = lambda q, r=retriever, c=config: kg_search(r, c, q, by_text)
        edge_filters["B2"] = retriever.edge_filter

    rows = []
    out = (LAB / "runs/12-eval.jsonl").open("w")
    print(f"\n=== 질문별 (정답 청크 중 상위 {TOP_N}개 안에 든 수 / gold 수). B 뒤 괄호는 PageRank 출발 점 수, 돌려준 청크 수")
    for q in questions:
        row = {"id": q["id"], "type": q["type"], "gold": q["gold"]}
        cells = []
        for v, search in searchers.items():
            found, state = search(q["question"])
            row[v] = {**score(found, q["gold"]), "found": found, **state}
            extra = f"({state['start_nodes']},{state['returned']})" if state else ""
            cells.append(f"{v} {row[v]['hits']}/{len(q['gold'])}{extra}")
        rows.append(row)
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  {q['id']:4} {q['type']:6} " + "  ".join(f"{c:14}" for c in cells) + f"  {q['question']}", flush=True)
    out.close()
    print_scores(rows, list(searchers))
    for v in searchers:
        if v.startswith("B"):
            no_start = sum(r[v]["start_nodes"] == 0 for r in rows)
            short = sum(r[v]["returned"] < TOP_N for r in rows)
            print(f"  {v}: 출발 점 0개라 유사도만으로 고른 질문 {no_start}개, {TOP_N}개보다 적게 돌려준 질문 {short}개, LLM 거름이 실패해 거르지 않은 선을 쓴 호출 {edge_filters[v].failures}번")


if __name__ == "__main__":
    commands = {"chunk": chunk, "extract": extract, "concepts": conceptualize, "check": check_questions, "evaluate": evaluate}
    commands[sys.argv[1]](*sys.argv[2:])
