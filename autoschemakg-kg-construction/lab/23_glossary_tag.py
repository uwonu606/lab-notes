"""용어집 태거: 텍스트 구간에 걸리는 용어집 항목, 그 항목의 상위 개념, 연도·버전 같은 값 개념을 매칭 근거와 함께 낸다.

    from importlib import import_module
    tagger = import_module("23_glossary_tag").GlossaryTagger()
    tagger.tag_span("gh-frr-009", 0, 1200)   # {"entries": [...], "concepts": [...], "values": [...]}
    tagger.tag_text("SMF 가 PFCP 세션을 못 맺는다")

    python3 23_glossary_tag.py span gh-frr-009 0 1200
    python3 23_glossary_tag.py text "BGP 이웃이 Established 로 못 올라간다"
    python3 23_glossary_tag.py stats            # docs.jsonl 전체와 claim 단위를 태그해 glossary/STATS.md 와 태그 jsonl 을 쓴다

매칭 규칙
- 라틴 글자·숫자로 시작하거나 끝나는 별칭은 그 쪽 바로 옆 글자가 라틴 글자·숫자·`_` 이면 걸리지 않는다. `-`·`/`·`.` 는 경계로 본다.
- 글자 수 3 이하 별칭(`SM`, `amf`, `N2`)은 대소문자까지 같아야 걸린다. 4 이상은 대소문자를 가리지 않는다. 별칭의 `case_sensitive` 가 true 면 길이와 상관없이 대소문자를 본다.
- 한글로 끝나는 별칭 뒤에 한글이 이어지면 그 한글이 조사 목록으로 시작할 때만 걸린다. 한글 두 글자 이하로 시작하는 별칭은 바로 앞이 한글이면 걸리지 않는다.
- 별칭 안의 공백은 공백 여러 개·줄바꿈과도 맞는다.
- 별칭 글자가 다른 한 항목의 정식 이름과 같으면(대소문자 무시) 그 정식 이름 항목만 매칭을 받는다. `AMF` 는 Authentication Management Field 의 별칭이기도 하지만 5G NF `AMF` 에만 걸린다. 그 밖에 여러 항목이 함께 쓰는 별칭은 모두에 걸고 `ambiguous: true` 를 단다.
- 한 항목의 매칭이 겹치면 긴 쪽 하나만 남긴다. 다른 항목끼리 겹치는 매칭은 둘 다 남긴다(`PDU Session` 안의 `PDU`).
"""
import json
import re
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

LAB = Path(__file__).parent
DOCS = LAB / "inputs/net-corpus/docs.jsonl"
GLOSSARY_DIR = LAB / "inputs/net-corpus/glossary"
CLAIMS = LAB / "runs/23-net-units/claim.jsonl"
TAGS_DIR = LAB / "runs/23-glossary"

LATIN = r"A-Za-z0-9_"
HANGUL = "가-힣ㄱ-ㆎ"
PARTICLES = ("은", "는", "이", "가", "을", "를", "의", "에", "에서", "에게", "께", "로", "으로", "와", "과", "도", "만", "까지",
             "부터", "나", "이나", "란", "이란", "라", "이라", "처럼", "보다", "마다", "들", "랑", "이랑", "하고", "인", "이며", "며",
             "이고", "고", "이다", "다", "였", "이었", "입니", "예요", "이에요", "죠", "이죠", "요", "와의", "과의", "로의", "에서의",
             "한", "하", "된", "되", "할", "했", "해", "등")
SHORT_ALIAS_LENGTH = 3
SHORT_HANGUL_PREFIX = 2

YEAR_PATTERN = re.compile(r"(?<![\d.:/#-])((?:19[89]|20[0-2])\d)(?:년|(?!\d|[.:]\d))")
YEAR_CONTEXT = re.compile(r"(?i)(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*$|(?:in|since|from|until|by|of|year|during|early|late|©|copyright)\s*$|[-/]\s*$")
RELEASE_PATTERN = re.compile(r"(?i)(?<![A-Za-z0-9])(?:3GPP\s+)?(?:Release|Rel)[-\s.]?(\d{2})(?!\d)")
VERSION_PATTERN = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.\d+){0,2}(?:[-.]?(?:rc|alpha|beta)\d*)?)(?![\w.]*\d)")
VERSION_WINDOW = 24


