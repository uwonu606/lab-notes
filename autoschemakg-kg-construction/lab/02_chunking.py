import re
import sys
from pathlib import Path


def split_text(text, chunk_size, chunk_overlap):
    words = text.split(' ')
    chunks, current_chunk, current_length = [], [], 0
    for word in words:
        word_len = len(word) + 1
        if current_length + word_len > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                overlap_len, new_start_index = 0, len(current_chunk)
                while new_start_index > 0 and overlap_len < chunk_overlap:
                    new_start_index -= 1
                    overlap_len += len(current_chunk[new_start_index]) + 1
                current_chunk = current_chunk[new_start_index:]
                current_length = overlap_len
        current_chunk.append(word)
        current_length += word_len
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def headings_before(text, offset):
    return [line for line in text[:offset].splitlines() if re.match(r"#{1,6} ", line)]


def main(path, chunk_size="8192", chunk_overlap="0"):
    text = Path(path).read_text()
    chunks = split_text(text, int(chunk_size), int(chunk_overlap))
    print(f"문서 {len(text)}자 → 청크 {len(chunks)}개 (chunk_size={chunk_size}자, overlap={chunk_overlap}자)")
    cursor = 0
    for index, chunk in enumerate(chunks):
        start = text.find(chunk[:200], max(0, cursor - int(chunk_overlap) - 1))
        cursor = start + len(chunk)
        inside = [line for line in chunk.splitlines() if re.match(r"#{1,6} ", line)]
        print(f"\n=== 청크 {index}: 원문 {start}~{cursor}자, 줄바꿈 {chunk.count(chr(10))}개 남음")
        print(f"  청크 안의 제목: {inside or '없음'}")
        print(f"  청크 앞에서 끝난 제목 경로(LLM 은 못 본다): {headings_before(text, start)[-3:] or '없음'}")
        print("  첫 3줄:")
        for line in chunk.splitlines()[:3]:
            print(f"    | {line[:100]}")
        print("  끝 2줄:")
        for line in chunk.splitlines()[-2:]:
            print(f"    | {line[:100]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
