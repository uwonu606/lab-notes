"""9단계 모르는 용어 층: 구심점 카드의 공개 이름을 문서마다 사내 별칭 하나로 바꾸고, 바뀐 문자 위치를 대응표로 옮긴다.

    import importlib
    cf = importlib.import_module("23_cf_layer")
    layer = cf.Layer.load()                                   # 카드(hubs.json) + 위치 대응표(inputs/net-corpus-cf/layer/posmap.jsonl)
    layer.cf_doc_id("gh-open5gs-001")                         # → "issue-123"
    layer.map_span("gh-open5gs-001", 1756, 1933)              # → ("issue-123", 새 start, 새 end)
    layer.orig_span("issue-123", 1760, 1940)                  # 거꾸로 → ("gh-open5gs-001", start, end)
    layer.replace_text("open5gs-amfd 가 …", "gh-open5gs-001")  # 그 문서가 쓰는 별칭으로 바꾼 글 (레코드 칸 값 같은 LLM 글)
    layer.leaks("바꾼 글")                                    # 남은 공개 이름 [Leak]

    python3 23_cf_layer.py build      # 사내화 말뭉치·단위·대응표 → inputs/net-corpus-cf/, runs/23-cf-units/
    python3 23_cf_layer.py leaks      # 바꾼 문서·단위의 새는 공개 이름 → runs/23-cf-units/leaks.json
    python3 23_cf_layer.py selftest   # 가짜 카드로 바꾸기·위치 대응을 시험한다

위치 대응: 바꾼 자리 [s, e) 안에 떨어지는 위치는 구간이 바깥쪽으로 넓어지게 옮긴다(시작은 새 자리의 시작, 끝은 새 자리의 끝).
대응표와 doc_id 대응은 공개 이름을 담고 있어서 색인·질의 코드가 읽으면 안 된다. 옮기는 코드와 채점·보고 코드만 읽는다.
"""
import argparse
import hashlib
import json
import re
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/net-corpus"
DOCS = CORPUS / "docs.jsonl"
HUBS = CORPUS / "relglossary/hubs.json"
UNITS_DIR = LAB / "runs/23-net-units"
CF_CORPUS = LAB / "inputs/net-corpus-cf"
CF_DOCS = CF_CORPUS / "docs.jsonl"
LAYER_DIR = CF_CORPUS / "layer"
POSMAP = LAYER_DIR / "posmap.jsonl"
CF_UNITS_DIR = LAB / "runs/23-cf-units"
UNIT_KINDS = ("fixed", "section", "claim", "doc")

SHORT_FORM = 3
IDENT_JOINERS = "-_/.:"


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Hub:
    id: str
    kind: str
    public_names: tuple
    internal_names: tuple
    slug: str


def hub_from_row(row):
    public = row.get("public") or {}
    public_names = [row.get("public_name"), *row.get("public_aliases", []), public.get("name"), *public.get("aliases", []),
                    *row.get("public_names", [])]
    internal = [row.get("name") or row.get("internal_name"), *(row.get("aliases") or row.get("internal_aliases") or [])]
    internal_names = tuple(n for n in dict.fromkeys(internal) if n and n.strip())
    return Hub(id=row["id"], kind=row.get("kind") or row.get("type", ""),
               public_names=tuple(n for n in dict.fromkeys(public_names) if n and n.strip()),
               internal_names=internal_names,
               slug=row.get("slug") or row.get("internal_slug") or default_slug(row["id"], internal_names))


def default_slug(hub_id, internal_names):
    """카드에 slug 가 없으면 사내 이름 가운데 라틴 코드(PJ-417)를 소문자로 쓴다. 코드도 없으면 id 해시로 만든다."""
    code = next((n for n in internal_names if re.fullmatch(r"[A-Za-z0-9-]+", n)), None)
    return code.lower() if code else "x" + hashlib.sha256(hub_id.encode()).hexdigest()[:5]


def read_hubs(path=HUBS):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    hubs = [hub_from_row(row) for row in (data["hubs"] if isinstance(data, dict) else data)]
    problems = card_problems(hubs)
    if problems:
        raise ValueError("카드 문제:\n" + "\n".join(problems))
    return hubs


