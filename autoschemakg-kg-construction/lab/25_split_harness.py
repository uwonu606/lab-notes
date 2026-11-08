"""마크다운 문서를 검색 청크로 쪼갠다. 문서 묶음(템플릿)마다 LLM 이 쪼개기 규칙(split plan)을 한 번 쓰고, 코드가 그 규칙을 같은 묶음의 다음 문서에 다시 쓴다.

    .venv-25/bin/python 25_split_harness.py build --model haiku --run runs/25-split/haiku
    .venv-25/bin/python 25_split_harness.py build --model qwen3:8b --run runs/25-split/qwen3-8b
    .venv-25/bin/python 25_split_harness.py baselines --run runs/25-split/base
    .venv-25/bin/python 25_split_harness.py build --model haiku --line-plans --md-dir inputs/parser-corpus-messy/L2/md --run runs/25-split-messy/L2/haiku-line

문서는 도착 순서(--order-seed 로 섞음)대로 하나씩 들어온다. 문서마다 길은 넷 가운데 하나다.
  reuse    등록된 규칙 가운데 검증을 통과하는 것이 있으면 LLM 없이 그 규칙으로 쪼갠다.
  repair   통과하는 규칙은 없지만 제목의 REPAIR_FLOOR 이상을 덮는 규칙이 있으면, LLM 이 그 규칙을 넓힌다. 넓힌 규칙은 그 규칙의 이전 표본에서도 통과해야 등록된다.
  new      LLM 이 이 문서를 표본으로 새 규칙을 쓴다. 검증 문제를 되먹여 GENERATE_ATTEMPTS 번까지 다시 쓴다.
  formless 제목 후보가 MIN_CANDIDATES 보다 적으면 LLM 없이 문단 묶음으로 쪼갠다.
new·repair 가 끝내 검증을 못 넘으면 fallback(모든 # 제목을 경계로 쓰는 일반 규칙)으로 쪼갠다.

검증은 정답을 보지 않는다. 제목 후보를 규칙이 덮는 비율, 필수 칸이 나온 비율, other 칸 글자 비율만 본다.

--line-plans 를 주면, 위 길이 formless 나 fallback 으로 끝난 문서(변환기가 # 과 ** 를 잃은 문서)를 줄 규칙(line plan)으로 한 번 더 본다.
줄 규칙은 원문 한 줄의 앞 LINE_TEXT_CHARS 자에 거는 정규식과 칸이고, 걸린 줄이 절 제목이 된다(블록 가운데 있어도 그 줄에서 끊는다).
등록된 줄 규칙 가운데 검증을 넘는 것이 있으면 reuse, 없으면 LLM 이 새로 쓰거나({"formless": true} 로) 제목 없는 문서라고 답한다.
줄 규칙 검증도 정답을 보지 않는다: 제목 줄 MIN_CANDIDATES 개 이상, 규칙 하나가 LINE_RULE_MAX_HITS 줄 이하, 첫 제목 앞 글자 비율,
필수 칸 비율, other 비율을 본다. --line-no-reuse 는 줄 규칙 재사용을 끄고 문서마다 새로 쓴다(회차 25 열화 실험의 사후 변형).

baselines --heuristic 은 mdheader-pseudo 의 제목에 더해, HEURISTIC_MAX_CHARS 자 이하 한 줄이 번호·로마 숫자·■·대괄호·제N장 꼴(HEURISTIC_SHAPE)이면
제목으로 보는 판(mdheader-heuristic)을 낸다. 이 꼴은 열화 말뭉치를 돌리기 전에 정했다.
"""
import argparse
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from markdown_it import MarkdownIt

from llm_cache import ClaudeClient, LLMCallFailed

LAB = Path(__file__).parent
MD_DIR = LAB / "inputs/parser-corpus/md"
SCHEMA_DIR = LAB / "inputs/parser-schemas"
PLAN_PROMPT = (LAB / "prompts/25-split-plan.txt").read_text(encoding="utf-8")
REPAIR_PROMPT = (LAB / "prompts/25-split-repair.txt").read_text(encoding="utf-8")
LINE_PLAN_PROMPT = (LAB / "prompts/25-split-lineplan.txt").read_text(encoding="utf-8")
CACHE = LAB / "runs/25-cache"

