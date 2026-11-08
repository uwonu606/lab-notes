import json, sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(sys.argv[1])
BASE_GLOSSARY = Path(sys.argv[2])
OUT = Path(sys.argv[3])
ACCEPTED_MERGES = {
    "queue t>=0.7, human accepts true merges (rebase, amend, ultra-fine typing)":
        [("git rebase", "rebase"), ("git commit --amend", "amend"), ("Choi 2018", "ultra-fine typing")],
    "answer-seen upper bound (+UFET)":
        [("git rebase", "rebase"), ("git commit --amend", "amend"), ("Choi 2018", "ultra-fine typing"), ("Choi 2018", "UFET")],
    "no merge": [],
}
METHOD = sys.argv[4] if len(sys.argv) > 4 else "fixed1000"


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tc = load("topic_chunking", LAB / "21_topic_chunking.py")
sg = tc.sg


def merged(entries, merges):
    by_canonical = {e["canonical"]: dict(e, aliases=list(e["aliases"])) for e in entries}
    for keep, absorbed in merges:
        source = by_canonical[absorbed]
        for form in [source["canonical"], *source["aliases"]]:
            if form not in by_canonical[keep]["aliases"]:
                by_canonical[keep]["aliases"].append(form)
    return list(by_canonical.values())


def thread_scores(entries, chunks, units):
    canonical_of = {sg.surface_key(f): e["canonical"] for e in entries for f in [e["canonical"], *e["aliases"]]}
    by_canonical = {e["canonical"]: e for e in entries}
    rows = []
    for t in json.loads(sg.STRUCTURE.read_text()):
        name = sg.short_name(t["target"])
        canonical = canonical_of.get(sg.surface_key(name))
        forms = [by_canonical[canonical]["canonical"], *by_canonical[canonical]["aliases"]] if canonical else [name]
        pieces = [(c["doc"], c["start"], c["end"]) for c in chunks if any(f.casefold() in c["text"].casefold() for f in forms)]
        relevant = [p for p in pieces if any(tc.covers(*p, u) for u in units[t["id"]])]
        recall, _ = tc.recall_of(pieces, units[t["id"]])
        rows.append((t["id"], len(relevant) / len(pieces) if pieces else 0.0, recall, len(pieces)))
    return rows


entries = json.loads(BASE_GLOSSARY.read_text())
chunks = tc.all_chunks(METHOD)
units, _ = tc.gold_units("structure")
lines = [f"chunks {METHOD}: {len(chunks)}, base glossary {BASE_GLOSSARY.name} ({len(entries)} entries)"]
for label, merges in ACCEPTED_MERGES.items():
    rows = thread_scores(merged(entries, merges), chunks, units)
    found = [r for r in rows if r[3]]
    lines.append(f"\n=== {label}")
    lines.append(f"  mean recall {sum(r[2] for r in rows) / len(rows):.2f} · mean precision over targets with hits {sum(r[1] for r in found) / len(found):.2f} ({len(found)} targets)")
    lines.append("  " + " · ".join(f"{tid} R{rec:.2f} P{prec:.2f} n{n}" for tid, prec, rec, n in rows))
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))

import numpy as np
vectors = json.loads((LAB / "runs/12-cache/embeddings.json").read_text())
structure = json.loads(sg.STRUCTURE.read_text())
missing = [t["question"] for t in structure if t["question"] not in vectors] + [c["text"] for c in chunks if c["text"] not in vectors]
lines2 = [f"\n=== conditional dense fallback (embedding 5000 chars only when alias match returns nothing); missing vectors {len(missing)}"]
if not missing:
    cm = np.array([vectors[c["text"]] for c in chunks]); cm /= np.linalg.norm(cm, axis=1, keepdims=True)
    for label, merges in ACCEPTED_MERGES.items():
        glossary = merged(entries, merges)
        base_rows = thread_scores(glossary, chunks, units)
        recalls, precisions = [], []
        for t, row in zip(structure, base_rows):
            if row[3]:
                recalls.append(row[2]); precisions.append(row[1]); continue
            qv = np.array(vectors[t["question"]]); qv /= np.linalg.norm(qv)
            ranked = [chunks[i] for i in np.argsort(-(cm @ qv))]
            pieces = tc.within_budget(ranked, 5000)
            relevant = [p for p in pieces if any(tc.covers(*p, u) for u in units[t["id"]])]
            recall, _ = tc.recall_of(pieces, units[t["id"]])
            recalls.append(recall); precisions.append(len(relevant) / len(pieces))
            lines2.append(f"  [{label}] fallback used for {t['id']}: R {recall:.2f} P {len(relevant) / len(pieces):.2f} pieces {len(pieces)}")
        lines2.append(f"  [{label}] mean recall {np.mean(recalls):.2f} · mean precision over all 10 {np.mean(precisions):.2f}")
OUT.write_text(OUT.read_text() + "\n".join(lines2) + "\n")
print("\n".join(lines2))