def card_problems(hubs):
    problems, owner = [], {}
    for hub in hubs:
        if not hub.public_names or not hub.internal_names:
            problems.append(f"{hub.id}: 공개 이름 {len(hub.public_names)}개, 사내 이름 {len(hub.internal_names)}개")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", hub.slug or ""):
            problems.append(f"{hub.id}: slug {hub.slug!r} 가 ASCII 소문자 식별자가 아니다")
        for form in hub.public_names:
            key = form.casefold()
            if key in owner and owner[key] != hub.id:
                problems.append(f"공개 표기 {form!r} 가 {owner[key]} 와 {hub.id} 두 카드에 있다")
            owner[key] = hub.id
    matcher = Matcher(hubs)
    for hub in hubs:
        for internal in (*hub.internal_names, hub.slug):
            for leak in matcher.leaks(internal):
                problems.append(f"{hub.id}: 사내 표기 {internal!r} 에 공개 표기 {leak.form!r}({leak.hub}) 가 들어 있다")
    return problems


def is_ascii_alnum(ch):
    return ch.isascii() and ch.isalnum()


def digit_edges(form, body):
    """숫자로 끝나는 표기는 뒤에 숫자가 오면, 숫자로 시작하는 표기는 앞에 숫자가 오면 맞추지 않는다(N210 은 SN2100 이 아니다)."""
    return ("(?<![0-9])" if form[0].isdigit() else "") + body + ("(?![0-9])" if form[-1].isdigit() else "")


def form_regex(form):
    """공개 표기 하나의 정규식. 3글자 이하는 대소문자를 지키고 영숫자 경계를 두며, 4글자 이상은 대소문자를 무시하고 낱말 안에서도 맞춘다."""
    body = r"[ \t_-]?".join(re.escape(part) for part in form.split(" ")) if " " in form else re.escape(form)
    if not form.isascii():
        return body
    edge = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"
    if len(form) <= SHORT_FORM:
        lower = re.escape(form.lower())
        in_identifier = rf"(?<![A-Za-z0-9]){lower}(?=[{re.escape(IDENT_JOINERS)}][A-Za-z0-9])|(?<=[A-Za-z0-9][{re.escape(IDENT_JOINERS)}]){lower}(?![A-Za-z0-9])"
        return edge.format(body) + ("|" + in_identifier if lower != form else "")
    return "(?i:" + digit_edges(form, body) + ")"


def leak_regex(form):
    if not form.isascii():
        return re.escape(form)
    if len(form) <= SHORT_FORM:
        return r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])".format(re.escape(form))
    return digit_edges(form, re.escape(form))


@dataclass(frozen=True)
class Found:
    start: int
    end: int
    hub: str
    form: str


Leak = Found


class Matcher:
    def __init__(self, hubs):
        forms = sorted({(form, hub.id) for hub in hubs for form in hub.public_names}, key=lambda fh: (-len(fh[0]), fh[0]))
        self.forms = forms
        self.pattern = re.compile("|".join(f"(?P<f{n}>{form_regex(form)})" for n, (form, _) in enumerate(forms)))
        self.leak_patterns = [(form, hub, re.compile(leak_regex(form), 0 if form.isascii() and len(form) <= SHORT_FORM else re.I))
                              for form, hub in forms]

    def find(self, text):
        found = []
        for m in self.pattern.finditer(text):
            form, hub = self.forms[int(m.lastgroup[1:])]
            found.append(Found(m.start(), m.end(), hub, form))
        return found

    def leaks(self, text):
        """바꾸기와 따로 짠 검사: 4글자 이상 표기는 대소문자 무시 부분 문자열(숫자 경계만), 3글자 이하는 대소문자를 지킨 영숫자 경계."""
        return sorted({Found(m.start(), m.end(), hub, form) for form, hub, p in self.leak_patterns for m in p.finditer(text)},
                      key=lambda f: (f.start, -f.end))


def in_identifier(text, start, end):
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if is_ascii_alnum(before) or is_ascii_alnum(after):
        return True
    if before and before in IDENT_JOINERS and start >= 2 and is_ascii_alnum(text[start - 2]):
        return True
    return bool(after) and after in IDENT_JOINERS and end + 1 < len(text) and is_ascii_alnum(text[end + 1])