VALIDATION = {"min_heading_match": 0.8, "min_required_hit": 0.5, "max_other_share": 0.3}
REPAIR_FLOOR = 0.4
GENERATE_ATTEMPTS = 3
REGRESSION_SAMPLES = 3
MIN_CANDIDATES = 2
DEFAULT_POLICY = {"split": "blocks", "max_chars": 1000}
MAX_CHARS_RANGE = (300, 2000)
PSEUDO_MAX_CHARS = 50
PSEUDO_SHAPE = re.compile(r"^(\*\*.+\*\*|\[[^\]]+\]|([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|\d+(\.\d+)*)\.\s*\S.*|[■□▶●◆]\s*\S.*)$")
TOP_BLOCKS = {"heading_open", "paragraph_open", "bullet_list_open", "ordered_list_open", "table_open", "fence", "code_block",
              "hr", "blockquote_open", "html_block"}
LINE_TEXT_CHARS = 60
LINE_RULE_MAX_HITS = 2
LINE_MAX_META_SHARE = 0.3
LINE_SKIP_BLOCKS = {"fence", "code_block", "table", "html_block"}
HEURISTIC_MAX_CHARS = 40
HEURISTIC_SHAPE = re.compile(r"^(\(?\d{1,2}(\.\d{1,2})*(\.|\)|\s)\s*[가-힣A-Za-z]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[.)]?\s*\S|[IVX]{1,4}[.)]\s*\S"
                             r"|[■□▶●◆]\s*\S|\[[^\]]+\]$|제\s*\d+\s*[장절])")
GENERIC_PLAN = {"doc_type": "generic", "new_fields": [], "heading_rules": [{"pattern": ".", "field": "section"}],
                "pseudo_headings": False, "fields": {}}

markdown = MarkdownIt("commonmark").enable("table")


@dataclass
class Block:
    kind: str
    start: int
    end: int
    text: str
    level: int = 0


@dataclass
class Candidate:
    block: int
    shape: str
    level: int
    text: str


@dataclass
class Doc:
    doc_id: str
    text: str
    blocks: list
    candidates: list
    title: Candidate = None

    @property
    def body_candidates(self):
        return [c for c in self.candidates if c is not self.title]


@dataclass
class Section:
    field: str
    heading_path: list
    blocks: list


@dataclass
class Fit:
    sections: list
    candidates: int
    covered: int
    unmatched: list
    fields_present: set
    other_share: float
    errors: list = field(default_factory=list)

    @property
    def heading_match(self):
        return self.covered / self.candidates if self.candidates else 1.0


def strip_markup(line):
    line = re.sub(r"^\s*#+\s*", "", line.strip())
    return re.sub(r"^\*\*(.*)\*\*$", r"\1", line).strip()


def read_doc(doc_id, text):
    line_starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]
    offset = lambda line: line_starts[line] if line < len(line_starts) else len(text)
    tokens = markdown.parse(text)
    blocks, candidates = [], []
    for i, token in enumerate(tokens):
        if token.level != 0 or token.type not in TOP_BLOCKS or not token.map:
            continue
        start, end = offset(token.map[0]), offset(token.map[1])
        raw = text[start:end].rstrip("\n")
        end = start + len(raw)
        kind = token.type.removesuffix("_open")
        level = int(token.tag[1]) if kind == "heading" else 0
        blocks.append(Block(kind, start, end, raw, level))
        if kind == "heading":
            candidates.append(Candidate(len(blocks) - 1, "H", level, strip_markup(tokens[i + 1].content)))
        elif kind == "paragraph" and "\n" not in raw and len(raw) <= PSEUDO_MAX_CHARS and PSEUDO_SHAPE.match(raw.strip()):
            candidates.append(Candidate(len(blocks) - 1, "P", 2, strip_markup(raw)))
    doc = Doc(doc_id, text, blocks, candidates)
    if candidates and candidates[0].shape == "H" and candidates[0].level == 1:
        doc.title = candidates[0]
    return doc


