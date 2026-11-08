import json
from pathlib import Path

LAB = Path(__file__).parent
CORPUS_DIR = LAB / "inputs/14-corpus"
OLD_CHUNKS = LAB / "inputs/12-chunks.jsonl"
SPANS = LAB / "runs/21-chunks-fixed1000.jsonl"
QUESTIONS = LAB / "inputs/12-questions.json"
EVIDENCE = LAB / "inputs/14-evidence.json"
OUT = LAB / "runs/23-57"


def jsonl(rows):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def main():
    old = [json.loads(line) for line in OLD_CHUNKS.read_text().splitlines()]
    spans = [json.loads(line) for line in SPANS.read_text().splitlines()]
    docs = {slug: (CORPUS_DIR / f"{slug}.md").read_text() for slug in dict.fromkeys(s["doc"] for s in spans)}
    chunks = []
    for chunk, span in zip(old, spans, strict=True):
        assert docs[span["doc"]][span["start"]:span["end"]] == chunk["text"], chunk["id"]
        chunks.append({"id": chunk["id"], "doc_id": span["doc"], "start": span["start"], "end": span["end"], "text": chunk["text"]})
    by_id = {c["id"]: c for c in chunks}

    evidence = json.loads(EVIDENCE.read_text())["questions"]
    gold = []
    for q in json.loads(QUESTIONS.read_text()):
        items = []
        for chunk_id, excerpts in evidence[q["id"]].items():
            c = by_id[chunk_id]
            found = [(c["text"].find(e), len(e)) for e in excerpts]
            assert all(at >= 0 for at, _ in found), (q["id"], chunk_id)
            items.append({"label": chunk_id, "spans": [{"doc_id": c["doc_id"], "start": c["start"] + at, "end": c["start"] + at + n} for at, n in found]})
        gold.append({"qid": q["id"], "type": q["type"], "question": q["question"], "evidence": items})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "docs.jsonl").write_text(jsonl({"doc_id": slug, "text": text} for slug, text in docs.items()))
    (OUT / "chunks.jsonl").write_text(jsonl(chunks))
    (OUT / "gold.jsonl").write_text(jsonl(gold))
    print(f"{OUT}: 문서 {len(docs)} · 청크 {len(chunks)} · 질문 {len(gold)} · 근거 묶음 {sum(len(g['evidence']) for g in gold)}")


if __name__ == "__main__":
    main()