def pick_internal(hub, key, avoid=()):
    """key(원래 doc_id 등)의 해시로 사내 이름 하나를 고른다. avoid 에 든 이름은 다른 것이 있으면 피한다."""
    choices = [n for n in hub.internal_names if n not in avoid] or list(hub.internal_names)
    digest = int(hashlib.sha256(f"{key}|{hub.id}".encode()).hexdigest(), 16)
    return choices[digest % len(choices)]


@dataclass(frozen=True)
class Op:
    start: int
    end: int
    new_start: int
    new_end: int
    hub: str
    form: str
    text: str

    def row(self):
        return [self.start, self.end, self.new_start, self.new_end, self.hub, self.form, self.text]


class Rewriter:
    def __init__(self, hubs):
        self.hubs = {hub.id: hub for hub in hubs}
        self.matcher = Matcher(hubs)

    def rewrite(self, text, key, choose=None):
        """(바꾼 글, [Op]). choose(hub) 가 있으면 그 이름을, 없으면 key 해시로 고른 사내 이름을 쓴다. 식별자 안이면 slug 를 쓴다."""
        pieces, ops, cursor, shift = [], [], 0, 0
        for f in self.matcher.find(text):
            hub = self.hubs[f.hub]
            new = hub.slug if in_identifier(text, f.start, f.end) else (choose(hub) if choose else pick_internal(hub, key))
            pieces.append(text[cursor:f.start])
            new_start = f.start + shift
            ops.append(Op(f.start, f.end, new_start, new_start + len(new), f.hub, text[f.start:f.end], new))
            pieces.append(new)
            shift += len(new) - (f.end - f.start)
            cursor = f.end
        pieces.append(text[cursor:])
        return "".join(pieces), ops

    def replace(self, text, key, choose=None):
        return self.rewrite(text, key, choose)[0]


class DocMap:
    def __init__(self, ops):
        self.ops = ops
        self.starts = [op.start for op in ops]

    def pos(self, p, side):
        i = bisect_right(self.starts, p) - 1
        if i < 0:
            return p
        op = self.ops[i]
        if p == op.start:
            return op.new_start
        if p < op.end:
            return op.new_start if side == "start" else op.new_end
        return p + (op.new_end - op.end)

    def span(self, start, end):
        return self.pos(start, "start"), self.pos(end, "end")

    def hubs_in(self, start, end):
        return sorted({op.hub for op in self.ops if op.start < end and start < op.end})


def cf_doc_ids(docs):
    """원래 문서 순서대로 종류마다 번호를 매긴다: issue-001, blog-001 …. 공개 이름이 든 원래 id(gh-open5gs-001)를 지운다."""
    counters, mapping = Counter(), {}
    for doc in docs:
        counters[doc["kind"]] += 1
        mapping[doc["doc_id"]] = f"{doc['kind']}-{counters[doc['kind']]:03d}"
    return mapping


def cf_unit_id(unit_id, doc_id, doc_map):
    return doc_map[doc_id] + unit_id[len(doc_id):]


