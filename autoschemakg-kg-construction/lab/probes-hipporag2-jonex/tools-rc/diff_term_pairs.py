import json, sys, re
chunks = [json.loads(l) for l in open(sys.argv[1])]
glossary = json.load(open(sys.argv[2]))
def forms_in(text, forms):
    low = text.casefold(); found = set()
    for f in forms:
        f2 = f.casefold()
        if re.fullmatch(r"[a-z0-9 ._-]+", f2):
            if re.search(r"(?<![a-z0-9])" + re.escape(f2) + r"(?![a-z0-9])", low): found.add(f2)
        elif f2 in low: found.add(f2)
    return found
new = [c for c in chunks if c["id"].startswith("doc-parsing-chunking")]
old = [c for c in chunks if not c["id"].startswith("doc-parsing-chunking")]
pairs_same, pairs_diff, examples = set(), set(), []
for e in glossary:
    forms = [e["canonical"]] + e.get("aliases", [])
    for n in new:
        fn = forms_in(n["text"], forms)
        if not fn: continue
        for o in old:
            fo = forms_in(o["text"], forms)
            if not fo: continue
            if fn & fo: pairs_same.add((n["id"], o["id"]))
            else:
                pairs_diff.add((n["id"], o["id"])); examples.append((e["canonical"], sorted(fn), sorted(fo), n["id"], o["id"]))
only_diff = pairs_diff - pairs_same
print("new chunks", len(new), "old", len(old))
print("pairs sharing an entry with a common surface form", len(pairs_same))
print("pairs linked only through different surface forms of one entry", len(only_diff))
for ex in examples[:12]:
    if (ex[3], ex[4]) in only_diff: print(" ", ex)
