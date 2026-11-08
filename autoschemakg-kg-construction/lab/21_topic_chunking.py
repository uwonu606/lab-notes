import json
import re
import sys
import time
import urllib.error
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
CORPUS_DIR = LAB / "inputs/14-corpus"
DOCS = ["commit-pr-workflow", "doc-parsing-chunking", "concept-extraction-papers"]
EVIDENCE = LAB / "inputs/14-evidence.json"
CACHE = LAB / "runs/21-cache"
DEFAULT_MODEL = "exaone3.5:2.4b"
BASELINE_SIZE = 1000
MAX_UNIT_CHARS = 600
GROUP_CHARS = 2000
COVER_SHARE = 0.5
TOP_N = 5
CHAR_BUDGETS = (1000, 2500, 5000)
STRUCTURE_BUDGET = 5000
SHIFT_PROMPT = """You will receive as input a document with paragraphs identified by 'ID XXXX: <text>'.

Task: Find the first paragraph (not the first one) where the content clearly changes compared to the previous paragraphs.

Output: Return the ID of the paragraph with the content shift.

Additional Considerations: Avoid very long groups of paragraphs. Aim for a good balance between identifying content shifts and keeping groups manageable.

Answer in the format 'Answer: ID XXXX'.

Document:
"""


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sg = load("schema_glossary", LAB / "13_schema_glossary.py")
kgd = sg.kgd
grep = load("glossary_grep", LAB / "17_glossary_grep.py")


def read_doc(slug):
    return (CORPUS_DIR / f"{slug}.md").read_text()


def span_chunk(slug, number, text, start, end, method):
    return {"id": f"{slug}#{number:03d}", "doc": slug, "start": start, "end": end, "text": text[start:end], "method": method}


def fixed_chunks(slug, text, size):
    spans, first, last, length, position = [], None, None, 0, 0
    for word in text.split(" "):
        if length + len(word) + 1 > size and first is not None:
            spans.append((first, last))
            first, length = None, 0
        if first is None:
            first = position
        last = position + len(word)
        length += len(word) + 1
        position += len(word) + 1
    if first is not None:
        spans.append((first, last))
    return [span_chunk(slug, i, text, s, e, f"fixed{size}") for i, (s, e) in enumerate(spans)]


def stripped(text, start, end):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def split_at(text, start, end, pattern):
    pieces, cursor = [], start
    for match in re.finditer(pattern, text[start:end]):
        cut = start + match.end()
        pieces.append((cursor, cut))
        cursor = cut
    pieces.append((cursor, end))
    return [p for p in (stripped(text, s, e) for s, e in pieces) if p]


def packed(pieces, limit):
    merged = []
    for start, end in pieces:
        if merged and end - merged[-1][0] <= limit:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def shrink(text, span):
    start, end = span
    if end - start <= MAX_UNIT_CHARS:
        return [span]
    for pattern in (r"\n", r"(?<=[.?!다])\s+", r" "):
        pieces = packed(split_at(text, start, end, pattern), MAX_UNIT_CHARS)
        if len(pieces) > 1:
            return [unit for piece in pieces for unit in shrink(text, piece)]
    return [span]


def paragraph_units(text):
    paragraphs = split_at(text, 0, len(text), r"\n[ \t]*\n\s*")
    return [unit for paragraph in paragraphs for unit in shrink(text, paragraph)]


def heading_chunks(slug, text):
    starts = sorted({0, *(m.start() for m in re.finditer(r"(?m)^#{1,6} ", text))})
    spans = [stripped(text, s, e) for s, e in zip(starts, [*starts[1:], len(text)])]
    return [span_chunk(slug, i, text, s, e, "heading") for i, (s, e) in enumerate(p for p in spans if p)]


