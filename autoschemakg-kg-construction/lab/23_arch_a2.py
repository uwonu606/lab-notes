"""안 2 개념 계층 펼치기: 질문의 개념을 hierarchy 로 하위 entry 까지 펼쳐 entry 마다 claim-ctx 상위 m 개를 번갈아 담고, 연도·Release·버전 조건으로 claim 을 거른다.

    .venv-hr2/bin/python 23_arch_a2.py run       # Haiku 파싱(캐시) → 두 판 retrieval·trace → 채점
    .venv-hr2/bin/python 23_arch_a2.py report    # claim-ctx·B0 대비 표, "계층이 일했나", per-question.jsonl
설정은 runs/23-arch-a2-abstraction/CONFIG.md.
"""
import importlib
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field

import embed_client
from llm_cache import DEFAULT_SYSTEM, ClaudeClient, LLMCallFailed

arch = importlib.import_module("23_arch_common")
tagging = importlib.import_module("23_glossary_tag")
b2 = importlib.import_module("23_arch_b2")

RUN_NAME = "a2-abstraction"
RUN_DIR = arch.RUNS / f"23-arch-{RUN_NAME}"
PROMPT_PATH = arch.LAB / "prompts/a2-abstraction-parse.txt"
CLAIM_TAGS = RUN_DIR / "claim-tags.jsonl"
PER_INSTANCE = 3
DEPTH = 400
HAIKU_CONCURRENCY = 4
MAX_CONCEPTS = 2
OPS = ("=", ">=", "<=", "between")
CONDITION_NAMES = {"year": "연도", "3gpp-release": "Release", "software-version": "버전"}
FILL_PATH_STAGE = "fallback=claimctx"
ENTRY_FIRST = f"{RUN_NAME}-entryfirst"
CONDITION_ONLY = f"{RUN_NAME}-condonly"
LISTING_CUES = ("별로", "별 ", "마다", "각 ", "각각", "모든", "모두", "전부", "per ", "each", "every", "by vendor", "by operator", "by carrier")


@dataclass(frozen=True)
class Variant:
    name: str
    expand: bool
    entry_first: bool = False
    mix: str = "lanes_first"
    cue_only: bool = False


VARIANTS = (Variant(RUN_NAME, expand=True), Variant(CONDITION_ONLY, expand=False), Variant(ENTRY_FIRST, expand=True, entry_first=True),
            Variant(f"{RUN_NAME}-rrf", expand=True, entry_first=True, mix="rrf"),
            Variant(f"{RUN_NAME}-percue", expand=True, entry_first=True, cue_only=True))


def listing_cues(question):
    folded = question.casefold()
    return [cue for cue in LISTING_CUES if cue in folded]


def version_tuple(text):
    return tuple(int(n) for n in re.findall(r"\d+", str(text).split("-")[0]))


def padded(a, b):
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)), b + (0,) * (width - len(b))


def satisfies(value, op, wanted, as_version=False):
    if as_version:
        v, ws = version_tuple(value), [version_tuple(w) for w in wanted]
        if op == "=":
            return any(v[:len(w)] == w for w in ws if w)
        pairs = [padded(v, w) for w in ws]
    else:
        pairs = [(value, w) for w in wanted]
    if op == "=":
        return any(a == b for a, b in pairs)
    if op == ">=":
        return pairs[0][0] >= pairs[0][1]
    if op == "<=":
        return pairs[0][0] <= pairs[0][1]
    low, high = min(b for _, b in pairs), max(b for _, b in pairs)
    return low <= pairs[0][0] <= high


@dataclass
class Condition:
    concept: str
    op: str
    values: list
    entry: str = None
    target_label: str = ""

    @property
    def label(self):
        shown = {"=": "", ">=": "≥", "<=": "≤"}
        values = "~".join(map(str, self.values)) if self.op == "between" else "|".join(map(str, self.values))
        if self.op in shown:
            values = shown[self.op] + values
        return f"{CONDITION_NAMES[self.concept]}:{self.target_label}{values}"

    def passes(self, tags):
        if self.concept == "year":
            return any(satisfies(y, self.op, self.values) for y in tags["years"])
        if self.concept == "3gpp-release":
            return any(satisfies(r, self.op, self.values) for r in tags["releases"])
        return any(satisfies(v, self.op, self.values, as_version=True) for e, v in tags["versions"] if e == self.entry)


