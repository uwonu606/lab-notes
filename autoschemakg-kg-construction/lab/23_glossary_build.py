"""네트워크 말뭉치 용어집을 단계별로 만든다. 단계마다 결과를 runs/23-glossary/ 에 남기고 다음 단계가 읽는다.

    python3 23_glossary_build.py extract     # Haiku: 청크마다 용어 후보, 코드가 원문 글자 확인
    python3 23_glossary_build.py aggregate   # 코드: 후보를 정규화 키로 모으고 말뭉치 등장 문서 수를 센다
    python3 23_glossary_build.py curate      # Opus: 분야 묶음마다 후보를 항목으로 묶고 버린다
    python3 23_glossary_build.py merge       # 코드가 겹치는 항목 쌍을 내고 Opus 가 합칠지 정한다
    python3 23_glossary_build.py hierarchy   # Opus: 개념 노드를 세우고 항목마다 부모를 단다
    python3 23_glossary_build.py finalize    # glossary.json, hierarchy.json, CURATION.md 를 쓴다
"""
import argparse
import hashlib
import importlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

LAB = Path(__file__).parent
sys.path.insert(0, str(LAB))
from llm_cache import ClaudeClient, LLMCallFailed, usage_line  # noqa: E402

fixed_spans = importlib.import_module("23_chunk_docs").fixed_spans

DOCS = LAB / "inputs/net-corpus/docs.jsonl"
WORK = LAB / "runs/23-glossary"
OUT = LAB / "inputs/net-corpus/glossary"
CHUNK_SIZE = 3000

DOMAINS = [
    "5g-core", "ran", "ue-sim-test-tool", "routing", "transport-l2-optical", "kubernetes-cloud-linux",
    "security-auth", "standards-org", "operator", "vendor-company", "test-event", "oss-project", "general-it",
]

EXTRACT_SYSTEM = "You extract glossary candidate terms from network engineering documents. Reply with a JSON array only."

EXTRACT_PROMPT = """Below is one chunk of a document from a network verification corpus (5G core/RAN issues, routing daemons, interop test reports, Korean blog posts).

List every term a network verification team would want in a shared glossary. Include:
- acronyms and abbreviations (AMF, PFCP, NGAP, TI-LFA, S-NSSAI)
- network functions, components, interfaces, reference points (UPF, gNB, N2, N3, Xn)
- protocols, messages, procedures, states, cause values (NG Setup, PDU Session Establishment, ExStart, Hold Timer Expired, MAC failure)
- configuration options and well-known parameters only if they name a concept (mtu-ignore, graceful-restart, SQN)
- products, open-source projects, tools, vendors, operators, standards bodies, specs and RFC numbers, test events (Open5GS, FRR, Nokia, SKT, 3GPP, TS 23.501, RFC 5549, EANTC, PlugFest)
- Korean translations and Korean in-house or colloquial expressions for technical things (세션 수립, 인접 관계, 블랙홀, 붙지 못함)
Exclude: people and user names, IP addresses, file paths, URLs, pure numbers, code identifiers that only appear in a stack trace, and plain everyday words.

For each term return an object:
{{"term": exact substring copied from the chunk (same spelling and case),
  "kind": one of "acronym", "name", "technical", "korean", "jargon",
  "expansion": the full form or English equivalent ONLY if the chunk itself states it (copy it exactly), else "",
  "domain": one of {domains},
  "generic": true if it is a broad everyday IT word (log, server, error, PDF, docker image, LLM), else false}}

Document title: {title}
<chunk>
{text}
</chunk>"""


def load_docs():
    return [json.loads(line) for line in DOCS.read_text().splitlines() if line.strip()]


def chunks_of(docs):
    for doc in docs:
        for number, (start, end) in enumerate(fixed_spans(doc["text"], CHUNK_SIZE)):
            yield {"id": f"{doc['doc_id']}#{number:03d}", "doc_id": doc["doc_id"], "title": doc["title"],
                   "start": start, "end": end, "text": doc["text"][start:end]}


def parse_json_array(text):
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise ValueError("no JSON array")
    return json.loads(match.group(0))