def ask_shift(model, units, text, first, last):
    listing = "\n".join(f"ID {i:04d}: {text[units[i][0]:units[i][1]]}" for i in range(first, last + 1))
    body = {"model": model, "stream": False,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "user", "content": SHIFT_PROMPT + listing}]}
    for attempt in range(1, 4):
        started = time.monotonic()
        try:
            response = kgd.distractor.post("/api/chat", body)
            answer = int(re.search(r"ID\s*(\d+)", response["message"]["content"]).group(1))
        except (urllib.error.HTTPError, AttributeError) as error:
            print(f"  {model} 답을 못 읽음 ({error!r:.60}) — 모델을 내렸다 올려 다시 묻는다 ({attempt}/3)", flush=True)
            kgd.single_post("/api/generate", {"model": model, "keep_alive": 0})
            continue
        usage = {"prompt_tokens": response.get("prompt_eval_count", 0), "completion_tokens": response.get("eval_count", 0),
                 "seconds": round(time.monotonic() - started, 2)}
        return answer, usage
    return None, {"prompt_tokens": 0, "completion_tokens": 0, "seconds": 0}


def lumber_boundaries(model, units, text):
    starts, calls, start = [], [], 0
    while start < len(units):
        last, size = start, units[start][1] - units[start][0]
        while last + 1 < len(units) and size <= GROUP_CHARS:
            last += 1
            size = units[last][1] - units[start][0]
        if last == start:
            starts.append(start)
            start += 1
            continue
        answer, usage = ask_shift(model, units, text, start, last)
        accepted = answer if isinstance(answer, int) and start < answer <= last else None
        calls.append({"first": start, "last": last, "answer": answer, "accepted": accepted, **usage})
        starts.append(start)
        start = accepted if accepted is not None else last + 1
    return starts, calls


def lumber_cache(model, slug):
    return CACHE / f"lumber-{model.replace(':', '_')}-{slug}.json"


def segment(model=DEFAULT_MODEL):
    CACHE.mkdir(parents=True, exist_ok=True)
    for slug in DOCS:
        path = lumber_cache(model, slug)
        if path.exists():
            continue
        text = read_doc(slug)
        units = paragraph_units(text)
        started = time.monotonic()
        starts, calls = lumber_boundaries(model, units, text)
        path.write_text(json.dumps({"model": model, "units": units, "starts": starts, "calls": calls}, ensure_ascii=False))
        rejected = sum(1 for c in calls if c["accepted"] is None)
        print(f"{slug}: 단위 {len(units)} → 조각 {len(starts)} · 호출 {len(calls)} (경계로 못 쓴 답 {rejected}) · {time.monotonic() - started:.0f}초", flush=True)
        kgd.single_post("/api/generate", {"model": model, "keep_alive": 0})


def lumber_chunks(model, slug, text):
    cached = json.loads(lumber_cache(model, slug).read_text())
    units, starts = cached["units"], cached["starts"]
    ends = [*starts[1:], len(units)]
    return [span_chunk(slug, i, text, units[s][0], units[e - 1][1], f"lumber:{model}") for i, (s, e) in enumerate(zip(starts, ends))]


def all_chunks(method):
    chunks = []
    for slug in DOCS:
        text = read_doc(slug)
        if method.startswith("fixed"):
            chunks += fixed_chunks(slug, text, int(method[len("fixed"):]))
        elif method == "heading":
            chunks += heading_chunks(slug, text)
        else:
            chunks += lumber_chunks(method.split(":", 1)[1], slug, text)
    return chunks


def check_baseline():
    old = kgd.read_chunks()
    new = all_chunks(f"fixed{BASELINE_SIZE}")
    assert [c["text"] for c in old] == [c["text"] for c in new], "고정 1000자 조각이 12-chunks.jsonl 과 다르다"


