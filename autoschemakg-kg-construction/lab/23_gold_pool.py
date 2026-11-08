"""집계 질문의 정답 집합을 풀(pool)로 모으고 Opus 판정으로 넣고 뺀다.

후보는 세 방법의 합집합이다: 초안의 정규식(대소문자 무시, 문서 전체), bge-m3 dense 상위 N 청크(embed_client 기본 백엔드), BM25 상위 N 청크 (질의마다).
청크는 23_chunk_docs.py 의 고정 1000자 규칙이고, 후보 단위는 문서다. 초안의 씨앗 문서도 후보에 넣는다.
후보 문서마다 Opus 가 기준(criterion)을 보고 넣고 빼며 (정규식·씨앗 후보나 4000자 이하 문서는 본문 전체,
dense·BM25 로만 온 긴 문서는 걸린 청크 앞뒤 1000자를 보여 준다), 넣으면 instance 와 원문 인용을 낸다. entity 질문은 마지막에
Opus 가 문서별 instance 이름을 같은 대상끼리 묶는다. 프롬프트 틀·판정 원문·묶음 결과를 out_dir 에 남긴다.

    .venv-hr2/bin/python 23_gold_pool.py <drafts...> --docs <docs.jsonl...> --scopes <scopes.json> --out-dir <dir> [--stage pool|judge|final]
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
sys.path.insert(0, str(LAB))
import embed_client  # noqa: E402
from llm_cache import ClaudeClient, LLMCallFailed  # noqa: E402

CHUNK_SIZE = 1000
FULL_TEXT_LIMIT = 4000
EXCERPT_MARGIN = 1000
TOKEN = re.compile(r"[a-z0-9][a-z0-9_.:/\-]*[a-z0-9]|[a-z0-9]|[가-힣]+")

JUDGE_SYSTEM = "You are a meticulous annotator building a gold answer set for a retrieval benchmark. Reply with one JSON object only."
JUDGE_TEMPLATE = """집계 질문의 정답 집합을 만들고 있다. 아래 문서 하나가 이 질문의 instance 를 담고 있는지 판정한다.

질문: {question}
포함 기준(이 기준만 따른다): {criterion}
instance 단위: {instance_kind} ("doc" 이면 문서 하나가 instance 하나다. "entity" 면 문서 안의 이름 붙은 대상마다 instance 하나다.)

판정 규칙:
- 기준의 범위·포함·제외 조건을 글자 그대로 적용한다. 애매하면 넣지 않고 reason 에 이유를 적는다.
- 넣으면 instance 마다 근거 문장을 문서 본문에서 글자 그대로 복사한다(20~400자, 고치거나 줄이지 않는다). 그 문장만 읽어도 기준을 채운다는 것이 보여야 한다.
- label 은 짧은 이름(doc 이면 이 문서 사례의 요지, entity 면 대상 이름), value 는 기준이 묻는 값, group 은 질문이 "~별" 로 묶는 기준값(없으면 "").

답 형식(JSON 하나만):
{{"include": true 또는 false, "reason": "한두 문장", "instances": [{{"label": "...", "value": "...", "group": "...", "quote": "본문 그대로"}}]}}

<document doc_id="{doc_id}" source="{source}" kind="{kind}" date="{date}" lang="{lang}">
제목: {title}

{text}
</document>"""

MERGE_TEMPLATE = """집계 질문의 instance 후보를 문서마다 따로 뽑았다. 같은 대상을 가리키는 후보끼리 묶어 정규 이름을 붙인다.

질문: {question}
포함 기준: {criterion}

후보(번호: doc_id | label | value | group):
{candidates}