def parse_json_object(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON object")
    return json.loads(match.group(0))


def collapse_space(text):
    return re.sub(r"\s+", " ", text).strip()


def extract(args):
    WORK.mkdir(parents=True, exist_ok=True)
    chunks = list(chunks_of(load_docs()))
    if args.limit:
        chunks = chunks[:args.limit]
    client = ClaudeClient("haiku", max_concurrency=args.concurrency)
    prompts = [EXTRACT_PROMPT.format(domains=", ".join(DOMAINS), title=c["title"], text=c["text"]) for c in chunks]
    started = time.monotonic()
    replies = client.ask_many(prompts, system=EXTRACT_SYSTEM, tag="extract")
    rows, failures, unverified = [], 0, 0
    for chunk, reply in zip(chunks, replies):
        if isinstance(reply, LLMCallFailed):
            failures += 1
            continue
        try:
            items = parse_json_array(reply.text)
        except (ValueError, json.JSONDecodeError):
            failures += 1
            continue
        squashed = collapse_space(chunk["text"])
        for item in items:
            if not isinstance(item, dict) or not str(item.get("term", "")).strip():
                continue
            term = collapse_space(str(item["term"]))
            verbatim = term in squashed
            unverified += not verbatim
            expansion = collapse_space(str(item.get("expansion") or ""))
            rows.append({"chunk": chunk["id"], "doc_id": chunk["doc_id"], "term": term, "verbatim": verbatim,
                         "kind": item.get("kind", ""), "domain": item.get("domain", ""), "generic": bool(item.get("generic")),
                         "expansion": expansion, "expansion_verbatim": bool(expansion) and expansion in squashed})
    (WORK / "candidates.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    summary = {"chunks": len(chunks), "chunk_size": CHUNK_SIZE, "failed_chunks": failures, "mentions": len(rows),
               "unverified_mentions": unverified, "wall_seconds": round(time.monotonic() - started),
               "usage": client.stats.snapshot()}
    (WORK / "extract-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"청크 {len(chunks)} · 실패 {failures} · 후보 언급 {len(rows)} · 원문에 없는 언급 {unverified}")
    print(client.usage_line())


def candidate_key(term):
    return re.sub(r"[\s\-_./]+", "", unicodedata.normalize("NFKC", term).casefold())


MAX_TERM_LENGTH = 60
MIN_DOCS = 2


def aggregate(args):
    docs = load_docs()
    rows = [json.loads(line) for line in (WORK / "candidates.jsonl").read_text().splitlines()]
    groups = defaultdict(lambda: {"surfaces": Counter(), "kinds": Counter(), "domains": Counter(), "generic": 0,
                                  "mentions": 0, "docs": set(), "expansions": Counter()})
    dropped = Counter()
    for row in rows:
        if not row["verbatim"]:
            dropped["원문에 없음"] += 1
            continue
        if len(row["term"]) > MAX_TERM_LENGTH or not re.search(r"[A-Za-z가-힣]", row["term"]):
            dropped["너무 길거나 글자 없음"] += 1
            continue
        group = groups[candidate_key(row["term"])]
        group["surfaces"][row["term"]] += 1
        group["kinds"][row["kind"]] += 1
        group["domains"][row["domain"]] += 1
        group["generic"] += row["generic"]
        group["mentions"] += 1
        group["docs"].add(row["doc_id"])
        if row["expansion_verbatim"] and candidate_key(row["expansion"]) != candidate_key(row["term"]):
            group["expansions"][row["expansion"]] += 1

    tagger_module = importlib.import_module("23_glossary_tag")
    matcher = tagger_module.AliasMatcher({key: [{"text": s} for s in g["surfaces"]] for key, g in groups.items()})
    corpus_docs = defaultdict(set)
    first_context = {}
    for doc in docs:
        for key, matches in matcher.find(doc["text"]).items():
            corpus_docs[key].add(doc["doc_id"])
            if key not in first_context:
                m = matches[0]
                first_context[key] = (doc["doc_id"], collapse_space(doc["text"][max(0, m["start"] - 70):m["end"] + 70]))

    kept = []
    for key, g in groups.items():
        corpus_df = len(corpus_docs.get(key, ()))
        if len(g["docs"]) < MIN_DOCS and corpus_df < MIN_DOCS:
            dropped[f"추출 문서·말뭉치 문서 모두 {MIN_DOCS} 미만"] += 1
            continue
        kept.append({"key": key, "surfaces": g["surfaces"].most_common(5), "kinds": g["kinds"].most_common(2),
                     "domain": g["domains"].most_common(1)[0][0], "generic_votes": g["generic"], "mentions": g["mentions"],
                     "extract_docs": len(g["docs"]), "corpus_docs": corpus_df, "expansions": g["expansions"].most_common(3),
                     "context": first_context.get(key)})
    kept.sort(key=lambda c: (c["domain"], -c["corpus_docs"]))
    for number, candidate in enumerate(kept):
        candidate["cid"] = f"c{number:05d}"
    (WORK / "aggregated.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in kept))
    summary = {"mentions": len(rows), "distinct_keys": len(groups), "kept": len(kept), "dropped": dict(dropped),
               "kept_by_domain": Counter(c["domain"] for c in kept)}
    (WORK / "aggregate-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


ENTRY_TYPES = ["network-function", "ran-component", "interface", "protocol", "procedure-message", "state-cause", "parameter",
               "mechanism-feature", "spec-standard", "organization", "operator", "vendor", "software", "test-event",
               "failure-symptom", "concept"]

CURATOR_SYSTEM = """You are the human glossary curator of a Samsung network verification department (5G core/RAN, IP routing, interop testing). Engineers write issues and reports in English and Korean with inconsistent terminology. The glossary you curate is used to link documents that talk about the same thing and to map search questions onto entries. Wrong merges and generic hub entries hurt linking precision more than a missing entry. Reply with one JSON object only."""

CURATE_PROMPT = """Here are glossary candidates an assistant model extracted from the corpus. Each line:
id | surface forms ×count | docs: documents whose text contains a surface form (extracted in N) | kind | stated expansion | generic votes/mentions | one context

Decide for every candidate id. Group candidates that name the same referent into one entry; drop the rest.

Rules
- One entry = one referent. Do not merge related but different things (AMF vs AMF selection, NG Setup Request vs NG Setup Failure can be one entry only if the corpus uses them as one topic; prefer the procedure as the entry and message names as aliases when they are the same procedure).
- Aliases: surface variants seen, the English full form, the acronym, and the Korean term(s) Korean engineers actually write (e.g. 세션 관리 기능, 인접 관계). Do not invent rare spellings. Mark each alias with kind: "variant" | "expansion" | "acronym" | "korean" | "jargon". Add "case_sensitive": true to an alias of 4+ letters only when lowercase or other-case occurrences would mean something else (e.g. BIRD the daemon vs bird).
- Ambiguous acronyms (PCC = Path Computation Client / Policy and Charging Control): make one entry per meaning that occurs in this corpus, both may list the acronym, and write ambiguity_note naming the other meanings.
- Mark "common": true for terms that would connect unrelated documents (log, server, error, config, Docker, Linux, PDF, LLM, IP address, kernel). Keep them as entries only if engineers would still look them up; otherwise discard.
- Discard: people/user names, code identifiers and file names that only matter inside one stack trace, sentence fragments, pure numbers, plain words.
- type: one of {types}.
- definition: one line in Korean.
- versioned: true for software whose version numbers matter (open5gs, free5GC, FRR, srsRAN, Linux kernel modules like gtp5g).

Output JSON:
{{"entries": [{{"canonical": "...", "type": "...", "members": ["c00012", ...], "aliases": [{{"text": "...", "kind": "..."}}], "definition": "...", "ambiguity_note": "", "common": false, "versioned": false}}],
  "discard": [{{"members": ["c00099", ...], "reason": "generic|person|fragment|code-identifier|number|other"}}]}}
Every id must appear exactly once across entries.members and discard.members. Do not repeat the canonical name inside aliases.

Candidates ({domain}, {count}):
{lines}"""

BATCH_SIZE = 120
SINGLE_DOC_KINDS = {"korean", "acronym", "jargon", "name"}


def for_curator(candidates):
    return [c for c in candidates if c["extract_docs"] >= MIN_DOCS or (c["kinds"] and c["kinds"][0][0] in SINGLE_DOC_KINDS)]


def candidate_line(c):
    surfaces = ", ".join(f"{s} ×{n}" for s, n in c["surfaces"])
    expansions = "; ".join(e for e, _ in c["expansions"]) or "-"
    context = c["context"][1][:150] if c["context"] else "-"
    kind = c["kinds"][0][0] if c["kinds"] else "-"
    return (f"{c['cid']} | {surfaces} | docs {c['corpus_docs']} (extracted in {c['extract_docs']}) | {kind} | {expansions} | "
            f"generic {c['generic_votes']}/{c['mentions']} | {context}")


def curation_batches(candidates):
    by_domain = defaultdict(list)
    for c in candidates:
        by_domain[c["domain"] if c["domain"] in DOMAINS else "general-it"].append(c)
    batches = []
    for domain, items in sorted(by_domain.items()):
        items.sort(key=lambda c: c["key"])
        count = -(-len(items) // BATCH_SIZE)
        size = -(-len(items) // count)
        for index in range(count):
            batches.append((f"{domain}-{index}", domain, items[index * size:(index + 1) * size]))
    return batches


def curate(args):
    candidates = for_curator([json.loads(line) for line in (WORK / "aggregated.jsonl").read_text().splitlines()])
    batches = curation_batches(candidates)
    client = ClaudeClient("opus", max_concurrency=args.concurrency, timeout=1800.0)
    prompts = [CURATE_PROMPT.format(types=", ".join(ENTRY_TYPES), domain=domain, count=len(items),
                                    lines="\n".join(candidate_line(c) for c in items)) for _, domain, items in batches]
    started = time.monotonic()
    replies = client.ask_many(prompts, system=CURATOR_SYSTEM, tag="curate")
    results, problems = [], []
    for (name, domain, items), reply in zip(batches, replies):
        if isinstance(reply, LLMCallFailed):
            problems.append(f"{name}: 호출 실패")
            continue
        try:
            decision = parse_json_object(reply.text)
        except (ValueError, json.JSONDecodeError) as error:
            problems.append(f"{name}: JSON 실패 {error}")
            continue
        asked = {c["cid"] for c in items}
        placed = [m for e in decision.get("entries", []) for m in e.get("members", [])]
        placed += [m for d in decision.get("discard", []) for m in d.get("members", [])]
        results.append({"batch": name, "domain": domain, "asked": sorted(asked), "decision": decision,
                        "unhandled": sorted(asked - set(placed)), "unknown_ids": sorted(set(placed) - asked),
                        "duplicated_ids": sorted(m for m, n in Counter(placed).items() if n > 1)})
    (WORK / "curated.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    summary = {"candidates": len(candidates), "batches": len(batches), "problems": problems, "wall_seconds": round(time.monotonic() - started),
               "usage": client.stats.snapshot()}
    (WORK / "curate-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    entries = sum(len(r["decision"].get("entries", [])) for r in results)
    unhandled = sum(len(r["unhandled"]) for r in results)
    print(f"묶음 {len(batches)} · 문제 {problems} · 항목 {entries} · 판단 없는 후보 {unhandled}")
    print(client.usage_line())


MERGE_PROMPT = """Glossary entries were curated in separate batches, so the same referent may now be two entries, and two different referents may share an alias. For each numbered pair below decide:
- "merge": same referent. Give keep_canonical (the name engineers would search for).
- "separate": different referents. Give shared_alias_owner: "a", "b" or "both" (both = the shared text really is used for both, e.g. an ambiguous acronym), and a short ambiguity_note when both keep it.

Output JSON: {{"decisions": [{{"pair": 1, "action": "merge", "keep_canonical": "..."}}, {{"pair": 2, "action": "separate", "shared_alias_owner": "both", "ambiguity_note": "..."}}]}}
Decide every pair.

{pairs}"""

MERGE_BATCH = 70
STOPWORDS = {"and", "of", "the", "for", "to", "in", "on", "a", "an", "with"}


def curated_entries():
    entries = []
    for result in json.loads((WORK / "curated.json").read_text()):
        for index, entry in enumerate(result["decision"].get("entries", [])):
            aliases = [a if isinstance(a, dict) else {"text": str(a), "kind": "variant"} for a in entry.get("aliases", [])]
            aliases = [a for a in aliases if a.get("text", "").strip() and a["text"].strip() != entry["canonical"]]
            entries.append(dict(entry, aliases=aliases, tmp=f"{result['batch']}:{index}"))
    return entries


def surface_keys(entry):
    return {candidate_key(entry["canonical"])} | {candidate_key(a["text"]) for a in entry["aliases"]}


def initials(text):
    words = [w for w in re.split(r"[\s\-/]+", text) if w]
    if len(words) < 2:
        return set()
    return {"".join(w[0] for w in words).upper(), "".join(w[0] for w in words if w.lower() not in STOPWORDS).upper()}


def acronyms(entry):
    forms = [entry["canonical"]] + [a["text"] for a in entry["aliases"]]
    return {f for f in forms if re.fullmatch(r"[A-Z][A-Z0-9]{1,6}", f)}


def merge_pairs(entries):
    by_key = defaultdict(set)
    by_initials = defaultdict(set)
    for index, entry in enumerate(entries):
        for key in surface_keys(entry):
            if key:
                by_key[key].add(index)
        for form in [entry["canonical"]] + [a["text"] for a in entry["aliases"]]:
            for initial in initials(form):
                by_initials[initial].add(index)
    pairs = set()
    for owners in by_key.values():
        for a in owners:
            for b in owners:
                if a < b:
                    pairs.add((a, b, "shared alias"))
    for index, entry in enumerate(entries):
        for acronym in acronyms(entry):
            for other in by_initials.get(acronym, ()):
                if other != index:
                    pairs.add((min(index, other), max(index, other), "acronym matches initials"))
    unique = {}
    for a, b, why in sorted(pairs):
        unique.setdefault((a, b), why)
    return [(a, b, why) for (a, b), why in unique.items()]


def entry_brief(entry):
    aliases = ", ".join(a["text"] for a in entry["aliases"][:12])
    return f"{entry['canonical']} [{entry.get('type', '')}] aliases: {aliases or '-'} — {entry.get('definition', '')}"


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, a, b):
        self.parent[self.find(b)] = self.find(a)


def merge(args):
    entries = curated_entries()
    pairs = merge_pairs(entries)
    client = ClaudeClient("opus", max_concurrency=args.concurrency, timeout=1800.0)
    batches = [pairs[i:i + MERGE_BATCH] for i in range(0, len(pairs), MERGE_BATCH)]
    prompts = []
    for batch in batches:
        text = "\n\n".join(f"Pair {n} ({why})\n a: {entry_brief(entries[a])}\n b: {entry_brief(entries[b])}"
                           for n, (a, b, why) in enumerate(batch, 1))
        prompts.append(MERGE_PROMPT.format(pairs=text))
    started = time.monotonic()
    replies = client.ask_many(prompts, system=CURATOR_SYSTEM, tag="merge")
    decisions, problems = [], []
    for batch, reply in zip(batches, replies):
        if isinstance(reply, LLMCallFailed):
            problems.append("호출 실패")
            continue
        try:
            answer = {d["pair"]: d for d in parse_json_object(reply.text).get("decisions", [])}
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as error:
            problems.append(f"JSON 실패 {error}")
            continue
        for n, (a, b, why) in enumerate(batch, 1):
            decision = answer.get(n, {"action": "undecided"})
            decisions.append({"a": entries[a]["tmp"], "b": entries[b]["tmp"], "a_name": entries[a]["canonical"],
                              "b_name": entries[b]["canonical"], "why": why, **decision})
    (WORK / "merge-decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=1))
    summary = {"entries_before": len(entries), "pairs": len(pairs), "problems": problems,
               "actions": Counter(d.get("action") for d in decisions), "wall_seconds": round(time.monotonic() - started),
               "usage": client.stats.snapshot()}
    (WORK / "merge-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "usage"}, ensure_ascii=False))
    print(client.usage_line())


def merged_entries():
    entries = curated_entries()
    index_of = {e["tmp"]: i for i, e in enumerate(entries)}
    union = UnionFind(len(entries))
    keep_name = {}
    alias_drop = defaultdict(set)
    notes = defaultdict(list)
    for d in json.loads((WORK / "merge-decisions.json").read_text()):
        a, b = index_of[d["a"]], index_of[d["b"]]
        if d.get("action") == "merge":
            union.union(a, b)
            if d.get("keep_canonical"):
                keep_name[union.find(a)] = d["keep_canonical"]
        elif d.get("action") == "separate":
            shared = surface_keys(entries[a]) & surface_keys(entries[b])
            owner = d.get("shared_alias_owner", "both")
            if owner == "a":
                alias_drop[b] |= shared
            elif owner == "b":
                alias_drop[a] |= shared
            elif d.get("ambiguity_note"):
                notes[a].append(d["ambiguity_note"])
                notes[b].append(d["ambiguity_note"])
    groups = defaultdict(list)
    for i in range(len(entries)):
        groups[union.find(i)].append(i)
    merged = []
    for root, members in groups.items():
        base = dict(entries[members[0]])
        canonical = keep_name.get(root, base["canonical"])
        named = [i for i in members if entries[i]["canonical"] == canonical]
        if named:
            base = dict(entries[named[0]])
        forms = []
        for i in members:
            forms += [{"text": entries[i]["canonical"], "kind": "variant"}] + entries[i]["aliases"]
        seen, aliases = {canonical.casefold()}, []
        dropped = set().union(*(alias_drop[i] for i in members))
        for form in forms:
            text = form["text"].strip()
            if text.casefold() in seen or (candidate_key(text) in dropped and candidate_key(text) != candidate_key(canonical)):
                continue
            seen.add(text.casefold())
            aliases.append({k: v for k, v in form.items() if k in ("text", "kind", "case_sensitive")})
        note_parts = [entries[i].get("ambiguity_note", "") for i in members] + [n for i in members for n in notes[i]]
        base.update(canonical=canonical, aliases=aliases,
                    members=sorted({m for i in members for m in entries[i].get("members", [])}),
                    ambiguity_note=" / ".join(dict.fromkeys(n for n in note_parts if n)),
                    common=any(entries[i].get("common") for i in members),
                    versioned=any(entries[i].get("versioned") for i in members),
                    merged_from=[entries[i]["tmp"] for i in members])
        merged.append(base)
    return merged


SEED_CONCEPTS = """연도(값으로 정해짐, 코드가 채운다 — 노드로 만들지 않는다), 통신사(SKT·KT·LG U+·Verizon·…), 벤더(Nokia·Ericsson·Huawei·Samsung·…), 5G NF(AMF·SMF·UPF·…), 프로토콜·인터페이스(NGAP·PFCP·GTP-U·BGP·OSPF·…), 계층(제어 평면·사용자 평면·전송망), 장애 유형(세션 수립 실패·인접 관계 실패·크래시·성능 저하·…), 시험 행사(PlugFest·Plugtests·EANTC), 표준 기구, 오픈소스 프로젝트"""

NODES_PROMPT = """Design the abstraction layer above a network-verification glossary. Concept nodes sit above entries; an entry can have several parents, and nodes can have parent nodes (several levels allowed, keep it to what the entries need). Users will ask questions like "통신사별 장애 이슈", "벤더별 상호운용 결과", "5G NF 중 등록 절차에 관여하는 것", "제어 평면 장애", so a node must be a category a person would name in a question.

Seed concepts from the department (keep them, refine or split as the entries require): {seeds}

Rules
- Do not create a node for a single entry, and do not create year or version nodes (code fills those from dates).
- Nodes are categories, not topics: "operator", "routing protocol", "session establishment failure", "control plane".
- Failure types should be usable across 5G core, RAN and routing (e.g. registration/authentication failure, session establishment failure, adjacency/peering failure, crash, performance degradation, packet loss/blackhole, configuration mismatch, interop failure).
- id: lowercase ascii slug. name: Korean name. aliases: English and Korean names people use for the category (통신사: operator, carrier, 이동통신사, 이통사). description: one line in Korean.

Output JSON: {{"nodes": [{{"id": "operator", "name": "통신사", "aliases": ["operator", "carrier", "이동통신사"], "parents": [], "description": "..."}}]}}

Entries ({count}, "canonical [type]"):
{entries}"""

ASSIGN_PROMPT = """Assign parent concept nodes to glossary entries. Use node ids from the list. An entry may have several parents (AMF: 5g-nf and control-plane). Give [] when no node fits; do not force generic entries into a category. Failure-symptom entries and cause values should get the failure-type node(s) they belong to. If a clearly needed category is missing, you may propose it in new_nodes (same fields as the list) and use it.

Output JSON: {{"assign": {{"entry-id": ["node-id", ...]}}, "new_nodes": []}}
Assign every entry id below.

Nodes (id | name | parents | description):
{nodes}

Entries (id | canonical | type | definition):
{entries}"""

ASSIGN_BATCH = 150

VALUE_NODES = [
    {"id": "year", "name": "연도", "aliases": ["year", "연도", "년도"], "parents": [], "kind": "value-range",
     "description": "문서·구간이 다루는 해. 값은 코드가 문서 메타와 본문 날짜에서 채운다.",
     "rule": "문서 메타 date 의 앞 네 자리(source=doc_date). 본문에서는 1980~말뭉치 최신 연도의 네 자리 수 가운데 뒤에 '년' 이 붙거나, 뒤에 -MM·/MM 이 오거나, 앞 12자 안에 월 이름·in/since/from/until/by/of/year/during/©/copyright·'-'·'/' 가 있는 것(source=body). 포트 번호(2152)처럼 이 조건이 없는 수는 버린다."},
    {"id": "3gpp-release", "name": "3GPP Release", "aliases": ["Release", "Rel", "릴리스"], "parents": ["standards"], "kind": "value-range",
     "description": "3GPP 규격 릴리스 번호.",
     "rule": "본문의 '(3GPP )Release NN', 'Rel-NN', 'Rel.NN', 'Rel NN' 에서 NN(8~21)."},
    {"id": "software-version", "name": "소프트웨어 버전", "aliases": ["version", "버전", "릴리스 버전"], "parents": [], "kind": "value-range",
     "description": "버전이 의미 있는 소프트웨어 항목(versioned=true) 바로 뒤에 붙은 버전 문자열.",
     "rule": "versioned 항목의 별칭 매칭 끝에서 24자 안, 줄바꿈·쉼표·세미콜론을 건너지 않고 처음 나오는 v?N.N(.N)(-rcN) 꼴. 값과 함께 어느 항목의 버전인지(entry)를 낸다."},
]


def slug(text):
    ascii_part = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()).strip("-")
    return ascii_part or re.sub(r"\s+", "-", text.strip())


def entries_with_ids():
    entries = merged_entries()
    entries.sort(key=lambda e: (e.get("type", ""), e["canonical"].casefold()))
    used = Counter()
    for entry in entries:
        base = slug(entry["canonical"])
        used[base] += 1
        entry["id"] = base if used[base] == 1 else f"{base}-{used[base]}"
    return entries


def hierarchy(args):
    entries = entries_with_ids()
    client = ClaudeClient("opus", max_concurrency=args.concurrency, timeout=1800.0)
    started = time.monotonic()
    listing = "\n".join(f"{e['canonical']} [{e.get('type', '')}]" for e in entries if not e.get("common"))
    reply = client.ask(NODES_PROMPT.format(seeds=SEED_CONCEPTS, count=listing.count("\n") + 1, entries=listing),
                       system=CURATOR_SYSTEM, tag="nodes")
    nodes = parse_json_object(reply.text)["nodes"]
    node_lines = "\n".join(f"{n['id']} | {n['name']} | {','.join(n.get('parents', []))} | {n.get('description', '')}" for n in nodes)
    batches = [entries[i:i + ASSIGN_BATCH] for i in range(0, len(entries), ASSIGN_BATCH)]
    prompts = [ASSIGN_PROMPT.format(nodes=node_lines, entries="\n".join(
        f"{e['id']} | {e['canonical']} | {e.get('type', '')} | {e.get('definition', '')}" for e in batch)) for batch in batches]
    replies = client.ask_many(prompts, system=CURATOR_SYSTEM, tag="assign")
    assign, new_nodes, problems = {}, [], []
    for batch, reply in zip(batches, replies):
        if isinstance(reply, LLMCallFailed):
            problems.append("호출 실패")
            continue
        try:
            answer = parse_json_object(reply.text)
        except (ValueError, json.JSONDecodeError) as error:
            problems.append(f"JSON 실패 {error}")
            continue
        assign.update({k: v for k, v in answer.get("assign", {}).items() if k in {e["id"] for e in batch}})
        new_nodes += answer.get("new_nodes", [])
    (WORK / "hierarchy-raw.json").write_text(json.dumps({"nodes": nodes, "new_nodes": new_nodes, "assign": assign},
                                                        ensure_ascii=False, indent=1))
    summary = {"entries": len(entries), "nodes": len(nodes), "new_nodes": len(new_nodes), "assigned": len(assign),
               "problems": problems, "wall_seconds": round(time.monotonic() - started), "usage": client.stats.snapshot()}
    (WORK / "hierarchy-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "usage"}, ensure_ascii=False))
    print(client.usage_line())


def final_nodes(raw):
    nodes = {}
    for node in raw["nodes"] + raw["new_nodes"]:
        if node.get("id") and node["id"] not in nodes:
            nodes[node["id"]] = {"id": node["id"], "name": node.get("name", node["id"]), "aliases": node.get("aliases", []),
                                 "parents": node.get("parents", []), "kind": "concept", "description": node.get("description", "")}
    standards = next((n for n in nodes if n in ("standards", "standard", "standards-body", "standards-spec", "standard-spec")), None)
    for value_node in VALUE_NODES:
        node = dict(value_node)
        node["parents"] = [standards] if node["id"] == "3gpp-release" and standards else []
        nodes[node["id"]] = node
    for node in nodes.values():
        node["parents"] = [p for p in dict.fromkeys(node["parents"]) if p in nodes and p != node["id"]]
    return nodes


def creates_cycle(nodes):
    state = {}

    def visit(node_id):
        if state.get(node_id) == "open":
            return True
        if state.get(node_id) == "done":
            return False
        state[node_id] = "open"
        found = any(visit(p) for p in nodes[node_id]["parents"])
        state[node_id] = "done"
        return found

    return [n for n in nodes if visit(n)]


def finalize(args):
    entries = entries_with_ids()
    raw = json.loads((WORK / "hierarchy-raw.json").read_text())
    nodes = final_nodes(raw)
    cyclic = creates_cycle(nodes)
    candidates = {c["cid"]: c for c in (json.loads(l) for l in (WORK / "aggregated.jsonl").read_text().splitlines())}
    docs = load_docs()
    tagger_module = importlib.import_module("23_glossary_tag")
    forms = {(e["id"], a["text"]): a for e in entries for a in [{"text": e["canonical"]}] + e["aliases"]}
    matcher = tagger_module.AliasMatcher({key: [alias] for key, alias in forms.items()})
    alias_docs = Counter()
    entry_docs = defaultdict(set)
    for doc in docs:
        for key in matcher.find(doc["text"]):
            alias_docs[key] += 1
            entry_docs[key[0]].add(doc["doc_id"])

    glossary, added_aliases = [], 0
    for entry in entries:
        member_keys = {candidate_key(s) for m in entry["members"] if m in candidates for s, _ in candidates[m]["surfaces"]}
        aliases = []
        for alias in entry["aliases"]:
            from_candidates = candidate_key(alias["text"]) in member_keys
            added_aliases += not from_candidates
            aliases.append({**alias, "docs": alias_docs[(entry["id"], alias["text"])], "from_candidates": from_candidates})
        glossary.append({
            "id": entry["id"], "canonical": entry["canonical"], "type": entry.get("type", "concept"), "aliases": aliases,
            "definition": entry.get("definition", ""), "parents": [p for p in raw["assign"].get(entry["id"], []) if p in nodes],
            "ambiguity_note": entry.get("ambiguity_note", ""), "common": bool(entry.get("common")),
            "versioned": bool(entry.get("versioned")), "canonical_docs": alias_docs[(entry["id"], entry["canonical"])],
            "docs": len(entry_docs[entry["id"]]), "candidates": entry["members"], "merged_from": entry["merged_from"]})

    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"built": time.strftime("%Y-%m-%d"), "docs": str(DOCS.relative_to(LAB)), "doc_count": len(docs),
            "docs_sha256": hashlib.sha256(DOCS.read_bytes()).hexdigest(),
            "builder": "lab/23_glossary_build.py", "candidate_model": "haiku", "curator_model": "opus (사람 대리)"}
    (OUT / "glossary.json").write_text(json.dumps({"meta": meta, "entry_types": ENTRY_TYPES, "entries": glossary},
                                                  ensure_ascii=False, indent=1))
    (OUT / "hierarchy.json").write_text(json.dumps({"meta": meta, "nodes": list(nodes.values())}, ensure_ascii=False, indent=1))
    stats = {"entries": len(glossary), "nodes": len(nodes), "cyclic_nodes": cyclic, "aliases": sum(len(e["aliases"]) for e in glossary),
             "aliases_added_by_curator": added_aliases,
             "aliases_without_docs": sum(1 for e in glossary for a in e["aliases"] if a["docs"] == 0),
             "entries_without_parent": sum(1 for e in glossary if not e["parents"]),
             "parent_edges": sum(len(e["parents"]) for e in glossary), "common": sum(e["common"] for e in glossary),
             "ambiguous": sum(1 for e in glossary if e["ambiguity_note"]), "versioned": sum(e["versioned"] for e in glossary)}
    (WORK / "finalize-summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps(stats, ensure_ascii=False))
    write_curation(glossary, nodes, stats)


def usage_totals(summary):
    usage = summary.get("usage", {})
    return (sum(t.get("unique_prompts", 0) for t in usage.values()), sum(t.get("recorded_seconds", 0) for t in usage.values()),
            sum(t.get("recorded_cost_usd", 0) for t in usage.values()))


def write_curation(glossary, nodes, stats):
    read = lambda name: json.loads((WORK / name).read_text())
    extract_s, aggregate_s, curate_s = read("extract-summary.json"), read("aggregate-summary.json"), read("curate-summary.json")
    merge_s, hierarchy_s = read("merge-summary.json"), read("hierarchy-summary.json")
    curated = read("curated.json")
    decisions = read("merge-decisions.json")
    raw = read("hierarchy-raw.json")

    asked = sum(len(r["asked"]) for r in curated)
    curated_entries_ = [e for r in curated for e in r["decision"].get("entries", [])]
    placed = sum(len(e.get("members", [])) for e in curated_entries_)
    discard_reasons = Counter()
    for r in curated:
        for d in r["decision"].get("discard", []):
            discard_reasons[d.get("reason", "other")] += len(d.get("members", []))
    multi = sum(1 for e in curated_entries_ if len(e.get("members", [])) > 1)
    unhandled = sum(len(r["unhandled"]) for r in curated)
    actions = Counter(d.get("action") for d in decisions)
    owners = Counter(d.get("shared_alias_owner") for d in decisions if d.get("action") == "separate")
    parent_judgements = len(raw["assign"])

    rows = [("후보 뽑기", "Haiku", extract_s), ("묶기·버리기", "Opus", curate_s), ("교차 병합", "Opus", merge_s),
            ("개념 계층", "Opus", hierarchy_s)]
    opus_calls = opus_seconds = opus_cost = 0
    table = ["| 단계 | 모델 | 호출 | 호출 초 합 | 벽시계 초 | 비용 |", "|---|---|---:|---:|---:|---:|"]
    for name, model, summary in rows:
        calls, seconds, cost = usage_totals(summary)
        if model == "Opus":
            opus_calls, opus_seconds, opus_cost = opus_calls + calls, opus_seconds + seconds, opus_cost + cost
        table.append(f"| {name} | {model} | {calls:.0f} | {seconds:,.0f} | {summary.get('wall_seconds', 0):,} | ${cost:.2f} |")

    judgement_total = placed + sum(discard_reasons.values()) + len(decisions) + parent_judgements
    lines = [
        "# 용어집 관리 기록", "",
        "사람 대리 Opus 가 이 용어집을 만들며 내린 판단 수와 걸린 시간·비용이다. 운영 때 사람이 들일 품의 대리 지표로 쓴다. "
        "Opus 판단 하나가 사람 판단 하나와 같은 품이라는 근거는 없다. 그래서 사람 시간으로 옮기지 않고 판단 수와 호출 비용만 적는다.", "",
        f"입력은 `lab/inputs/net-corpus/docs.jsonl` v2 ({len(load_docs())}건, sha256 `{hashlib.sha256(DOCS.read_bytes()).hexdigest()}`)다. 합성 문서와 정답 폴더는 쓰지 않았다.", "",
        "만든 스크립트는 `lab/23_glossary_build.py` 이고, 단계별 중간 결과는 `lab/runs/23-glossary/` 에 있다.", "",
        "## 단계별 비용", "", "호출 초 합은 호출마다 걸린 시간을 더한 값이고, 벽시계 초는 동시 호출로 실제 걸린 시간이다. 캐시에서 읽은 호출도 처음 부를 때의 시간·비용으로 센다.", "",
        *table, "",
        f"Opus 합: 호출 {opus_calls:.0f}번, 호출 초 합 {opus_seconds:,.0f}초, ${opus_cost:.2f}.", "",
        "## 판단 수", "",
        "| 판단 | 수 | 무엇을 셌나 |", "|---|---:|---|",
        f"| 후보를 항목에 넣기 | {placed} | Opus 가 본 후보 {asked}개 중 항목의 members 에 넣은 수 |",
        f"| 후보 버리기 | {sum(discard_reasons.values())} | 이유별: {', '.join(f'{k} {v}' for k, v in discard_reasons.most_common())} |",
        f"| 판단 없이 남은 후보 | {unhandled} | 답 JSON 에 id 가 없던 후보. 용어집에 들어가지 않았다 |",
        f"| 후보 여럿을 한 항목으로 묶기 | {multi} | members 가 둘 이상인 항목 수(묶음 단계) |",
        f"| 묶음 사이 병합 판정 | {len(decisions)} | 코드가 낸 쌍(별칭 공유·약어 머리글자 일치). 합침 {actions.get('merge', 0)}, 따로 {actions.get('separate', 0)}(공유 글자를 a 만 {owners.get('a', 0)}, b 만 {owners.get('b', 0)}, 둘 다 {owners.get('both', 0)}), 답 없음 {actions.get('undecided', 0)} |",
        f"| 개념 노드 세우기 | {len(raw['nodes'])} + {len(raw['new_nodes'])} | 첫 설계 노드 + 부모 달기 중 더 제안한 노드 |",
        f"| 항목에 부모 달기 | {parent_judgements} | 항목마다 한 판단으로 셌다. 단 부모 선 {stats['parent_edges']}개, 부모 없는 항목 {stats['entries_without_parent']} |",
        f"| 흔한 항목 표시 | {stats['common']} | `common: true` |",
        f"| 모호함 메모 | {stats['ambiguous']} | `ambiguity_note` 가 있는 항목 |",
        f"| 후보에 없던 별칭 더하기 | {stats['aliases_added_by_curator']} | 별칭 {stats['aliases']}개 중 Opus 가 후보 표면형 밖에서 더한 것(영어 풀이·한국어 번역어 등). 이 가운데 말뭉치에 한 번도 안 나오는 별칭은 {stats['aliases_without_docs']}개다 |",
        "", f"판단 합(넣기 + 버리기 + 병합 판정 + 부모 달기): {judgement_total:,}.", "",
        "## 입력 규모", "",
        f"- 청크 {extract_s['chunks']}개({extract_s['chunk_size']}자), Haiku 실패 청크 {extract_s['failed_chunks']}.",
        f"- 후보 언급 {extract_s['mentions']:,}개 중 원문에 글자 그대로 없는 것 {extract_s['unverified_mentions']}개(버림).",
        f"- 정규화 키(소문자, 공백·`-`·`_`·`.`·`/` 지움)로 모은 서로 다른 후보 {aggregate_s['distinct_keys']:,}개 중 "
        f"Haiku 가 2문서 이상에서 뽑았거나 말뭉치 2문서 이상에 글자가 나오는 {aggregate_s['kept']:,}개를 남겼다. "
        f"그중 Haiku 가 한 문서에서만 뽑은 후보는 종류가 {'·'.join(sorted(SINGLE_DOC_KINDS))} 일 때만 두어 {curate_s['candidates']:,}개를 Opus 에 넘겼다. "
        "Opus 비용을 줄이려고 실행 전에 정한 규칙이고, 빠진 것은 대부분 한 문서의 technical 낱말(`OK`, `Mbps`, `syslogs`)이다.",
        f"- 결과: 항목 {stats['entries']}개, 개념 노드 {stats['nodes']}개(값 개념 3개 포함).",
    ]
    (OUT / "CURATION.md").write_text("\n".join(lines) + "\n")
    print(f"{OUT / 'CURATION.md'} 씀")


def collisions(args):
    entries = json.loads((OUT / "glossary.json").read_text())["entries"]
    nodes = {n["id"]: n for n in json.loads((OUT / "hierarchy.json").read_text())["nodes"]}

    def ancestors(parent_ids):
        seen, stack = set(), list(parent_ids)
        while stack:
            node_id = stack.pop()
            if node_id in seen or node_id not in nodes:
                continue
            seen.add(node_id)
            stack.extend(nodes[node_id].get("parents", []))
        return seen

    entry_forms = defaultdict(list)
    for entry in entries:
        entry_forms[candidate_key(entry["canonical"])].append((entry, entry["canonical"], "canonical"))
        for alias in entry["aliases"]:
            entry_forms[candidate_key(alias["text"])].append((entry, alias["text"], "alias"))
    rows = []
    for node in nodes.values():
        node_forms = [(node["name"], "name")] + [(a, "alias") for a in node.get("aliases", [])]
        for form, field in node_forms:
            for entry, entry_form, role in entry_forms.get(candidate_key(form), []):
                under = node["id"] in ancestors(entry.get("parents", []))
                rows.append({"node": node["id"], "node_name": node["name"], "node_form": form, "node_field": field,
                             "entry": entry["id"], "entry_canonical": entry["canonical"], "entry_form": entry_form,
                             "entry_role": role, "entry_docs": entry["docs"],
                             "relation": "instance-under-node" if under else "unrelated-entry"})
    rows.sort(key=lambda r: (-r["entry_docs"], r["node"], r["entry"]))
    summary = {"pairs": len(rows), "nodes": len({r["node"] for r in rows}), "entries": len({r["entry"] for r in rows}),
               "by_relation": Counter(r["relation"] for r in rows), "by_node_field": Counter(r["node_field"] for r in rows),
               "by_entry_role": Counter(r["entry_role"] for r in rows),
               "rule": "개념 노드의 name·aliases 와 항목의 canonical·aliases 를 정규화 키(소문자, 공백·-·_·.·/ 지움)로 견준다. "
                       "relation 은 그 항목이 그 노드 아래(조상 경로)에 있으면 instance-under-node, 아니면 unrelated-entry 다."}
    (OUT / "collisions.json").write_text(json.dumps({"summary": summary, "collisions": rows}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["extract", "aggregate", "curate", "merge", "hierarchy", "finalize", "collisions"])
    parser.add_argument("--limit", type=int, default=0, help="extract: 앞 N 청크만")
    parser.add_argument("--concurrency", type=int, default=10)
    arguments = parser.parse_args()
    {"extract": extract, "aggregate": aggregate, "curate": curate, "merge": merge, "hierarchy": hierarchy, "finalize": finalize, "collisions": collisions}[arguments.step](arguments)
