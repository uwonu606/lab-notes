import json, sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(sys.argv[1])
OUT = Path(sys.argv[2])
spec = spec_from_file_location("entry_weight", LAB / "19_entry_weight.py")
ew = module_from_spec(spec)
spec.loader.exec_module(ew)
sg, gg = ew.sg, ew.gg

entries = json.loads(sg.GLOSSARY.read_text())
chunks = sg.kgd.read_chunks()
gold = {(item["new"], link["old"]) for item in json.loads(sg.LINKS.read_text()) for link in item["links"]}
forms, df, shared = ew.shared_entries(chunks, entries)

variants = {
    "Adamic-Adar sum 1/log(df)": {pair: ew.adamic_adar(names, df) for pair, names in shared.items()},
    "node specificity sum 1/df (HippoRAG)": {pair: sum(1 / df[n] for n in names) for pair, names in shared.items()},
    "node specificity max 1/df": {pair: max(1 / df[n] for n in names) for pair, names in shared.items()},
}
lines = [f"gold pairs {len(gold)} · candidate pairs {len(shared)}"]
for label, scores in variants.items():
    points = ew.curve(scores, gold)
    best = ew.best_at_floor(points)
    lines.append(f"\n=== {label}")
    for threshold, found, p, r in points[:8]:
        lines.append(f"  >= {threshold:.4f}  found {found:3d}  P {p:.2f}  R {r:.2f}")
    lines.append(f"  best P with R >= {ew.RECALL_FLOOR}: {best}")
OUT.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
