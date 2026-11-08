import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
spec = spec_from_file_location("schema_glossary", LAB / "13_schema_glossary.py")
sg = module_from_spec(spec)
spec.loader.exec_module(sg)

OLLAMA_CHAT = "http://localhost:11434/api/chat"
ACTIONS = ("alias", "new", "discard")

GROW_PROMPT = """You maintain the glossary of a personal knowledge wiki. A new document chunk has arrived. Names were extracted from it that are not in the glossary yet. Decide what to do with each name, with no human review.

For each name choose exactly one action:
- "alias": the name is another spelling or form of an existing glossary entry. Give that entry's canonical name exactly as written in the glossary.
- "new": the name is a meaningful term that later documents may mention again. Give a canonical name (it may be the name itself, cleaned up), one entity type from the list, and a one-sentence definition. Other names in this list that mean the same new term should use "alias" with this new canonical name.
- "discard": the name is a fragment, a file path, a sentence, an instruction, a number, or too generic to connect documents.

Entity types:
{types}

Glossary (canonical | type | aliases):
{glossary}

Chunk:
<<<
{chunk}
>>>

Names to decide:
{names}

Return only a JSON array, one object per name, in this form:
[{{"name": "...", "action": "alias|new|discard", "canonical": "...", "type": "...", "definition": "..."}}]
For "discard", leave canonical, type and definition empty."""


def glossary_lines(entries):
    return "\n".join(f"{e['canonical']} | {e['type']} | {', '.join(e['aliases'])}" for e in entries)


def type_lines():
    return "\n".join(f"- {t['name']}: {t['description']}" for t in json.loads(sg.SCHEMA.read_text())["entity_types"])


def candidates_by_chunk(canonical_of):
    recs, _ = sg.records("b3")
    by_chunk = {}
    for r in recs:
        if r["id"].startswith(sg.NEW_DOC):
            names = sg.mentions_by_record([r])[r["id"]]
            by_chunk[r["id"]] = sorted(n for n in names if sg.surface_key(n) not in canonical_of)
    return by_chunk


def ask_claude(prompt, model):
    completed = subprocess.run(
        ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
         "--setting-sources", "", "--output-format", "json"],
        input=prompt, capture_output=True, text=True, timeout=900,
    )
    reply = json.loads(completed.stdout)
    return reply["result"], reply.get("total_cost_usd", 0.0)


def ask_ollama(prompt, model):
    body = {"model": model, "stream": False, "options": {"temperature": 0, "num_ctx": 16384},
            "messages": [{"role": "user", "content": prompt}]}
    request = urllib.request.Request(OLLAMA_CHAT, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=1800) as response:
        return json.loads(response.read())["message"]["content"], 0.0


def parse_decisions(answer):
    match = re.search(r"\[.*\]", answer, re.S)
    return json.loads(match.group(0)) if match else []


def grow(model, out_prefix):
    entries, canonical_of = sg.read_glossary()
    chunks = {c["id"]: c for c in sg.kgd.read_chunks()}
    ask = ask_claude if model in ("sonnet", "haiku", "opus") else ask_ollama
    log, total_cost = [], 0.0
    for chunk_id, names in candidates_by_chunk(canonical_of).items():
        prompt = GROW_PROMPT.format(types=type_lines(), glossary=glossary_lines(entries),
                                    chunk=chunks[chunk_id]["text"], names="\n".join(f"- {n}" for n in names))
        answer, cost = ask(prompt, model)
        total_cost += cost
        decisions = parse_decisions(answer)
        log.append({"chunk": chunk_id, "names": names, "answer": answer, "decisions": decisions})
        print(f"{chunk_id}  names {len(names)}  decisions {len(decisions)}  {dict(Counter(d.get('action') for d in decisions))}", flush=True)
    Path(f"{out_prefix}-decisions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in log) + "\n")
    grown = apply(entries, [d for r in log for d in r["decisions"]])
    Path(f"{out_prefix}-glossary.json").write_text(json.dumps(grown, ensure_ascii=False, indent=1))
    print(f"glossary {len(entries)} -> {len(grown)} entries · cost ${total_cost:.2f}")


def apply(entries, decisions):
    grown = [dict(e, aliases=list(e["aliases"])) for e in entries]
    by_canonical = {sg.surface_key(e["canonical"]): e for e in grown}
    for d in decisions:
        if d.get("action") == "new" and d.get("canonical") and sg.surface_key(d["canonical"]) not in by_canonical:
            entry = {"canonical": d["canonical"], "type": d.get("type", ""), "aliases": [], "definition": d.get("definition", ""), "added_by": "llm"}
            grown.append(entry)
            by_canonical[sg.surface_key(d["canonical"])] = entry
    for d in decisions:
        target = by_canonical.get(sg.surface_key(d.get("canonical", "")))
        if d.get("action") in ("alias", "new") and target and sg.surface_key(d["name"]) != sg.surface_key(target["canonical"]) \
                and d["name"] not in target["aliases"]:
            target["aliases"].append(d["name"])
    return grown


def mentions(form, text):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(form) + r"(?![A-Za-z0-9])", text, re.I) is not None