def line_doc(doc, detect, keep_markup=False):
    heads, cursor = [], 0
    skip = [(b.start, b.end) for b in doc.blocks if b.kind in LINE_SKIP_BLOCKS]
    markup_starts = {doc.blocks[c.block].start for c in doc.candidates} if keep_markup else set()
    for raw in doc.text.split("\n"):
        start, end = cursor, cursor + len(raw)
        cursor = end + 1
        stripped = raw.strip()
        if not stripped or start in markup_starts or any(s <= start < e for s, e in skip):
            continue
        found = detect(stripped)
        if found:
            heads.append((start + len(raw) - len(raw.lstrip()), end, stripped[:LINE_TEXT_CHARS], found))
    blocks, candidates = [], []
    kept = {doc.blocks[c.block].start: c for c in doc.candidates} if keep_markup else {}

    def add(kind, start, end, level=0):
        raw = doc.text[start:end].rstrip()
        lead = len(raw) - len(raw.lstrip())
        if raw.strip():
            blocks.append(Block(kind, start + lead, start + len(raw), raw.strip(), level))
            return True
        return False

    for block in doc.blocks:
        if block.start in kept:
            original = kept[block.start]
            blocks.append(block)
            candidates.append(Candidate(len(blocks) - 1, original.shape, original.level, original.text))
            continue
        cursor = block.start
        for head_start, head_end, text, (level, _) in heads:
            if not block.start <= head_start < block.end + 1:
                continue
            add(block.kind, cursor, head_start)
            if add("heading", head_start, head_end, level):
                candidates.append(Candidate(len(blocks) - 1, "L", level, text))
            cursor = head_end + 1
        if cursor < block.end:
            add(block.kind, cursor, block.end)
    result = Doc(doc.doc_id, doc.text, blocks, candidates)
    if keep_markup and doc.title:
        result.title = next((c for c in candidates if c.text == doc.title.text and c.shape == "H"), None)
    return result


def heuristic_heading(line):
    if len(line) > HEURISTIC_MAX_CHARS or "  " in line or line.endswith(".") or not HEURISTIC_SHAPE.match(line):
        return None
    number = re.match(r"^\(?(\d{1,2}(\.\d{1,2})*)", line)
    return (2 + number.group(1).count(".") if number else 2), ["section"]


def title_text(doc):
    if doc.title:
        return doc.title.text
    first_line = doc.text.strip().splitlines()[0] if doc.text.strip() else ""
    return strip_markup(first_line)[:60]


def load_schemas(schema_dir=SCHEMA_DIR):
    schemas = {}
    for path in sorted(Path(schema_dir).glob("*.yaml")):
        schema = yaml.safe_load(path.read_text(encoding="utf-8"))
        schemas[schema["doc_type"]] = schema
    return schemas


def schemas_text(schemas):
    lines = []
    for doc_type, schema in schemas.items():
        fields = "; ".join(f"{f['name']}{'*' if f['required'] else ''} = {f['description']}" for f in schema["fields"])
        lines.append(f"{doc_type} ({schema['name']}) | {fields}")
    return "\n".join(lines)


def plan_fields(plan, schemas):
    if plan["doc_type"] in schemas:
        return schemas[plan["doc_type"]]["fields"]
    return plan.get("new_fields") or []


def apply_plan(doc, plan, schemas):
    errors, rules = [], []
    for rule in plan["heading_rules"]:
        try:
            fields = rule["field"] if isinstance(rule["field"], list) else [rule["field"]]
            rules.append((re.compile(rule["pattern"], re.IGNORECASE), [str(f) for f in fields]))
        except re.error as error:
            errors.append(f"pattern {rule['pattern']!r} does not compile: {error}")
    known = {f["name"] for f in plan_fields(plan, schemas)} | {"other"}
    if plan["doc_type"] != "generic":
        errors += [f"field {f!r} is not a field of {plan['doc_type']}" for _, fields in rules for f in fields if f not in known]

    headings = [c for c in doc.candidates if c.shape == "H" or plan.get("pseudo_headings")]
    starts, present = {}, set()
    covered, unmatched = 0, []
    current_level, current_field, stack = None, "meta", []
    for candidate in headings:
        stack = [(level, text) for level, text in stack if level < candidate.level] + [(candidate.level, candidate.text)]
        path = [text for _, text in stack if candidate is doc.title or text != (doc.title.text if doc.title else None)]
        if candidate is doc.title:
            starts[candidate.block] = ("meta", [candidate.text])
            continue
        matched = next((f for pattern, f in rules if pattern.search(candidate.text)), None)
        if matched is not None:
            covered += 1
            current_level, current_field = candidate.level, matched[0]
            present.update(matched)
        elif current_level is not None and candidate.level > current_level:
            covered += 1
        else:
            unmatched.append(candidate.text)
            current_level, current_field = candidate.level, "other"
        starts[candidate.block] = (current_field, path)

    sections, total, other = [], 0, 0
    current = Section("meta", [], [])
    for index, block in enumerate(doc.blocks):
        if index in starts:
            carried = []
            if current.blocks and all(b.kind == "heading" for b in current.blocks) and current.field == starts[index][0]:
                carried = current.blocks
            elif current.blocks:
                sections.append(current)
            current = Section(starts[index][0], starts[index][1], list(carried))
        current.blocks.append(block)
        total += len(block.text)
        other += len(block.text) if current.field == "other" else 0
    if current.blocks:
        sections.append(current)
    body_count = len([c for c in headings if c is not doc.title])
    return Fit(sections, body_count, covered, unmatched, {s.field for s in sections} | present, other / total if total else 0.0, errors)