@dataclass
class Parsed:
    raw: str
    concepts: list = field(default_factory=list)
    instances: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    dropped: list = field(default_factory=list)
    error: str = None


def collision_key(text):
    """collisions.json 과 같은 정규화 키: 소문자, 공백·-·_·.·/ 지움."""
    return re.sub(r"[\s\-_./]", "", text.casefold())


class Glossary:
    def __init__(self):
        self.tagger = tagging.GlossaryTagger()
        self.nodes = self.tagger.nodes
        self.children = defaultdict(set)
        for node in self.nodes.values():
            for parent in node.get("parents", []):
                self.children[parent].add(node["id"])
        self.node_by_name = {}
        for node in self.nodes.values():
            for name in [node["id"], node["name"], *node.get("aliases", [])]:
                self.node_by_name.setdefault(name.casefold(), node["id"])
        self.node_matcher = tagging.AliasMatcher({node_id: [{"text": form} for form in [n["name"], *n.get("aliases", [])]]
                                                  for node_id, n in self.nodes.items()})
        self.entries_by_form = defaultdict(set)
        for entry_id, entry in self.tagger.entries.items():
            for form in [entry["canonical"], *(a["text"] for a in entry["aliases"])]:
                self.entries_by_form[collision_key(form)].add(entry_id)

    def concept_surfaces(self, node_id, question):
        return [m["matched"] for m in self.node_matcher.find(question).get(node_id, [])]

    def entries_spelled(self, surface):
        return self.entries_by_form.get(collision_key(surface), set())

    def concept_list(self):
        return "\n".join(f"{n['id']} | {n['name']} | {', '.join(n.get('aliases', []))}" for n in self.nodes.values())

    def resolve_concept(self, item):
        text = str(item.get("id") or item.get("name") or "") if isinstance(item, dict) else str(item)
        node_id = text if text in self.nodes else self.node_by_name.get(text.casefold())
        if node_id is None:
            return None, "unknown"
        if self.nodes[node_id]["kind"] != "concept":
            return None, "value_concept"
        return node_id, None

    def descendant_nodes(self, node_id):
        seen, stack = {node_id}, [node_id]
        while stack:
            for child in self.children[stack.pop()]:
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen

    def entries_under(self, node_id):
        nodes = self.descendant_nodes(node_id)
        return [eid for eid, e in self.tagger.entries.items() if set(e.get("parents", [])) & nodes], len(nodes)

    def entries_named(self, text):
        return [e["id"] for e in self.tagger.tag_text(text)["entries"]]


def claim_tags(glossary, claims):
    """claim 마다 entries·years·releases·versions. 문서마다 한 번 tag_span 하고, 매칭이 claim 구간 안에 다 든 것만 그 claim 에 준다."""
    if CLAIM_TAGS.exists():
        cached = {r["unit_id"]: r for r in arch.read_jsonl(CLAIM_TAGS)}
        if set(cached) == {c["unit_id"] for c in claims.rows}:
            return cached
    by_doc = defaultdict(list)
    for claim in claims.rows:
        by_doc[claim["doc_id"]].append(claim)
    tags = {}
    for doc_id, doc_claims in by_doc.items():
        text = glossary.tagger.docs[doc_id]["text"]
        tagged = glossary.tagger.tag_span(doc_id, 0, len(text))
        values = tagged["values"]
        doc_years = [v["value"] for v in values if v["concept"] == "year" and v["source"] == "doc_date"]
        doc_releases = sorted({v["value"] for v in values if v["concept"] == "3gpp-release"})
        doc_versions = sorted({(v["entry"], v["value"]) for v in values if v["concept"] == "software-version"})
        for claim in doc_claims:
            s, e = claim["start"], claim["end"]
            inside = lambda v: v.get("source") == "body" and s <= v["start"] and v["end"] <= e
            entries = [t["id"] for t in tagged["entries"] if any(s <= m["start"] and m["end"] <= e for m in t["matches"])]
            releases = sorted({v["value"] for v in values if v["concept"] == "3gpp-release" and inside(v)})
            versions = sorted({(v["entry"], v["value"]) for v in values if v["concept"] == "software-version" and inside(v)})
            tags[claim["unit_id"]] = {
                "unit_id": claim["unit_id"], "entries": entries,
                "years": sorted(set(doc_years) | {v["value"] for v in values if v["concept"] == "year" and inside(v)}),
                "releases": releases or doc_releases, "releases_from": "claim" if releases else "doc",
                "versions": [list(p) for p in (versions or doc_versions)], "versions_from": "claim" if versions else "doc"}
    arch.write_jsonl(CLAIM_TAGS, [tags[c["unit_id"]] for c in claims.rows])
    return tags


