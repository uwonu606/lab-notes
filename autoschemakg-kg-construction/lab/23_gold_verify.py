"""정답을 작성 맥락 없는 Opus 호출로 다시 판정한다.

1. 무작위 표본: 질문·정답·근거 구간 원문만 주고 근거가 정답을 뒷받침하는지 묻는다.
2. 근거 없음 전수: 질문마다 BM25·dense 상위 청크와 near 구간을 주고 그 안에 답이 있는지 묻는다.
프롬프트와 판정 원문을 out_dir 에 남긴다.

    .venv-hr2/bin/python 23_gold_verify.py <questions.jsonl> --docs <docs.jsonl...> --out-dir <dir> [--sample 20] [--seed 23]
"""
import argparse
import json
import random
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pool = load("gold_pool", LAB / "23_gold_pool.py")
build = pool.build

SYSTEM = "You are an independent reviewer of a retrieval benchmark. You have not seen how it was made. Reply with one JSON object only."
SUPPORT_TEMPLATE = """검색 평가용 질문 하나와 그 정답, 그리고 정답의 근거라고 표시된 원문 구간들을 준다. 구간 밖의 지식이나 추측은 쓰지 말고 구간만 읽고 판정한다.

질문: {question}
정답: {answer}

근거 구간:
{spans}

판정:
- support: 근거 구간이 정답의 핵심 주장을 모두 뒷받침하면 "full", 일부만이면 "partial", 뒷받침하지 않으면 "none".
- fits_question: 근거가 질문이 묻는 대상·조건(시기·범위 포함)을 다루면 true.
- unsupported_claims: 정답에서 구간으로 뒷받침되지 않는 주장 목록(없으면 []).
- note: 한두 문장.

답 형식: {{"support": "full|partial|none", "fits_question": true|false, "unsupported_claims": [...], "note": "..."}}"""

ABSENCE_TEMPLATE = """검색 평가용 질문 하나와, 말뭉치에서 이 질문과 가장 가까운 발췌들을 준다. 이 질문은 "말뭉치에 답이 없음" 으로 표시돼 있다. 발췌만 읽고, 발췌 가운데 질문에 답하는 것이 있는지 판정한다.

질문: {question}

발췌:
{spans}

판정:
- answered: 어떤 발췌가 질문에 직접 답하면 "yes", 일부만 답하면 "partial", 답하지 않으면 "no".
- answering_excerpts: 답하는 발췌 번호 목록.
- note: 한두 문장.

답 형식: {{"answered": "yes|partial|no", "answering_excerpts": [...], "note": "..."}}"""


def span_block(docs, spans):
    lines = []
    for number, (doc_id, start, end) in enumerate(spans, 1):
        doc = docs[doc_id]
        lines.append(f"[{number}] {doc_id} ({doc['kind']}, {doc['date'][:10]}, 제목: {doc['title']})\n{doc['text'][start:end]}")
    return "\n\n".join(lines)


def evidence_spans(row):
    return [(s["doc_id"], s["start"], s["end"]) for g in row["evidence"] for s in g["spans"]]


def nearest_chunks(rows, docs, per_method):
    chunks = pool.chunks_of(docs)
    matrix = pool.embed([c["text"] for c in chunks])
    bm25 = pool.BM25([c["text"] for c in chunks])
    queries = pool.embed([r["question"] for r in rows])
    picked = {}
    for row, vector in zip(rows, queries):
        order = []
        for score in (matrix @ vector, bm25.scores(row["question"])):
            order += [i for i in np.argsort(-score)[:per_method] if i not in order]
        near = [(s["doc_id"], s["start"], s["end"]) for s in row.get("near", [])]
        picked[row["qid"]] = near + [(chunks[i]["doc_id"], chunks[i]["start"], chunks[i]["end"]) for i in order]
    return picked


def ask_all(client, jobs, tag):
    replies = client.ask_many([prompt for _, prompt in jobs], system=SYSTEM, tag=tag)
    out = []
    for (row, prompt), reply in zip(jobs, replies):
        record = {"qid": row["qid"], "type": row["type"], "prompt": prompt}
        if isinstance(reply, pool.LLMCallFailed):
            record["error"] = str(reply)
        else:
            record["reply"] = reply.text
            try:
                record["parsed"] = pool.parse_json(reply.text)
            except (ValueError, json.JSONDecodeError) as error:
                record["parse_error"] = str(error)
        out.append(record)
    return out


def main():
    parser = argparse.ArgumentParser(description="정답을 작성 맥락 없는 Opus 호출로 다시 판정한다.")
    parser.add_argument("questions")
    parser.add_argument("--docs", nargs="+", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--near-per-method", type=int, default=6)
    parser.add_argument("--qids", nargs="*", help="무작위 표본 대신 이 질문들을 판정한다")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = build.read_docs(args.docs)
    rows = build.read_jsonl(args.questions)
    client = pool.ClaudeClient("opus")

    sample = [r for r in rows if r["qid"] in args.qids] if args.qids else random.Random(args.seed).sample(rows, args.sample)
    answered = [r for r in sample if r["type"] != "noevidence"]
    absent = [r for r in rows if r["type"] == "noevidence"]
    near = nearest_chunks(absent, docs, args.near_per_method)
    support_jobs = [(r, SUPPORT_TEMPLATE.format(question=r["question"], answer=r["answer"], spans=span_block(docs, evidence_spans(r)))) for r in answered]
    absence_jobs = [(r, ABSENCE_TEMPLATE.format(question=r["question"], spans=span_block(docs, near[r["qid"]]))) for r in absent]
    name = "verify-" + ("listed" if args.qids else f"random{args.sample}-seed{args.seed}")
    pool.write_jsonl(out_dir / f"{name}.jsonl", ask_all(client, support_jobs, "gold-verify-support"))
    absence = ask_all(client, absence_jobs, "gold-verify-absence")
    pool.write_jsonl(out_dir / "verify-noevidence-all.jsonl", absence)
    print(f"{name}: 표본 {[r['qid'] for r in sample]}")
    for path in (out_dir / f"{name}.jsonl", out_dir / "verify-noevidence-all.jsonl"):
        for record in build.read_jsonl(path):
            parsed = record.get("parsed", {})
            flag = parsed.get("support", parsed.get("answered", record.get("error", record.get("parse_error"))))
            print(f"  {record['qid']} ({record['type']}): {flag} {parsed.get('fits_question', '')} {parsed.get('unsupported_claims', parsed.get('answering_excerpts', ''))}")
    print(client.usage_line())


if __name__ == "__main__":
    main()