class Layer:
    def __init__(self, hubs, posmap_rows):
        self.hubs = {hub.id: hub for hub in hubs}
        self.rewriter = Rewriter(hubs)
        self.doc_maps = {r["doc_id"]: DocMap([Op(*op) for op in r["ops"]]) for r in posmap_rows}
        self.reverse_maps = {r["cf_doc_id"]: DocMap([Op(ns, ne, s, e, hub, text, form) for s, e, ns, ne, hub, form, text in r["ops"]])
                             for r in posmap_rows}
        self.to_cf = {r["doc_id"]: r["cf_doc_id"] for r in posmap_rows}
        self.to_orig = {cf: orig for orig, cf in self.to_cf.items()}

    @classmethod
    def load(cls, hubs_path=HUBS, posmap_path=POSMAP):
        return cls(read_hubs(hubs_path), read_jsonl(posmap_path))

    def cf_doc_id(self, doc_id):
        return self.to_cf[doc_id]

    def orig_doc_id(self, cf_doc_id):
        return self.to_orig[cf_doc_id]

    def map_span(self, doc_id, start, end):
        """원래 문서의 [start, end) → (사내화 doc_id, 새 start, 새 end). 바꾼 이름에 걸친 끝은 바깥쪽으로 넓힌다."""
        return (self.to_cf[doc_id], *self.doc_maps[doc_id].span(start, end))

    def orig_span(self, cf_doc_id, start, end):
        """map_span 의 거꾸로: 사내화 문서의 [start, end) → (원래 doc_id, start, end)."""
        return (self.to_orig[cf_doc_id], *self.reverse_maps[cf_doc_id].span(start, end))

    def map_unit_id(self, unit_id, doc_id):
        return cf_unit_id(unit_id, doc_id, self.to_cf)

    def replace_text(self, text, doc_id):
        """그 문서가 쓰는 사내 이름으로 글을 바꾼다. doc_id 는 원래 id. 문서에 묶이지 않은 글은 아무 고정 문자열을 key 로 준다."""
        return self.rewriter.replace(text, doc_id)

    def leaks(self, text):
        return self.rewriter.matcher.leaks(text)

    def hubs_in(self, doc_id, start=0, end=None):
        ops = self.doc_maps[doc_id].ops
        return sorted({op.hub for op in ops if end is None or (op.start < end and start < op.end)})

    def internal_used(self, doc_id, hub_id):
        """그 문서 본문에서 hub 를 바꾼 사내 이름별 수. 식별자 slug 는 그 slug 를 낸 라틴 코드 이름(PJ-417 ↔ pj-417)으로 센다."""
        hub = self.hubs[hub_id]
        slug_owner = next((n for n in hub.internal_names if n.lower() == hub.slug), None)
        used = Counter(slug_owner if op.text == hub.slug else op.text for op in self.doc_maps[doc_id].ops if op.hub == hub_id)
        used.pop(None, None)
        return used


def rewrite_value(value, key, rewriter):
    if isinstance(value, str):
        return rewriter.replace(value, key)
    if isinstance(value, list):
        return [rewrite_value(v, key, rewriter) for v in value]
    if isinstance(value, dict):
        return {k: rewrite_value(v, key, rewriter) for k, v in value.items()}
    return value


def rewrite_meta(meta, key, rewriter, doc_map):
    meta = rewrite_value(meta, key, rewriter)
    for post in meta.get("posts", []):
        post["start"], post["end"] = doc_map.span(post["start"], post["end"])
    for omitted in meta.get("omitted", []):
        omitted["at"] = doc_map.pos(omitted["at"], "start")
    return meta


def build_docs(hubs, docs):
    rewriter = Rewriter(hubs)
    id_map = cf_doc_ids(docs)
    cf_docs, posmap = [], []
    for doc in docs:
        key = doc["doc_id"]
        text, ops = rewriter.rewrite(doc["text"], key)
        doc_map = DocMap(ops)
        cf = {k: rewrite_value(v, key, rewriter) for k, v in doc.items() if k not in ("doc_id", "text", "meta")}
        cf_docs.append({"doc_id": id_map[key], **cf, "text": text, "meta": rewrite_meta(doc.get("meta", {}), key, rewriter, doc_map)})
        posmap.append({"doc_id": key, "cf_doc_id": id_map[key], "ops": [op.row() for op in ops]})
    return cf_docs, posmap


def move_unit(row, layer, cf_text_of, rewriter):
    doc_id = row["doc_id"]
    new_doc, start, end = layer.map_span(doc_id, row["start"], row["end"])
    moved = {**row, "unit_id": layer.map_unit_id(row["unit_id"], doc_id), "doc_id": new_doc, "start": start, "end": end,
             "text": cf_text_of[new_doc][start:end]}
    if "id" in moved:
        moved["id"] = moved["unit_id"]
    for parent in ("parent_section", "parent_doc"):
        if parent in moved:
            moved[parent] = layer.map_unit_id(row[parent], doc_id)
    if "title" in moved:
        moved["title"] = rewriter.replace(row["title"], doc_id)
    return moved