def validate(fit, plan, schemas):
    problems = list(fit.errors)
    if fit.heading_match < VALIDATION["min_heading_match"]:
        problems.append(f"headings matched by no rule: {fit.unmatched}")
    required = [f["name"] for f in plan_fields(plan, schemas) if f.get("required")]
    missing = [name for name in required if name not in fit.fields_present]
    if required and 1 - len(missing) / len(required) < VALIDATION["min_required_hit"]:
        problems.append(f"required fields with no section: {missing}")
    if fit.other_share > VALIDATION["max_other_share"]:
        problems.append(f"{fit.other_share:.0%} of the text fell into 'other'")
    return problems


def compiled_line_rules(plan):
    rules, errors = [], []
    for rule in plan["heading_rules"]:
        try:
            fields = rule["field"] if isinstance(rule["field"], list) else [rule["field"]]
            rules.append((re.compile(rule["pattern"], re.IGNORECASE), [str(f) for f in fields], rule["pattern"]))
        except re.error as error:
            errors.append(f"pattern {rule['pattern']!r} does not compile: {error}")
    return rules, errors


def apply_line_plan(doc, plan, schemas):
    rules, errors = compiled_line_rules(plan)
    hits = {}

    def detect(line):
        for pattern, fields, source in rules:
            if pattern.search(line[:LINE_TEXT_CHARS]):
                hits.setdefault(source, []).append(line[:LINE_TEXT_CHARS])
                return 2, fields
        return None

    ldoc = line_doc(doc, detect)
    fit = apply_plan(ldoc, {**plan, "pseudo_headings": True}, schemas)
    fit.errors = errors + fit.errors
    fit.line_hits = hits
    first = ldoc.blocks[ldoc.candidates[0].block].start if ldoc.candidates else len(doc.text)
    fit.meta_share = len(doc.text[:first].strip()) / max(len(doc.text.strip()), 1)
    return ldoc, fit


def validate_line(fit, plan, schemas):
    problems = list(fit.errors)
    if fit.candidates < MIN_CANDIDATES:
        problems.append(f"only {fit.candidates} lines matched a rule; a sectioned document has at least {MIN_CANDIDATES}")
    for source, lines in fit.line_hits.items():
        if len(lines) > LINE_RULE_MAX_HITS:
            problems.append(f"pattern {source!r} matched {len(lines)} lines, so it also hits body lines: {lines[:6]}")
    if fit.meta_share > LINE_MAX_META_SHARE:
        problems.append(f"{fit.meta_share:.0%} of the text comes before the first matched heading line")
    required = [f["name"] for f in plan_fields(plan, schemas) if f.get("required")]
    missing = [name for name in required if name not in fit.fields_present]
    if required and 1 - len(missing) / len(required) < VALIDATION["min_required_hit"]:
        problems.append(f"required fields with no section: {missing}")
    if fit.other_share > VALIDATION["max_other_share"]:
        problems.append(f"{fit.other_share:.0%} of the text fell into 'other'")
    return problems


def line_pieces(block, max_chars):
    pieces, first, length, cursor = [], None, 0, block.start
    for line in block.text.split("\n"):
        line_start, line_end = cursor, cursor + len(line)
        cursor = line_end + 1
        if first is not None and length + len(line) + 1 > max_chars:
            pieces.append((first, last))
            first, length = None, 0
        if first is None:
            first = line_start
        last, length = line_end, length + len(line) + 1
    if first is not None:
        pieces.append((first, last))
    return pieces


def table_header(block):
    return " ".join(block.text.split("\n")[:1]).strip()


