import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
spec = spec_from_file_location("schema_glossary", LAB / "13_schema_glossary.py")
sg = module_from_spec(spec)
spec.loader.exec_module(sg)


def forms_of(entry):
    return [entry["canonical"], *entry["aliases"]]


def chunks_with(forms, chunks):
    return {c["id"] for c in chunks if any(f.casefold() in c["text"].casefold() for f in forms)}


def structure(chunks, entries, canonical_of):
    by_canonical = {e["canonical"]: e for e in entries}
    scores = []
    for t in json.loads(sg.STRUCTURE.read_text()):
        name = sg.short_name(t["target"])
        canonical = canonical_of.get(sg.surface_key(name))
        forms = forms_of(by_canonical[canonical]) if canonical else [name]
        found = chunks_with(forms, chunks)
        p, r = sg.precision_recall(found, set(t["gold"]))
        scores.append((p, r))
        print(f"  {t['id']} {t['target'][:24]:24} gold {len(t['gold']):2}  in glossary {'yes' if canonical else 'no '}  found {len(found):2}  P {p:.2f} R {r:.2f}")
    print(f"  mean  P {np.mean([s[0] for s in scores]):.2f}  R {np.mean([s[1] for s in scores]):.2f}")


def links(chunks, entries, excluded=()):
    gold = {(l["new"], x["old"]) for l in json.loads(sg.LINKS.read_text()) for x in l["links"]}
    terms = {c["id"]: {e["canonical"] for e in sg.glossary_in(c["text"], entries) if e["canonical"] not in excluded} for c in chunks}
    new = [c for c in terms if c.startswith(sg.NEW_DOC)]
    old = [c for c in terms if not c.startswith(sg.NEW_DOC)]
    found = {(n, o) for n in new for o in old if terms[n] & terms[o]}
    p, r = sg.precision_recall(found, gold)
    label = f"excluding {sorted(excluded)}" if excluded else "all glossary entries"
    print(f"  {label}: found {len(found)} · correct {len(found & gold)} · P {p:.2f} · R {r:.2f}")


if __name__ == "__main__":
    chunks = sg.kgd.read_chunks()
    entries, canonical_of = sg.read_glossary()
    print("=== structure questions: chunks containing the glossary entry's canonical name or any alias (no LLM)")
    structure(chunks, entries, canonical_of)
    print("\n=== new doc -> old doc links: chunk pairs sharing a glossary entry by text match (no LLM)")
    links(chunks, entries)
    links(chunks, entries, excluded=("KG", "schema", "LLM", "용어 추출"))
