"""안 3 판들의 채점 쪽 진단. 정답 근거(evidence)를 읽으므로 색인·질의 코드에는 쓰지 않는다."""
import argparse
import importlib
import json
from collections import Counter, defaultdict

import numpy as np

import embed_client

arch = importlib.import_module("23_arch_common")
a3 = importlib.import_module("23_arch_a3_query")

BUDGET = 5000
DEFAULT_VARIANTS = ["a3-section", "a3-section-nolink", "a3-section-free", "a3-section-free-linkafter"]


def read_run(variant, name):
    return {r["qid"]: r for r in arch.read_jsonl(arch.RUNS / f"23-arch-{variant}" / name) if r["variant"] == variant}


def within_budget(units, budget=BUDGET):
    kept, total = [], 0
    for u in units:
        if total >= budget:
            break
        kept.append(u)
        total += u["end"] - u["start"]
    return kept


def evidence_docs(question):
    return {s["doc_id"] for e in question.get("evidence") or [] for s in e["spans"]}


def first_hit(order, wanted):
    return next((rank for rank, doc_id in enumerate(order) if doc_id in wanted), None)


def doc_selection(index, gold, traces):
    """상위 5문서에 근거 문서가 든 문항 수: 판의 실제 선택, 같은 조각의 칸 제한 판·자유 판, 질문 벡터 섹션 최댓값."""
    questions = arch.read_questions()
    qvecs = dict(zip([q.qid for q in questions], arch.embed_questions(questions)))
    doc_of = [r["doc_id"] for r in index.sections.rows]
    hits, by_type = Counter(), defaultdict(Counter)
    for qid, trace in traces.items():
        wanted = evidence_docs(gold[qid])
        fragments = (trace.get("parsed") or {}).get("fragments")
        if not wanted or not fragments:
            continue
        vectors = np.asarray(embed_client.embed([f["value"] for f in fragments]), dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        best = {}
        for doc_id, score in zip(doc_of, (index.sections.matrix @ qvecs[qid]).tolist()):
            best[doc_id] = max(best.get(doc_id, -1.0), score)
        orders = {"slot_only": [d for d, _, _ in a3.rank_docs(index, fragments, vectors, True)],
                  "free": [d for d, _, _ in a3.rank_docs(index, fragments, vectors, False)],
                  "question_max_section": sorted(best, key=lambda d: -best[d])}
        qtype = gold[qid]["type"]
        hits["questions"] += 1
        by_type[qtype]["questions"] += 1
        for name, order in orders.items():
            rank = first_hit(order, wanted)
            in_top = rank is not None and rank < a3.TOP_DOCS
            hits[name] += in_top
            by_type[qtype][name] += in_top
    return dict(hits), {t: dict(c) for t, c in sorted(by_type.items())}


def intent_coverage(index, gold, traces):
    """근거 구간을 덮는 섹션의 칸이 intent 에 든 비율과 근거 구간의 칸 분포."""
    counts, slots = Counter(), Counter()
    for qid, trace in traces.items():
        intent = set((trace.get("parsed") or {}).get("intent") or ())
        for evidence in gold[qid].get("evidence") or []:
            for span in evidence["spans"]:
                covering = {index.slot_of_row[i] for i in index.sections.covering(span["doc_id"], span["start"], span["end"])}
                counts["spans"] += 1
                counts["in_intent"] += bool(covering & intent)
                slots.update(covering)
    return dict(counts), dict(slots.most_common())


def neighbour_use(gold, traces, retrieval):
    stats = Counter()
    reached = []
    for qid, trace in traces.items():
        wanted = evidence_docs(gold[qid])
        links = trace.get("linked") or []
        stats["questions_with_neighbour"] += bool(links)
        stats["neighbours"] += len(links)
        budget_units = within_budget(retrieval[qid]["units"])
        in_budget = [u for u in budget_units if "link=explicit" in u["path"]]
        stats["neighbour_units_in_budget"] += len(in_budget)
        to_evidence = [l["to"] for l in links if l["to"] in wanted]
        if to_evidence:
            reached.append({"qid": qid, "type": gold[qid]["type"], "neighbours": to_evidence,
                            "evidence_neighbour_units_in_budget": sum(u["doc_id"] in to_evidence for u in in_budget)})
    return dict(stats), reached


def found_paths(variant, traces, mode):
    lead, stage = Counter(), Counter()
    for (qid, m), row in arch.read_detail(arch.RUNS / f"23-arch-{variant}", variant).items():
        if m != mode:
            continue
        intent = set((traces[qid].get("parsed") or {}).get("intent") or ())
        for found in row["found"]:
            for unit_path in set(found["paths"]):
                stages = unit_path.split(">")
                lead[stages[0]] += 1
                slot = [s for s in stages if s.startswith("section=")][-1].split("=", 1)[1] if "section=" in unit_path else None
                stage["neighbour" if "link=" in unit_path else "fallback" if stages[0].startswith("fallback") else
                      "intent" if slot in intent else "other"] += 1
    return dict(lead.most_common()), dict(stage)


def by_language(variant):
    languages = {q.qid: q.lang for q in arch.read_questions()}
    groups = defaultdict(list)
    for (qid, mode), row in arch.read_detail(arch.RUNS / f"23-arch-{variant}", variant).items():
        groups[f"{languages[qid]} {mode}"].append(row["recall"])
    return {key: {"questions": len(v), "recall": round(sum(v) / len(v), 3)} for key, v in sorted(groups.items())}


def main():
    parser = argparse.ArgumentParser(description="안 3 판들의 진단: 문서 고르기 적중, intent 칸 일치, 이웃 사용, 찾은 path, 언어별 재현율. 정답 근거를 읽는다.")
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    parser.add_argument("--out", default=str(arch.RUNS / "23-arch-a3-section/diag.json"))
    args = parser.parse_args()

    index = a3.load_index()
    gold = {str(r["qid"]): r for r in arch.read_jsonl(arch.GOLD)}
    report = {}
    for variant in args.variants.split(","):
        traces, retrieval = read_run(variant, "trace.jsonl"), read_run(variant, "retrieval.jsonl")
        neighbour_stats, reached = neighbour_use(gold, traces, retrieval)
        report[variant] = {
            "actual_top5_has_evidence_doc": sum(bool(evidence_docs(gold[q]) & {d["doc_id"] for d in t.get("top_docs") or ()})
                                                for q, t in traces.items() if evidence_docs(gold[q])),
            "neighbours": neighbour_stats, "neighbours_reaching_evidence_docs": reached,
            "found_paths": {mode: dict(zip(("lead", "stage"), found_paths(variant, traces, mode))) for mode in ("@5", "1000자", "5000자")},
            "by_language": by_language(variant),
        }
    first = read_run(DEFAULT_VARIANTS[0], "trace.jsonl")
    report["doc_selection_same_fragments"] = dict(zip(("all", "by_type"), doc_selection(index, gold, first)))
    report["intent_coverage"] = dict(zip(("spans", "evidence_slots"), intent_coverage(index, gold, first)))
    report["embed_backend"] = embed_client.stats["backend"]
    arch.Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