def section_chunks(section, policy):
    max_chars = min(max(int(policy.get("max_chars", DEFAULT_POLICY["max_chars"])), MAX_CHARS_RANGE[0]), MAX_CHARS_RANGE[1])
    split = policy.get("split", DEFAULT_POLICY["split"])
    span = (section.blocks[0].start, section.blocks[-1].end)
    if split == "whole" and span[1] - span[0] <= max_chars * 1.5:
        return [(span[0], span[1], None)]
    chunks, group = [], []

    def flush():
        if group:
            chunks.append((group[0].start, group[-1].end, None))
            group.clear()

    for block in section.blocks:
        size = len(block.text)
        breaks_table = split == "table_rows" and block.kind == "table" and size > max_chars // 2
        if size > max_chars or breaks_table:
            head = group[:]
            flush()
            header = table_header(block) if block.kind == "table" else None
            pieces = line_pieces(block, max_chars)
            if head and pieces:
                pieces[0] = (head[0].start, pieces[0][1])
            chunks += [(start, end, header) for start, end in pieces]
            continue
        if group and group[-1].end - group[0].start + size > max_chars and group[-1].kind != "heading":
            flush()
        group.append(block)
    flush()
    return chunks


def doc_chunks(doc, fit, plan, schemas, route, extra=None, embed_label="full"):
    type_name = schemas[plan["doc_type"]]["name"] if plan["doc_type"] in schemas else plan["doc_type"].removeprefix("new:")
    descriptions = {f["name"]: f["description"] for f in plan_fields(plan, schemas)}
    rows = []
    for section in fit.sections:
        policy = plan.get("fields", {}).get(section.field, DEFAULT_POLICY)
        for start, end, header in section_chunks(section, policy):
            if not doc.text[start:end].strip():
                continue
            label_parts = [title_text(doc)] + ([type_name] if embed_label == "full" else [])
            if embed_label == "full" and (section.field in descriptions or section.field == "other"):
                label_parts.append(f"{section.field}: {descriptions.get(section.field, '템플릿 밖 절')}")
            if section.heading_path != [title_text(doc)]:
                label_parts.append(" > ".join(section.heading_path))
            if header:
                label_parts.append(f"표 머리: {header}")
            rows.append({"id": f"{doc.doc_id}#{len(rows):03d}", "doc_id": doc.doc_id, "start": start, "end": end,
                         "field": section.field, "heading_path": section.heading_path, "route": route,
                         "label": " | ".join(p for p in label_parts if p), **(extra or {})})
    return rows


def formless_chunks(doc, route="formless"):
    fit = apply_plan(doc, GENERIC_PLAN, {})
    plan = {**GENERIC_PLAN, "doc_type": "형식 없는 메모"}
    return doc_chunks(doc, fit, plan, {}, route)


def parse_json(reply):
    text = reply.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def normalized_plan(raw):
    plan = {"doc_type": str(raw.get("doc_type", "")).strip(), "new_fields": raw.get("new_fields") or [],
            "heading_rules": [r for r in raw.get("heading_rules") or [] if isinstance(r, dict) and "pattern" in r and "field" in r],
            "pseudo_headings": bool(raw.get("pseudo_headings")), "fields": raw.get("fields") or {}}
    if not plan["doc_type"]:
        raise ValueError("plan has no doc_type")
    if not plan["heading_rules"]:
        raise ValueError("plan has no heading_rules")
    return plan


def candidates_text(doc, plan=None, schemas=None):
    unmatched = set()
    if plan is not None:
        unmatched = set(apply_plan(doc, {**plan, "pseudo_headings": True}, schemas).unmatched)
    lines = []
    for candidate in doc.candidates:
        mark = "  UNMATCHED" if candidate.text in unmatched else ""
        tag = f"H{candidate.level}" if candidate.shape == "H" else "P"
        lines.append(f"- [{tag}] {candidate.text}{' (document title)' if candidate is doc.title else ''}{mark}")
    return "\n".join(lines) or "(none)"


