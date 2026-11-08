"""9단계 cf-table: 8단계 레코드 표를 다시 추출하지 않고 사내화 말뭉치로 옮긴 뒤, 칸 값을 구심점 카드·관계 목록으로 정규화한다.
옮기는 코드라 23_cf_layer.Layer(공개 이름을 품은 대응표)를 여기서만 쓴다. 질의 코드(23_table_query.py)는 이 스크립트가 낸 표·schema 만 읽는다."""
import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from importlib import import_module
from pathlib import Path

LAB = Path(__file__).parent
SOURCE_DIR = LAB / "runs/23-arch-a4-table"
OUT = LAB / "runs/23-cf-table"
RELATIONS = LAB / "inputs/net-corpus/relglossary/relations.json"
CF_DOCS = LAB / "inputs/net-corpus-cf/docs.jsonl"
SCHEMA_KEY = "a4-schema"


def squash(text):
    return re.sub(r"[\s_\-./]+", "", str(text).lower())


def column_relations(relations):
    """칸 이름 → 관계 id 목록. 관계의 뒤 끝이 칸 값, 앞 끝이 레코드 주체다."""
    by_column = defaultdict(list)
    for relation in relations:
        if relation.get("record_column"):
            by_column[relation["record_column"]].append(relation["id"])
    return dict(by_column)


def relation_for(column, kind, by_column):
    """제품 칸만 관계가 둘(문제 → 제품, 시험 → 제품)이라 레코드 종류로 고른다. 보고서 레코드가 시험이다."""
    choices = by_column.get(column, [])
    if len(choices) <= 1:
        return choices[0] if choices else None
    wanted = "tested_product" if kind == "report" else "affects_product"
    return wanted if wanted in choices else choices[0]


def cf_record_id(record_id, orig_doc, cf_doc):
    return cf_doc + record_id[len(orig_doc):]


def replace_schema(schema, layer):
    """슬롯 프롬프트에 들어가는 schema 글(칸 설명·예시·레코드 정의)의 공개 이름을 사내 이름으로 바꾼 사본."""
    swap = lambda text: layer.replace_text(text, SCHEMA_KEY)
    out = dict(schema)
    out["record_definitions"] = {k: swap(v) for k, v in schema["record_definitions"].items()}
    out["columns"] = [{**c, "description": swap(c["description"]), "examples": [swap(e) for e in c["examples"]]} for c in schema["columns"]]
    out["extraction_notes"] = [swap(n) for n in schema["extraction_notes"]]
    out["rationale"] = swap(schema["rationale"])
    out.pop("sample_doc_ids", None)
    return out


def write_schema(db):
    db.executescript("""
        CREATE TABLE records (record_id TEXT PRIMARY KEY, doc_id TEXT, kind TEXT, source TEXT, date TEXT, year INTEGER,
                              piece INTEGER, start INTEGER, end INTEGER);
        CREATE TABLE cell_values (record_id TEXT, col TEXT, value TEXT, norm TEXT);
        CREATE TABLE cell_spans (record_id TEXT, col TEXT, start INTEGER, end INTEGER);
        CREATE TABLE cell_entries (record_id TEXT, col TEXT, entry_id TEXT, source TEXT);
        CREATE TABLE record_edges (record_id TEXT, rel TEXT, col TEXT, tail TEXT, value TEXT);
        CREATE INDEX cell_values_col ON cell_values (col, norm);
        CREATE INDEX cell_spans_record ON cell_spans (record_id);
        CREATE INDEX cell_entries_record ON cell_entries (record_id, col);
        CREATE INDEX record_edges_rel ON record_edges (rel, tail);
    """)