def is_hangul(char):
    return bool(char) and re.match(f"[{HANGUL}]", char) is not None


def alias_pattern(alias):
    body = r"\s+".join(re.escape(part) for part in alias.split())
    prefix = f"(?<![{LATIN}])" if re.match(f"[{LATIN}]", alias[0]) else ""
    if re.match(f"[{LATIN}]", alias[-1]):
        suffix = f"(?![{LATIN}])"
    elif is_hangul(alias[-1]):
        suffix = f"(?:(?![{HANGUL}])|(?=(?:{'|'.join(sorted(PARTICLES, key=len, reverse=True))})))"
    else:
        suffix = ""
    leading_hangul = re.match(f"[{HANGUL}]+", alias)
    if leading_hangul and len(leading_hangul.group(0)) <= SHORT_HANGUL_PREFIX:
        prefix = f"(?<![{HANGUL}])"
    return prefix + body + suffix


def letter_count(alias):
    return sum(ch.isalnum() for ch in alias)


def case_sensitive(alias, flag=None):
    if flag is not None:
        return bool(flag)
    return letter_count(alias) <= SHORT_ALIAS_LENGTH


class AliasMatcher:
    """(항목 id, 별칭 dict) 목록을 받아 텍스트에서 항목별 매칭을 찾는다. 별칭 dict 는 {"text", "case_sensitive"?}."""

    def __init__(self, aliases_by_entry):
        self.forms = []
        for entry_id, aliases in aliases_by_entry.items():
            for alias in aliases:
                text = alias["text"].strip()
                if not text:
                    continue
                exact = case_sensitive(text, alias.get("case_sensitive"))
                flags = 0 if exact else re.IGNORECASE
                needle = text.split()[0] if exact else text.split()[0].casefold()
                self.forms.append((entry_id, text, exact, needle, re.compile(alias_pattern(text), flags)))

    def find(self, text, start=0, end=None):
        end = len(text) if end is None else end
        window = text[start:end]
        folded = window.casefold()
        found = defaultdict(list)
        for entry_id, alias, exact, needle, pattern in self.forms:
            if needle not in (window if exact else folded):
                continue
            for match in pattern.finditer(window):
                found[entry_id].append({"alias": alias, "start": start + match.start(), "end": start + match.end(),
                                        "matched": match.group(0)})
        return {entry_id: longest_without_overlap(matches) for entry_id, matches in found.items()}


def longest_without_overlap(matches):
    kept = []
    for match in sorted(matches, key=lambda m: (-(m["end"] - m["start"]), m["start"])):
        if all(match["end"] <= other["start"] or match["start"] >= other["end"] for other in kept):
            kept.append(match)
    return sorted(kept, key=lambda m: m["start"])


def load_docs(path=DOCS):
    return {doc["doc_id"]: doc for doc in (json.loads(line) for line in Path(path).read_text().splitlines() if line.strip())}


def doc_year(doc):
    match = re.match(r"(\d{4})", doc.get("date") or "")
    return int(match.group(1)) if match else None


def body_years(text, start, end, latest):
    for match in YEAR_PATTERN.finditer(text, start, end):
        year = int(match.group(1))
        if year > latest:
            continue
        before = text[max(0, match.start() - 12):match.start()]
        korean_year = match.group(0).endswith("년")
        date_like = re.match(r"[-/.]\d{1,2}", text[match.end():match.end() + 3]) is not None
        if korean_year or date_like or YEAR_CONTEXT.search(before):
            yield {"concept": "year", "value": year, "source": "body", "start": match.start(), "end": match.end(1),
                   "matched": match.group(0)}