class Planner:
    def __init__(self, model, schemas):
        self.schemas = schemas
        self.schema_block = schemas_text(schemas)
        if model in ("haiku", "sonnet", "opus"):
            self.client = ClaudeClient(model, cache_dir=CACHE / "llm")
        else:
            from ollama_cache import OllamaClient
            self.client = OllamaClient(model, num_ctx=16384, num_predict=2048, json_output=True, cache_dir=CACHE / "ollama")
        self.calls = []

    def _ask(self, prompt, tag):
        try:
            reply = self.client.ask(prompt, tag=tag)
        except LLMCallFailed as error:
            self.calls.append({"tag": tag, "ok": False, "error": str(error)[:200]})
            return None
        self.calls.append({"tag": tag, "ok": True, "cache_hit": reply.cache_hit})
        return reply.text

    def _loop(self, build_prompt, check, tag, stop_when=None):
        feedback, attempts = "", []
        for attempt in range(1, GENERATE_ATTEMPTS + 1):
            reply = self._ask(build_prompt(feedback), tag)
            if reply is None:
                attempts.append({"attempt": attempt, "problems": ["LLM call failed"]})
                continue
            if stop_when and stop_when(reply):
                attempts.append({"attempt": attempt, "problems": ["formless" if stop_when == self.is_formless else "different family"]})
                return None, attempts
            try:
                plan = normalized_plan(parse_json(reply))
            except (ValueError, json.JSONDecodeError) as error:
                problems = [f"reply was not a usable plan: {error}"]
            else:
                problems = check(plan)
                if not problems:
                    attempts.append({"attempt": attempt, "problems": []})
                    return plan, attempts
            attempts.append({"attempt": attempt, "problems": problems})
            feedback = ("\nYOUR PREVIOUS PLAN FAILED THESE CHECKS. Fix every one:\n- " + "\n- ".join(problems) + "\n")
        return None, attempts

    def generate(self, doc):
        def build(feedback):
            return (PLAN_PROMPT.replace("{schemas}", self.schema_block).replace("{candidates}", candidates_text(doc))
                    .replace("{document}", doc.text).replace("{feedback}", feedback))
        return self._loop(build, lambda plan: validate(apply_plan(doc, plan, self.schemas), plan, self.schemas), "plan")

    def generate_lines(self, doc):
        def build(feedback):
            return (LINE_PLAN_PROMPT.replace("{schemas}", self.schema_block).replace("{document}", doc.text)
                    .replace("{feedback}", feedback))

        def check(plan):
            _, fit = apply_line_plan(doc, plan, self.schemas)
            return validate_line(fit, plan, self.schemas)
        return self._loop(build, check, "lineplan", stop_when=self.is_formless)

    def is_formless(self, reply):
        try:
            return bool(parse_json(reply).get("formless"))
        except (ValueError, json.JSONDecodeError):
            return False

    def is_other_family(self, reply):
        try:
            return bool(parse_json(reply).get("different_family"))
        except (ValueError, json.JSONDecodeError):
            return False

    def repair(self, plan, doc, earlier_docs, problems):
        def build(feedback):
            return (REPAIR_PROMPT.replace("{schemas}", self.schema_block).replace("{plan}", json.dumps(plan, ensure_ascii=False, indent=1))
                    .replace("{candidates}", candidates_text(doc, plan, self.schemas)).replace("{document}", doc.text)
                    .replace("{problems}", "; ".join(problems)).replace("{feedback}", feedback))

        def check(new_plan):
            found = validate(apply_plan(doc, new_plan, self.schemas), new_plan, self.schemas)
            for earlier in earlier_docs:
                found += [f"earlier document of this family now fails: {p}"
                          for p in validate(apply_plan(earlier, new_plan, self.schemas), new_plan, self.schemas)]
            return found
        return self._loop(build, check, "repair", stop_when=self.is_other_family)


def best_fit(doc, registry, schemas):
    scored = []
    for plan_id, entry in registry.items():
        fit = apply_plan(doc, entry["plan"], schemas)
        problems = validate(fit, entry["plan"], schemas)
        scored.append((not problems, fit.heading_match, -fit.other_share, plan_id, fit, problems))
    scored.sort(key=lambda s: s[:3], reverse=True)
    return scored[0] if scored else None


def read_corpus(order_seed, md_dir=MD_DIR):
    docs = [read_doc(path.stem, path.read_text(encoding="utf-8")) for path in sorted(Path(md_dir).glob("*.md"))]
    random.Random(order_seed).shuffle(docs)
    return docs


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def best_line_fit(doc, line_registry, schemas):
    scored = []
    for plan_id, entry in line_registry.items():
        ldoc, fit = apply_line_plan(doc, entry["plan"], schemas)
        problems = validate_line(fit, entry["plan"], schemas)
        scored.append((not problems, -len(problems), -fit.other_share, plan_id, ldoc, fit))
    scored.sort(key=lambda s: s[:3], reverse=True)
    return scored[0] if scored and scored[0][0] else None


