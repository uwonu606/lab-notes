"""새 문서 종류를 승인했을 때, 이미 색인한 문서 가운데 영향받은 것만 다시 찍는 증분 갱신을 처음부터 다시 만드는 전체 재색인과 견준다.

    .venv-25/bin/python 25_split_migrate.py --run runs/25-split-migrate

상태 넷을 만든다. 모두 같은 도착 순서(--order-seed), 임베딩 이름표는 제목·제목 경로만(칸·종류는 청크 메타데이터)이다.
  before       칸 정의 OLD_SCHEMAS(기술 검토 의견서 없음)로 색인한 상태
  incremental  before 에서 NEW_SCHEMAS 를 승인한 뒤 영향받은 문서만 다시 찍은 상태
  full-triage  NEW_SCHEMAS 로 처음부터 다시 색인하되, incremental 과 같은 종류 분류 결과로 규칙 후보를 거른 상태
  full-naive   NEW_SCHEMAS 로 처음부터 다시 색인만 한 상태(종류 분류 없음)
증분 갱신의 순서:
  1. 종류 분류: LLM 한 번이 모든 문서의 제목과 첫 제목들을 보고 새 종류 문서 번호를 고른다(TRIAGE_PROMPT).
  2. 옮길 문서: 새 종류로 분류됐는데 before 에서 다른 종류였던 문서.
  3. 오염된 규칙: 옮길 문서를 표본으로 새로 태어났거나 보수된 규칙. 태어난 규칙은 지우고, 보수된 규칙은 그 문서가 들어오기 직전 판으로 되돌린다.
  4. 영향받은 문서: 옮길 문서와, before 에서 오염된 규칙으로 찍힌 문서. 이 문서만 도착 순서대로 다시 찍는다.
     새 종류 문서는 새 종류 규칙만, 나머지는 새 종류가 아닌 규칙만 후보로 본다.
청크마다 doc_type·plan·plan_version 을 남겨서 어느 규칙 어느 판으로 찍혔는지 추적한다.
"""
import argparse
import importlib.util
import json
from pathlib import Path

LAB = Path(__file__).parent


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, LAB / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = load_module("harness25", "25_split_harness.py")
evaluation = load_module("eval25", "25_split_eval.py")

OLD_SCHEMAS = LAB / "inputs/parser-schemas"
NEW_SCHEMAS = LAB / "inputs/parser-schemas-v2"
NEW_TYPE = "tech_review"
TRIAGE_PROMPT = (LAB / "prompts/25-type-triage.txt").read_text(encoding="utf-8")
TRIAGE_HEADINGS = 6
EMBED_LABEL = "title-path"