def terms_in(text, entries):
    return {e["canonical"] for e in entries if any(mentions(f, text) for f in [e["canonical"], *e["aliases"]])}


def structure(chunks, entries):
    by_canonical = {sg.surface_key(e["canonical"]): e for e in entries}
    canonical_of = {sg.surface_key(f): e["canonical"] for e in entries for f in [e["canonical"], *e["aliases"]]}
    lookup = {"t02": "rebase", "t03": "amend"}
    scores = []
    for t in json.loads(sg.STRUCTURE.read_text()):
        name = lookup.get(t["id"], sg.short_name(t["target"]))
        canonical = canonical_of.get(sg.surface_key(name))
        if canonical is None:
            continue
        entry = by_canonical[sg.surface_key(canonical)]
        found = {c["id"] for c in chunks if any(mentions(f, c["text"]) for f in [entry["canonical"], *entry["aliases"]])}
        scores.append(sg.precision_recall(found, set(t["gold"])))
    return np.mean([s[0] for s in scores]), np.mean([s[1] for s in scores]), len(scores)


def links(chunks, entries):
    gold = {(l["new"], x["old"]) for l in json.loads(sg.LINKS.read_text()) for x in l["links"]}
    terms = {c["id"]: terms_in(c["text"], entries) for c in chunks}
    via = defaultdict(set)
    for n in (c for c in terms if c.startswith(sg.NEW_DOC)):
        for o in (c for c in terms if not c.startswith(sg.NEW_DOC)):
            for name in terms[n] & terms[o]:
                via[n, o].add(name)
    found = set(via)
    precision, recall = sg.precision_recall(found, gold)
    return found, gold, via, precision, recall


def evaluate(*glossary_paths):
    chunks = sg.kgd.read_chunks()
    base, _ = sg.read_glossary()
    variants = {"original 150 (written by Claude from old docs)": base}
    for path in glossary_paths:
        variants[Path(path).stem] = json.loads(Path(path).read_text())
    base_found = links(chunks, base)[0]
    for name, entries in variants.items():
        p, r, n = structure(chunks, entries)
        found, gold, via, lp, lr = links(chunks, entries)
        added = [e for e in entries if e.get("added_by") == "llm"]
        print(f"\n=== {name}: entries {len(entries)} (llm-added {len(added)})")
        print(f"  structure ({n} targets in glossary): P {p:.2f} R {r:.2f}")
        print(f"  links: found {len(found)} · correct {len(found & gold)} · P {lp:.2f} · R {lr:.2f}")
        new_pairs = sorted(found - base_found)
        if new_pairs:
            names = Counter(x for pair in new_pairs for x in via[pair] if x in {e["canonical"] for e in added} or True)
            print(f"  pairs not found by original: {len(new_pairs)} (correct {len(set(new_pairs) & gold)}) · via most often: {names.most_common(8)}")
            for pair in new_pairs[:5]:
                print(f"      {pair[0]} <-> {pair[1]}  via {sorted(via[pair])[:4]}")


if __name__ == "__main__":
    {"grow": grow, "evaluate": evaluate}[sys.argv[1]](*sys.argv[2:])