def line_route(doc, planner, line_registry, schemas, position, reuse=True):
    best = best_line_fit(doc, line_registry, schemas) if reuse else None
    if best:
        plan_id = best[3]
        line_registry[plan_id]["samples"].append(doc.doc_id)
        return "reuse", plan_id, line_registry[plan_id]["plan"], best[4], best[5], []
    plan, attempts = planner.generate_lines(doc)
    if plan:
        plan_id = f"L{len(line_registry) + 1:02d}"
        line_registry[plan_id] = {"plan": plan, "samples": [doc.doc_id], "version": 1, "born_at": position, "mode": "line"}
        ldoc, fit = apply_line_plan(doc, plan, schemas)
        return "new", plan_id, plan, ldoc, fit, attempts
    route = "formless" if attempts and attempts[-1]["problems"] == ["formless"] else "fallback"
    return route, None, None, None, None, attempts


def markup_route(doc, registry, planner, schemas, by_id, position):
    best = best_fit(doc, registry, schemas)
    route, plan_id, plan, attempts = None, None, None, []
    if best and best[0]:
        plan_id, route = best[3], "reuse"
        plan = registry[plan_id]["plan"]
    elif best and best[1] >= REPAIR_FLOOR:
        target = best[3]
        earlier = [by_id[i] for i in registry[target]["samples"][-REGRESSION_SAMPLES:]]
        plan, attempts = planner.repair(registry[target]["plan"], doc, earlier, best[5])
        if plan:
            plan_id, route = target, "repair"
            entry = registry[target]
            entry["plan"] = plan
            entry["version"] += 1
            entry["samples"].append(doc.doc_id)
            entry.setdefault("history", []).append({"version": entry["version"], "sample": doc.doc_id, "plan": plan})
    if plan is None:
        plan, new_attempts = planner.generate(doc)
        attempts += new_attempts
        if plan:
            plan_id, route = f"p{max((int(k[1:]) for k in registry), default=0) + 1:02d}", "new"
            registry[plan_id] = {"plan": plan, "samples": [doc.doc_id], "version": 1, "born_at": position,
                                 "history": [{"version": 1, "sample": doc.doc_id, "plan": plan}]}
    return route, plan_id, plan, attempts


def build(args):
    run = Path(args.run)
    schemas = load_schemas()
    planner = Planner(args.model, schemas)
    registry, line_registry, decisions, chunks = {}, {}, [], []
    docs = read_corpus(args.order_seed, args.md_dir)
    by_id = {d.doc_id: d for d in docs}
    for position, doc in enumerate(docs):
        calls_before = len(planner.calls)
        decision = {"position": position, "doc_id": doc.doc_id, "candidates": len(doc.body_candidates)}
        if len(doc.body_candidates) < MIN_CANDIDATES and args.line_plans:
            route, plan_id, plan, ldoc, fit, attempts = line_route(doc, planner, line_registry, schemas, position, not args.line_no_reuse)
            decisions.append(line_decision(decision, doc, route, plan_id, plan, ldoc, fit, attempts, planner, calls_before, chunks, schemas))
            continue
        if len(doc.body_candidates) < MIN_CANDIDATES:
            chunks += formless_chunks(doc)
            decisions.append({**decision, "route": "formless", "llm_calls": 0})
            continue
        route, plan_id, plan, attempts = markup_route(doc, registry, planner, schemas, by_id, position)
        if plan is None and args.line_plans:
            route, plan_id, plan, ldoc, fit, line_attempts = line_route(doc, planner, line_registry, schemas, position, not args.line_no_reuse)
            decision["markup_attempts"] = attempts
            decisions.append(line_decision(decision, doc, route, plan_id, plan, ldoc, fit, line_attempts, planner, calls_before, chunks, schemas))
            continue
        if plan is None:
            plan_id, route, plan = None, "fallback", GENERIC_PLAN
        fit = apply_plan(doc, plan, schemas)
        chunks += doc_chunks(doc, fit, plan, schemas, f"{route}:{plan_id}" if plan_id else route)
        decisions.append({**decision, "route": route, "plan": plan_id, "doc_type": plan["doc_type"], "heading_match": round(fit.heading_match, 3),
                          "other_share": round(fit.other_share, 3), "unmatched": fit.unmatched, "attempts": attempts,
                          "llm_calls": len(planner.calls) - calls_before})
        print(f"{position:3d} {doc.doc_id:22} {route:8} {plan_id or '-':4} {plan['doc_type']:24} match={fit.heading_match:.2f} calls={len(planner.calls) - calls_before}")

    write_jsonl(run / "chunks-harness.jsonl", chunks)
    write_jsonl(run / "decisions.jsonl", decisions)
    (run / "plans").mkdir(parents=True, exist_ok=True)
    for plan_id, entry in {**registry, **line_registry}.items():
        (run / "plans" / f"{plan_id}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    usage = {"model": args.model, "llm_calls": len(planner.calls), "plans": len(registry), "line_plans": len(line_registry), "stats": planner.client.stats.snapshot(),
             "usage_line": planner.client.usage_line() if hasattr(planner.client, "usage_line") else ""}
    (run / "usage.json").write_text(json.dumps(usage, ensure_ascii=False, indent=1), encoding="utf-8")
    routes = {}
    for d in decisions:
        routes[d["route"]] = routes.get(d["route"], 0) + 1
    print(f"문서 {len(docs)} · 청크 {len(chunks)} · 규칙 {len(registry)} · 줄 규칙 {len(line_registry)} · 길 {routes} · LLM 호출 {len(planner.calls)}")
    print(usage["usage_line"])