def gold_units(section):
    old = {c["id"]: c for c in kgd.read_chunks()}
    offsets, position = {}, {}
    for c in kgd.read_chunks():
        slug = c["id"].split("#")[0]
        offsets[c["id"]] = position.get(slug, 0)
        position[slug] = offsets[c["id"]] + len(c["text"]) + 1
    evidence = json.loads(EVIDENCE.read_text())[section]
    units, dropped = {}, []
    for key, per_chunk in evidence.items():
        units[key] = []
        for chunk_id, excerpts in per_chunk.items():
            spans = []
            for excerpt in excerpts:
                at = old[chunk_id]["text"].find(excerpt)
                spans.append((offsets[chunk_id] + at, offsets[chunk_id] + at + len(excerpt)))
            if spans:
                units[key].append({"chunk": chunk_id, "doc": chunk_id.split("#")[0], "spans": spans})
            else:
                dropped.append((key, chunk_id))
    return units, dropped


def covers(doc, start, end, unit):
    return doc == unit["doc"] and any(min(end, e) - max(start, s) >= COVER_SHARE * (e - s) for s, e in unit["spans"])


def within_budget(ranked, budget):
    pieces, left = [], budget
    for c in ranked:
        if left <= 0:
            break
        pieces.append((c["doc"], c["start"], min(c["end"], c["start"] + left)))
        left -= c["end"] - c["start"]
    return pieces


def recall_of(pieces, units):
    hit = [any(covers(*p, u) for p in pieces) for u in units]
    return sum(hit) / len(units), all(hit)


def ranked_for(query, chunks, vectors, encoder):
    return [chunks[i] for i in np.argsort(-(vectors @ encoder.encode([query])[0]))]


def describe(chunks):
    sizes = [c["end"] - c["start"] for c in chunks]
    return f"조각 {len(chunks)}개 · 글자 수 최소 {min(sizes)} / 중앙 {int(np.median(sizes))} / 평균 {int(np.mean(sizes))} / 최대 {max(sizes)}"


def qa_scores(chunks, vectors, encoder, questions, units):
    rows = []
    for q in questions:
        if not units.get(q["id"]):
            continue
        ranked = ranked_for(q["question"], chunks, vectors, encoder)
        row = {"id": q["id"], "type": q["type"], "top": [c["id"] for c in ranked[:TOP_N]]}
        row["at5"] = recall_of([(c["doc"], c["start"], c["end"]) for c in ranked[:TOP_N]], units[q["id"]])
        for budget in CHAR_BUDGETS:
            row[budget] = recall_of(within_budget(ranked, budget), units[q["id"]])
        rows.append(row)
    return rows


def structure_scores(chunks, vectors, encoder, units):
    entries, canonical_of = sg.read_glossary()
    by_canonical = {e["canonical"]: e for e in entries}
    rows = []
    for t in json.loads(sg.STRUCTURE.read_text()):
        name = sg.short_name(t["target"])
        canonical = canonical_of.get(sg.surface_key(name))
        forms = grep.forms_of(by_canonical[canonical]) if canonical else [name]
        threads = [c for c in chunks if any(f.casefold() in c["text"].casefold() for f in forms)]
        embedded = within_budget(ranked_for(t["question"], chunks, vectors, encoder), STRUCTURE_BUDGET)
        thread_pieces = [(c["doc"], c["start"], c["end"]) for c in threads]
        kinds = {"실": thread_pieces, "임베딩": embedded, "실+임베딩": thread_pieces + [p for p in embedded if p not in thread_pieces]}
        row = {"id": t["id"]}
        for kind, pieces in kinds.items():
            relevant = [p for p in pieces if any(covers(*p, u) for u in units[t["id"]])]
            recall, _ = recall_of(pieces, units[t["id"]])
            row[kind] = (len(relevant) / len(pieces) if pieces else 0.0, recall, sum(e - s for _, s, e in pieces))
        rows.append(row)
    return rows


def segmented_models():
    names = [json.loads(p.read_text())["model"] for p in CACHE.glob(f"lumber-*-{DOCS[0]}.json")]
    return sorted(m for m in names if all(lumber_cache(m, slug).exists() for slug in DOCS))