def releases(text, start, end):
    for match in RELEASE_PATTERN.finditer(text, start, end):
        number = int(match.group(1))
        if 8 <= number <= 21:
            yield {"concept": "3gpp-release", "value": number, "source": "body", "start": match.start(), "end": match.end(),
                   "matched": match.group(0)}


def versions(text, entry_matches, versioned_entries, end):
    for entry_id, matches in entry_matches.items():
        if entry_id not in versioned_entries:
            continue
        for match in matches:
            tail = text[match["end"]:min(end, match["end"] + VERSION_WINDOW)]
            found = VERSION_PATTERN.search(tail)
            if found and not re.search(r"[\n,;]", tail[:found.start()]):
                yield {"concept": "software-version", "value": found.group(1), "entry": entry_id, "source": "body",
                       "start": match["end"] + found.start(), "end": match["end"] + found.end(), "matched": found.group(0)}


class GlossaryTagger:
    def __init__(self, glossary_dir=GLOSSARY_DIR, docs_path=DOCS):
        glossary_dir = Path(glossary_dir)
        self.entries = {e["id"]: e for e in json.loads((glossary_dir / "glossary.json").read_text())["entries"]}
        hierarchy = json.loads((glossary_dir / "hierarchy.json").read_text())
        self.nodes = {n["id"]: n for n in hierarchy["nodes"]}
        self.docs = load_docs(docs_path)
        self.latest_year = max(filter(None, (doc_year(d) for d in self.docs.values())), default=date.today().year)
        aliases = {eid: [{"text": e["canonical"], "case_sensitive": e.get("case_sensitive")}] + e["aliases"] for eid, e in self.entries.items()}
        canonical_owners = defaultdict(set)
        for eid, e in self.entries.items():
            canonical_owners[e["canonical"].casefold()].add(eid)
        self.yielded_aliases = []
        for eid, forms in aliases.items():
            kept = []
            for form in forms:
                owners = canonical_owners.get(form["text"].casefold(), set())
                if len(owners) == 1 and eid not in owners:
                    self.yielded_aliases.append((eid, form["text"], next(iter(owners))))
                else:
                    kept.append(form)
            aliases[eid] = kept
        self.matcher = AliasMatcher(aliases)
        self.versioned_entries = {eid for eid, e in self.entries.items() if e.get("versioned")}
        alias_owners = defaultdict(set)
        for eid, forms in aliases.items():
            for form in forms:
                alias_owners[form["text"].casefold()].add(eid)
        self.ambiguous_aliases = {text for text, owners in alias_owners.items() if len(owners) > 1}

    def ancestors(self, parent_ids):
        seen, stack = [], list(parent_ids)
        while stack:
            node_id = stack.pop()
            if node_id in seen or node_id not in self.nodes:
                continue
            seen.append(node_id)
            stack.extend(self.nodes[node_id].get("parents", []))
        return seen

    def _entries_and_concepts(self, entry_matches):
        entries, concept_via = [], defaultdict(list)
        for entry_id, matches in sorted(entry_matches.items(), key=lambda item: item[1][0]["start"]):
            entry = self.entries[entry_id]
            entries.append({"id": entry_id, "canonical": entry["canonical"], "common": entry.get("common", False),
                            "matches": [dict(m, ambiguous=m["alias"].casefold() in self.ambiguous_aliases) for m in matches]})
            for node_id in self.ancestors(entry.get("parents", [])):
                concept_via[node_id].append(entry_id)
        concepts = [{"id": node_id, "name": self.nodes[node_id]["name"], "via": via} for node_id, via in concept_via.items()]
        return entries, concepts

    def tag_text(self, text):
        entries, concepts = self._entries_and_concepts(self.matcher.find(text))
        values = list(body_years(text, 0, len(text), self.latest_year + 1)) + list(releases(text, 0, len(text)))
        return {"entries": entries, "concepts": concepts, "values": values}

    def tag_span(self, doc_id, start, end):
        doc = self.docs[doc_id]
        text = doc["text"]
        entry_matches = self.matcher.find(text, start, end)
        entries, concepts = self._entries_and_concepts(entry_matches)
        values = []
        if doc_year(doc):
            values.append({"concept": "year", "value": doc_year(doc), "source": "doc_date", "matched": doc["date"]})
        values += list(body_years(text, start, end, self.latest_year))
        values += list(releases(text, start, end))
        values += list(versions(text, entry_matches, self.versioned_entries, end))
        return {"doc_id": doc_id, "start": start, "end": end, "entries": entries, "concepts": concepts, "values": values}


