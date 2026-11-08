import json, re, sys, glob, os, collections
cache_dir = sys.argv[1]
HANGUL = re.compile('[가-힣]')
def norm(s):
    return re.sub(r'\s+', ' ', s).strip().casefold()
def ascii_ok(e):
    return len(re.sub('[^A-Za-z0-9]', '', e)) > 2
def text_processing(s):
    s = s.lower()
    s = ''.join(c if (c.isalnum() or c.isspace()) else ' ' for c in s)
    return re.sub(r'\s+', ' ', s).strip()
stats = collections.Counter()
chunk_hangul_ratio = []
per_chunk = []
names_all = set()
for path in sorted(glob.glob(os.path.join(cache_dir, '*#*.json')) + glob.glob(os.path.join(cache_dir, '*_[0-9][0-9].json'))):
    d = json.load(open(path))
    text = d.get('original_text', '')
    ntext = norm(text)
    hg = len(HANGUL.findall(text)); 
    letters = sum(1 for c in text if c.isalpha())
    chunk_hangul_ratio.append(hg / max(letters,1))
    triples = d.get('entity_relation_dict', []) or []
    c = collections.Counter()
    for t in triples:
        if not isinstance(t, dict): continue
        for k in ('Head', 'Tail'):
            e = t.get(k)
            if not isinstance(e, str) or not e.strip(): continue
            c['names'] += 1
            names_all.add(text_processing(e))
            if HANGUL.search(e): c['hangul_name'] += 1
            if norm(e) in ntext: c['verbatim'] += 1
            if ascii_ok(text_processing(e)): c['ascii_ok'] += 1
        h, tl = t.get('Head'), t.get('Tail')
        if isinstance(h, str) and isinstance(tl, str):
            c['triples'] += 1
            if norm(h) in ntext and norm(tl) in ntext: c['both_verbatim'] += 1
    stats.update(c)
    per_chunk.append((d.get('id', os.path.basename(path)), hg / max(letters,1), c['triples'], c['both_verbatim'], c['hangul_name'], c['names']))
print('chunks', len(per_chunk))
print('triples', stats['triples'], 'names', stats['names'])
print('name verbatim in chunk (casefold, ws-normalized):', stats['verbatim'], round(stats['verbatim']/max(stats['names'],1),3))
print('triple with both ends verbatim:', stats['both_verbatim'], round(stats['both_verbatim']/max(stats['triples'],1),3))
print('names containing hangul:', stats['hangul_name'], round(stats['hangul_name']/max(stats['names'],1),3))
print('names passing HippoRAG.py:1333 ascii>2 (after text_processing):', stats['ascii_ok'], round(stats['ascii_ok']/max(stats['names'],1),3))
print('unique normalized names', len(names_all))
hr = sorted(chunk_hangul_ratio)
print('chunk hangul share of letters: median', round(hr[len(hr)//2],3), 'min', round(hr[0],3), 'max', round(hr[-1],3))
# korean-heavy chunks (hangul share >= 0.5)
kh = [p for p in per_chunk if p[1] >= 0.5]
tk = sum(p[2] for p in kh); bk = sum(p[3] for p in kh); hk = sum(p[4] for p in kh); nk = sum(p[5] for p in kh)
print('korean-heavy chunks (>=0.5 hangul):', len(kh), 'triples', tk, 'both verbatim', bk, round(bk/max(tk,1),3), 'hangul names', hk, '/', nk, round(hk/max(nk,1),3))