def parse_reply(text, glossary):
    parsed = Parsed(raw=text)
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        reply = json.loads(body[body.find("{"):body.rfind("}") + 1])
    except json.JSONDecodeError:
        parsed.error = "json"
        return parsed
    for concept in (reply.get("concepts") or [])[:MAX_CONCEPTS]:
        node_id, problem = glossary.resolve_concept(concept)
        if node_id and node_id not in parsed.concepts:
            parsed.concepts.append(node_id)
        elif problem:
            parsed.dropped.append({"concept": concept, "reason": problem})
    parsed.instances = [str(i) for i in (reply.get("instances") or []) if str(i).strip()]
    for raw in reply.get("conditions") or []:
        condition, problem = parse_condition(raw, glossary)
        if condition:
            parsed.conditions.append(condition)
        else:
            parsed.dropped.append({"condition": raw, "reason": problem})
    return parsed


def parse_condition(raw, glossary):
    if not isinstance(raw, dict) or raw.get("concept") not in CONDITION_NAMES or raw.get("op") not in OPS:
        return None, "shape"
    concept, values = raw["concept"], raw.get("values") or []
    if concept == "software-version":
        values = [str(v) for v in values if version_tuple(v)]
        entries = glossary.entries_named(str(raw.get("target", "")))
        if not values:
            return None, "version_value"
        if not entries:
            return None, "version_target_unlinked"
        return Condition(concept, raw["op"], values, entry=entries[0], target_label=glossary.tagger.entries[entries[0]]["canonical"] + " "), None
    try:
        values = [int(str(v)[:4]) if concept == "year" else int(re.sub(r"\D", "", str(v))) for v in values]
    except ValueError:
        return None, "number"
    if not values or (raw["op"] == "between" and len(values) < 2):
        return None, "values"
    return Condition(concept, raw["op"], values), None


def parse_questions(questions, glossary):
    template = PROMPT_PATH.read_text()
    concept_list = glossary.concept_list()
    prompts = [template.replace("{concept_list}", concept_list).replace("{question}", q.question) for q in questions]
    client = ClaudeClient("haiku", max_concurrency=HAIKU_CONCURRENCY)
    replies = client.ask_many(prompts, tag="a2-parse")
    parsed = []
    for prompt, reply in zip(prompts, replies):
        llm = {"calls": 1, **arch.llm_record(client, prompt, DEFAULT_SYSTEM)}
        if isinstance(reply, LLMCallFailed):
            parsed.append((Parsed(raw="", error=f"llm:{str(reply)[:120]}"), llm))
        else:
            parsed.append((parse_reply(reply.text, glossary), llm))
    return parsed, client


