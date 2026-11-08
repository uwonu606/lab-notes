"""깔끔한 마크다운 말뭉치를 docx·PDF 변환기 출력처럼 망가뜨린다. 절 정답과 질문 근거 구간을 새 문자 위치로 옮긴다.

    .venv-25/bin/python 25_degrade.py --level L1 --level L2 --level L3

수준은 앞 수준을 모두 담는다.
  L1  제목 스타일 없이 쓴 docx 를 변환한 꼴. # 표시와 ** 가 사라져 제목이 평범한 한 줄이 된다. 표·목록·코드 울타리는 남는다.
  L2  L1 + PDF 텍스트 추출 꼴. 표는 공백 구분 줄로 평탄화(구분 줄 삭제), 코드 울타리와 백틱 삭제, 목록 기호는 항목마다
      LIST_DROP 확률로 사라지고 나머지는 • 로 바뀜, 문서마다 폭 WRAP_WIDTH 안에서 하드 줄바꿈, 빈 줄을 BLANK_DROP 확률로 잃음,
      쪽 끝마다 꼬리말("- 3 -" 등)과 다음 쪽 머리말(문서 번호, 기밀 표시)이 끼어듦.
  L3  L2 + 본문 절 제목의 GLUE 비율이 다음 문단 첫머리에 붙고("4. 원인 분석 절체 시 …"), 번호 붙은 제목의 RENUMBER 비율이
      번호 형식을 잃음("4 원인", "4.원인", "(4) 원인", "4) 원인", "Ⅳ." → "IV.").

결정적이다: 문서·단계마다 random.Random(f"{doc_id}:{단계}") 를 쓴다.
위치 추적: 줄마다 글자별 원래 위치(새로 넣은 글자는 None)를 들고 다닌다. 근거 구간은 그 안에서 살아남은 첫 글자부터 마지막 글자까지로 옮긴다.
지운 글자 가운데 마크업(공백, # * | ` -) 이 아닌 것이 구간 안에 있거나 살아남은 글자가 없으면 옮기지 못한 근거로 버리고 센다.
절 시작은 제목 줄의 살아남은 첫 글자가 놓인 새 줄의 시작이다.
"""
import argparse
import json
import random
import re
import zlib
from dataclasses import dataclass
from pathlib import Path

LAB = Path(__file__).parent
SOURCE = LAB / "inputs/parser-corpus"
SOURCE_GOLD = LAB / "runs/25-split/gold.jsonl"
OUT = LAB / "inputs/parser-corpus-messy"

LIST_DROP = 0.45
WRAP_WIDTH = (60, 90)
BLANK_DROP = 0.3
PAGE_LINES = (38, 50)
GLUE = 0.35
RENUMBER = 0.4
MARKUP = set(" \t\n#*|`-")
FOOTERS = ["- {k} -", "{k} / {n}", "Page {k} of {n}", "— {k} —"]
CONFIDENTIAL = ["대외비", "사내 한정 (Internal Use Only)", "CONFIDENTIAL", "", "Company Confidential"]
DOC_NUMBER = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+){2,}\b")
NUMBERED = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.\s*")
ROMAN = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V", "Ⅵ": "VI", "Ⅶ": "VII", "Ⅷ": "VIII", "Ⅸ": "IX", "Ⅹ": "X"}


@dataclass
class Line:
    text: str
    origin: list
    newline: object
    kind: str = "text"
    heading: bool = False
    title: bool = False

    def delete(self, start, end):
        self.text = self.text[:start] + self.text[end:]
        self.origin = self.origin[:start] + self.origin[end:]

    def replace(self, start, end, new):
        kept = self.origin[start:end] if len(new) == end - start else [None] * len(new)
        self.text = self.text[:start] + new + self.text[end:]
        self.origin = self.origin[:start] + kept + self.origin[end:]

    def delete_all(self, pattern):
        for match in reversed(list(re.finditer(pattern, self.text))):
            self.delete(*match.span())


def inserted(text, kind="noise"):
    return Line(text, [None] * len(text), None, kind)


def normalize_line(line):
    line = re.sub(r"^\s*#+\s*", "", line.strip())
    line = re.sub(r"^\*\*(.*)\*\*$", r"\1", line.strip())
    return re.sub(r"\s+", " ", line).strip()


def split_lines(text):
    lines, cursor = [], 0
    for raw in text.split("\n"):
        end = cursor + len(raw)
        lines.append(Line(raw, list(range(cursor, end)), end if end < len(text) else None))
        cursor = end + 1
    if lines and lines[-1].text == "" and lines[-1].newline is None:
        lines.pop()
        lines[-1].newline = len(text) - 1 if text.endswith("\n") else None
    return lines


def heading_line_indexes(lines, gold):
    found, position = [], 0
    normalized = [normalize_line(line.text) for line in lines]
    for section in gold["sections"]:
        if section["heading"] is None:
            found.append(None)
            continue
        wanted = normalize_line(section["heading"])
        while position < len(lines) and normalized[position] != wanted:
            position += 1
        found.append(position if position < len(lines) else None)
        position += 1
    return found


