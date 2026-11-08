"""쪼개기 판마다 청크를 bge-m3 로 임베딩하고 질문마다 순위를 낸다. 채점은 23_score.py 가 한다.

    .venv-25/bin/python 25_split_retrieve.py gold --out runs/25-split/gold.jsonl
    .venv-25/bin/python 25_split_retrieve.py search --gold runs/25-split/gold.jsonl --out runs/25-split/retrieval.jsonl \
        --arm fixed=runs/25-split/base/chunks-fixed.jsonl \
        --arm mdheader=runs/25-split/base/chunks-mdheader.jsonl \
        --arm harness=runs/25-split/haiku/chunks-harness.jsonl \
        --arm harness-raw=runs/25-split/haiku/chunks-harness.jsonl:raw
    python3 23_score.py runs/25-split/retrieval.jsonl runs/25-split/gold.jsonl --baseline fixed

임베딩 글은 "<label>\n<원문 구간>" 이다. 판 이름 뒤 :raw 는 label 을 빼고 원문 구간만 임베딩한다.
gold 는 qa/*.json 의 quote 를 md 원문에서 찾아 문자 위치로 바꾼다. 찾지 못한 quote 는 버리고 그 수를 알린다.

route 는 하네스 청크의 칸을 질의 때 쓴다. Haiku 가 질문마다 답이 있을 (문서 종류, 칸)을 최대 3개 고르고,
전체 dense 순위와 그 칸 청크만의 dense 순위를 RRF(k=RRF_K)로 섞는다. 고른 칸이 없거나 칸 청크가 없으면 dense 순위 그대로다.
--within-top-docs 를 주면 칸 청크를 dense 문서 순위(문서 안 청크 최고점) 상위 ROUTE_TOP_DOCS 문서 안에서만 센다.
    .venv-25/bin/python 25_split_retrieve.py route --gold runs/25-split/gold.jsonl --out runs/25-split/retrieval-route.jsonl \
        --chunks runs/25-split/haiku/chunks-harness.jsonl --decisions runs/25-split/haiku/decisions.jsonl --name harness-route

--corpus 는 md/ 와 qa/ 를 담은 말뭉치 폴더다(기본 inputs/parser-corpus). 열화 말뭉치는 부속 명령 앞에 준다.
    .venv-25/bin/python 25_split_retrieve.py --corpus inputs/parser-corpus-messy/L2 search --gold inputs/parser-corpus-messy/L2/gold.jsonl ...
"""
import argparse
import json
from pathlib import Path

import numpy as np

from embed_client import embed

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/parser-corpus"
KEEP_UNITS = 40
RRF_K = 60
ROUTE_TOP_DOCS = 5


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def doc_text(doc_id, cache={}):
    if doc_id not in cache:
        cache[doc_id] = (Path(CORPUS) / "md" / f"{doc_id}.md").read_text(encoding="utf-8")
    return cache[doc_id]


def gold(args):
    rows, lost, total = [], [], 0
    for path in sorted((CORPUS / "qa").glob("*.json")):
        for question in json.loads(path.read_text(encoding="utf-8")):
            items = []
            for item in question.get("evidence") or []:
                spans = []
                for quote in item.get("quotes") or []:
                    total += 1
                    doc_path = CORPUS / "md" / f"{quote['doc']}.md"
                    start = doc_text(quote["doc"]).find(quote["quote"]) if doc_path.exists() else -1
                    if start < 0:
                        lost.append((question["qid"], quote["doc"], quote["quote"][:40]))
                        continue
                    spans.append({"doc_id": quote["doc"], "start": start, "end": start + len(quote["quote"])})
                if spans:
                    items.append({"label": item.get("label", ""), "spans": spans})
            if question.get("evidence") and not items:
                lost.append((question["qid"], "-", "근거 묶음이 모두 사라짐"))
                continue
            rows.append({"qid": question["qid"], "type": question["type"], "question": question["question"],
                         "answer": question.get("answer", ""), "ambiguous": bool(question.get("ambiguous")), "evidence": items})
    write_jsonl(args.out, rows)
    print(f"질문 {len(rows)}개 · quote {total}개 중 못 찾음 {len(lost)}개")
    for row in lost[:20]:
        print("  못 찾음", row)