def histogram(counts, edges):
    rows = []
    for low, high in zip(edges, edges[1:] + [None]):
        label = f"{low}" if high == low + 1 else (f"{low}–{high - 1}" if high else f"{low}+")
        rows.append((label, sum(1 for c in counts if c >= low and (high is None or c < high))))
    return rows


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def claim_tags(tagger, doc_tags, claims):
    for claim in claims:
        inside = [e for e in doc_tags[claim["doc_id"]]["entries"]
                  if any(claim["start"] <= m["start"] and m["end"] <= claim["end"] for m in e["matches"])]
        entry_ids = [e["id"] for e in inside]
        concepts = tagger.ancestors([p for eid in entry_ids for p in tagger.entries[eid].get("parents", [])])
        yield {"unit_id": claim["unit_id"], "doc_id": claim["doc_id"], "entries": entry_ids, "concepts": concepts}


def claim_section(tagger, rows, claims):
    entries = tagger.entries
    by_unit = {r["unit_id"]: r for r in rows}
    total = len(rows)
    has = lambda r: bool(r["entries"])
    has_plain = lambda r: any(not entries[e].get("common") for e in r["entries"])
    counts = sorted(len(r["entries"]) for r in rows)
    lines = ["", "## claim 단위 태그", "",
             f"`{CLAIMS.relative_to(LAB)}` 의 claim {total:,}개에 건 결과다. 문서 전체를 태그한 매칭 가운데 claim 구간 안에 다 든 것만 그 claim 에 준다. "
             f"claim 별 태그는 `{(TAGS_DIR / 'claim-tags.jsonl').relative_to(LAB)}` 에 있다.", "",
             "| 항목 | 값 |", "|---|---:|",
             f"| entry 가 하나라도 걸린 claim | {sum(map(has, rows)):,} ({sum(map(has, rows)) / total:.1%}) |",
             f"| 흔한 항목을 빼고도 걸린 claim | {sum(map(has_plain, rows)):,} ({sum(map(has_plain, rows)) / total:.1%}) |",
             f"| claim 당 entry 수 평균 | {sum(counts) / total:.2f} |",
             f"| claim 당 entry 수 중앙값 · 90번째 · 최대 | {counts[total // 2]} · {counts[int(total * 0.9)]} · {counts[-1]} |",
             f"| 개념 노드가 하나라도 걸린 claim | {sum(1 for r in rows if r['concepts']):,} ({sum(1 for r in rows if r['concepts']) / total:.1%}) |",
             "", "claim 당 entry 수 분포다.", "", "| entry 수 | claim |", "|---|---:|"]
    lines += [f"| {label} | {n:,} |" for label, n in histogram(counts, [0, 1, 2, 3, 5, 10])]
    for title, field in (("언어별", "lang"), ("문서 종류별", "kind")):
        groups = defaultdict(list)
        for claim in claims:
            groups[tagger.docs[claim["doc_id"]].get(field, "?")].append(by_unit[claim["unit_id"]])
        lines += ["", f"{title} (`docs.jsonl` 의 `{field}`)이다.", "",
                  "| 값 | claim | entry 걸림 | 흔한 항목 빼고 걸림 | claim 당 entry 평균 |", "|---|---:|---:|---:|---:|"]
        for value, group in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            n = len(group)
            lines.append(f"| {value} | {n:,} | {sum(map(has, group)) / n:.1%} | {sum(map(has_plain, group)) / n:.1%} | "
                         f"{sum(len(r['entries']) for r in group) / n:.2f} |")
    claim_df = Counter(e for r in rows for e in r["entries"])
    lines += ["", "가장 많은 claim 에 걸린 entry 30 이다. 흔한 항목도 함께 센다.", "",
              "| id | 정식 이름 | common | claim | 비율 |", "|---|---|---|---:|---:|"]
    lines += [f"| `{eid}` | {entries[eid]['canonical']} | {'예' if entries[eid].get('common') else ''} | {n:,} | {n / total:.1%} |"
              for eid, n in claim_df.most_common(30)]
    return lines