def mark_kinds(lines):
    in_fence = False
    for line in lines:
        if line.text.lstrip().startswith("```"):
            line.kind = "fence"
            in_fence = not in_fence
        elif in_fence:
            line.kind = "code"
        elif line.text.lstrip().startswith("|"):
            line.kind = "table"
        elif re.match(r"^\s*[-*] ", line.text):
            line.kind = "bullet"
        elif not line.text.strip():
            line.kind = "blank"


def strip_heading_markup(lines):
    for line in lines:
        if line.kind in ("code", "fence"):
            continue
        match = re.match(r"^\s*#{1,6}\s+", line.text)
        if match:
            line.delete(*match.span())
        line.delete_all(r"\*\*")


def renumber(lines, rng):
    for line in lines:
        if not line.heading or line.title or rng.random() >= RENUMBER:
            continue
        match = NUMBERED.match(line.text)
        if match:
            number = match.group(1)
            choice = rng.randrange(4)
            if choice == 0:
                line.replace(len(number), match.end(), " ")
            elif choice == 1:
                line.replace(len(number), match.end(), ".")
            elif choice == 2:
                line.replace(0, match.end(), f"({number}) ")
            else:
                line.replace(len(number), match.end(), ") ")
        elif line.text[:1] in ROMAN:
            line.replace(0, 1, ROMAN[line.text[0]])


def glue(lines, rng):
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        j = i + 1
        while j < len(lines) and lines[j].kind == "blank":
            j += 1
        if line.heading and not line.title and j < len(lines) and lines[j].kind in ("text", "bullet") and not lines[j].heading \
                and rng.random() < GLUE:
            body = lines[j]
            if body.kind == "bullet":
                body.delete(*re.match(r"^\s*[-*] ", body.text).span())
            joined = Line(line.text + " " + body.text, line.origin + [line.newline] + body.origin, body.newline, "text", True)
            out.append(joined)
            i = j + 1
            continue
        out.append(line)
        i += 1
    return out


def flatten_tables(lines):
    out = []
    for line in lines:
        if line.kind == "table":
            if re.fullmatch(r"\s*\|[\s:|-]+\|\s*", line.text):
                continue
            line.delete_all(r"^\s*\|\s?")
            line.delete_all(r"\s?\|\s*$")
            line.delete_all(r"\|")
        out.append(line)
    return out


def drop_code_markup(lines):
    out = []
    for line in lines:
        if line.kind == "fence":
            continue
        if line.kind != "code":
            line.delete_all(r"`")
        out.append(line)
    return out


def lose_bullets(lines, rng):
    for line in lines:
        if line.kind != "bullet":
            continue
        match = re.match(r"^(\s*)([-*]) ", line.text)
        if rng.random() < LIST_DROP:
            line.delete(*match.span())
        else:
            line.delete(0, len(match.group(1)))
            line.replace(0, 1, "•")


def hard_wrap(lines, rng):
    width = rng.randint(*WRAP_WIDTH)
    out = []
    for line in lines:
        while line.kind not in ("table", "code") and len(line.text) > width:
            cut = line.text.rfind(" ", 0, width + 1)
            if cut <= 0:
                break
            head = Line(line.text[:cut], line.origin[:cut], line.origin[cut], line.kind, line.heading, line.title)
            out.append(head)
            line = Line(line.text[cut + 1:], line.origin[cut + 1:], line.newline, "wrapped")
        out.append(line)
    return out, width


def drop_blanks(lines, rng):
    return [line for line in lines if line.kind != "blank" or rng.random() >= BLANK_DROP]