규칙: 이름·표기만 다르고 같은 대상이면 묶는다. 다른 대상은 묶지 않는다. 모든 번호가 정확히 한 묶음에 들어가야 한다.
답 형식(JSON 하나만): {{"groups": [{{"label": "정규 이름", "value": "대표 값", "group": "~별 기준값 또는 빈 문자열", "members": [번호, ...]}}]}}"""


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("gold_build", LAB / "23_gold_build.py")
chunking = load("chunk_docs", LAB / "23_chunk_docs.py")


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def chunks_of(docs):
    return [{"doc_id": d, "start": s, "end": e, "text": doc["text"][s:e]}
            for d, doc in docs.items() for s, e in chunking.fixed_spans(doc["text"], CHUNK_SIZE)]


def embed(texts):
    matrix = np.asarray(embed_client.embed(list(texts)), dtype=np.float32)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def tokens(text):
    words = TOKEN.findall(text.lower())
    return words + [w[i:i + 2] for w in words if re.match(r"[가-힣]", w) for i in range(len(w) - 1)]


class BM25:
    def __init__(self, texts, k1=1.2, b=0.75):
        self.docs = [Counter(tokens(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.docs]
        self.average = sum(self.lengths) / len(self.lengths)
        frequency = Counter(w for c in self.docs for w in c)
        self.idf = {w: math.log(1 + (len(self.docs) - n + 0.5) / (n + 0.5)) for w, n in frequency.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        terms = set(tokens(query))
        out = np.zeros(len(self.docs))
        for i, (counts, length) in enumerate(zip(self.docs, self.lengths)):
            norm = self.k1 * (1 - self.b + self.b * length / self.average)
            out[i] = sum(self.idf[w] * counts[w] * (self.k1 + 1) / (counts[w] + norm) for w in terms if w in counts)
        return out


def in_scope(doc, scope):
    prefixes = scope.get("prefixes")
    if prefixes and not any(doc["doc_id"].startswith(p) for p in prefixes):
        return False
    return not scope.get("lang") or doc["lang"] == scope["lang"]


def build_pools(drafts, docs, scopes, top, use_dense=True):
    chunks = chunks_of(docs)
    if use_dense:
        print(f"청크 {len(chunks)}개 임베딩 (embed_client, 백엔드 {embed_client.backend_of().name})", flush=True)
        matrix = embed([c["text"] for c in chunks])
    bm25 = BM25([c["text"] for c in chunks])
    pools = {}
    for draft in drafts:
        scope = scopes[draft["draft_id"]]
        allowed = np.array([in_scope(docs[c["doc_id"]], scope) for c in chunks])
        methods, hit_chunks = defaultdict(set), defaultdict(set)
        for pattern in draft["patterns"]:
            compiled = re.compile(pattern, re.I)
            for doc_id, doc in docs.items():
                if in_scope(doc, scope) and compiled.search(doc["title"] + "\n" + doc["text"]):
                    methods[doc_id].add("regex")
        query_vectors = embed(draft["queries"]) if use_dense else [None] * len(draft["queries"])
        for query, vector in zip(draft["queries"], query_vectors):
            for name, score in ((("dense", matrix @ vector),) if use_dense else ()) + (("bm25", bm25.scores(query)),):
                score = np.where(allowed, score, -np.inf)
                for i in np.argsort(-score)[:top]:
                    if np.isfinite(score[i]):
                        methods[chunks[i]["doc_id"]].add(name)
                        hit_chunks[chunks[i]["doc_id"]].add((chunks[i]["start"], chunks[i]["end"]))
        for group in draft.get("evidence", []):
            for quote in group["quotes"]:
                methods[quote["doc_id"]].add("seed")
        pools[draft["draft_id"]] = {d: {"methods": sorted(m), "chunks": sorted(hit_chunks[d])} for d, m in sorted(methods.items())}
        print(f"  {draft['draft_id']}: 후보 문서 {len(pools[draft['draft_id']])} · "
              + " · ".join(f"{k} {sum(k in m for m in methods.values())}" for k in ("regex", "dense", "bm25", "seed")), flush=True)
    return pools


def parse_json(text):
    start = text.find("{")
    if start < 0:
        raise ValueError("JSON 없음")
    return json.JSONDecoder().raw_decode(text[start:])[0]


def judged_text(doc, candidate):
    if {"regex", "seed"} & set(candidate["methods"]) or len(doc["text"]) <= FULL_TEXT_LIMIT:
        return doc["text"]
    windows = sorted((max(0, s - EXCERPT_MARGIN), min(len(doc["text"]), e + EXCERPT_MARGIN)) for s, e in candidate["chunks"])
    merged = []
    for start, end in windows:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return "\n[...]\n".join(doc["text"][s:e] for s, e in merged)


def judge_prompt(draft, doc, candidate):
    return JUDGE_TEMPLATE.format(question=draft["question"], criterion=draft["criterion"], instance_kind=draft.get("instance_kind", "doc"),
                                 doc_id=doc["doc_id"], source=doc["source"], kind=doc["kind"], date=doc["date"][:10], lang=doc["lang"],
                                 title=doc["title"], text=judged_text(doc, candidate))


def judge(drafts, docs, pools, out_dir, client):
    jobs = [(draft, doc_id) for draft in drafts for doc_id in pools[draft["draft_id"]]]
    print(f"판정 {len(jobs)}건 (Opus)", flush=True)
    prompts = [judge_prompt(d, docs[doc_id], pools[d["draft_id"]][doc_id]) for d, doc_id in jobs]
    replies = client.ask_many(prompts, system=JUDGE_SYSTEM, tag="gold-agg-judge")
    by_draft = defaultdict(list)
    for (draft, doc_id), prompt, reply in zip(jobs, prompts, replies):
        candidate = pools[draft["draft_id"]][doc_id]
        row = {"draft_id": draft["draft_id"], "doc_id": doc_id, "methods": candidate["methods"],
               "shown": "full" if judged_text(docs[doc_id], candidate) == docs[doc_id]["text"] else "excerpt",
               "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}
        if isinstance(reply, LLMCallFailed):
            row.update(error=str(reply))
        else:
            row["reply"] = reply.text
            try:
                row["parsed"] = parse_json(reply.text)
            except (ValueError, json.JSONDecodeError) as error:
                row["parse_error"] = str(error)
        by_draft[draft["draft_id"]].append(row)
    for draft_id, rows in by_draft.items():
        write_jsonl(out_dir / f"{draft_id}.judgments.jsonl", rows)
    return by_draft


def located_instances(rows, docs):
    found, lost = [], []
    for row in rows:
        parsed = row.get("parsed") or {}
        if not parsed.get("include"):
            continue
        for instance in parsed.get("instances", []):
            span = build.locate(docs, row["doc_id"], instance.get("quote", ""))
            item = {"doc_id": row["doc_id"], "label": instance.get("label", ""), "value": instance.get("value", ""),
                    "group": instance.get("group", ""), "quote": instance.get("quote", ""), "methods": row["methods"]}
            (found if span else lost).append(item)
    return found, lost


def merge_entities(draft, items, client, out_dir):
    listing = "\n".join(f"{i}: {it['doc_id']} | {it['label']} | {it['value']} | {it['group']}" for i, it in enumerate(items))
    prompt = MERGE_TEMPLATE.format(question=draft["question"], criterion=draft["criterion"], candidates=listing)
    reply = client.ask(prompt, system=JUDGE_SYSTEM, tag="gold-agg-merge")
    (out_dir / f"{draft['draft_id']}.merge.json").write_text(json.dumps({"prompt": prompt, "reply": reply.text}, ensure_ascii=False, indent=1))
    groups = parse_json(reply.text)["groups"]
    members = sorted(m for g in groups for m in g["members"])
    if members != list(range(len(items))):
        raise SystemExit(f"{draft['draft_id']} 묶음이 후보 번호를 정확히 한 번씩 덮지 않는다")
    return [{"label": g["label"], "value": g.get("value", ""), "group": g.get("group", ""),
             "quotes": [{"doc_id": items[m]["doc_id"], "quote": items[m]["quote"]} for m in g["members"]],
             "methods": sorted({x for m in g["members"] for x in items[m]["methods"]})} for g in groups]


def doc_instances(items):
    by_doc = defaultdict(list)
    for item in items:
        by_doc[item["doc_id"]].append(item)
    return [{"label": f"{doc_id}: {group[0]['label']}", "value": group[0]["value"], "group": group[0]["group"],
             "quotes": [{"doc_id": doc_id, "quote": it["quote"]} for it in group], "methods": group[0]["methods"]}
            for doc_id, group in sorted(by_doc.items())]


def answer_text(draft, instances):
    form = draft.get("answer_form", "list")
    if form == "grouped":
        groups = defaultdict(list)
        for instance in instances:
            groups[instance["group"] or "(묶음 없음)"].append(instance)
        body = " / ".join(f"{g} {len(items)}건: " + ", ".join(i["label"].split(": ", 1)[-1] + (f" ({i['value']})" if i["value"] else "") for i in items)
                          for g, items in sorted(groups.items(), key=lambda kv: -len(kv[1])))
        return f"{len(instances)}건, {len(groups)}묶음. {body}"
    listing = "; ".join(i["label"] + (f" — {i['value']}" if i["value"] else "") for i in instances)
    return f"{len(instances)}건. {listing}"


def apply_fixes(instances, fix):
    kept = [i for i in instances if i["label"] not in fix.get("drop", [])]
    return kept + [dict(i, methods=i.get("methods", ["manual"])) for i in fix.get("add", [])]


def finalize(drafts, docs, judged, out_dir, client, fixes):
    rows = []
    for draft in drafts:
        items, lost = located_instances(judged[draft["draft_id"]], docs)
        instances = merge_entities(draft, items, client, out_dir) if draft.get("instance_kind") == "entity" and items else doc_instances(items)
        instances = apply_fixes(instances, fixes.get(draft["draft_id"], {}))
        judgments = judged[draft["draft_id"]]
        method_hits = Counter(m for i in instances for m in i["methods"])
        only = Counter(i["methods"][0] for i in instances if len([m for m in i["methods"] if m != "seed"]) == 1 and i["methods"][0] != "seed")
        rows.append({"draft_id": draft["draft_id"], "answer": answer_text(draft, instances), "instances": instances,
                     "pool": {"candidates": len(judgments), "included_docs": sum(bool((j.get("parsed") or {}).get("include")) for j in judgments),
                              "errors": sum("error" in j or "parse_error" in j for j in judgments), "lost_quotes": len(lost),
                              "manual_fix": fixes.get(draft["draft_id"], {}).get("reason"),
                              "instances_by_method": dict(method_hits), "instances_found_by_one_method": dict(only)}})
        print(f"  {draft['draft_id']}: 후보 {len(judgments)} → instance {len(instances)} (인용 못 찾음 {len(lost)}) · 방법별 {dict(method_hits)} · 한 방법만 {dict(only)}")
    write_jsonl(out_dir / "agg.jsonl", rows)


def main():
    parser = argparse.ArgumentParser(description="집계 질문 정답 집합을 풀 + Opus 판정으로 만든다.")
    parser.add_argument("drafts", nargs="+")
    parser.add_argument("--docs", nargs="+", required=True)
    parser.add_argument("--scopes", required=True, help="{draft_id: {prefixes?: [...], lang?: ko}} json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--stage", choices=("pool", "judge", "final"), default="final", help="이 단계까지 돈다")
    parser.add_argument("--only", nargs="*", help="이 draft_id 만")
    parser.add_argument("--fixes", help="{draft_id: {add: [instance], drop: [label], reason}} json. 판정 뒤 사람(정답 작성자)이 고친 것")
    parser.add_argument("--skip-dense", action="store_true", help="dense 없이 정규식·BM25·씨앗만으로 풀을 만든다 (pools-nodense.json)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = build.read_docs(args.docs)
    scopes = json.loads(Path(args.scopes).read_text())
    drafts = [d for p in args.drafts for d in build.read_jsonl(p) if d["type"] == "aggregation" and (not args.only or d["draft_id"] in args.only)]
    pools_path = out_dir / ("pools-nodense.json" if args.skip_dense else "pools.json")
    pools = json.loads(pools_path.read_text()) if pools_path.exists() else {}
    todo = [d for d in drafts if d["draft_id"] not in pools]
    for draft in todo:
        pools.update(build_pools([draft], docs, scopes, args.top, use_dense=not args.skip_dense))
        pools_path.write_text(json.dumps(pools, ensure_ascii=False, indent=1))
    if args.stage == "pool":
        return
    (out_dir / "judge-prompt-template.txt").write_text(f"[system]\n{JUDGE_SYSTEM}\n\n[user]\n{JUDGE_TEMPLATE}\n\n[merge]\n{MERGE_TEMPLATE}\n")
    client = ClaudeClient("opus")
    judged = judge(drafts, docs, pools, out_dir, client)
    print(client.usage_line())
    if args.stage == "judge":
        return
    finalize(drafts, docs, judged, out_dir, client, json.loads(Path(args.fixes).read_text()) if args.fixes else {})
    print(client.usage_line())


if __name__ == "__main__":
    main()
