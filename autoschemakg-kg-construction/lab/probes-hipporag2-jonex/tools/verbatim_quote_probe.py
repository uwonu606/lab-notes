import json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

import numpy as np

LAB = Path(sys.argv[1])
MODEL = sys.argv[2]
OUT = Path(sys.argv[3])
TOP_N = 5
PROMPT = """아래 자료만 보고 질문에 답하라.
JSON 하나로만 답한다: {{"answer": "짧은 답", "quotes": ["답의 근거가 되는 구간"]}}
quotes 의 각 구간은 자료 본문에서 글자 그대로 복사한 연속 구간이어야 한다. 고치거나 줄이거나 번역하지 마라. 자료에 답이 없으면 {{"answer": "자료에 없음", "quotes": []}}.

{context}

질문: {question}"""


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


def unload():
    body = json.dumps({"model": MODEL, "keep_alive": 0}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", data=body, headers={"Content-Type": "application/json"}), timeout=120).read()
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(3)


def chat(prompt):
    body = json.dumps({"model": MODEL, "stream": False, "format": "json",
                       "options": {"temperature": 0, "num_ctx": 8192},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    reply = {}
    for attempt in range(6):
        try:
            req = urllib.request.Request("http://localhost:11434/api/chat", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                reply = json.load(resp)
        except (urllib.error.URLError, TimeoutError) as error:
            reply = {"error": str(error)}
        if reply.get("message", {}).get("content", "").strip():
            reply["attempts"] = attempt + 1
            return reply
        unload()
    reply["attempts"] = 6
    return reply


chunks = [json.loads(line) for line in (LAB / "inputs/12-chunks.jsonl").read_text().splitlines()]
by_id = {c["id"]: c for c in chunks}
questions = json.loads((LAB / "inputs/12-questions.json").read_text())
evidence = json.loads((LAB / "inputs/14-evidence.json").read_text())["questions"]
vectors = json.loads((LAB / "runs/12-cache/embeddings.json").read_text())


def unit_matrix(texts):
    m = np.array([vectors[t] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


chunk_vectors = unit_matrix([c["text"] for c in chunks])
question_vectors = unit_matrix([q["question"] for q in questions])

records, started = [], time.time()
for q, qv in zip(questions, question_vectors):
    top = [chunks[i] for i in np.argsort(-(chunk_vectors @ qv))[:TOP_N]]
    context = "\n\n".join(f"[자료 {k + 1}]\n{c['text']}" for k, c in enumerate(top))
    reply = chat(PROMPT.format(context=context, question=q["question"]))
    raw = reply["message"]["content"]
    try:
        parsed = json.loads(raw)
        quotes = [s for s in parsed.get("quotes", []) if isinstance(s, str) and s.strip()]
        answer = str(parsed.get("answer", ""))
        parse_ok = True
    except (json.JSONDecodeError, AttributeError):
        quotes, answer, parse_ok = [], "", False
    verbatim = [any(squash(s) in squash(c["text"]) for c in top) for s in quotes]
    gold_excerpts = [squash(x) for cid, xs in evidence.get(q["id"], {}).items() for x in xs]
    hits_gold = [ok and any(squash(s) in g or g in squash(s) or (len(set(squash(s).split()) & set(g.split())) >= 0.5 * len(set(g.split()))) for g in gold_excerpts)
                 for s, ok in zip(quotes, verbatim)]
    retrieved_gold = [g for g in q["gold"] if g in {c["id"] for c in top}]
    records.append({"id": q["id"], "type": q["type"], "parse_ok": parse_ok, "raw": raw[:600], "done_reason": reply.get("done_reason"), "attempts": reply.get("attempts"), "answer": answer, "gold_answer": q["answer"],
                    "quotes": quotes, "verbatim": verbatim, "hits_gold_evidence": hits_gold,
                    "retrieved_gold": retrieved_gold, "eval_count": reply.get("eval_count"), "prompt_eval_count": reply.get("prompt_eval_count")})

n = len(records)
all_quotes = [v for r in records for v in r["verbatim"]]
lines = [f"model {MODEL} · questions {n} · dense top-{TOP_N} context · {time.time() - started:.0f}s · calls {n}",
         f"JSON parsed {sum(r['parse_ok'] for r in records)}/{n}",
         f"answers with >=1 quote {sum(bool(r['quotes']) for r in records)}/{n}",
         f"quotes verbatim (whitespace-normalised substring of a retrieved chunk) {sum(all_quotes)}/{len(all_quotes)}",
         f"answers whose quotes are all verbatim and non-empty {sum(bool(r['quotes']) and all(r['verbatim']) for r in records)}/{n}",
         f"answers with >=1 verbatim quote overlapping gold evidence (14-evidence.json) {sum(any(r['hits_gold_evidence']) for r in records)}/{n}",
         f"  of which questions where dense top-5 held >=1 gold chunk: {sum(bool(r['retrieved_gold']) for r in records)}/{n}",
         f"empty replies after 4 attempts {sum(not r['raw'] for r in records)}/{n} · calls with retries {sum((r['attempts'] or 1) > 1 for r in records)}",
         f"max prompt_eval_count {max((r['prompt_eval_count'] or 0) for r in records)} (num_ctx 8192)"]
OUT.write_text("\n".join(lines) + "\n")
(OUT.with_suffix(".jsonl")).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")
print("\n".join(lines))
