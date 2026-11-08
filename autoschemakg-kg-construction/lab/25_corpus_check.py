"""합성 문서와 정답 칸 파일이 서로 맞는지 검사한다.

    python3 25_corpus_check.py                 # 전체
    python3 25_corpus_check.py failure          # 한 종류만

정답 파일의 절 제목이 문서에 혼자 선 줄로, 같은 순서로 있어야 한다. 줄을 견줄 때는 앞의 #, 감싼 ** 와 앞뒤 공백을 떼고 본다.
"""
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/parser-corpus"
SPEC = json.loads((CORPUS / "spec/templates.json").read_text(encoding="utf-8"))
SIZE = (1200, 6500)


def normalize_line(line):
    line = re.sub(r"^\s*#+\s*", "", line.strip())
    line = re.sub(r"^\*\*(.*)\*\*$", r"\1", line.strip())
    return re.sub(r"\s+", " ", line).strip()


def planned_ids(doc_type):
    if doc_type == "formless":
        return [f"formless-{n:02d}" for n in range(1, SPEC["formless"]["count"] + 1)]
    plan = SPEC["plan_new"] if doc_type == "tech_review" else SPEC["plan_templated"]
    return [f"{doc_type}-{template}-{n}" for template in ("A", "B") for n in range(1, len(plan) + 1)]


def allowed_fields(doc_type):
    if doc_type == "formless":
        return {"body"}
    fields = {"other"}
    for template in SPEC["templates"][doc_type].values():
        for field, _ in template["sections"]:
            fields.update([field] if isinstance(field, str) else field)
    return fields


def check_doc(doc_id, doc_type):
    md_path, gold_path = CORPUS / "md" / f"{doc_id}.md", CORPUS / "gold" / f"{doc_id}.json"
    if not md_path.exists() or not gold_path.exists():
        return [f"파일 없음: {md_path.name if not md_path.exists() else ''} {gold_path.name if not gold_path.exists() else ''}".strip()]
    text = md_path.read_text(encoding="utf-8")
    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"정답 JSON 깨짐: {error}"]

    problems = []
    if not SIZE[0] <= len(text) <= SIZE[1]:
        problems.append(f"길이 {len(text)}자 (허용 {SIZE[0]}~{SIZE[1]})")
    for key in ("id", "doc_type", "drift", "sections"):
        if key not in gold:
            problems.append(f"정답에 {key} 없음")
    if problems:
        return problems
    if gold["id"] != doc_id or gold["doc_type"] != doc_type:
        problems.append(f"id/doc_type 불일치: {gold['id']} {gold['doc_type']}")

    lines = [normalize_line(line) for line in text.splitlines()]
    cursor = 0
    for section in gold["sections"]:
        unknown = set(section["fields"]) - allowed_fields(doc_type)
        if unknown:
            problems.append(f"모르는 칸 {sorted(unknown)}")
        if section["heading"] is None:
            continue
        wanted = normalize_line(section["heading"])
        try:
            cursor = lines.index(wanted, cursor) + 1
        except ValueError:
            problems.append(f"제목 줄을 순서대로 못 찾음: {section['heading']!r}")

    if gold["drift"] == "pseudo_heading":
        hash_lines = [line for line in text.splitlines() if line.lstrip().startswith("#")]
        if len(hash_lines) > 1:
            problems.append(f"pseudo_heading 인데 # 줄이 {len(hash_lines)}개")
    return problems


def main():
    doc_types = sys.argv[1:] or list(SPEC["templates"]) + ["formless"]
    total_bad = 0
    for doc_type in doc_types:
        for doc_id in planned_ids(doc_type):
            problems = check_doc(doc_id, doc_type)
            if problems:
                total_bad += 1
                print(f"FAIL {doc_id}: " + " | ".join(problems))
    print("ALL OK" if total_bad == 0 else f"{total_bad}개 문서에 문제")
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
