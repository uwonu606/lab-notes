import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(__file__).parent
spec = spec_from_file_location("entry_weight", LAB / "19_entry_weight.py")
ew = module_from_spec(spec)
spec.loader.exec_module(ew)
gg, sg = ew.gg, ew.sg
JUDGE_CACHE = LAB / "runs/20-judge.jsonl"
GLOSSARIES = {"original 150": None, "sonnet": LAB / "runs/18-sonnet-glossary.json", "llama": LAB / "runs/18-llama-glossary.json"}

JUDGE_PROMPT = """Two chunks come from a personal research notebook. The first is from a newly added document, the second from an older one. A code rule paired them because both mention: {shared}.

Decide whether the old chunk should be linked from the new chunk. Link only if both chunks actually discuss the same specific thing (the same system, method, experiment or note) so that a reader of the new chunk would gain something from the old one. Do not link if the shared name is only mentioned in passing in either chunk, or if the shared word is generic.

New chunk:
<<<
{new}
>>>

Old chunk:
<<<
{old}
>>>

Answer with only a JSON object: {{"link": true or false, "subject": "the shared thing, or empty", "why": "one sentence"}}"""


def glossary(label):
    path = GLOSSARIES[label]
    return sg.read_glossary()[0] if path is None else json.loads(path.read_text())


def candidates():
    chunks = sg.kgd.read_chunks()
    by_label = {}
    for label in GLOSSARIES:
        _, df, shared = ew.shared_entries(chunks, glossary(label))
        by_label[label] = {pair: {"names": sorted(names), "aa": ew.adamic_adar(names, df)} for pair, names in shared.items()}
    return chunks, by_label


def cosine_by_pair(chunks, pairs):
    encoder = sg.kgd.distractor.OllamaEncoder(sg.kgd.CACHE / "embeddings.json")
    text = {c["id"]: c["text"] for c in chunks}
    ids = sorted({c for pair in pairs for c in pair})
    vectors = dict(zip(ids, encoder.encode([text[i] for i in ids])))
    return {pair: float(vectors[pair[0]] @ vectors[pair[1]]) for pair in pairs}


def read_judged():
    if not JUDGE_CACHE.exists():
        return {}
    return {(r["new"], r["old"]): r for r in map(json.loads, JUDGE_CACHE.read_text().splitlines())}


def judge_one(pair, names, text, model):
    prompt = JUDGE_PROMPT.format(shared=", ".join(names), new=text[pair[0]], old=text[pair[1]])
    answer, cost = gg.ask_claude(prompt, model)
    match = re.search(r"\{.*\}", answer, re.S)
    verdict = json.loads(match.group(0)) if match else {"link": False, "subject": "", "why": f"unparsed: {answer[:200]}"}
    return {"new": pair[0], "old": pair[1], "shared": names, "cost": cost, **verdict}


def judge(model="sonnet"):
    chunks, by_label = candidates()
    text = {c["id"]: c["text"] for c in chunks}
    names_of = {}
    for pairs in by_label.values():
        for pair, info in pairs.items():
            names_of.setdefault(pair, set()).update(info["names"])
    done = read_judged()
    todo = sorted(set(names_of) - set(done))
    print(f"unique candidate pairs {len(names_of)} · already judged {len(done)} · to judge {len(todo)}", flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool, JUDGE_CACHE.open("a") as out:
        for record in pool.map(lambda pair: judge_one(pair, sorted(names_of[pair]), text, model), todo):
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
    total = sum(r["cost"] for r in read_judged().values())
    print(f"judge cost so far ${total:.2f}")


def all_pairs(chunks):
    new = [c["id"] for c in chunks if c["id"].startswith(sg.NEW_DOC)]
    old = [c["id"] for c in chunks if not c["id"].startswith(sg.NEW_DOC)]
    return [(n, o) for n in new for o in old]


def summarize_curve(name, scores, gold):
    points = ew.curve(scores, gold)
    best = ew.best_at_floor(points)
    line = f"  {name}: candidates {len(scores)}"
    if best:
        line += f" · best P with R >= {ew.RECALL_FLOOR}: P {best[2]:.2f} R {best[3]:.2f} (found {best[1]}, threshold {best[0]:.3f})"
    else:
        line += f" · R never reaches {ew.RECALL_FLOOR}"
    return line


def evaluate():
    chunks, by_label = candidates()
    gold = {(l["new"], x["old"]) for l in json.loads(sg.LINKS.read_text()) for x in l["links"]}
    judged = read_judged()
    every = all_pairs(chunks)
    cosine = cosine_by_pair(chunks, every)
    print(f"gold {len(gold)} · all new x old pairs {len(every)}")
    print(summarize_curve("dense only, all pairs (no glossary)", cosine, gold))
    for label, pairs in by_label.items():
        found = set(pairs)
        p, r = sg.precision_recall(found, gold)
        print(f"\n=== {label}: glossary candidates {len(found)} · P {p:.2f} R {r:.2f}")
        print(summarize_curve("glossary candidates ranked by Adamic-Adar", {pair: pairs[pair]["aa"] for pair in found}, gold))
        print(summarize_curve("glossary candidates ranked by dense cosine", {pair: cosine[pair] for pair in found}, gold))
        kept = {pair for pair in found if judged.get(pair, {}).get("link")}
        jp, jr = sg.precision_recall(kept, gold)
        unjudged = len([pair for pair in found if pair not in judged])
        print(f"  glossary candidates kept by LLM judge: found {len(kept)} · P {jp:.2f} R {jr:.2f}" + (f" · unjudged {unjudged}" if unjudged else ""))
        for pair in sorted(gold - kept):
            print(f"      judge dropped gold {pair[0]} <-> {pair[1]}: {judged.get(pair, {}).get('why', '')}")
        for pair in sorted(kept - gold):
            print(f"      judge kept non-gold {pair[0]} <-> {pair[1]} via {pairs[pair]['names']}: {judged[pair]['why']}")
    autoschemakg = [pair for pair in by_label["original 150"] if by_label["original 150"][pair]["names"] == ["AutoSchemaKG"]]
    print(f"\n=== pairs sharing only AutoSchemaKG (original glossary): {len(autoschemakg)} · gold {len(set(autoschemakg) & gold)}")
    for pair in sorted(autoschemakg, key=lambda x: -cosine[x]):
        verdict = judged.get(pair, {}).get("link")
        print(f"      cos {cosine[pair]:.3f}  judge {verdict!s:5}  gold {'yes' if pair in gold else 'no '}  {pair[0]} <-> {pair[1]}")


if __name__ == "__main__":
    {"judge": judge, "evaluate": evaluate}[sys.argv[1]](*sys.argv[2:])