def write_stats(tagger, out_path, claims_path=CLAIMS):
    doc_entries, entry_docs, alias_docs = {}, defaultdict(set), defaultdict(set)
    concept_docs, value_docs = defaultdict(set), defaultdict(set)
    ambiguous_hits = Counter()
    doc_tags = {}
    for doc_id, doc in tagger.docs.items():
        tagged = tagger.tag_span(doc_id, 0, len(doc["text"]))
        doc_tags[doc_id] = tagged
        doc_entries[doc_id] = {e["id"] for e in tagged["entries"]}
        for entry in tagged["entries"]:
            entry_docs[entry["id"]].add(doc_id)
            for match in entry["matches"]:
                alias_docs[(entry["id"], match["alias"])].add(doc_id)
                if match["ambiguous"]:
                    ambiguous_hits[match["alias"]] += 1
        for concept in tagged["concepts"]:
            concept_docs[concept["id"]].add(doc_id)
        for value in tagged["values"]:
            value_docs[(value["concept"], value["source"], str(value["value"]))].add(doc_id)

    total_docs = len(tagger.docs)
    entries = tagger.entries
    df = {eid: len(entry_docs.get(eid, ())) for eid in entries}
    plain = [eid for eid in entries if not entries[eid].get("common")]
    edges = [0, 1, 2, 3, 5, 10, 20, 50, 100, 200]
    lines = [f"# 용어집 항목별 등장 문서 수", "",
             f"`python3 23_glossary_tag.py stats` 가 `docs.jsonl` {total_docs}건 전체를 태그해 쓴 표다. 매칭 규칙은 `23_glossary_tag.py` 머리 문서에 있다.", "",
             "## 요약", "", "| 항목 | 값 |", "|---|---:|",
             f"| 항목 | {len(entries)} |",
             f"| 흔한 항목 표시(`common`) | {len(entries) - len(plain)} |",
             f"| 한 문서에도 안 걸린 항목 | {sum(1 for v in df.values() if v == 0)} |",
             f"| 항목이 하나라도 걸린 문서 | {sum(1 for ids in doc_entries.values() if ids)} / {total_docs} |",
             f"| 흔한 항목을 빼고도 하나라도 걸린 문서 | {sum(1 for ids in doc_entries.values() if any(not entries[i].get('common') for i in ids))} / {total_docs} |",
             f"| 문서당 걸린 항목 수 중앙값 | {sorted(len(ids) for ids in doc_entries.values())[total_docs // 2]} |",
             f"| 별칭(정식 이름 포함) 수 | {sum(1 + len(e['aliases']) for e in entries.values())} |",
             f"| 한 문서에라도 걸린 별칭 수 | {len(alias_docs)} |",
             f"| 다른 항목의 정식 이름이라 양보한 별칭 | {len(tagger.yielded_aliases)} |",
             "", "## 등장 문서 수 분포", "", "흔한 항목을 뺀 것과 넣은 것을 함께 센다.", "",
             "| 등장 문서 수 | 항목 수 (흔한 항목 뺌) | 항목 수 (전체) |", "|---|---:|---:|"]
    for (label, plain_count), (_, all_count) in zip(histogram([df[e] for e in plain], edges), histogram(list(df.values()), edges)):
        lines.append(f"| {label} | {plain_count} | {all_count} |")

    def entry_row(eid):
        top_alias = Counter({alias: len(docs) for (owner, alias), docs in alias_docs.items() if owner == eid}).most_common(3)
        aliases = ", ".join(f"`{a}` {n}" for a, n in top_alias)
        return f"| `{eid}` | {entries[eid]['canonical']} | {df[eid]} | {df[eid] / total_docs:.0%} | {aliases} |"

    lines += ["", "## 많이 걸린 항목 30", "", "흔한 항목 표시가 없는 것만 센다. 별칭 칸은 가장 많은 문서에 걸린 별칭 셋과 그 문서 수다.", "",
              "| id | 정식 이름 | 문서 | 비율 | 걸린 별칭 |", "|---|---|---:|---:|---|"]
    lines += [entry_row(eid) for eid in sorted(plain, key=lambda e: -df[e])[:30]]
    common = [eid for eid in entries if entries[eid].get("common")]
    lines += ["", "## 흔한 항목", "", "Opus 가 `common` 으로 표시한 항목이다. 링크·시작점에서 뺄 후보다.", "",
              "| id | 정식 이름 | 문서 | 비율 | 걸린 별칭 |", "|---|---|---:|---:|---|"]
    lines += [entry_row(eid) for eid in sorted(common, key=lambda e: -df[e])]
    lines += ["", "## 여러 항목이 함께 쓰는 별칭", "", "같은 글자가 둘 이상 항목의 별칭이다. 태거는 이런 매칭에 `ambiguous: true` 를 단다.", "",
              "| 별칭 | 항목 | 걸린 문서 |", "|---|---|---:|"]
    for alias, hits in ambiguous_hits.most_common(30):
        owners = sorted({eid for (eid, a) in alias_docs if a.casefold() == alias.casefold()})
        lines.append(f"| `{alias}` | {', '.join(owners)} | {hits} |")
    lines += ["", "## 개념 노드별 등장 문서 수", "", "노드에 걸린 문서는 그 노드 아래 어느 항목이라도 걸린 문서다.", "",
              "| 노드 | 이름 | 종류 | 문서 |", "|---|---|---|---:|"]
    for node_id in sorted(tagger.nodes, key=lambda n: -len(concept_docs.get(n, ()))):
        node = tagger.nodes[node_id]
        lines.append(f"| `{node_id}` | {node['name']} | {node['kind']} | {len(concept_docs.get(node_id, ()))} |")
    lines += ["", "## 값 개념", "", "연도는 문서 메타 `date` 와 본문 날짜를, 3GPP Release 와 소프트웨어 버전은 본문을 읽은 값이다.", "",
              "| 개념 | 출처 | 값 | 문서 |", "|---|---|---|---:|"]
    for (concept, source, value), docs in sorted(value_docs.items(), key=lambda kv: (kv[0][0], kv[0][1], -len(kv[1]))):
        if concept == "software-version" and len(docs) < 2:
            continue
        lines.append(f"| {concept} | {source} | {value} | {len(docs)} |")
    write_jsonl(TAGS_DIR / "doc-tags.jsonl", doc_tags.values())
    if Path(claims_path).exists():
        claims = [json.loads(line) for line in Path(claims_path).read_text().splitlines() if line.strip()]
        claims = [c for c in claims if c["doc_id"] in tagger.docs]
        rows = list(claim_tags(tagger, doc_tags, claims))
        write_jsonl(TAGS_DIR / "claim-tags.jsonl", rows)
        lines += claim_section(tagger, rows, claims)
    Path(out_path).write_text("\n".join(lines) + "\n")
    print(f"{out_path}: 항목 {len(entries)}, 걸린 문서 {sum(1 for ids in doc_entries.values() if ids)}/{total_docs}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("span", "text", "stats"):
        print(__doc__)
        sys.exit(2)
    tagger = GlossaryTagger()
    if sys.argv[1] == "span":
        result = tagger.tag_span(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1] == "text":
        result = tagger.tag_text(" ".join(sys.argv[2:]))
    else:
        write_stats(tagger, GLOSSARY_DIR / "STATS.md")
        return
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
