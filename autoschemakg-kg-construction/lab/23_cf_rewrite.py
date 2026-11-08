"""9단계 검색 판 cf-rewrite: 작은 모델(qwen3:8b)이 질문 + 연결된 카드를 읽고 사내 말로 검색 질의를 다시 쓴다 → 사내화 claim-ctx dense.

    .venv-hr2/bin/python 23_cf_rewrite.py queries   # qwen3:8b 만 부른다 → runs/23-cf-rewrite/queries.jsonl (scope-retrieval.txt 199문항)
    .venv-hr2/bin/python 23_cf_rewrite.py embed     # 다시 쓴 질의를 임베딩해 캐시에만 넣는다 (embed-stage.sh rewrite 가 부른다)
    .venv-hr2/bin/python 23_cf_rewrite.py search    # 캐시의 질의 벡터로 검색 → retrieval·trace·score, questions-cf.jsonl 로 채점

두 단계로 나눈 것은 qwen3:8b 를 내린 뒤에 임베딩을 하기 위해서다. 둘이 같은 GPU(8GB)에 함께 올라가면 임베딩 서버가 CUDA 오류로 깨졌다.
검색은 cf-claimctx(23_cf_runs.run_claimctx)와 같다: 같은 벡터, 상위 400, fill_budget. 질의 글만 다르다.
연결된 카드가 없거나 다시 쓰기가 실패한 문항은 원래 질문으로 찾고 path 첫 단계를 dense 로 둔다.
작은 모델 호출 자체가 실패한 문항(빈 답 등)이 있으면 queries 는 결과를 쓴 뒤 종료 코드 1 로 끝난다. 실패는 캐시되지 않아 다시 돌리면 그것만 부른다.
JSON 이 깨진 답은 모델 품질이라 실패로 치지 않는다.
"""
import argparse
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path

LAB = Path(__file__).parent
os.environ.setdefault("NET_CORPUS", "cf")
os.environ.setdefault("NET_GOLD", "inputs/net-corpus-cf/gold/questions-cf.jsonl")
sys.path.insert(0, str(LAB))
arch = importlib.import_module("23_arch_common")
cf_runs = importlib.import_module("23_cf_runs")
link = importlib.import_module("23_cf_link")

SCOPE = LAB / "inputs/net-corpus-cf/gold/scope-retrieval.txt"
LINKS = [LAB / "runs/23-cf-link/questions-alias.jsonl", LAB / "runs/23-cf-link/questions-fact.jsonl"]
PROMPT = LAB / "prompts/cf-rewrite.txt"
VECTORS = cf_runs.CF_IDX / "emb-claim-ctx.npy"
RUN_DIR = LAB / "runs/23-cf-rewrite"
QUERIES = RUN_DIR / "queries.jsonl"
VARIANT = "cf-rewrite"


def scoped_questions():
    scope = link.read_scope(SCOPE)
    return [q for q in arch.read_questions() if q.qid in scope]


def read_links():
    return {row["qid"]: row for path in LINKS for row in arch.read_jsonl(path)}


def rewrite_prompt(question, cards):
    return f"[질문]\n{question}\n\n[카드]\n{link.render_cards(cards)}"


def parse_query(text):
    match = re.search(r"\{.*\}", text, re.S)
    query = json.loads(match.group(0)).get("query", "") if match else ""
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"query 가 없다: {text[:200]}")
    return query.strip()