def page_noise(lines, rng, text):
    match = DOC_NUMBER.search(text)
    number = match.group(0) if match else f"NV-DOC-{zlib.crc32(text.encode()) % 10000:04d}"
    footer, confidential = rng.choice(FOOTERS), rng.choice(CONFIDENTIAL)
    revision = f"  Rev.{rng.randint(1, 4)}" if rng.random() < 0.5 else ""
    page = rng.randint(*PAGE_LINES)
    pages = -(-len(lines) // page)
    out = []
    for i, line in enumerate(lines):
        if i and i % page == 0:
            k = i // page
            out.append(inserted(footer.format(k=k, n=pages)))
            out.append(inserted(number + revision))
            if confidential:
                out.append(inserted(confidential))
        out.append(line)
    out.append(inserted(footer.format(k=pages, n=pages)))
    return out


def join(lines):
    text, origin = [], []
    for i, line in enumerate(lines):
        text.append(line.text)
        origin += line.origin
        if i < len(lines) - 1 or line.newline is not None:
            text.append("\n")
            origin.append(line.newline)
    return "".join(text), origin


def degrade(doc_id, text, gold, level):
    rng = lambda step: random.Random(f"{doc_id}:{step}")
    lines = split_lines(text)
    mark_kinds(lines)
    indexes = heading_line_indexes(lines, gold)
    for number, index in enumerate(indexes):
        if index is not None:
            lines[index].heading = True
            lines[index].title = number == 0
    strip_heading_markup(lines)
    width = None
    if level >= 3:
        renumber(lines, rng("renumber"))
        lines = glue(lines, rng("glue"))
    if level >= 2:
        lines = flatten_tables(lines)
        lines = drop_code_markup(lines)
        lose_bullets(lines, rng("bullets"))
        lines, width = hard_wrap(lines, rng("wrap"))
        lines = drop_blanks(lines, rng("blanks"))
        lines = page_noise(lines, rng("pages"), text)
    new_text, origin = join(lines)
    return new_text, origin, width


class Mapping:
    def __init__(self, old_text, new_text, origin):
        self.old_text, self.new_text = old_text, new_text
        self.new_of = [None] * (len(old_text) + 1)
        for new, old in enumerate(origin):
            if old is not None:
                self.new_of[old] = new
        self.line_starts = [0] + [i + 1 for i, ch in enumerate(new_text) if ch == "\n"]

    def survivors(self, start, end):
        return [self.new_of[i] for i in range(start, end) if self.new_of[i] is not None]

    def span(self, start, end):
        alive = self.survivors(start, end)
        deleted = [self.old_text[i] for i in range(start, end) if self.new_of[i] is None and self.old_text[i] not in MARKUP]
        if not alive or deleted:
            return None
        return min(alive), max(alive) + 1

    def line_start(self, old_offset):
        alive = next((self.new_of[i] for i in range(old_offset, len(self.old_text)) if self.new_of[i] is not None), len(self.new_text))
        line = max(i for i, s in enumerate(self.line_starts) if s <= alive)
        return self.line_starts[line]


def gold_sections(text, gold, mapping):
    lines = split_lines(text)
    indexes = heading_line_indexes(lines, gold)
    starts = []
    for section, index in zip(gold["sections"], indexes):
        if section["heading"] is None:
            starts.append((0, section))
        elif index is not None:
            old_start = lines[index].origin[0] if lines[index].origin else 0
            starts.append((mapping.line_start(old_start), section))
    rows = []
    for i, (start, section) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(mapping.new_text)
        rows.append({"heading": section["heading"], "fields": section["fields"], "start": start, "end": end})
    return rows, len(gold["sections"]) - len(starts)


def run_level(level_name):
    level = int(level_name[1:])
    out = OUT / level_name
    (out / "md").mkdir(parents=True, exist_ok=True)
    mappings, section_rows, unplaced, widths = {}, [], 0, {}
    for path in sorted((SOURCE / "md").glob("*.md")):
        doc_id = path.stem
        text = path.read_text(encoding="utf-8")
        gold = json.loads((SOURCE / "gold" / f"{doc_id}.json").read_text(encoding="utf-8"))
        new_text, origin, width = degrade(doc_id, text, gold, level)
        (out / "md" / f"{doc_id}.md").write_text(new_text, encoding="utf-8")
        mapping = Mapping(text, new_text, origin)
        mappings[doc_id] = mapping
        widths[doc_id] = width
        sections, missing = gold_sections(text, gold, mapping)
        unplaced += missing
        section_rows.append({"doc_id": doc_id, "doc_type": gold["doc_type"], "drift": gold.get("drift"), "sections": sections})
    (out / "gold-sections.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in section_rows), encoding="utf-8")

    questions, spans_total, spans_lost, items_lost, questions_lost, lost_rows = [], 0, 0, 0, 0, []
    for line in SOURCE_GOLD.read_text(encoding="utf-8").splitlines():
        question = json.loads(line)
        items = []
        for item in question["evidence"]:
            spans = []
            for span in item["spans"]:
                spans_total += 1
                moved = mappings[span["doc_id"]].span(span["start"], span["end"])
                if moved is None:
                    spans_lost += 1
                    lost_rows.append((question["qid"], span["doc_id"], mappings[span["doc_id"]].old_text[span["start"]:span["end"]][:50]))
                    continue
                spans.append({"doc_id": span["doc_id"], "start": moved[0], "end": moved[1]})
            if spans:
                items.append({**item, "spans": spans})
            else:
                items_lost += 1
        if question["evidence"] and not items:
            questions_lost += 1
            continue
        questions.append({**question, "evidence": items})
    (out / "gold.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8")
    summary = {"level": level_name, "docs": len(mappings), "sections_unplaced": unplaced, "spans": spans_total, "spans_lost": spans_lost,
               "items_lost": items_lost, "questions": len(questions), "questions_lost": questions_lost, "lost": lost_rows}
    (out / "degrade-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{level_name}: 문서 {len(mappings)} · 못 놓은 절 {unplaced} · 근거 구간 {spans_total} 중 잃음 {spans_lost} · "
          f"잃은 근거 묶음 {items_lost} · 질문 {len(questions)} (잃은 질문 {questions_lost})")
    for row in lost_rows[:10]:
        print("  잃음", row)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--level", action="append", choices=["L1", "L2", "L3"], required=True)
    args = parser.parse_args()
    for level in args.level:
        run_level(level)


if __name__ == "__main__":
    main()