def search(args):
    questions = read_jsonl(args.gold)
    query_vectors = np.array(embed([q["question"] for q in questions]), dtype=np.float32)
    out = []
    for spec in args.arm:
        name, _, source = spec.partition("=")
        path, _, mode = source.partition(":")
        chunks = read_jsonl(path)
        matrix = chunk_matrix(chunks, mode)
        scores = query_vectors @ matrix.T
        for qi, question in enumerate(questions):
            order = np.argsort(-scores[qi])[:KEEP_UNITS]
            units = [{"doc_id": chunks[i]["doc_id"], "start": chunks[i]["start"], "end": chunks[i]["end"], "score": float(scores[qi, i]),
                      "path": f"{chunks[i].get('route', name).split(':')[0]}>unit={chunks[i].get('field', 'chunk')}"} for i in order]
            out.append({"qid": question["qid"], "variant": name, "units": units})
        sizes = [c["end"] - c["start"] for c in chunks]
        print(f"{name}: 청크 {len(chunks)}개 · 평균 {sum(sizes) / len(sizes):.0f}자 · 중앙 {sorted(sizes)[len(sizes) // 2]}자")
    write_jsonl(args.out, out)


def chunk_matrix(chunks, mode=""):
    texts = [doc_text(c["doc_id"])[c["start"]:c["end"]] for c in chunks]
    if mode != "raw":
        texts = [f"{c['label']}\n{t}" if c.get("label") else t for c, t in zip(chunks, texts)]
    return np.array(embed(texts), dtype=np.float32)


def route(args):
    import importlib.util
    spec = importlib.util.spec_from_file_location("harness25", LAB / "25_split_harness.py")
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    from llm_cache import ClaudeClient, LLMCallFailed

    questions = read_jsonl(args.gold)
    chunks = read_jsonl(args.chunks)
    doc_types = {d["doc_id"]: d.get("doc_type") for d in read_jsonl(args.decisions)}
    keys = [(doc_types.get(c["doc_id"]), c.get("field")) for c in chunks]
    matrix = chunk_matrix(chunks)
    query_vectors = np.array(embed([q["question"] for q in questions]), dtype=np.float32)
    template = (LAB / "prompts/25-query-fields.txt").read_text(encoding="utf-8")
    schemas = harness.schemas_text(harness.load_schemas(args.schemas or harness.SCHEMA_DIR))
    client = ClaudeClient("haiku", cache_dir=LAB / "runs/25-cache/llm")
    prompts = [template.replace("{schemas}", schemas).replace("{question}", q["question"]) for q in questions]
    replies = client.ask_many(prompts, tag="route")

    out, trace = [], []
    for qi, (question, reply) in enumerate(zip(questions, replies)):
        try:
            targets = {(t["doc_type"], t["field"]) for t in harness.parse_json(reply.text).get("targets", [])}
        except (ValueError, KeyError, TypeError, AttributeError):
            targets = set()
        scores = matrix @ query_vectors[qi]
        dense = list(np.argsort(-scores))
        allowed = None
        if args.within_top_docs:
            allowed = list(dict.fromkeys(chunks[i]["doc_id"] for i in dense))[:ROUTE_TOP_DOCS]
        inside = [i for i in dense if keys[i] in targets and (allowed is None or chunks[i]["doc_id"] in allowed)]
        fused = {}
        for rank, i in enumerate(dense):
            fused[i] = 1 / (RRF_K + rank + 1)
        for rank, i in enumerate(inside):
            fused[i] += 1 / (RRF_K + rank + 1)
        order = sorted(fused, key=lambda i: -fused[i])[:KEEP_UNITS]
        units = [{"doc_id": chunks[i]["doc_id"], "start": chunks[i]["start"], "end": chunks[i]["end"], "score": fused[i],
                  "path": f"{'field' if keys[i] in targets else 'dense'}>unit={chunks[i].get('field')}"} for i in order]
        out.append({"qid": question["qid"], "variant": args.name, "units": units})
        trace.append({"qid": question["qid"], "targets": sorted(map(list, targets)), "inside": len(inside)})
    write_jsonl(args.out, out)
    write_jsonl(Path(args.out).with_suffix(".trace.jsonl"), trace)
    print(f"{args.name}: 칸을 고른 질문 {sum(1 for t in trace if t['targets'])}/{len(trace)} · {client.usage_line()}")


def main():
    global CORPUS
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", default=CORPUS)
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("gold")
    g.add_argument("--out", required=True)
    s = sub.add_parser("search")
    s.add_argument("--gold", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--arm", action="append", required=True, help="이름=청크 jsonl[:raw]")
    r = sub.add_parser("route")
    r.add_argument("--gold", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--chunks", required=True)
    r.add_argument("--decisions", required=True)
    r.add_argument("--name", default="harness-route")
    r.add_argument("--within-top-docs", action="store_true")
    r.add_argument("--schemas", help="칸 정의 폴더 (기본: inputs/parser-schemas)")
    args = parser.parse_args()
    CORPUS = Path(args.corpus)
    {"gold": gold, "search": search, "route": route}[args.command](args)


if __name__ == "__main__":
    main()
