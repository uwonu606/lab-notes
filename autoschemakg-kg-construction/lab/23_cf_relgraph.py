"""9단계 cf-relgraph: 사내화 claim 에서 관계 목록에 정의된 선만 Haiku 로 뽑고, 질문 → 구심점 → 관계 선 → claim 길로 찾는다.

    python3 23_cf_relgraph.py pilot --docs 12     # 시범 문서로 Haiku 비용 추정 → runs/23-cf-relgraph/pilot.json
    python3 23_cf_relgraph.py extract             # 전 문서 → runs/23-cf-relgraph/extract-raw.jsonl
    python3 23_cf_relgraph.py edges               # 끝 이름 풀기 → edges.jsonl, undefined-relations.jsonl, edges-stats.json
    .venv-hr2/bin/python 23_cf_relgraph.py embed-edges   # 선 글 bge-m3 → idx/emb-edges.npy (GPU)
    .venv-hr2/bin/python 23_cf_relgraph.py run --link model --scope inputs/net-corpus-cf/gold/scope-retrieval.txt
                                                  # cf-relgraph: 공유 연결 결과 runs/23-cf-link/*.jsonl 의 hubs 를 읽는다
    .venv-hr2/bin/python 23_cf_relgraph.py run --link text    # cf-relgraph-textlink (글자 매칭 연결)

색인 쪽은 사내화 문서·claim·카드(hubs.json)·관계 목록·용어집만 읽는다. 위치 대응표와 정답은 읽지 않는다.
설정은 runs/23-cf-relgraph/CONFIG.md.
"""
import argparse
import hashlib
import importlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

LAB = Path(__file__).parent
sys.path.insert(0, str(LAB))
OUT = LAB / "runs/23-cf-relgraph"
CF_DOCS = LAB / "inputs/net-corpus-cf/docs.jsonl"
CF_CLAIMS = LAB / "runs/23-cf-units/claim.jsonl"
CF_IDX = LAB / "runs/23-cf-units/idx"
RELATIONS = LAB / "inputs/net-corpus/relglossary/relations.json"
HUBS = LAB / "inputs/net-corpus/relglossary/hubs.json"
PROMPT = LAB / "prompts/relgraph-extract.txt"
SYSTEM = "Follow the user's instructions exactly. Reply with only the JSON that is asked for, no commentary."
CHUNK_CHARS = 6000
CLAIM_CHARS = 500
VALUE_KINDS = {"version", "year", "date", "spec-id", "test-case-id", "error-text", "measurement"}
ENTRY_COVER = 0.5
CTX_DEPTH = 400
LINK_DIR = LAB / "runs/23-cf-link"


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalized(text):
    return re.sub(r"[\s\-_./]", "", text.lower())


def relations():
    return json.loads(RELATIONS.read_text(encoding="utf-8"))["relations"]


def hubs():
    cf_layer = importlib.import_module("23_cf_layer")
    rows = {row["id"]: row for row in json.loads(HUBS.read_text(encoding="utf-8"))["hubs"]}
    return [(hub, rows[hub.id]) for hub in cf_layer.read_hubs(HUBS)]


def prompt_template():
    rel_lines = [f'{r["id"]} | {r["name_en"]} / {r["name_ko"]} | {r["definition"]} | {", ".join(r["head_types"])} -> {", ".join(r["tail_types"])}'
                 for r in relations()]
    card_lines = [f'{hub.id} | {", ".join([*hub.internal_names, hub.slug])} | {row["type"]}' for hub, row in hubs()]
    return (PROMPT.read_text(encoding="utf-8").replace("<<RELATIONS>>", "\n".join(rel_lines))
            .replace("<<CARDS>>", "\n".join(card_lines)))


def doc_chunks():
    docs = {d["doc_id"]: d for d in read_jsonl(CF_DOCS)}
    by_doc = defaultdict(list)
    for claim in read_jsonl(CF_CLAIMS):
        by_doc[claim["doc_id"]].append(claim)
    chunks = []
    for doc_id in sorted(by_doc):
        current, size = [], 0
        for claim in sorted(by_doc[doc_id], key=lambda c: c["start"]):
            text = claim["text"].replace("\n", " ")[:CLAIM_CHARS]
            if current and size + len(text) > CHUNK_CHARS:
                chunks.append((docs[doc_id], current))
                current, size = [], 0
            current.append((claim["unit_id"], text))
            size += len(text)
        if current:
            chunks.append((docs[doc_id], current))
    return chunks


