import json, re, sys, glob, os, math, itertools, urllib.request, collections
cache_dir = sys.argv[1]
def text_processing(text):
    lowered = text.casefold()
    kept = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in lowered)
    return re.sub(r"\s+", " ", kept).strip()
def embed(texts):
    body = json.dumps({"model": "bge-m3", "input": texts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/embed", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r: return json.load(r)["embeddings"]
def unit(v):
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v]
name_chunks = collections.defaultdict(set)
for p in sorted(glob.glob(os.path.join(cache_dir, '*_[0-9][0-9].json'))):
    d = json.load(open(p))
    for t in d.get('entity_relation_dict', []) or []:
        for k in ('Head', 'Tail'):
            e = t.get(k) if isinstance(t, dict) else None
            if isinstance(e, str) and text_processing(e):
                name_chunks[text_processing(e)].add(d['id'])
names = sorted(name_chunks)
vec = {}
for s in range(0, len(names), 64):
    b = names[s:s+64]
    for n, v in zip(b, embed(b)): vec[n] = unit(v)
bins = collections.Counter(); contain = collections.Counter(); cross_chunk = collections.Counter()
examples = collections.defaultdict(list)
for a, b in itertools.combinations(names, 2):
    s = sum(x*y for x, y in zip(vec[a], vec[b]))
    key = '>=0.9' if s >= 0.9 else '0.8-0.9' if s >= 0.8 else '0.7-0.8' if s >= 0.7 else '0.6-0.7' if s >= 0.6 else '<0.6'
    bins[key] += 1
    if a in b or b in a: contain[key] += 1
    if name_chunks[a] != name_chunks[b]: cross_chunk[key] += 1
    if key in ('>=0.9', '0.8-0.9') and len(examples[key]) < 12: examples[key].append((round(s,3), a, b))
total = len(names) * (len(names) - 1) // 2
print('unique names', len(names), 'pairs', total)
for k in ['>=0.9', '0.8-0.9', '0.7-0.8', '0.6-0.7', '<0.6']:
    print(f'{k}: pairs {bins[k]}, one name contains the other {contain[k]}, appear in different chunk sets {cross_chunk[k]}')
for k in ('>=0.9', '0.8-0.9'):
    print('examples', k)
    for e in examples[k]: print('  ', e)
hangul = re.compile('[가-힣]')
print('names failing official ASCII>2 gate', sum(1 for n in names if len(re.sub('[^A-Za-z0-9]', '', n)) <= 2), 'of which contain hangul', sum(1 for n in names if len(re.sub('[^A-Za-z0-9]', '', n)) <= 2 and hangul.search(n)))
print('names with unicode alnum length < 2', sum(1 for n in names if len(re.sub(r'[\W_]', '', n)) < 2))
