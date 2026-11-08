import argparse
import json
from pathlib import Path


def fixed_spans(text, size):
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
    return spans


def main():
    parser = argparse.ArgumentParser(description="docs.jsonl 을 회차 21 의 고정 길이 규칙(공백 경계, size 자 이하)으로 잘라 {id, doc_id, start, end, text} 청크로 낸다.")
    parser.add_argument("docs", help="한 줄에 {doc_id, text} 하나인 jsonl")
    parser.add_argument("out")
    parser.add_argument("--size", type=int, default=1000)
    args = parser.parse_args()

    rows = []
    for doc in (json.loads(line) for line in Path(args.docs).read_text().splitlines() if line.strip()):
        for number, (start, end) in enumerate(fixed_spans(doc["text"], args.size)):
            rows.append({"id": f"{doc['doc_id']}#{number:03d}", "doc_id": doc["doc_id"], "start": start, "end": end, "text": doc["text"][start:end]})
    Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"{args.out}: 청크 {len(rows)}개")


if __name__ == "__main__":
    main()