def chunk_prompt(template, doc, claims):
    lines = "\n".join(f"{n}. {text}" for n, (_, text) in enumerate(claims, start=1))
    return (template.replace("<<TITLE>>", doc["title"].replace("\n", " ")[:200]).replace("<<KIND>>", doc["kind"])
            .replace("<<CLAIMS>>", lines))


def chunk_key(doc_id, claims):
    return doc_id + ":" + hashlib.sha256("|".join(u for u, _ in claims).encode()).hexdigest()[:10]


def extract(limit_docs=None, out_name="extract-raw.jsonl", concurrency=8):
    from llm_cache import ClaudeClient, LLMCallFailed

    template = prompt_template()
    chunks = doc_chunks()
    if limit_docs:
        doc_ids = sorted({doc["doc_id"] for doc, _ in chunks})
        step = max(1, len(doc_ids) // limit_docs)
        picked = set(doc_ids[::step][:limit_docs])
        chunks = [(doc, claims) for doc, claims in chunks if doc["doc_id"] in picked]
    prompts = [chunk_prompt(template, doc, claims) for doc, claims in chunks]
    client = ClaudeClient("haiku", max_concurrency=concurrency, timeout=600.0)
    replies = client.ask_many(prompts, SYSTEM, tag="relgraph-extract")
    rows = []
    for (doc, claims), prompt, reply in zip(chunks, prompts, replies):
        row = {"chunk": chunk_key(doc["doc_id"], claims), "doc_id": doc["doc_id"], "claim_ids": [u for u, _ in claims],
               "prompt_chars": len(prompt)}
        if isinstance(reply, LLMCallFailed):
            row["error"] = str(reply)[:300]
        else:
            row["reply"] = reply.text
            row["usage"] = reply.metadata
            entry = json.loads(client.cache_path(prompt, SYSTEM).read_text(encoding="utf-8"))
            row["cost_usd"], row["seconds"] = entry["cost_usd"], entry["seconds"]
        rows.append(row)
    write_jsonl(OUT / out_name, rows)
    return rows, chunks, client


def pilot(docs):
    rows, chunks, client = extract(limit_docs=docs, out_name="pilot-raw.jsonl")
    all_chunks = doc_chunks()
    ok = [r for r in rows if "reply" in r]
    cost = sum(r["cost_usd"] for r in ok)
    chars = sum(r["prompt_chars"] for r in rows)
    total_chars = sum(len(chunk_prompt(prompt_template(), d, c)) for d, c in all_chunks)
    summary = {"pilot_docs": docs, "pilot_chunks": len(rows), "failed": len(rows) - len(ok), "pilot_cost_usd": round(cost, 3),
               "pilot_prompt_chars": chars, "all_chunks": len(all_chunks), "all_prompt_chars": total_chars,
               "estimate_usd_by_chars": round(cost * total_chars / chars, 2) if chars else None,
               "estimate_usd_by_chunks": round(cost * len(all_chunks) / len(rows), 2) if rows else None,
               "usage": client.usage_line()}
    (OUT / "pilot.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def parse_reply(text):
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


class Resolver:
    """끝 이름 → 노드. 구심점(사내 이름·slug 글자 같음 → 그 안에 든 사내 이름), 용어집 항목(글자 같음 → 태거가 글자 절반 이상 덮음), 등록 안 된 용어, 값."""

    def __init__(self):
        glossary = json.loads((LAB / "inputs/net-corpus/glossary/glossary.json").read_text(encoding="utf-8"))
        self.entry_type = {e["id"]: e["type"] for e in glossary["entries"]}
        self.hub_rows = hubs()
        self.hub_ids = {hub.id for hub, _ in self.hub_rows}
        self.hub_key = {}
        self.hub_patterns = []
        for hub, row in self.hub_rows:
            for surface in [*hub.internal_names, hub.slug]:
                self.hub_key[normalized(surface)] = hub.id
                self.hub_patterns.append((re.compile(re.escape(surface), re.I), hub.id, len(surface)))
        self.hub_patterns.sort(key=lambda p: -p[2])
        self.entry_key = {}
        for entry in sorted(glossary["entries"], key=lambda e: -e["docs"]):
            if entry["id"] in self.hub_ids:
                continue
            for name in [entry["canonical"], *(a["text"] for a in entry["aliases"])]:
                self.entry_key.setdefault(normalized(name), entry["id"])
        self.tagger = importlib.import_module("23_glossary_tag").GlossaryTagger()

    def resolve(self, text, kind):
        text = (text or "").strip()
        if not text:
            return None
        if kind in VALUE_KINDS:
            return {"node": f"{kind}:{normalized(text)[:80]}", "text": text, "type": kind, "how": "value"}
        key = normalized(text)
        if key in self.hub_key:
            return self._hub(self.hub_key[key], text, "hub-exact")
        if key in self.entry_key:
            entry_id = self.entry_key[key]
            return {"node": f"entry:{entry_id}", "text": text, "type": self.entry_type[entry_id], "how": "entry-exact"}
        if "://" not in text:
            for pattern, hub_id, _ in self.hub_patterns:
                if pattern.search(text):
                    return self._hub(hub_id, text, "hub-inside")
        best = None
        for entry in self.tagger.tag_text(text)["entries"]:
            if entry["id"] in self.hub_ids:
                continue
            covered = max(m["end"] - m["start"] for m in entry["matches"])
            if covered >= ENTRY_COVER * len(text) and (best is None or covered > best[1]):
                best = (entry["id"], covered)
        if best:
            return {"node": f"entry:{best[0]}", "text": text, "type": self.entry_type[best[0]], "how": "entry-tagged"}
        return {"node": f"term:{key[:80]}", "text": text, "type": None, "how": "term"}

    def _hub(self, hub_id, text, how):
        return {"node": f"hub:{hub_id}", "text": text, "type": self.entry_type.get(hub_id), "how": how}


def type_ok(end, allowed):
    if end["type"] is None:
        return None
    return end["type"] in allowed


def build_edges():
    rels = {r["id"]: r for r in relations()}
    resolver = Resolver()
    raw = read_jsonl(OUT / "extract-raw.jsonl")
    merged, undefined = {}, []
    counts = Counter()
    for row in raw:
        if "reply" not in row:
            counts["failed_chunks"] += 1
            continue
        try:
            parsed = parse_reply(row["reply"])
        except (ValueError, json.JSONDecodeError):
            counts["broken_json_chunks"] += 1
            continue
        claim_ids = row["claim_ids"]

        def claims_of(numbers):
            out = []
            for n in numbers or []:
                if isinstance(n, int) and 1 <= n <= len(claim_ids):
                    out.append(claim_ids[n - 1])
                else:
                    counts["bad_claim_numbers"] += 1
            return out

        for item in parsed.get("other", []):
            undefined.append({"doc_id": row["doc_id"], "reason": "other", "rel": item.get("rel_name", ""),
                              "head": item.get("head", ""), "tail": item.get("tail", ""), "claims": claims_of(item.get("claims"))})
        for item in parsed.get("edges", []):
            counts["proposed"] += 1
            claims = claims_of(item.get("claims"))
            if item.get("rel") not in rels:
                undefined.append({"doc_id": row["doc_id"], "reason": "unknown-id", "rel": item.get("rel", ""),
                                  "head": item.get("head", ""), "tail": item.get("tail", ""), "claims": claims})
                continue
            if not claims:
                counts["dropped_no_claim"] += 1
                continue
            head = resolver.resolve(item.get("head"), item.get("head_kind", "term"))
            tail = resolver.resolve(item.get("tail"), item.get("tail_kind", "term"))
            if not head or not tail:
                counts["dropped_empty_end"] += 1
                continue
            if head["node"] == tail["node"]:
                counts["dropped_self_loop"] += 1
                continue
            relation = rels[item["rel"]]
            key = (row["doc_id"], item["rel"], head["node"], tail["node"])
            if key in merged:
                merged[key]["claims"] = sorted(set(merged[key]["claims"]) | set(claims))
                counts["merged_duplicates"] += 1
                continue
            merged[key] = {"rel": item["rel"], "head": head, "tail": tail, "doc_id": row["doc_id"], "claims": sorted(set(claims)),
                           "head_type_ok": type_ok(head, relation["head_types"]), "tail_type_ok": type_ok(tail, relation["tail_types"])}
    edges = [{"edge_id": f"e{n:06d}", **edge} for n, edge in enumerate(merged.values())]
    write_jsonl(OUT / "edges.jsonl", edges)
    write_jsonl(OUT / "undefined-relations.jsonl", undefined)
    stats = {
        "chunks": len(raw), **counts, "edges": len(edges), "undefined": len(undefined),
        "undefined_by_reason": Counter(u["reason"] for u in undefined),
        "undefined_top_names": Counter(u["rel"].lower() for u in undefined).most_common(40),
        "edges_by_rel": Counter(e["rel"] for e in edges).most_common(),
        "end_resolution": Counter(end["how"] for e in edges for end in (e["head"], e["tail"])),
        "edges_touching_hub": sum(e["head"]["node"].startswith("hub:") or e["tail"]["node"].startswith("hub:") for e in edges),
        "hubs_with_edges": len({end["node"] for e in edges for end in (e["head"], e["tail"]) if end["node"].startswith("hub:")}),
        "claims_with_edges": len({c for e in edges for c in e["claims"]}),
        "type_check": {side: Counter(str(e[f"{side}_type_ok"]) for e in edges) for side in ("head", "tail")},
        "cost_usd": round(sum(r.get("cost_usd", 0) for r in raw), 3),
        "seconds": round(sum(r.get("seconds", 0) for r in raw), 1),
    }
    (OUT / "edges-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=dict))
    print(json.dumps(stats, ensure_ascii=False, indent=1, default=dict))


def edge_text(edge, rels):
    relation = rels[edge["rel"]]
    return f'{edge["head"]["text"]} — {relation["name_ko"]} ({relation["name_en"]}) — {edge["tail"]["text"]}'


def edge_vectors(edges, rels):
    import numpy as np
    import embed_client

    path = OUT / "idx/emb-edges.npy"
    ids_path = path.with_suffix(".ids.json")
    ids = [e["edge_id"] for e in edges]
    if path.exists() and json.loads(ids_path.read_text()) == ids:
        return np.load(path)
    matrix = np.asarray(embed_client.embed([edge_text(e, rels) for e in edges]), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, matrix)
    ids_path.write_text(json.dumps(ids))
    return matrix


class RelGraph:
    """구심점에 닿은 선을 질문과 선 글의 cosine 순으로 세우고, claim 은 그 claim 을 낸 선 가운데 가장 높은 선의 점수·순위를 받는다."""

    def __init__(self, arch, ctx):
        self.arch, self.ctx = arch, ctx
        self.rels = {r["id"]: r for r in relations()}
        self.edges = read_jsonl(OUT / "edges.jsonl")
        self.matrix = edge_vectors(self.edges, self.rels)
        self.edges_of_hub = defaultdict(list)
        for n, edge in enumerate(self.edges):
            for end in (edge["head"], edge["tail"]):
                if end["node"].startswith("hub:"):
                    self.edges_of_hub[end["node"][4:]].append(n)

    def ranking(self, qvec, hub_ids):
        """(닿은 선 행 번호, 선 길 claim 단위 순위). 단위에 best_edge(선 행 번호)를 단다."""
        import numpy as np

        edge_rows = sorted({n for h in hub_ids for n in self.edges_of_hub.get(h, [])})
        graph_ranked = []
        if not edge_rows:
            return edge_rows, graph_ranked
        edge_scores = self.matrix[edge_rows] @ np.asarray(qvec, dtype=np.float32)
        best_edge_of_claim = {}
        for row_n, score in sorted(zip(edge_rows, edge_scores), key=lambda p: -p[1]):
            for claim_id in self.edges[row_n]["claims"]:
                best_edge_of_claim.setdefault(claim_id, (row_n, float(score)))
        for claim_id, (row_n, score) in best_edge_of_claim.items():
            if claim_id not in self.ctx.index_of:
                continue
            edge = self.edges[row_n]
            hub = next(end["node"][4:] for end in (edge["head"], edge["tail"]) if end["node"][4:] in hub_ids)
            unit = self.ctx.as_unit(self.ctx.index_of[claim_id], score,
                                    self.arch.path(f"relgraph={hub}", f"rel={edge['rel']}", unit="claim"))
            graph_ranked.append({**unit, "best_edge": row_n})
        return edge_rows, graph_ranked


def run(link_mode, scope=None):
    os.environ["NET_CORPUS"] = "cf"
    arch = importlib.import_module("23_arch_common")
    cf_runs = importlib.import_module("23_cf_runs")
    link = importlib.import_module("23_cf_link")
    import embed_client

    questions = arch.read_questions()
    if scope:
        keep = {line.split("\t")[0].strip() for line in Path(scope).read_text().splitlines() if line.strip()}
        questions = [q for q in questions if q.qid in keep]
    qvecs = arch.embed_questions(questions)
    ctx = cf_runs.claim_ctx_units(arch, CF_IDX / "emb-claim-ctx.npy")
    graph = RelGraph(arch, ctx)
    edges = graph.edges
    cards = link.read_cards()
    if link_mode == "model":
        link_rows = {r["qid"]: r for f in sorted(LINK_DIR.glob("*.jsonl")) for r in read_jsonl(f)}
        missing = [q.qid for q in questions if q.qid not in link_rows]
        if missing:
            raise SystemExit(f"연결 결과가 없는 문항 {len(missing)}개: {missing[:5]}")
        link_errors = [q.qid for q in questions if link_rows[q.qid].get("error")]
        linked = {q.qid: link_rows[q.qid]["hubs"] for q in questions}
    else:
        link_errors = []
        linked = {q.qid: link.text_match(q.question, cards) for q in questions}
    variant = "cf-relgraph" if link_mode == "model" else "cf-relgraph-textlink"
    run_ = arch.Run(variant.removeprefix("cf-"))
    for q, qvec in zip(questions, qvecs):
        ctx_ranked = ctx.dense_units(qvec, path_stages=("dense=claim-ctx",), top=CTX_DEPTH)
        hub_ids = linked.get(q.qid, [])
        edge_rows, graph_ranked = graph.ranking(qvec, hub_ids)
        graph_ranked = [{k: v for k, v in u.items() if k != "best_edge"} for u in graph_ranked]
        units = arch.fill_budget(arch.rrf(graph_ranked, ctx_ranked) if graph_ranked else ctx_ranked)
        run_.add(q.qid, variant, units, linked=hub_ids,
                 stage_counts={"edges": len(edge_rows), "relgraph_claims": len(graph_ranked), "dense=claim-ctx": CTX_DEPTH},
                 empty_stages=[] if graph_ranked else ["relgraph"], llm={"calls": 1 if link_mode == "model" else 0},
                 link_error=q.qid in link_errors)
    run_.write()
    print(run_.score())
    (run_.dir / "run-report.json").write_text(json.dumps({
        "variant": variant, "link": link_mode, "edges": len(edges), "edges_sha256": arch.sha256_of(OUT / "edges.jsonl"),
        "gold": str(arch.GOLD.relative_to(LAB)), "gold_sha256": arch.sha256_of(arch.GOLD), "questions": len(questions),
        "linked_questions": sum(bool(linked.get(q.qid)) for q in questions), "link_errors": link_errors,
        "scope": scope, "embed_stats": embed_client.stats},
        ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description="9단계 cf-relgraph")
    parser.add_argument("command", choices=["pilot", "extract", "edges", "embed-edges", "run"])
    parser.add_argument("--docs", type=int, default=12)
    parser.add_argument("--link", choices=["model", "text"], default="model")
    parser.add_argument("--scope")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.command == "pilot":
        pilot(args.docs)
    elif args.command == "extract":
        rows, _, client = extract()
        print(f"chunks {len(rows)}, failed {sum('error' in r for r in rows)}; {client.usage_line()}")
    elif args.command == "edges":
        build_edges()
    elif args.command == "embed-edges":
        import embed_client
        edges = read_jsonl(OUT / "edges.jsonl")
        matrix = edge_vectors(edges, {r["id"]: r for r in relations()})
        print(f"edge vectors {matrix.shape}, backend {embed_client.stats.get('backend')}, new texts {embed_client.stats.get('requested_texts')}")
    else:
        run(args.link, args.scope)


if __name__ == "__main__":
    main()