def move_tree(row, layer, rewriter):
    doc_id = row["doc_id"]
    doc_map = layer.doc_maps[doc_id]
    moved = {**row, "doc_id": layer.cf_doc_id(doc_id), "title": rewriter.replace(row["title"], doc_id)}
    moved["start"], moved["end"] = doc_map.span(row["start"], row["end"])
    moved["blocks"] = [{**b, "label": rewriter.replace(b["label"], doc_id), "start": doc_map.pos(b["start"], "start"),
                        "end": doc_map.pos(b["end"], "end"), "sections": [layer.map_unit_id(s, doc_id) for s in b["sections"]]}
                       for b in row["blocks"]]
    return moved


def build(hubs_path=HUBS, docs_path=DOCS, units_dir=UNITS_DIR, out_docs=CF_DOCS, out_units=CF_UNITS_DIR, posmap_path=POSMAP):
    hubs = read_hubs(hubs_path)
    docs = read_jsonl(docs_path)
    cf_docs, posmap = build_docs(hubs, docs)
    write_jsonl(out_docs, cf_docs)
    write_jsonl(posmap_path, posmap)
    layer = Layer(hubs, posmap)
    rewriter = layer.rewriter
    cf_text_of = {d["doc_id"]: d["text"] for d in cf_docs}
    orig_text_of = {d["doc_id"]: d["text"] for d in docs}
    stats = {"docs": len(cf_docs), "ops": sum(len(r["ops"]) for r in posmap),
             "ops_by_hub": dict(Counter(op[4] for r in posmap for op in r["ops"]).most_common()),
             "slug_ops": sum(op[6] == layer.hubs[op[4]].slug for r in posmap for op in r["ops"]),
             "docs_with_ops": sum(bool(r["ops"]) for r in posmap), "units": {}}
    for kind in UNIT_KINDS:
        rows = read_jsonl(units_dir / f"{kind}.jsonl")
        moved = [move_unit(r, layer, cf_text_of, rewriter) for r in rows]
        widened = sum(rewriter.replace(r["text"], r["doc_id"]) != m["text"] for r, m in zip(rows, moved))
        orig_ok = sum(orig_text_of[r["doc_id"]][r["start"]:r["end"]] == r["text"] for r in rows)
        write_jsonl(out_units / f"{kind}.jsonl", moved)
        stats["units"][kind] = {"rows": len(rows), "orig_text_matches_doc": orig_ok, "differs_from_replaced_text": widened,
                                "touched": sum(bool(layer.doc_maps[r["doc_id"]].hubs_in(r["start"], r["end"])) for r in rows)}
    tree = read_jsonl(units_dir / "section-tree.jsonl")
    write_jsonl(out_units / "section-tree.jsonl", [move_tree(r, layer, rewriter) for r in tree])
    stats["inputs"] = {"hubs_sha256": sha256_of(hubs_path), "docs_sha256": sha256_of(docs_path),
                       **{f"{k}_sha256": sha256_of(units_dir / f"{k}.jsonl") for k in UNIT_KINDS}}
    stats["outputs"] = {"cf_docs_sha256": sha256_of(out_docs), "posmap_sha256": sha256_of(posmap_path),
                        **{f"{k}_sha256": sha256_of(out_units / f"{k}.jsonl") for k in UNIT_KINDS}}
    (out_units / "build-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    return stats


def strings_of(value, where=""):
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, list):
        for n, v in enumerate(value):
            yield from strings_of(v, f"{where}[{n}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from strings_of(v, f"{where}.{k}" if where else k)


def leak_report(layer, docs_path=CF_DOCS, units_dir=CF_UNITS_DIR, context=40):
    """문서의 모든 글 칸과 단위의 text·title 에서 남은 공개 이름. 표기별 수와 앞뒤 글 예."""
    by_form, examples, total = Counter(), defaultdict(list), Counter()
    sources = [("docs", r["doc_id"], r) for r in read_jsonl(docs_path)]
    sources += [(kind, r["unit_id"], {k: r[k] for k in ("text", "title") if k in r}) for kind in UNIT_KINDS
                for r in read_jsonl(units_dir / f"{kind}.jsonl")]
    sources += [("section-tree", r["doc_id"], r) for r in read_jsonl(units_dir / "section-tree.jsonl")]
    for source, ident, row in sources:
        for where, text in strings_of(row):
            for leak in layer.leaks(text):
                by_form[(source, leak.hub, leak.form)] += 1
                total[source] += 1
                if len(examples[leak.form]) < 5 and source == "docs":
                    examples[leak.form].append({"doc_id": ident, "field": where,
                                                "context": text[max(0, leak.start - context):leak.end + context]})
    return {"total": dict(total), "by_form": [{"source": s, "hub": h, "form": f, "count": c} for (s, h, f), c in by_form.most_common()],
            "examples": dict(examples)}


FAKE_HUBS = [
    {"id": "open5gs", "kind": "software", "name": "누리코어", "aliases": ["NC랩코어", "청솔"], "slug": "nuricore",
     "public": {"name": "Open5GS", "aliases": ["Open 5GC"]}, "facts": [{"text": "Open5GS 기반 5G 코어", "invented": False}]},
    {"id": "free5gc", "kind": "software", "name": "바람코어", "aliases": ["BR코어"], "slug": "baramcore",
     "public": {"name": "free5GC", "aliases": ["F5GC"]}, "facts": [{"text": "free5GC 기반 5G 코어", "invented": False}]},
    {"id": "kt", "kind": "operator", "name": "동쪽망", "aliases": ["E사"], "slug": "eastnet",
     "public": {"name": "KT", "aliases": ["케이티"]}, "facts": [{"text": "국내 통신사 KT", "invented": False}]},
    {"id": "usrp-n210", "kind": "ran-component", "internal_name": "너울", "internal_aliases": ["KQ-77"],
     "public_name": "USRP N210", "public_aliases": ["N210", "USRP"], "facts": []},
]


def selftest():
    hubs = [hub_from_row(r) for r in FAKE_HUBS]
    assert not card_problems(hubs), card_problems(hubs)
    rewriter = Rewriter(hubs)
    text = ("Open5GS 2.4.2 를 k8s 에 올렸는데 open5gs-ausf 가 /etc/open5gs/amf.yaml 을 못 읽음. OPEN5GS 와 free5GC, F5GC, "
            "KT 과제(케이티)에서 PKT 와 kt-lab, libopen5gs, Open 5GC, Open5GS. N210 과 SN2100, USRPs.")
    new, ops = rewriter.rewrite(text, "doc-a")
    doc_map = DocMap(ops)
    for op in ops:
        assert new[op.new_start:op.new_end] == op.text, op
        assert doc_map.span(op.start, op.end) == (op.new_start, op.new_end)
    assert "SN2100" in new and "N210 " not in new
    assert "PKT" in new and "eastnet-lab" in new and "/etc/nuricore/" in new and "nuricore-ausf" in new and "libnuricore" in new
    assert not rewriter.matcher.leaks(new), rewriter.matcher.leaks(new)
    anchor = text.index("를 k8s")
    assert new[doc_map.pos(anchor, "start"):].startswith("를 k8s")
    inside = text.index("open5gs-ausf") + 3
    assert doc_map.span(inside, inside + 10)[0] == new.index("nuricore-ausf")
    assert pick_internal(hubs[0], "doc-a") == pick_internal(hubs[0], "doc-a")
    assert pick_internal(hubs[0], "doc-a", avoid={pick_internal(hubs[0], "doc-a")}) != pick_internal(hubs[0], "doc-a")
    bad = [hub_from_row({**FAKE_HUBS[0], "aliases": ["오픈Open5GS"]})]
    assert card_problems(bad)
    print("selftest 통과")
    print(new)


def main():
    parser = argparse.ArgumentParser(description="모르는 용어 층: 사내화 말뭉치·단위·대응표를 만들고 새는 이름을 센다.")
    parser.add_argument("command", choices=["build", "leaks", "selftest"])
    parser.add_argument("--hubs", default=str(HUBS))
    args = parser.parse_args()
    if args.command == "selftest":
        selftest()
    elif args.command == "build":
        print(json.dumps(build(Path(args.hubs)), ensure_ascii=False, indent=1))
    else:
        report = leak_report(Layer.load(Path(args.hubs)))
        (CF_UNITS_DIR / "leaks.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"total": report["total"], "by_form": report["by_form"][:40]}, ensure_ascii=False, indent=1))
        sys.exit(1 if report["total"] else 0)


if __name__ == "__main__":
    main()