class Index:
    def __init__(self, schemas, model):
        self.schemas = schemas
        self.planner = harness.Planner(model, schemas)
        self.registry = {}
        self.chunks = {}
        self.decisions = {}

    def next_plan_id(self):
        numbers = [int(plan_id[1:]) for plan_id in self.registry]
        return f"p{max(numbers, default=0) + 1:02d}"

    def put(self, doc, position, by_id, allowed=None):
        calls_before = len(self.planner.calls)
        decision = {"position": position, "doc_id": doc.doc_id}
        if len(doc.body_candidates) < harness.MIN_CANDIDATES:
            self.chunks[doc.doc_id] = harness.formless_chunks(doc)
            self.decisions[doc.doc_id] = {**decision, "route": "formless", "doc_type": None, "llm_calls": 0}
            return
        view = {k: v for k, v in self.registry.items() if allowed is None or allowed(v["plan"]["doc_type"])}
        before_ids = set(view)
        route, plan_id, plan, attempts = harness.markup_route(doc, view, self.planner, self.schemas, by_id, position)
        if route == "new":
            fresh = self.next_plan_id()
            entry = view.pop(plan_id)
            plan_id = fresh
            view[plan_id] = entry
        for key in set(view) - before_ids:
            self.registry[key] = view[key]
        if plan is None:
            route, plan_id, plan = "fallback", None, harness.GENERIC_PLAN
        version = self.registry[plan_id]["version"] if plan_id else None
        fit = harness.apply_plan(doc, plan, self.schemas)
        extra = {"doc_type": plan["doc_type"], "plan": plan_id, "plan_version": version}
        self.chunks[doc.doc_id] = harness.doc_chunks(doc, fit, plan, self.schemas, f"{route}:{plan_id}" if plan_id else route,
                                                     extra=extra, embed_label=EMBED_LABEL)
        self.decisions[doc.doc_id] = {**decision, "route": route, "plan": plan_id, "plan_version": version, "doc_type": plan["doc_type"],
                                      "attempts": attempts, "llm_calls": len(self.planner.calls) - calls_before}

    def all_chunks(self, order):
        return [row for doc_id in order for row in self.chunks[doc_id]]

    def write(self, run, order, extra_summary=None):
        run.mkdir(parents=True, exist_ok=True)
        harness.write_jsonl(run / "chunks.jsonl", self.all_chunks(order))
        harness.write_jsonl(run / "decisions.jsonl", [self.decisions[d] for d in order])
        (run / "plans.json").write_text(json.dumps(self.registry, ensure_ascii=False, indent=1), encoding="utf-8")
        summary = {"llm_calls": len(self.planner.calls), "new_llm_calls": sum(1 for c in self.planner.calls if c.get("ok") and not c.get("cache_hit")),
                   "plans": len(self.registry), "usage": self.planner.client.usage_line(), **(extra_summary or {})}
        (run / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        return summary


def gate_for(triaged):
    def gate(doc_id):
        if doc_id in triaged:
            return lambda doc_type: doc_type == NEW_TYPE
        return lambda doc_type: doc_type != NEW_TYPE
    return gate


def build_full(docs, by_id, schemas, model, gate=None):
    index = Index(schemas, model)
    for position, doc in enumerate(docs):
        index.put(doc, position, by_id, gate(doc.doc_id) if gate else None)
    return index


def triage(docs, schemas, model):
    card = harness.load_schemas(NEW_SCHEMAS)[NEW_TYPE]
    card_text = json.dumps(card, ensure_ascii=False, indent=1)
    lines = []
    for number, doc in enumerate(docs, 1):
        headings = " / ".join(c.text for c in doc.body_candidates[:TRIAGE_HEADINGS])
        lines.append(f"{number} | {harness.title_text(doc)} | {headings or '(no headings)'}")
    prompt = TRIAGE_PROMPT.replace("{type_card}", card_text).replace("{documents}", "\n".join(lines))
    planner = harness.Planner(model, schemas)
    reply = planner._ask(prompt, "triage")
    numbers = harness.parse_json(reply).get("numbers", []) if reply else []
    return {docs[n - 1].doc_id for n in numbers if 1 <= n <= len(docs)}, planner


def incremental(before, docs, by_id, triaged, model):
    index = Index(harness.load_schemas(NEW_SCHEMAS), model)
    index.registry = json.loads(json.dumps(before.registry))
    index.chunks = dict(before.chunks)
    index.decisions = dict(before.decisions)

    moved = {d for d in triaged if before.decisions[d].get("doc_type") != NEW_TYPE}
    rolled, deleted = {}, []
    for plan_id, entry in list(index.registry.items()):
        history = entry.get("history", [])
        first = next((i for i, h in enumerate(history) if h["sample"] in moved), None)
        if first is None:
            continue
        if first == 0:
            deleted.append(plan_id)
            del index.registry[plan_id]
            continue
        keep = history[:first]
        entry.update(plan=keep[-1]["plan"], version=keep[-1]["version"], history=keep, samples=[h["sample"] for h in keep])
        rolled[plan_id] = keep[-1]["version"]
    touched_plans = set(rolled) | set(deleted)
    affected = moved | {d for d, dec in before.decisions.items() if dec.get("plan") in touched_plans}
    gate = gate_for(triaged)
    for position, doc in enumerate(docs):
        if doc.doc_id in affected:
            index.put(doc, position, by_id, gate(doc.doc_id))
    return index, {"moved": sorted(moved), "rolled_back": rolled, "deleted": deleted, "affected": sorted(affected)}


def chunk_key(row):
    return (row["start"], row["end"], row["field"], row.get("doc_type"))


def compare(left, right, order):
    same_docs = sum(1 for d in order if [chunk_key(r) for r in left.chunks[d]] == [chunk_key(r) for r in right.chunks[d]])
    left_keys = {(d,) + chunk_key(r) for d in order for r in left.chunks[d]}
    right_keys = {(d,) + chunk_key(r) for d in order for r in right.chunks[d]}
    differing = [d for d in order if [chunk_key(r) for r in left.chunks[d]] != [chunk_key(r) for r in right.chunks[d]]]
    return {"same_docs": same_docs, "docs": len(order), "same_chunks": len(left_keys & right_keys),
            "left_chunks": len(left_keys), "right_chunks": len(right_keys), "differing_docs": differing}


def quality(index, order):
    gold = {d: json.loads((LAB / "inputs/parser-corpus/gold" / f"{d}.json").read_text(encoding="utf-8")) for d in order}
    templated = [d for d in order if gold[d]["doc_type"] != "formless"]
    type_hits = sum(1 for d in templated if index.decisions[d].get("doc_type") == gold[d]["doc_type"])
    evaluation.SCHEMA_TYPES = {p.stem for p in NEW_SCHEMAS.glob("*.yaml")}
    rows = evaluation.evaluate(index.all_chunks(order), index.decisions)
    accuracies = [r["field_accuracy"] for r in rows if r.get("field_accuracy") is not None]
    by_type = {}
    for r in rows:
        if r.get("field_accuracy") is not None:
            by_type.setdefault(r["doc_type"], []).append(r["field_accuracy"])
    misfiled = {d: index.decisions[d].get("doc_type") for d in templated if index.decisions[d].get("doc_type") != gold[d]["doc_type"]}
    return {"type_accuracy": f"{type_hits}/{len(templated)}", "field_accuracy": round(sum(accuracies) / len(accuracies), 4),
            "field_accuracy_docs": len(accuracies), "tech_review_field_accuracy": round(sum(by_type.get(NEW_TYPE, [0])) / max(len(by_type.get(NEW_TYPE, [])), 1), 4),
            "misfiled": misfiled}


def embed_texts(index, order):
    texts = set()
    for d in order:
        text = (LAB / "inputs/parser-corpus/md" / f"{d}.md").read_text(encoding="utf-8")
        for row in index.chunks[d]:
            texts.add(f"{row['label']}\n{text[row['start']:row['end']]}" if row.get("label") else text[row["start"]:row["end"]])
    return texts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--order-seed", type=int, default=0)
    args = parser.parse_args()
    run = Path(args.run)

    docs = harness.read_corpus(args.order_seed)
    by_id = {d.doc_id: d for d in docs}
    order = [d.doc_id for d in docs]
    old_schemas, new_schemas = harness.load_schemas(OLD_SCHEMAS), harness.load_schemas(NEW_SCHEMAS)

    before = build_full(docs, by_id, old_schemas, args.model)
    report = {"before": before.write(run / "before", order)}

    triaged, triage_planner = triage(docs, new_schemas, args.model)
    gold_new = {d for d in order if d.startswith(NEW_TYPE)}
    triage_info = {"triaged": sorted(triaged), "true_positive": len(triaged & gold_new), "false_positive": sorted(triaged - gold_new),
                   "missed": sorted(gold_new - triaged), "usage": triage_planner.client.usage_line()}
    (run / "triage.json").parent.mkdir(parents=True, exist_ok=True)
    (run / "triage.json").write_text(json.dumps(triage_info, ensure_ascii=False, indent=1), encoding="utf-8")

    inc, plan_changes = incremental(before, docs, by_id, triaged, args.model)
    report["incremental"] = inc.write(run / "incremental", order, plan_changes)
    full_triage = build_full(docs, by_id, new_schemas, args.model, gate_for(triaged))
    report["full-triage"] = full_triage.write(run / "full-triage", order)
    full_naive = build_full(docs, by_id, new_schemas, args.model)
    report["full-naive"] = full_naive.write(run / "full-naive", order)

    states = {"before": before, "incremental": inc, "full-triage": full_triage, "full-naive": full_naive}
    report["quality"] = {name: quality(index, order) for name, index in states.items()}
    report["incremental_vs_full_triage"] = compare(inc, full_triage, order)
    report["incremental_vs_before"] = compare(inc, before, order)
    before_texts = embed_texts(before, order)
    report["reembed"] = {name: len(embed_texts(index, order) - before_texts) for name, index in states.items() if name != "before"}
    report["triage"] = triage_info
    (run / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "triage"}, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