class Abstraction:
    def __init__(self, glossary, ctx_units, tags):
        self.glossary = glossary
        self.ctx = ctx_units
        self.tags = tags
        self.claims_of_entry = defaultdict(list)
        for i, unit_id in enumerate(ctx_units.ids):
            for entry_id in tags[unit_id]["entries"]:
                self.claims_of_entry[entry_id].append(i)

    def passing(self, rows, conditions):
        return [i for i in rows if all(c.passes(self.tags[self.ctx.ids[i]]) for c in conditions)]

    def concept_entries(self, node_id, named, question, entry_first):
        """개념 하나가 내는 instance entry 와 그 근거. entry_first 면 질문 속 표면이 모두 entry 이름일 때 펼치지 않고 그 entry 만 둔다."""
        under, node_count = self.glossary.entries_under(node_id)
        record = {"id": node_id, "name": self.glossary.nodes[node_id]["name"], "nodes": node_count, "entries": len(under)}
        if entry_first:
            surfaces = self.glossary.concept_surfaces(node_id, question)
            spelled = [self.glossary.entries_spelled(s) for s in surfaces]
            record["surfaces"] = surfaces
            if surfaces and all(spelled):
                kept = sorted(set().union(*spelled))
                record.update(rule="collision_kept_entry", narrowed_to=[])
                return kept, record
            record["rule"] = "expand_free_surface" if surfaces else "expand_no_surface"
        narrowed = sorted(named & set(under))
        record["narrowed_to"] = narrowed
        return narrowed or under, record

    def lanes(self, parsed, question, qvec, condition_stages, entry_first):
        """펼친 instance 마다 상위 PER_INSTANCE 개, 1위 점수 순으로 번갈아 담은 단위와 trace."""
        named = {eid for text in parsed.instances for eid in self.glossary.entries_named(text)}
        trace = {"concepts": [], "lanes": []}
        lane_entries = {}
        for node_id in parsed.concepts:
            chosen, record = self.concept_entries(node_id, named, question, entry_first)
            trace["concepts"].append(record)
            for eid in chosen:
                lane_entries.setdefault(eid, node_id)
        lanes = []
        for eid, node_id in lane_entries.items():
            tagged = self.claims_of_entry.get(eid, [])
            allowed = self.passing(tagged, parsed.conditions)
            stages = (f"abstraction={self.glossary.nodes[node_id]['name']}", f"glossary={self.glossary.tagger.entries[eid]['canonical']}", *condition_stages)
            ranked = [self.ctx.as_unit(i, s, arch.path(*stages, unit="claim")) for i, s in self.ctx.search(qvec, among=allowed, top=PER_INSTANCE)] if allowed else []
            lanes.append(ranked)
            trace["lanes"].append({"entry": eid, "tagged": len(tagged), "allowed": len(allowed), "taken": len(ranked)})
        lanes.sort(key=lambda lane: -lane[0]["score"] if lane else 0.0)
        interleaved = [lane[r] for r in range(PER_INSTANCE) for lane in lanes if len(lane) > r]
        trace["instances"] = len(lane_entries)
        trace["empty_instances"] = sum(1 for lane in trace["lanes"] if lane["taken"] == 0)
        trace["named_entries"] = sorted(named)
        return interleaved, trace

    def condition_units(self, parsed, qvec, condition_stages):
        allowed = self.passing(range(len(self.ctx)), parsed.conditions)
        return self.ctx.dense_units(qvec, path_stages=condition_stages, among=allowed, top=DEPTH) if allowed else [], len(allowed)

    def retrieve(self, parsed, question, qvec, variant):
        condition_stages = tuple(f"abstraction={c.label}" for c in parsed.conditions)
        cues = listing_cues(question)
        expand = variant.expand and (cues or not variant.cue_only)
        trace = {"expand": bool(expand), "entry_first": variant.entry_first, "mix": variant.mix, "listing_cues": cues}
        lane_units = []
        if expand and parsed.concepts:
            lane_units, trace["expansion"] = self.lanes(parsed, question, qvec, condition_stages, variant.entry_first)
        condition_units, trace["condition_allowed"] = self.condition_units(parsed, qvec, condition_stages) if parsed.conditions else ([], None)
        fill = self.ctx.dense_units(qvec, path_stages=(FILL_PATH_STAGE,), top=DEPTH)
        if variant.mix == "rrf" and lane_units:
            ranked = arch.rrf(condition_units + fill, lane_units)
        else:
            ranked = lane_units + condition_units + fill
        kept = arch.fill_budget(ranked)
        trace["stage_units"] = {"lanes": sum(u["path"].startswith("abstraction=") and ">glossary=" in u["path"] for u in kept),
                                "condition": sum(u["path"].startswith("abstraction=") and ">glossary=" not in u["path"] for u in kept),
                                "fill": sum(u["path"].startswith("fallback=") for u in kept)}
        trace["fallback_reasons"] = [reason for reason, applies in (("no_concept", expand and not parsed.concepts),
                                                                    ("no_condition", not parsed.conditions),
                                                                    ("fill", trace["stage_units"]["fill"] > 0)) if applies]
        trace["path_fallback"] = not lane_units and not condition_units
        return kept, trace


