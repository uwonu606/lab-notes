"""9단계 관계 용어집: 구심점 고르기, Opus 카드(사내 이름·박아 둔 사실), Opus 관계 목록.

    python3 23_relglossary.py select       # 규칙대로 구심점을 고른다(LLM 0) → runs/23-relglossary/selection.json
    python3 23_relglossary.py names        # Opus 1번 + 검사에 걸린 것만 다시 → names.json
    python3 23_relglossary.py facts        # Opus 구심점 5개씩 → facts.json
    python3 23_relglossary.py facts-retry vrrpd   # 검사에 걸린 카드 하나만 다시
    python3 23_relglossary.py relations    # Opus 1번 → relations-raw.json
    python3 23_relglossary.py verify       # Opus 사실 20개씩, 근거 claim 이 받치는지 → verify.json (build 가 고침·뺌을 반영)
    python3 23_relglossary.py build        # hubs.json, relations.json 을 inputs/net-corpus/relglossary/ 에 쓴다

규칙은 inputs/net-corpus/relglossary/CURATION.md #구심점 고르는 규칙. 정답 파일은 select 만 읽는다(질문 글·근거 문서 id).
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict
from importlib import import_module
from pathlib import Path

from llm_cache import ClaudeClient, LLMCallFailed

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/net-corpus"
GLOSSARY_DIR = CORPUS / "glossary"
OUT_DIR = CORPUS / "relglossary"
WORK = LAB / "runs/23-relglossary"
PROMPTS = LAB / "prompts"
SCHEMA = LAB / "runs/23-arch-a4-table/schema.json"

HUB_TYPES = {"software", "vendor", "operator", "test-event", "organization", "ran-component"}
MIN_DOCS = 3
MAX_HUBS = 60
ROLE_PARENTS = {"ran-component", "oran-component", "radio-protocol"}
GENERAL_IT = {"cloud-infra", "kubernetes", "cni-plugin", "load-balancing", "linux-networking", "nat-firewall", "open-source-project"}
FACT_BATCH = 5
CLAIMS_PER_HUB = 36
DOCS_PER_HUB = 25
CLAIM_CHARS = 300
NAME_RETRIES = 3
SYSTEM = "Follow the user's instructions exactly. Reply with only the JSON that is asked for, no commentary."


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_json_reply(text):
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def normalized(text):
    return re.sub(r"[\s\-_./]", "", text.lower())


class Glossary:
    def __init__(self):
        self.entries = {e["id"]: e for e in read_json(GLOSSARY_DIR / "glossary.json")["entries"]}
        self.nodes = {n["id"]: n for n in read_json(GLOSSARY_DIR / "hierarchy.json")["nodes"]}
        self.entry_docs = defaultdict(set)
        for row in read_jsonl(LAB / "runs/23-glossary/doc-tags.jsonl"):
            for entry in row["entries"]:
                self.entry_docs[entry["id"]].add(row["doc_id"])

    def ancestors(self, entry_id):
        seen, stack = set(), list(self.entries[entry_id]["parents"])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack += self.nodes.get(node, {}).get("parents", [])
        return seen

    def public_names(self, entry_id):
        entry = self.entries[entry_id]
        return [entry["canonical"]] + [alias["text"] for alias in entry["aliases"]]


def exclusion_reason(glossary, entry_id, claim_counts):
    entry = glossary.entries[entry_id]
    if entry["common"]:
        return "common"
    if "test-method" in entry["parents"]:
        return "activity"
    if entry["type"] == "ran-component" and set(entry["parents"]) <= ROLE_PARENTS:
        return "role"
    if entry["type"] == "software" and glossary.ancestors(entry_id) <= GENERAL_IT:
        return "general-it"
    if entry["type"] == "organization" and "standards-body" in entry["parents"]:
        return "standards-body"
    if not claim_counts[entry_id]:
        return "no-claim"
    return None


def select():
    glossary = Glossary()
    tagger = import_module("23_glossary_tag").GlossaryTagger()
    questions = read_jsonl(CORPUS / "gold/questions.jsonl")
    doc_entries = defaultdict(set)
    for entry_id, docs in glossary.entry_docs.items():
        for doc_id in docs:
            doc_entries[doc_id].add(entry_id)
    claim_counts = Counter(entry_id for row in read_jsonl(LAB / "runs/23-glossary/claim-tags.jsonl") for entry_id in row["entries"])
    in_question, in_evidence = defaultdict(set), defaultdict(set)
    for question in questions:
        for entry in tagger.tag_text(question["question"])["entries"]:
            in_question[entry["id"]].add(question["qid"])
        for doc_id in {span["doc_id"] for evidence in question["evidence"] for span in evidence["spans"]}:
            for entry_id in doc_entries[doc_id]:
                in_evidence[entry_id].add(question["qid"])

    rows = []
    for entry_id, entry in glossary.entries.items():
        docs = len(glossary.entry_docs[entry_id])
        if entry["type"] not in HUB_TYPES or docs < MIN_DOCS or not (in_question[entry_id] or in_evidence[entry_id]):
            continue
        rows.append({"id": entry_id, "type": entry["type"], "canonical": entry["canonical"], "docs": docs,
                     "question_qids": sorted(in_question[entry_id]), "evidence_questions": len(in_evidence[entry_id]),
                     "claims": claim_counts[entry_id], "excluded": exclusion_reason(glossary, entry_id, claim_counts)})
    rows.sort(key=lambda r: (-len(r["question_qids"]), -r["evidence_questions"], -r["docs"], r["id"]))
    kept = [r for r in rows if not r["excluded"] and r["question_qids"]][:MAX_HUBS]
    chosen = {r["id"] for r in kept}
    for row in rows:
        row["chosen"] = row["id"] in chosen
    summary = {"rule_pool": len(rows), "excluded": Counter(r["excluded"] for r in rows if r["excluded"]),
               "kept_without_question": sum(1 for r in rows if not r["excluded"] and not r["question_qids"]),
               "chosen": len(kept), "chosen_types": Counter(r["type"] for r in kept),
               "questions_touched": len({q for r in kept for q in r["question_qids"]})}
    write_json(WORK / "selection.json", {"summary": summary, "rows": rows})
    print(json.dumps(summary, ensure_ascii=False))
    for row in kept:
        print(f'{row["id"]}\t{row["type"]}\t{row["canonical"]}\tq={len(row["question_qids"])}\tev={row["evidence_questions"]}\tdocs={row["docs"]}')


def chosen_hubs():
    return [r for r in read_json(WORK / "selection.json")["rows"] if r["chosen"]]


def corpus_text_lower():
    return "\n".join(doc["text"] for doc in read_jsonl(CORPUS / "docs.jsonl")).lower()


def name_problems(name, owner_id, glossary, corpus_lower, taken):
    problems = []
    if name.lower() in corpus_lower:
        problems.append("appears in the documents")
    key = normalized(name)
    if key in taken and taken[key] != owner_id:
        problems.append(f"already used by {taken[key]}")
    for entry in glossary.entries.values():
        if any(normalized(alias) == key for alias in [entry["canonical"]] + [a["text"] for a in entry["aliases"]]):
            problems.append(f"is a public glossary name of {entry['id']}")
            break
    for public in glossary.public_names(owner_id):
        public_key = normalized(public)
        if any(key[i:i + 3] in public_key for i in range(len(key) - 2) if re.match(r"[a-z0-9]{3}", key[i:i + 3])):
            problems.append(f"shares letters with public name {public}")
            break
    return problems


def names_prompt(hubs, glossary, taken_names=()):
    lines = []
    for hub in hubs:
        entry = glossary.entries[hub["id"]]
        others = ", ".join(a["text"] for a in entry["aliases"]) or "-"
        lines.append(f'{hub["id"]} | {entry["type"]} | {entry["canonical"]} | {others} | {entry["definition"]}')
    prompt = (PROMPTS / "relglossary-names.txt").read_text(encoding="utf-8").replace("<<ENTRIES>>", "\n".join(lines))
    if taken_names:
        prompt += "\nThese names are already taken by other entries and must not be used or share a word: " + ", ".join(taken_names) + "\n"
    return prompt


def names():
    glossary = Glossary()
    hubs = chosen_hubs()
    corpus_lower = corpus_text_lower()
    client = ClaudeClient("opus", max_concurrency=2, timeout=900.0)
    accepted, rounds = {}, []
    pending = hubs
    for attempt in range(NAME_RETRIES + 1):
        taken = {normalized(n): hub_id for hub_id, card in accepted.items() for n in [card["internal_name"], *card["internal_aliases"]]}
        prompt = names_prompt(pending, glossary, sorted({n for c in accepted.values() for n in [c["internal_name"], *c["internal_aliases"]]}))
        reply = parse_json_reply(client.ask(prompt, SYSTEM, tag="relglossary-names").text)
        answered = {card["id"]: card for card in reply["hubs"]}
        rejected = []
        for hub in pending:
            card = answered.get(hub["id"])
            if not card:
                rejected.append({"id": hub["id"], "problems": ["no answer"]})
                continue
            surfaces = [card["internal_name"], *card["internal_aliases"]]
            problems = {}
            local_taken = dict(taken)
            for surface in surfaces:
                found = name_problems(surface, hub["id"], glossary, corpus_lower, local_taken)
                if found:
                    problems[surface] = found
                local_taken[normalized(surface)] = hub["id"]
            if not 2 <= len(card["internal_aliases"]) <= 3:
                problems["internal_aliases"] = [f"{len(card['internal_aliases'])} aliases"]
            if problems:
                rejected.append({"id": hub["id"], "card": card, "problems": problems})
            else:
                accepted[hub["id"]] = {"internal_name": card["internal_name"], "internal_aliases": card["internal_aliases"]}
                taken.update({normalized(s): hub["id"] for s in surfaces})
        rounds.append({"round": attempt, "asked": len(pending), "accepted": len(pending) - len(rejected), "rejected": rejected})
        pending = [hub for hub in pending if hub["id"] not in accepted]
        if not pending:
            break
    write_json(WORK / "names.json", {"accepted": accepted, "rounds": rounds, "unresolved": [h["id"] for h in pending]})
    print(json.dumps([{k: v for k, v in r.items() if k != "rejected"} | {"rejected": [x["id"] for x in r["rejected"]]} for r in rounds], ensure_ascii=False))
    print(client.usage_line())


class ClaimIndex:
    def __init__(self):
        self.claims = {row["unit_id"]: row for row in read_jsonl(LAB / "runs/23-net-units/claim.jsonl")}
        self.tags = {row["unit_id"]: set(row["entries"]) for row in read_jsonl(LAB / "runs/23-glossary/claim-tags.jsonl")}
        self.docs = {doc["doc_id"]: doc for doc in read_jsonl(CORPUS / "docs.jsonl")}
        self.by_entry = defaultdict(list)
        for unit_id, entries in self.tags.items():
            for entry_id in entries:
                self.by_entry[entry_id].append(unit_id)


def round_robin_by_doc(unit_ids, claims, limit):
    by_doc = defaultdict(list)
    for unit_id in unit_ids:
        by_doc[claims[unit_id]["doc_id"]].append(unit_id)
    queues = [by_doc[d] for d in sorted(by_doc, key=lambda d: -len(by_doc[d]))]
    picked = []
    while queues and len(picked) < limit:
        for queue in list(queues):
            if queue:
                picked.append(queue.pop(0))
            if not queue:
                queues.remove(queue)
            if len(picked) >= limit:
                break
    return picked


def hub_evidence(hub_id, hub_ids, index):
    unit_ids = sorted(index.by_entry[hub_id])
    linked = [u for u in unit_ids if index.tags[u] & (hub_ids - {hub_id})]
    plain = [u for u in unit_ids if u not in set(linked)]
    picked = round_robin_by_doc(linked, index.claims, CLAIMS_PER_HUB * 2 // 3)
    picked += round_robin_by_doc(plain, index.claims, CLAIMS_PER_HUB - len(picked))
    return picked


def card_block(hub_id, glossary, names_table, index, hub_ids):
    entry = glossary.entries[hub_id]
    docs = sorted(glossary.entry_docs[hub_id], key=lambda d: index.docs[d]["date"] or "")
    doc_lines = [f'{d} | {index.docs[d]["kind"]} | {(index.docs[d]["date"] or "")[:10]} | {index.docs[d]["title"][:100]}'
                 for d in docs[:DOCS_PER_HUB]]
    claim_lines = []
    for unit_id in hub_evidence(hub_id, hub_ids, index):
        other = sorted(index.tags[unit_id] & (hub_ids - {hub_id}))
        text = index.claims[unit_id]["text"].replace("\n", " ")[:CLAIM_CHARS]
        claim_lines.append(f'{unit_id} | {text}' + (f' | other cards: {", ".join(other)}' if other else ""))
    names = names_table[hub_id]
    return (f'<card id="{hub_id}">\nin-house name: {names["internal_name"]} (also {", ".join(names["internal_aliases"])})\n'
            f'public name: {entry["canonical"]}; other public names: {", ".join(a["text"] for a in entry["aliases"]) or "-"}\n'
            f'entry type: {entry["type"]}; glossary meaning: {entry["definition"]}\n'
            f'documents ({len(docs)} in total, first {len(doc_lines)} by date):\n' + "\n".join(doc_lines) +
            "\nclaims:\n" + "\n".join(claim_lines) + "\n</card>")


def facts_prompts():
    glossary = Glossary()
    hubs = chosen_hubs()
    names_table = read_json(WORK / "names.json")["accepted"]
    index = ClaimIndex()
    hub_ids = {h["id"] for h in hubs}
    table = "\n".join(f'{h["id"]} | {names_table[h["id"]]["internal_name"]} | {h["canonical"]}' for h in hubs)
    template = (PROMPTS / "relglossary-facts.txt").read_text(encoding="utf-8").replace("<<NAMES>>", table)
    batches = [hubs[i:i + FACT_BATCH] for i in range(0, len(hubs), FACT_BATCH)]
    prompts = [template.replace("<<CARDS>>", "\n\n".join(card_block(h["id"], glossary, names_table, index, hub_ids) for h in batch))
               for batch in batches]
    return batches, prompts, index, glossary, hub_ids


def check_fact(fact, hub_id, index, glossary, hub_ids):
    problems = []
    if fact["kind"] == "corpus":
        sources = fact.get("source_claims", [])
        missing = [u for u in sources if u not in index.claims]
        foreign = [u for u in sources if u in index.claims and index.claims[u]["doc_id"] not in glossary.entry_docs[hub_id]]
        if not sources or len(missing) + len(foreign) == len(sources):
            problems.append("no valid source claim")
        if missing:
            problems.append(f"unknown claims {missing}")
        if foreign:
            problems.append(f"claims outside the hub's documents {foreign}")
    if fact["kind"] == "invented" and not fact.get("invented"):
        problems.append("invented kind without invented flag")
    unknown_hubs = [h for h in fact.get("related_hubs", []) if h not in hub_ids]
    if unknown_hubs:
        problems.append(f"unknown related hubs {unknown_hubs}")
    return problems


def facts():
    batches, prompts, index, glossary, hub_ids = facts_prompts()
    client = ClaudeClient("opus", max_concurrency=4, timeout=900.0)
    replies = client.ask_many(prompts, SYSTEM, tag="relglossary-facts")
    cards, problems, failed = {}, [], []
    for batch, reply in zip(batches, replies):
        if isinstance(reply, LLMCallFailed):
            failed.append([h["id"] for h in batch])
            continue
        answered = {card["id"]: card["facts"] for card in parse_json_reply(reply.text)["cards"]}
        for hub in batch:
            hub_facts = answered.get(hub["id"], [])
            cards[hub["id"]] = hub_facts
            card_problems = []
            if not 3 <= len(hub_facts) <= 6:
                card_problems.append(f"{len(hub_facts)} facts")
            if not hub_facts or hub_facts[0]["kind"] != "identity":
                card_problems.append("first fact is not identity")
            if sum(f["kind"] == "invented" for f in hub_facts) > 1:
                card_problems.append("more than one invented fact")
            for position, fact in enumerate(hub_facts):
                for problem in check_fact(fact, hub["id"], index, glossary, hub_ids):
                    card_problems.append(f"fact {position}: {problem}")
            if card_problems:
                problems.append({"id": hub["id"], "problems": card_problems})
    write_json(WORK / "facts.json", {"cards": cards, "problems": problems, "failed_batches": failed,
                                     "prompt_chars": [len(p) for p in prompts]})
    print(f"cards {len(cards)}, cards with problems {len(problems)}, failed batches {len(failed)}")
    for problem in problems:
        print(problem)
    print(client.usage_line())


def facts_retry(hub_id):
    batches, prompts, index, glossary, hub_ids = facts_prompts()
    hub = next(h for batch in batches for h in batch if h["id"] == hub_id)
    names_table = read_json(WORK / "names.json")["accepted"]
    template = prompts[0][:prompts[0].index("<card ")]
    prompt = (template + card_block(hub_id, glossary, names_table, index, hub_ids) + "\n</cards>\n\n"
              + "This card must have at least 2 corpus facts with source claims.\n"
              + prompts[0][prompts[0].index("Reply with only JSON"):])
    client = ClaudeClient("opus", timeout=900.0)
    hub_facts = {c["id"]: c["facts"] for c in parse_json_reply(client.ask(prompt, SYSTEM, tag="relglossary-facts-retry").text)["cards"]}[hub_id]
    problems = [p for f in hub_facts for p in check_fact(f, hub_id, index, glossary, hub_ids)]
    saved = read_json(WORK / "facts.json")
    saved["cards"][hub_id] = hub_facts
    saved["problems"] = [p for p in saved["problems"] if p["id"] != hub_id] + ([{"id": hub_id, "problems": problems}] if problems else [])
    saved.setdefault("retried", []).append(hub_id)
    write_json(WORK / "facts.json", saved)
    print(hub["id"], len(hub_facts), "facts", problems or "ok")
    print(client.usage_line())


def public_name_pattern(name):
    return re.compile(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])", 0 if len(name) <= 3 else re.IGNORECASE)


def hub_name_replacer(glossary, hubs, names_table):
    surfaces = sorted(((name, hub["id"]) for hub in hubs for name in glossary.public_names(hub["id"])), key=lambda s: -len(s[0]))
    patterns = [(public_name_pattern(name), hub_id) for name, hub_id in surfaces]

    def replace(text, keep_hub=None):
        replaced = []
        for pattern, hub_id in patterns:
            if hub_id == keep_hub:
                continue
            text, count = pattern.subn(names_table[hub_id]["internal_name"], text)
            if count:
                replaced.append(hub_id)
        return text, replaced
    return replace


VERIFY_BATCH = 20


def verify():
    hubs_out = read_json(OUT_DIR / "hubs.json")["hubs"]
    index = ClaimIndex()
    table = "\n".join(f'{h["id"]} | {h["internal_name"]} | {h["public_name"]}' for h in hubs_out)
    facts_to_check = [f for h in hubs_out for f in h["facts"] if f["kind"] == "corpus"]
    blocks = []
    for fact in facts_to_check:
        claim_lines = [f'  [{u}] (document: {index.docs[index.claims[u]["doc_id"]]["title"][:100]}) {index.claims[u]["text"][:600]}'
                       for u in fact["source_claims"] if u in index.claims]
        blocks.append(f'<fact id="{fact["id"]}">\n{fact["text"]}\nsource claims:\n' + "\n".join(claim_lines) + "\n</fact>")
    template = (PROMPTS / "relglossary-verify.txt").read_text(encoding="utf-8").replace("<<NAMES>>", table)
    prompts = [template.replace("<<FACTS>>", "\n\n".join(blocks[i:i + VERIFY_BATCH])) for i in range(0, len(blocks), VERIFY_BATCH)]
    client = ClaudeClient("opus", max_concurrency=5, timeout=900.0)
    replies = client.ask_many(prompts, SYSTEM, tag="relglossary-verify")
    verdicts, failed = {}, 0
    for reply in replies:
        if isinstance(reply, LLMCallFailed):
            failed += 1
            continue
        for verdict in parse_json_reply(reply.text)["verdicts"]:
            verdicts[verdict["fact"]] = verdict
    missing = [f["id"] for f in facts_to_check if f["id"] not in verdicts]
    write_json(WORK / "verify.json", {"checked": len(facts_to_check), "verdicts": verdicts, "missing": missing, "failed_batches": failed,
                                      "hubs_sha256_checked": __import__("hashlib").sha256((OUT_DIR / "hubs.json").read_bytes()).hexdigest()})
    print(Counter(v["support"] for v in verdicts.values()), "fixed", sum(bool(v.get("fixed")) for v in verdicts.values()
                                                                         if v["support"] != "full"), "missing", len(missing))
    print(client.usage_line())


def apply_verdicts(hub_facts, verdicts, replace, hub_id):
    """받침 검사 결과: full 은 그대로, partial·none 은 고친 글로 바꾸고 고친 글이 없으면 뺀다."""
    kept, changes = [], []
    for fact in hub_facts:
        verdict = verdicts.get(fact["id"])
        if not verdict or verdict["support"] == "full":
            kept.append(fact)
            continue
        if verdict.get("fixed"):
            text, _ = replace(verdict["fixed"])
            kept.append({**fact, "text": text, "verified": "fixed"})
            changes.append({"fact": fact["id"], "support": verdict["support"], "action": "fixed", "before": fact["text"], "after": text,
                            "problem": verdict.get("problem", "")})
        else:
            changes.append({"fact": fact["id"], "support": verdict["support"], "action": "dropped", "before": fact["text"],
                            "problem": verdict.get("problem", "")})
    return kept, changes


def relation_claim_sample(index, hub_ids, per_kind=14, seed=9):
    rng = random.Random(seed)
    by_kind = defaultdict(list)
    for unit_id, entries in index.tags.items():
        if len(entries) >= 2 and len(index.claims[unit_id]["text"]) >= 60:
            by_kind[index.docs[index.claims[unit_id]["doc_id"]]["kind"]].append(unit_id)
    lines = []
    for kind in sorted(by_kind):
        pool = sorted(by_kind[kind])
        with_hub = [u for u in pool if index.tags[u] & hub_ids]
        sample = rng.sample(with_hub, min(per_kind * 2 // 3, len(with_hub)))
        sample += rng.sample([u for u in pool if u not in set(sample)], per_kind - len(sample))
        for unit_id in sample:
            text = index.claims[unit_id]["text"].replace("\n", " ")[:CLAIM_CHARS]
            lines.append(f'{kind} | {text} | {", ".join(sorted(index.tags[unit_id]))}')
    return lines


def relations_prompt():
    glossary = Glossary()
    hubs = chosen_hubs()
    index = ClaimIndex()
    hub_ids = {h["id"] for h in hubs}
    type_counts = Counter(e["type"] for e in glossary.entries.values())
    columns = read_json(SCHEMA)["columns"]
    column_lines = [f'{c["name"]} ({c["value_set"]}): {c["description"]} e.g. {"; ".join(c["examples"][:3])}' for c in columns]
    return ((PROMPTS / "relglossary-relations.txt").read_text(encoding="utf-8")
            .replace("<<ENTRY_TYPES>>", ", ".join(f"{t} {n}" for t, n in type_counts.most_common()))
            .replace("<<HUBS>>", "\n".join(f'{h["id"]} | {h["type"]} | {h["canonical"]}' for h in hubs))
            .replace("<<COLUMNS>>", "\n".join(column_lines))
            .replace("<<CLAIMS>>", "\n".join(relation_claim_sample(index, hub_ids))))


def relations():
    client = ClaudeClient("opus", timeout=900.0)
    reply = client.ask(relations_prompt(), SYSTEM, tag="relglossary-relations")
    parsed = parse_json_reply(reply.text)
    write_json(WORK / "relations-raw.json", parsed)
    columns = {c["name"] for c in read_json(SCHEMA)["columns"]}
    for relation in parsed["relations"]:
        bad_column = relation.get("record_column") and relation["record_column"] not in columns
        print(relation["id"], relation["name_ko"], relation["head_types"], "->", relation["tail_types"], relation.get("record_column"),
              "BAD COLUMN" if bad_column else "")
    print(len(parsed["relations"]), "relations;", client.usage_line())


def build():
    glossary = Glossary()
    hubs = chosen_hubs()
    names_table = read_json(WORK / "names.json")["accepted"]
    cards = read_json(WORK / "facts.json")["cards"]
    replace = hub_name_replacer(glossary, hubs, names_table)
    verify_path = WORK / "verify.json"
    verdicts = read_json(verify_path)["verdicts"] if verify_path.exists() else {}
    out, replacements, verify_changes = [], [], []
    for hub in hubs:
        entry = glossary.entries[hub["id"]]
        names = names_table[hub["id"]]
        hub_facts = []
        for i, fact in enumerate(cards[hub["id"]], 1):
            text, replaced = replace(fact["text"], keep_hub=hub["id"] if fact["kind"] == "identity" else None)
            if replaced:
                replacements.append({"fact": f'{hub["id"]}#f{i}', "hubs": replaced, "before": fact["text"], "after": text})
            hub_facts.append({"id": f'{hub["id"]}#f{i}', "text": text, "kind": fact["kind"], "invented": bool(fact.get("invented")),
                              "source_claims": fact.get("source_claims", []),
                              "related_hubs": sorted(set(fact.get("related_hubs", [])) | set(replaced) - {hub["id"]})})
        hub_facts, changes = apply_verdicts(hub_facts, verdicts, replace, hub["id"])
        verify_changes += changes
        out.append({"id": hub["id"], "glossary_id": hub["id"], "type": entry["type"],
                    "internal_name": names["internal_name"], "internal_aliases": names["internal_aliases"],
                    "public_name": entry["canonical"], "public_aliases": [a["text"] for a in entry["aliases"]],
                    "facts": hub_facts})
    write_json(OUT_DIR / "hubs.json", {"meta": {"made_by": "23_relglossary.py build", "glossary": "glossary.json f4138f66c22ad126…",
                                                "hubs": len(out)}, "hubs": out})
    write_json(WORK / "fact-name-replacements.json", replacements)
    write_json(WORK / "verify-changes.json", verify_changes)
    relations_out = read_json(WORK / "relations-raw.json")["relations"]
    write_json(OUT_DIR / "relations.json", {"meta": {"made_by": "23_relglossary.py build", "relations": len(relations_out)},
                                            "relations": relations_out})
    print(f"hubs {len(out)}, facts {sum(len(h['facts']) for h in out)}, relations {len(relations_out)}, "
          f"facts with hub names replaced {len(replacements)}, verify changes {Counter(c['action'] for c in verify_changes)}")


COMMANDS = {"select": select, "names": names, "facts": facts, "facts-retry": facts_retry, "relations": relations, "verify": verify,
            "build": build}

if __name__ == "__main__":
    COMMANDS[sys.argv[1]](*sys.argv[2:])
