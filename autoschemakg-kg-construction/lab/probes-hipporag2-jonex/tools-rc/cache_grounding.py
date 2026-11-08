import json, sys, os, re, unicodedata
from collections import Counter

def norm(s):
    s = unicodedata.normalize("NFKC", s).casefold()
    return re.sub(r"\s+", " ", s).strip()

cache_dir = sys.argv[1]
files = sorted(f for f in os.listdir(cache_dir) if f.endswith(".json") and "#" not in f and f != "embeddings.json")
stats = Counter()
nodes_per_chunk = []
for f in files:
    c = json.load(open(os.path.join(cache_dir, f)))
    if "original_text" not in c:
        continue
    stats["chunks"] += 1
    text = norm(c["original_text"])
    ents = set()
    for t in c.get("entity_relation_dict") or []:
        h, r, tl = (t.get("Head") or ""), (t.get("Relation") or ""), (t.get("Tail") or "")
        stats["triples"] += 1
        hin = norm(h) in text and norm(h) != ""
        tin = norm(tl) in text and norm(tl) != ""
        stats["head_in"] += hin
        stats["tail_in"] += tin
        stats["both_in"] += (hin and tin)
        ents.update([norm(h), norm(tl)])
    nodes_per_chunk.append(len(ents))
    for ev in c.get("event_entity_dict") or []:
        e = ev.get("Event") or ""
        stats["events"] += 1
        stats["event_verbatim"] += (norm(e) in text and norm(e) != "")
        stats["event_chars"] += len(e)
    if not (c.get("entity_relation_dict") or []):
        stats["chunks_no_triples"] += 1
print(dict(stats))
print("both_in ratio", stats["both_in"] / max(1, stats["triples"]))
print("event verbatim ratio", stats["event_verbatim"] / max(1, stats["events"]))
print("avg event chars", stats["event_chars"] / max(1, stats["events"]))
print("avg unique phrases per chunk", sum(nodes_per_chunk) / max(1, len(nodes_per_chunk)))