def write_queries():
    from llm_cache import LLMCallFailed
    from ollama_cache import OllamaClient

    questions = scoped_questions()
    links = read_links()
    cards_by_id = {c.id: c for c in link.read_cards()}
    client = OllamaClient("qwen3:8b", num_predict=256, json_output=True)
    system = PROMPT.read_text(encoding="utf-8")
    to_rewrite = [q for q in questions if links[q.qid]["hubs"]]
    prompts = {q.qid: rewrite_prompt(q.question, [cards_by_id[h] for h in links[q.qid]["hubs"]]) for q in to_rewrite}
    started = time.monotonic()
    replies = dict(zip(prompts, client.ask_many(list(prompts.values()), system=system, tag="cf-rewrite")))
    rows = []
    for q in questions:
        row = {"qid": q.qid, "question": q.question, "linked_hubs": links[q.qid]["hubs"], "text_hubs": links[q.qid]["text_hubs"],
               "link_error": links[q.qid]["error"]}
        if q.qid in prompts:
            reply = replies[q.qid]
            row["llm"] = {"calls": 2, **arch.llm_record(client, prompts[q.qid], system)}
            if isinstance(reply, LLMCallFailed):
                row.update(llm_failed=True, rewrite_error=str(reply)[:300])
            else:
                try:
                    row["rewritten"] = parse_query(reply.text)
                except (ValueError, json.JSONDecodeError) as error:
                    row["rewrite_error"] = str(error)[:300]
        else:
            row["llm"] = {"calls": 1}
        rows.append(row)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    arch.write_jsonl(QUERIES, rows)
    failed = sum(bool(r.get("llm_failed")) for r in rows)
    print(f"{QUERIES}: {len(rows)}문항 · 다시 씀 {sum('rewritten' in r for r in rows)} · 카드 없음 {sum(not r['linked_hubs'] for r in rows)} · "
          f"JSON 깨짐 {sum('rewrite_error' in r and not r.get('llm_failed') for r in rows)} · LLM 실패 {failed} · "
          f"{time.monotonic() - started:.0f}초 · {client.usage_line()}", flush=True)
    if failed:
        sys.exit(1)


def query_texts(rows):
    return [r.get("rewritten", r["question"]) for r in rows]


def embed_queries():
    import embed_client

    rows = arch.read_jsonl(QUERIES)
    arch.embed_questions(query_texts(rows))
    print(f"embed: 질의 {len(rows)}개 · 서버에 보낸 글 {embed_client.stats['requested_texts']}개 · "
          f"캐시에서 읽은 글 {embed_client.stats['cached_texts']}개 · 백엔드 {embed_client.stats['backend']}", flush=True)


def search():
    import embed_client

    rows = arch.read_jsonl(QUERIES)
    queries = query_texts(rows)
    qvecs = arch.embed_questions(queries)
    ctx = cf_runs.claim_ctx_units(arch, VECTORS)
    run = arch.Run("rewrite")
    for row, query, qvec in zip(rows, queries, qvecs):
        rewritten = "rewritten" in row
        stages = (f"rewrite={'|'.join(row['linked_hubs'])}", "dense=claim-ctx") if rewritten else ("dense=claim-ctx",)
        ranked = ctx.dense_units(qvec, path_stages=stages, top=cf_runs.DEPTH)
        trace = {k: v for k, v in row.items() if k not in ("qid", "question")}
        run.add(row["qid"], VARIANT, arch.fill_budget(ranked), stage_counts={"dense=claim-ctx": cf_runs.DEPTH},
                empty_stages=[] if rewritten else ["rewrite"], parsed={"query": query}, **trace)
    run.write()
    print(run.score())
    (run.dir / "run-report.json").write_text(json.dumps({
        "variant": VARIANT, "questions": len(rows), "rewritten": sum("rewritten" in r for r in rows),
        "no_hub": sum(not r["linked_hubs"] for r in rows), "rewrite_errors": sum("rewrite_error" in r for r in rows),
        "llm_failed": sum(bool(r.get("llm_failed")) for r in rows), "prompt": str(PROMPT.relative_to(LAB)),
        "docs_sha256": arch.sha256_of(arch.DOCS), "gold": str(arch.GOLD.relative_to(LAB)), "gold_sha256": arch.sha256_of(arch.GOLD),
        "hubs_sha256": arch.sha256_of(link.HUBS), "scope_sha256": arch.sha256_of(SCOPE), "vectors_sha256": arch.sha256_of(VECTORS),
        "queries_sha256": arch.sha256_of(QUERIES), "embed_stats": embed_client.stats}, ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description="cf-rewrite: queries(qwen3:8b) 와 search(임베딩·검색·채점) 두 단계.")
    parser.add_argument("command", choices=["queries", "embed", "search"])
    {"queries": write_queries, "embed": embed_queries, "search": search}[parser.parse_args().command]()


if __name__ == "__main__":
    main()
