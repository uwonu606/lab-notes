import json, sys, os

cache_dir, evidence_path = sys.argv[1], sys.argv[2]
COVER = 0.5
evidence = json.load(open(evidence_path))

def chunk_file(cid):
    return os.path.join(cache_dir, cid.replace("#", "_") + ".json")

def verbatim_spans(cid):
    c = json.load(open(chunk_file(cid)))
    text = c["original_text"]
    spans = []
    for ev in c.get("event_entity_dict") or []:
        e = (ev.get("Event") or "").strip()
        if not e:
            continue
        at = text.find(e)
        if at >= 0:
            spans.append((at, at + len(e)))
    return text, spans

def covered(units_for_chunk, text, spans):
    for excerpt in units_for_chunk:
        at = text.find(excerpt)
        if at < 0:
            continue
        s, e = at, at + len(excerpt)
        if any(min(e, b) - max(s, a) >= COVER * (e - s) for a, b in spans):
            return True
    return False

for section in ("questions", "structure"):
    total = hit = 0
    per_q_all = []
    for key, per_chunk in evidence[section].items():
        allhit = True
        for cid, excerpts in per_chunk.items():
            text, spans = verbatim_spans(cid)
            total += 1
            h = covered(excerpts, text, spans)
            hit += h
            allhit &= h
        per_q_all.append(allhit)
    print(section, "gold units", total, "covered by >=1 verbatim event", hit, round(hit / total, 3), "items fully covered", sum(per_q_all), "/", len(per_q_all))
