import json
import math
import sys
from collections import Counter, defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(__file__).parent
spec = spec_from_file_location("glossary_grow", LAB / "18_glossary_grow.py")
gg = module_from_spec(spec)
spec.loader.exec_module(gg)
sg = gg.sg

RECALL_FLOOR = 0.9


def matched_forms(text, entries):
    forms = {}
    for e in entries:
        hits = [f for f in [e["canonical"], *e["aliases"]] if gg.mentions(f, text)]
        if hits:
            forms[e["canonical"]] = hits
    return forms


def shared_entries(chunks, entries):
    forms = {c["id"]: matched_forms(c["text"], entries) for c in chunks}
    df = Counter(name for f in forms.values() for name in f)
    shared = {}
    for n in (c for c in forms if c.startswith(sg.NEW_DOC)):
        for o in (c for c in forms if not c.startswith(sg.NEW_DOC)):
            common = forms[n].keys() & forms[o].keys()
            if common:
                shared[n, o] = common
    return forms, df, shared


def adamic_adar(names, df):
    return sum(1 / math.log(df[name]) for name in names)


def purged(shared, df, total, ratio):
    return {pair: names for pair, names in shared.items() if any(df[name] <= ratio * total for name in names)}


def curve(scores, gold):
    points = []
    for threshold in sorted(set(scores.values()), reverse=True):
        found = {pair for pair, s in scores.items() if s >= threshold}
        p, r = sg.precision_recall(found, gold)
        points.append((threshold, len(found), p, r))
    return points


def best_at_floor(points):
    kept = [pt for pt in points if pt[3] >= RECALL_FLOOR]
    return max(kept, key=lambda pt: (pt[2], pt[3])) if kept else None


def via_alias_only(name, pair, forms):
    return any(all(f.casefold() != name.casefold() for f in forms[c][name]) for c in pair)


def error_kind(pair, names, forms):
    return "alias" if all(via_alias_only(name, pair, forms) for name in names) else "entry"


def report(label, entries, chunks, gold):
    forms, df, shared = shared_entries(chunks, entries)
    total = len(chunks)
    lines = [f"\n=== {label}: entries {len(entries)} · chunks {total} · candidate pairs {len(shared)}"]

    variants = {
        "shared count >= k": {pair: len(names) for pair, names in shared.items()},
        "Adamic-Adar sum 1/log(df)": {pair: adamic_adar(names, df) for pair, names in shared.items()},
    }
    chosen = {}
    for name, scores in variants.items():
        points = curve(scores, gold)
        best = best_at_floor(points)
        chosen[name] = {pair for pair, s in scores.items() if best and s >= best[0]}
        lines.append(f"  {name}")
        for threshold, n, p, r in points[-6:][::-1] if name.startswith("shared") else points:
            if name.startswith("shared") or r >= 0.6:
                lines.append(f"      >= {threshold:6.3f}  found {n:3}  P {p:.2f}  R {r:.2f}")
        if best:
            lines.append(f"    best P with R >= {RECALL_FLOOR}: threshold {best[0]:.3f} · found {best[1]} · P {best[2]:.2f} · R {best[3]:.2f}")

    for ratio in (0.5, 0.45):
        kept = purged(shared, df, total, ratio)
        dropped = sorted((n for n in df if df[n] > ratio * total), key=lambda n: -df[n])
        p, r = sg.precision_recall(set(kept), gold)
        name = f"drop entries in > {int(ratio * 100)}% of chunks"
        chosen[name] = set(kept)
        lines.append(f"  {name}: dropped {dropped} · found {len(kept)} · P {p:.2f} · R {r:.2f}")

    for name, found in chosen.items():
        wrong = found - gold
        kinds = Counter(error_kind(pair, shared[pair], forms) for pair in wrong)
        culprits = Counter(n for pair in wrong for n in shared[pair])
        missed = gold - found
        lines.append(f"  residual errors under '{name}': {len(wrong)} wrong · by kind {dict(kinds)} · missed gold {len(missed)}")
        lines.append(f"      most shared in wrong pairs: {[(n, c, df[n]) for n, c in culprits.most_common(8)]}  (entry, wrong pairs, df)")
        for pair in sorted(missed):
            lines.append(f"      missed {pair[0]} <-> {pair[1]} via {[(n, df[n]) for n in sorted(shared.get(pair, []))]}")
    return "\n".join(lines)


def main(*glossary_paths):
    chunks = sg.kgd.read_chunks()
    gold = {(l["new"], x["old"]) for l in json.loads(sg.LINKS.read_text()) for x in l["links"]}
    base, _ = sg.read_glossary()
    variants = {"original 150": base}
    for path in glossary_paths:
        variants[Path(path).stem] = json.loads(Path(path).read_text())
    print(f"gold pairs {len(gold)}")
    for label, entries in variants.items():
        print(report(label, entries, chunks, gold))


if __name__ == "__main__":
    main(*sys.argv[1:])