def main():
    parser = argparse.ArgumentParser(description="8단계 레코드 표를 사내화 말뭉치로 옮겨 runs/23-cf-table/ 에 table.sqlite·records.jsonl·schema.json 을 낸다")
    parser.add_argument("--source-table", default=str(SOURCE_DIR / "table.sqlite"))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    layer = import_module("23_cf_layer").Layer.load()
    link = import_module("23_cf_link")
    cards = link.read_cards()
    hub_ids = {card.id for card in cards}
    relations = json.loads(RELATIONS.read_text())["relations"]
    by_column = column_relations(relations)
    cf_docs = {d["doc_id"]: d for d in (json.loads(line) for line in CF_DOCS.read_text().splitlines() if line.strip())}

    src = sqlite3.connect(args.source_table)
    target_path = out / "table.sqlite"
    target_path.unlink(missing_ok=True)
    db = sqlite3.connect(target_path)
    write_schema(db)
    counts, leaks = Counter(), []

    record_of = {}
    for record_id, doc_id, kind, source, date, year, piece, start, end in src.execute("SELECT * FROM records ORDER BY rowid"):
        cf_doc = layer.cf_doc_id(doc_id)
        new_id = cf_record_id(record_id, doc_id, cf_doc)
        _, new_start, new_end = layer.map_span(doc_id, start, end)
        record_of[record_id] = (new_id, doc_id, kind)
        db.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?)",
                   (new_id, cf_doc, kind, cf_docs[cf_doc]["source"], date, year, piece, new_start, new_end))
        counts["records"] += 1

    hub_cells = defaultdict(set)
    for record_id, col, start, end in src.execute("SELECT record_id, col, start, end FROM cell_spans"):
        new_id, doc_id, _ = record_of[record_id]
        _, new_start, new_end = layer.map_span(doc_id, start, end)
        db.execute("INSERT INTO cell_spans VALUES (?,?,?,?)", (new_id, col, new_start, new_end))
        for hub in layer.hubs_in(doc_id, start, end):
            hub_cells[new_id, col].add(hub)
        counts["spans"] += 1

    value_hubs = {}
    for record_id, col, value, norm in src.execute("SELECT record_id, col, value, norm FROM cell_values"):
        new_id, doc_id, kind = record_of[record_id]
        new_value = layer.replace_text(value, doc_id)
        found = layer.leaks(new_value)
        if found:
            leaks.append({"record_id": new_id, "col": col, "value": new_value, "forms": [f.form for f in found]})
        counts["values"] += 1
        counts["values_changed"] += new_value != value
        db.execute("INSERT INTO cell_values VALUES (?,?,?,?)", (new_id, col, new_value, norm))
        hubs = set(link.text_match(new_value, cards))
        value_hubs[new_id, col, new_value] = hubs
        relation = relation_for(col, kind, by_column)
        if relation:
            entry_ids = [e for e in (norm or "").split(";") if e]
            tails = [f"hub:{h}" for h in sorted(hubs)] or [f"entry:{e}" for e in entry_ids] or [f"term:{squash(new_value)}"]
            db.executemany("INSERT INTO record_edges VALUES (?,?,?,?,?)", [(new_id, relation, col, t, new_value) for t in tails])
            counts[f"edges_{tails[0].split(':')[0]}"] += len(tails)
        else:
            counts["values_without_relation"] += 1

    for record_id, col, entry_id, source in src.execute("SELECT record_id, col, entry_id, source FROM cell_entries"):
        db.execute("INSERT INTO cell_entries VALUES (?,?,?,?)", (record_of[record_id][0], col, entry_id, source))
        counts["entries_copied"] += 1
    for (new_id, col), hubs in hub_cells.items():
        db.executemany("INSERT INTO cell_entries VALUES (?,?,?,?)", [(new_id, col, h, "hub-quote") for h in sorted(hubs)])
        counts["hub_quote_entries"] += len(hubs)
    for (new_id, col, _), hubs in value_hubs.items():
        db.executemany("INSERT INTO cell_entries VALUES (?,?,?,?)", [(new_id, col, h, "hub-value") for h in sorted(hubs)])
        counts["hub_value_entries"] += len(hubs)
    db.commit()

    copied_hub_entries = db.execute(f"SELECT COUNT(*) FROM cell_entries WHERE source NOT LIKE 'hub-%' AND entry_id IN ({','.join('?' * len(hub_ids))})",
                                    sorted(hub_ids)).fetchone()[0]
    counts["copied_entries_that_are_hubs"] = copied_hub_entries
    db.close()

    schema = replace_schema(json.loads((SOURCE_DIR / "schema.json").read_text()), layer)
    schema_leaks = layer.leaks(json.dumps(schema, ensure_ascii=False))
    (out / "schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=1))

    rows = defaultdict(lambda: {"cells": defaultdict(lambda: {"values": [], "spans": []})})
    tdb = sqlite3.connect(target_path)
    for new_id, cf_doc, kind, source, date, year, piece, start, end in tdb.execute("SELECT * FROM records ORDER BY rowid"):
        rows[new_id].update(record_id=new_id, doc_id=cf_doc, kind=kind, source=source, date=date, piece=piece, start=start, end=end)
    for new_id, col, value, _ in tdb.execute("SELECT * FROM cell_values"):
        rows[new_id]["cells"][col]["values"].append(value)
    for new_id, col, start, end in tdb.execute("SELECT * FROM cell_spans"):
        rows[new_id]["cells"][col]["spans"].append([start, end])
    tdb.close()
    (out / "records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()))

    quote_leaks = sum(len(layer.leaks(cf_docs[r["doc_id"]]["text"][s:e])) for r in rows.values() for c in r["cells"].values() for s, e in c["spans"])
    stats = {"counts": dict(counts), "value_leaks": len(leaks), "quote_leaks": quote_leaks, "schema_leaks": [f.form for f in schema_leaks],
             "column_relations": by_column, "columns_without_relation": sorted({c["name"] for c in schema["columns"]} - set(by_column))}
    (out / "build-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    (out / "leaks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in leaks))
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