def parsed_trace(parsed):
    return {"raw": parsed.raw, "error": parsed.error, "concepts": parsed.concepts, "instances": parsed.instances,
            "conditions": [{"concept": c.concept, "op": c.op, "values": c.values, "entry": c.entry, "label": c.label} for c in parsed.conditions],
            "dropped": parsed.dropped}


def run():
    started = time.monotonic()
    questions = arch.read_questions()
    qvecs = arch.embed_questions(questions)
    glossary = Glossary()
    ctx, _ = b2.claim_ctx_units()
    tags = claim_tags(glossary, ctx)
    abstraction = Abstraction(glossary, ctx, tags)
    parsed_all, client = parse_questions(questions, glossary)
    out = arch.Run(RUN_NAME)
    for variant in VARIANTS:
        for q, qvec, (parsed, llm) in zip(questions, qvecs, parsed_all):
            units, trace = abstraction.retrieve(parsed, q.question, qvec, variant)
            out.add(q.qid, variant.name, units, parsed=parsed_trace(parsed), llm=llm, **trace)
    out.write()
    print(out.score())
    report = {"seconds": round(time.monotonic() - started, 1), "llm": client.stats.snapshot(), "usage": client.usage_line(),
              "embed_stats": embed_client.stats, "gold_sha256": arch.sha256_of(arch.GOLD),
              "glossary_sha256": arch.sha256_of(tagging.GLOSSARY_DIR / "glossary.json"),
              "hierarchy_sha256": arch.sha256_of(tagging.GLOSSARY_DIR / "hierarchy.json"),
              "prompt_sha256": arch.sha256_of(PROMPT_PATH)}
    (RUN_DIR / "run-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(report["usage"])


CLAIM_CTX_DIR = arch.RUNS / "23-arch-b2-mix"
CLAIM_CTX_VARIANT = "claim-ctx"
HEADLINE_MODES = ("2500자", "5000자")


def same_units(a, b):
    return [(u["doc_id"], u["start"], u["end"]) for u in a] == [(u["doc_id"], u["start"], u["end"]) for u in b]


def hierarchy_worked(variant):
    """개념을 뽑은 문항, 펼친 단위가 담긴 문항, 결과가 claim-ctx 와 달라진 문항과 그 문항들의 claim-ctx 대비 승패."""
    mine = {r["qid"]: r["units"] for r in arch.read_jsonl(RUN_DIR / "retrieval.jsonl") if r["variant"] == variant}
    base = {r["qid"]: r["units"] for r in arch.read_jsonl(CLAIM_CTX_DIR / "retrieval.jsonl") if r["variant"] == CLAIM_CTX_VARIANT}
    traces = {t["qid"]: t for t in arch.read_jsonl(RUN_DIR / "trace.jsonl") if t["variant"] == variant}
    scored = {q for q, _ in arch.read_detail(RUN_DIR, variant)}
    detail, base_detail = arch.read_detail(RUN_DIR, variant), arch.read_detail(CLAIM_CTX_DIR, CLAIM_CTX_VARIANT)
    groups = {
        "개념을 뽑음": [q for q, t in traces.items() if t["parsed"]["concepts"]],
        "펼친 단위가 담김": [q for q, t in traces.items() if t["stage_units"]["lanes"]],
        "조건을 뽑음": [q for q, t in traces.items() if t["parsed"]["conditions"]],
        "조건 단위가 담김": [q for q, t in traces.items() if t["stage_units"]["condition"]],
        "결과가 claim-ctx 와 다름": [q for q in mine if not same_units(mine[q], base[q])],
        "개념도 조건도 없음 (claim-ctx 그대로)": [q for q, t in traces.items() if t["path_fallback"]],
    }
    lines = ["| 묶음 | 문항(250) | 근거 있는 문항 | " + " | ".join(f"claim-ctx 대비 {m}" for m in HEADLINE_MODES) + " |", "|---|---|---|" + "---|" * len(HEADLINE_MODES)]
    sign_test = arch._scorer().sign_test
    for name, qids in groups.items():
        graded = [q for q in qids if q in scored]
        cells = []
        for mode in HEADLINE_MODES:
            diffs = [detail[q, mode]["recall"] - base_detail[q, mode]["recall"] for q in graded]
            wins, losses = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            cells.append(f"{wins}승 {losses}패 (p={sign_test(wins, losses):.2f})")
        lines.append(f"| {name} | {len(qids)} | {len(graded)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def per_question(variant, qids=None):
    questions = {q.qid: q.question for q in arch.read_questions()}
    types = arch._question_groups("type")
    traces = {t["qid"]: t for t in arch.read_jsonl(RUN_DIR / "trace.jsonl") if t["variant"] == variant}
    detail, base_detail = arch.read_detail(RUN_DIR, variant), arch.read_detail(CLAIM_CTX_DIR, CLAIM_CTX_VARIANT)
    rows = []
    for qid, t in traces.items():
        if qids is not None and qid not in qids:
            continue
        if not t["parsed"]["concepts"] and not t["parsed"]["conditions"] and qids is None:
            continue
        recall = lambda d, m: round(d[qid, m]["recall"], 3) if (qid, m) in d else None
        rows.append({"qid": qid, "type": types[qid], "question": questions[qid],
                     "concepts": [c["name"] + f"({c['entries']})" for c in t.get("expansion", {}).get("concepts", [])] or t["parsed"]["concepts"],
                     "conditions": [c["label"] for c in t["parsed"]["conditions"]], "stage_units": t["stage_units"],
                     "empty_instances": t.get("expansion", {}).get("empty_instances"),
                     **{f"{m} mine": recall(detail, m) for m in HEADLINE_MODES}, **{f"{m} ctx": recall(base_detail, m) for m in HEADLINE_MODES}})
    return rows


def report():
    parts = []
    for variant in (v.name for v in VARIANTS):
        parts += [f"## {variant}", arch.type_table(RUN_DIR, variant), arch.type_table(RUN_DIR, variant, by="lang"),
                  f"### {variant} 대 claim-ctx", arch.compare_table(RUN_DIR, variant, CLAIM_CTX_DIR, CLAIM_CTX_VARIANT),
                  arch.compare_table(RUN_DIR, variant, CLAIM_CTX_DIR, CLAIM_CTX_VARIANT, by="lang"),
                  f"### {variant} 대 B0", arch.compare_table(RUN_DIR, variant), arch.compare_table(RUN_DIR, variant, by="lang"),
                  f"### {variant} path", arch.path_table(RUN_DIR, variant), json.dumps(arch.trace_summary(RUN_DIR, variant), ensure_ascii=False),
                  f"### {variant} 계층이 일했나", hierarchy_worked(variant)]
    for mine, base in ((RUN_NAME, CONDITION_ONLY), (ENTRY_FIRST, CONDITION_ONLY), (ENTRY_FIRST, RUN_NAME),
                       (f"{RUN_NAME}-rrf", CONDITION_ONLY), (f"{RUN_NAME}-percue", CONDITION_ONLY), (f"{RUN_NAME}-percue", ENTRY_FIRST)):
        parts += [f"## {mine} 대 {base}", arch.compare_table(RUN_DIR, mine, RUN_DIR, base), arch.compare_table(RUN_DIR, mine, RUN_DIR, base, by="lang")]
    print("\n\n".join(parts))
    arch.write_jsonl(RUN_DIR / "per-question.jsonl", per_question(RUN_NAME))
    arch.write_jsonl(RUN_DIR / "per-question-entryfirst.jsonl", per_question(ENTRY_FIRST))


if __name__ == "__main__":
    commands = {"run": run, "report": report}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(2)
    commands[sys.argv[1]]()