def evaluate(*methods):
    check_baseline()
    if not methods:
        lumber_methods = [f"lumber:{m}" for m in segmented_models()]
        matched = [f"fixed{int(np.mean([c['end'] - c['start'] for c in all_chunks(m)]))}" for m in lumber_methods]
        methods = (f"fixed{BASELINE_SIZE}", *lumber_methods, *matched, "heading")
    models = [m.split(":", 1)[1] for m in methods if m.startswith("lumber:")]
    questions = json.loads(kgd.QUESTIONS.read_text())
    qa_units, qa_dropped = gold_units("questions")
    st_units, st_dropped = gold_units("structure")
    encoder = kgd.distractor.OllamaEncoder(kgd.CACHE / "embeddings.json")
    print(f"=== 근거 구간: 질문 {len(qa_units)}개 · 구조 대상 {len(st_units)}개 · 근거 없어 뺀 정답 조각 {len(qa_dropped) + len(st_dropped)}개 {qa_dropped + st_dropped}")
    print(f"=== 맞힘 규칙: 가져온 조각이 근거 구간 하나의 {int(COVER_SHARE * 100)}% 이상을 덮으면 그 정답 조각을 찾은 것으로 친다")
    for slug in DOCS:
        for model in models:
            calls = json.loads(lumber_cache(model, slug).read_text())["calls"]
            print(f"    {model} {slug}: 호출 {len(calls)} · 입력 토큰 {sum(c['prompt_tokens'] for c in calls):,} · {sum(c['seconds'] for c in calls):.0f}초 · 경계로 못 쓴 답 {sum(1 for c in calls if c['accepted'] is None)}")
    results = {}
    for method in methods:
        chunks = all_chunks(method)
        vectors = encoder.encode([c["text"] for c in chunks])
        results[method] = (describe(chunks), qa_scores(chunks, vectors, encoder, questions, qa_units), structure_scores(chunks, vectors, encoder, st_units))
        (LAB / f"runs/21-chunks-{method.replace(':', '_')}.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n")

    print("\n=== 조각 모양")
    for method, (shape, _, _) in results.items():
        print(f"  {method:28} {shape}")
    print(f"\n=== 질문 {len(questions)}개 재현율 — 상위 {TOP_N}개 / 글자 예산 {' · '.join(map(str, CHAR_BUDGETS))}자 (괄호: 정답 조각을 다 찾은 질문 수)")
    for method, (_, qa, _) in results.items():
        cells = [f"@{TOP_N} {np.mean([r['at5'][0] for r in qa]):.3f} ({sum(r['at5'][1] for r in qa)})"]
        cells += [f"{b}자 {np.mean([r[b][0] for r in qa]):.3f} ({sum(r[b][1] for r in qa)})" for b in CHAR_BUDGETS]
        split = " · ".join(f"{kind} @{TOP_N} {np.mean([r['at5'][0] for r in qa if r['type'] == kind]):.3f}" for kind in ("single", "bridge"))
        print(f"  {method:28} {'  '.join(cells)}   [{split}]")
    print(f"\n=== 구조 질문 10개 — 정밀도 / 재현율 / 가져온 글자 수 (임베딩은 글자 예산 {STRUCTURE_BUDGET}자)")
    for method, (_, _, st) in results.items():
        cells = "  ".join(f"{kind} {np.mean([r[kind][0] for r in st]):.2f} / {np.mean([r[kind][1] for r in st]):.2f} / {int(np.mean([r[kind][2] for r in st]))}" for kind in ("실", "임베딩", "실+임베딩"))
        print(f"  {method:28} {cells}")
    (LAB / "runs/21-eval.jsonl").write_text("\n".join(json.dumps({"method": m, "qa": qa, "structure": st}, ensure_ascii=False, default=str) for m, (_, qa, st) in results.items()) + "\n")


def show(model=DEFAULT_MODEL, slug="doc-parsing-chunking"):
    for c in lumber_chunks(model, slug, read_doc(slug)):
        head = c["text"][:70].replace("\n", " ⏎ ")
        print(f"{c['id']}  {c['end'] - c['start']:5}자  {head}")


if __name__ == "__main__":
    {"segment": segment, "evaluate": evaluate, "show": show}[sys.argv[1]](*sys.argv[2:])