def line_decision(decision, doc, route, plan_id, plan, ldoc, fit, attempts, planner, calls_before, chunks, schemas):
    calls = len(planner.calls) - calls_before
    if plan is None:
        chunks += formless_chunks(doc, route)
        print(f"{decision['position']:3d} {doc.doc_id:22} line-{route:8} {'-':4} {'-':24} calls={calls}")
        return {**decision, "route": route, "mode": "line", "attempts": attempts, "llm_calls": calls}
    chunks += doc_chunks(ldoc, fit, plan, schemas, f"{route}:{plan_id}")
    print(f"{decision['position']:3d} {doc.doc_id:22} line-{route:8} {plan_id:4} {plan['doc_type']:24} lines={fit.candidates} calls={calls}")
    return {**decision, "route": route, "mode": "line", "plan": plan_id, "doc_type": plan["doc_type"], "heading_lines": fit.candidates,
            "meta_share": round(fit.meta_share, 3), "other_share": round(fit.other_share, 3), "attempts": attempts, "llm_calls": calls}


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


def baselines(args):
    run = Path(args.run)
    docs = read_corpus(args.order_seed, args.md_dir)
    fixed, generic, pseudo, heuristic = [], [], [], []
    pseudo_plan = {**GENERIC_PLAN, "doc_type": "", "pseudo_headings": True}
    for doc in docs:
        for start, end in fixed_spans(doc.text, args.size):
            if doc.text[start:end].strip():
                fixed.append({"id": f"{doc.doc_id}#{len(fixed):04d}", "doc_id": doc.doc_id, "start": start, "end": end, "label": title_text(doc)})
        generic += doc_chunks(doc, apply_plan(doc, GENERIC_PLAN, {}), {**GENERIC_PLAN, "doc_type": ""}, {}, "mdheader")
        pseudo += doc_chunks(doc, apply_plan(doc, pseudo_plan, {}), pseudo_plan, {}, "mdheader-pseudo")
        if args.heuristic:
            hdoc = line_doc(doc, heuristic_heading, keep_markup=True)
            heuristic += doc_chunks(hdoc, apply_plan(hdoc, pseudo_plan, {}), pseudo_plan, {}, "mdheader-heuristic")
    write_jsonl(run / "chunks-fixed.jsonl", fixed)
    write_jsonl(run / "chunks-mdheader.jsonl", generic)
    write_jsonl(run / "chunks-mdheader-pseudo.jsonl", pseudo)
    if args.heuristic:
        write_jsonl(run / "chunks-mdheader-heuristic.jsonl", heuristic)
    print(f"고정 {len(fixed)}개 · 제목 경계 {len(generic)}개 · 굵은 줄까지 제목 경계 {len(pseudo)}개")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--model", default="haiku")
    b.add_argument("--run", required=True)
    b.add_argument("--order-seed", type=int, default=0)
    b.add_argument("--md-dir", default=MD_DIR)
    b.add_argument("--line-plans", action="store_true", help="formless·fallback 문서를 줄 규칙으로 한 번 더 본다")
    b.add_argument("--line-no-reuse", action="store_true", help="줄 규칙을 재사용하지 않고 문서마다 새로 쓴다")
    base = sub.add_parser("baselines")
    base.add_argument("--run", required=True)
    base.add_argument("--order-seed", type=int, default=0)
    base.add_argument("--size", type=int, default=1000)
    base.add_argument("--md-dir", default=MD_DIR)
    base.add_argument("--heuristic", action="store_true", help="짧은 번호·로마 숫자·■·대괄호 줄을 제목으로 보는 판도 낸다")
    args = parser.parse_args()
    {"build": build, "baselines": baselines}[args.command](args)


if __name__ == "__main__":
    main()
