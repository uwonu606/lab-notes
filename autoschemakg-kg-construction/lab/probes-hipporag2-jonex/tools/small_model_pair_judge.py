import json, re, sys, urllib.request, itertools, math, random, time, collections

GLOSSARY, CHUNKS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
MODELS = sys.argv[4].split(',')
BAND_LO, BAND_HI = 0.6, 0.8
random.seed(20261012)

def text_processing(text):
    lowered = text.casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)

def embed(texts):
    return post("http://localhost:11434/api/embed", {"model": "bge-m3", "input": texts})["embeddings"]

def unit(v):
    n = math.sqrt(sum(x * x for x in v)); return [x / n for x in v]

entries = json.load(open(GLOSSARY, encoding="utf-8"))
name_to_entry, display = {}, {}
for idx, entry in enumerate(entries):
    for raw in [entry["canonical"], *entry.get("aliases", [])]:
        name = text_processing(raw)
        if name:
            name_to_entry.setdefault(name, set()).add(idx)
            display.setdefault(name, raw)
names = sorted(name_to_entry)
vec = {}
for s in range(0, len(names), 64):
    b = names[s:s + 64]
    for n, v in zip(b, embed(b)):
        vec[n] = unit(v)

chunks = [json.loads(l) for l in open(CHUNKS, encoding="utf-8")]
def context_for(raw):
    pat = re.escape(raw.casefold())
    for c in chunks:
        t = c["text"]; m = re.search(pat, t.casefold())
        if m:
            a, b = max(0, m.start() - 120), min(len(t), m.end() + 120)
            return re.sub(r"\s+", " ", t[a:b]).strip()
    return None

same, diff = [], []
for a, b in itertools.combinations(names, 2):
    s = sum(x * y for x, y in zip(vec[a], vec[b]))
    if BAND_LO <= s < BAND_HI:
        (same if name_to_entry[a] & name_to_entry[b] else diff).append((round(s, 3), a, b))
diff_sample = random.sample(diff, min(len(same), len(diff)))
pairs = [(s, a, b, True) for s, a, b in same] + [(s, a, b, False) for s, a, b in diff_sample]
random.shuffle(pairs)

PROMPT = ("Two names appear in internal notes, possibly written by different authors in Korean or English.\n"
          "Name A: {a}\nContext A: {ca}\nName B: {b}\nContext B: {cb}\n"
          "Do Name A and Name B refer to the same thing (same object, system, concept or document)? "
          "A part, a version, a sub-step or a related but different thing counts as no. Answer only yes or no.")

def judge(model, a, b):
    ca = context_for(display[a]) or "(no context found)"
    cb = context_for(display[b]) or "(no context found)"
    body = {"model": model, "stream": False, "think": False,
            "options": {"temperature": 0, "num_ctx": 4096},
            "messages": [{"role": "user", "content": PROMPT.format(a=display[a], b=display[b], ca=ca, cb=cb)}]}
    t0 = time.time()
    try:
        out = post("http://localhost:11434/api/chat", body)["message"]["content"]
    except Exception as e:
        return None, f"ERR {e}", time.time() - t0
    m = re.search(r"\b(yes|no)\b", out.casefold())
    return (m.group(1) == "yes") if m else None, out[:80], time.time() - t0

rows, lines = [], []
lines.append(f"band [{BAND_LO},{BAND_HI}): same {len(same)}, diff {len(diff)} (sampled {len(diff_sample)})")
for model in MODELS:
    tp = fp = fn = tn = bad = 0; secs = 0.0
    for s, a, b, gold in pairs:
        pred, raw, dt = judge(model, a, b); secs += dt
        rows.append({"model": model, "cos": s, "a": display[a], "b": display[b], "gold": gold, "pred": pred, "raw": raw})
        if pred is None: bad += 1
        elif pred and gold: tp += 1
        elif pred and not gold: fp += 1
        elif not pred and gold: fn += 1
        else: tn += 1
    p = tp / max(tp + fp, 1); r = tp / max(tp + fn, 1)
    # extrapolated to full band: diff sampled at rate len(diff_sample)/len(diff)
    scale = len(diff) / max(len(diff_sample), 1)
    p_full = tp / max(tp + fp * scale, 1)
    lines.append(f"{model}: n={len(pairs)} tp={tp} fp={fp} fn={fn} tn={tn} unparsable={bad} "
                 f"precision(sample)={p:.3f} recall={r:.3f} precision(full band est.)={p_full:.3f} sec/call={secs/len(pairs):.2f}")
    print(lines[-1], flush=True)
json.dump(rows, open(OUT + ".jsonl", "w", encoding="utf-8"), ensure_ascii=False)
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
