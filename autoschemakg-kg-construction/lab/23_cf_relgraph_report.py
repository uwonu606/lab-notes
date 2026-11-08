"""cf-relgraph 판 보고 표: 묶음별 재현율, cf-claimctx 대비 승패, 연결 정확도, 선 길 기여, 흔적 문항.

    .venv-hr2/bin/python 23_cf_relgraph_report.py            # runs/23-cf-relgraph/report-tables.md
    .venv-hr2/bin/python 23_cf_relgraph_report.py diagnose   # 근거 claim 에 선이 닿았나·순위 → diagnosis*.json(l)

정답(gold_hubs·evidence·set)과 labels.jsonl 을 읽는 보고 전용 코드다. 색인·질의 코드(23_cf_relgraph.py)는 이 파일을 쓰지 않는다.
"""
import importlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

os.environ["NET_CORPUS"] = "cf"
LAB = Path(__file__).parent
sys.path.insert(0, str(LAB))
arch = importlib.import_module("23_arch_common")
sign_test = arch._scorer().sign_test

GOLD_DIR = LAB / "inputs/net-corpus-cf/gold"
SCOPE = GOLD_DIR / "scope-retrieval.txt"
RUNS = {"cf-relgraph": LAB / "runs/23-cf-relgraph", "cf-relgraph-textlink": LAB / "runs/23-cf-relgraph-textlink"}
BASE = ("cf-claimctx", LAB / "runs/23-cf-claimctx")
MODES = arch.MODES


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def groups():
    gold = {r["qid"]: r for r in read_jsonl(GOLD_DIR / "questions-cf.jsonl")}
    labels = {r["qid"]: r for r in read_jsonl(GOLD_DIR / "labels.jsonl")}
    scope = {line.split("\t")[0] for line in SCOPE.read_text().splitlines() if line.strip()}
    has_evidence = {q for q, r in gold.items() if r["evidence"]}
    out = {
        "alias·범위·근거 있음 (주)": {q for q in scope & has_evidence if gold[q]["set"] == "alias"},
        "fact·범위 (참고)": {q for q in scope & has_evidence if gold[q]["set"] == "fact"},
        "범위 전체": scope & has_evidence,
        "범위·흔적 있음": {q for q in scope & has_evidence if labels.get(q, {}).get("trace_hint")},
        "범위·흔적 없음": {q for q in scope & has_evidence if not labels.get(q, {}).get("trace_hint")},
        "pub 전체": {q for q in has_evidence if gold[q]["set"] == "pub"},
        "fact 전체": {q for q in has_evidence if gold[q]["set"] == "fact"},
        "hub_touch 전체": {q for q in has_evidence if gold[q].get("hub_touch")},
    }
    return gold, out


def recall_table(details, group_sets):
    names = list(details)
    lines = ["| 묶음 | 문항 | 판 | " + " | ".join(MODES) + " |", "|---|---:|---|" + "---:|" * len(MODES)]
    for group, qids in group_sets.items():
        for name in names:
            covered = [q for q in qids if all((q, m) in details[name] for m in MODES)]
            if len(covered) < len(qids):
                continue
            cells = [f"{mean(details[name][q, m]['recall'] for q in qids):.3f}" if qids else "-" for m in MODES]
            lines.append(f"| {group} | {len(qids)} | {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def versus_table(mine, base, group_sets):
    lines = ["| 묶음 | 문항 | " + " | ".join(MODES) + " |", "|---|---:|" + "---|" * len(MODES)]
    for group, qids in group_sets.items():
        if not all((q, MODES[0]) in mine for q in qids) or not qids:
            continue
        cells = []
        for mode in MODES:
            diffs = [mine[q, mode]["recall"] - base[q, mode]["recall"] for q in qids]
            wins, losses = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            cells.append(f"{wins}승 {losses}패 (p={sign_test(wins, losses):.2f})")
        lines.append(f"| {group} | {len(qids)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def link_accuracy(run_dir, variant, gold, qids):
    traces = {t["qid"]: t for t in read_jsonl(run_dir / "trace.jsonl") if t["variant"] == variant}
    tp = fp = fn = exact = no_gold_picked = no_gold = 0
    for q in qids:
        if q not in traces:
            continue
        picked, wanted = set(traces[q]["linked"]), set(gold[q].get("gold_hubs") or [])
        tp, fp, fn = tp + len(picked & wanted), fp + len(picked - wanted), fn + len(wanted - picked)
        exact += picked == wanted
        if not wanted:
            no_gold += 1
            no_gold_picked += bool(picked)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "exact": exact, "questions": len(qids),
            "no_gold_questions": no_gold, "no_gold_but_picked": no_gold_picked}


def graph_contribution(run_dir, variant, base_dir, base_variant, qids):
    """5000자 담긴 단위 가운데 선 길에서 온 claim 과, 그중 cf-claimctx 5000자에 없던 claim. 찾은 묶음을 덮은 path."""
    mine = {r["qid"]: r for r in read_jsonl(run_dir / "retrieval.jsonl") if r["variant"] == variant}
    base = {r["qid"]: r for r in read_jsonl(base_dir / "retrieval.jsonl") if r["variant"] == base_variant}
    detail = arch.read_detail(run_dir, variant)
    graph_units = new_units = questions_with_new = 0
    found_paths = Counter()
    rel_of_found = Counter()
    for q in qids:
        if q not in mine:
            continue
        base_spans = {(u["doc_id"], u["start"], u["end"]) for u in base[q]["units"]}
        graph = [u for u in mine[q]["units"] if u["path"].startswith("relgraph")]
        new = [u for u in graph if (u["doc_id"], u["start"], u["end"]) not in base_spans]
        graph_units, new_units, questions_with_new = graph_units + len(graph), new_units + len(new), questions_with_new + bool(new)
        for found in detail.get((q, "5000자"), {}).get("found", []):
            stages = {arch.first_stage(p) for p in found["paths"]}
            found_paths["relgraph" if "relgraph" in stages else "claim-ctx 만"] += 1
            for p in found["paths"]:
                if p.startswith("relgraph"):
                    rel_of_found[p.split(">")[1].removeprefix("rel=")] += 1
    return {"graph_units": graph_units, "graph_units_not_in_base": new_units, "questions_with_new_graph_units": questions_with_new,
            "found_groups_5000": dict(found_paths), "found_by_relation": rel_of_found.most_common(10)}


def main():
    gold, group_sets = groups()
    base = arch.read_detail(BASE[1], BASE[0])
    details = {BASE[0]: base}
    sections = []
    for variant, run_dir in RUNS.items():
        if (run_dir / "detail.jsonl").exists():
            details[variant] = arch.read_detail(run_dir, variant)
    sections.append("## 재현율\n\n" + recall_table(details, group_sets))
    for variant, run_dir in RUNS.items():
        if variant not in details:
            continue
        if arch.gold_stamp(run_dir) != arch.gold_stamp(BASE[1]):
            raise RuntimeError(f"{variant} 와 cf-claimctx 의 gold 해시가 다르다")
        traces = read_jsonl(run_dir / "trace.jsonl")
        scope_qids = group_sets["범위 전체"] if variant == "cf-relgraph" else set().union(*group_sets.values())
        linked_q = sum(bool(t["linked"]) for t in traces)
        graph_q = sum(t["stage_counts"]["relgraph_claims"] > 0 for t in traces)
        sections.append(f"## {variant} 대 cf-claimctx\n\n질문 {len(traces)}개, 연결된 구심점이 있는 질문 {linked_q}, 선 길 claim 이 있는 질문 {graph_q}, "
                        f"연결 오류 {sum(bool(t.get('link_error')) for t in traces)}.\n\n" + versus_table(details[variant], base, group_sets))
        sections.append(f"### {variant} 연결 정확도 (gold_hubs 대비)\n\n```\n"
                        + json.dumps({g: link_accuracy(run_dir, variant, gold, qs) for g, qs in group_sets.items()
                                      if qs <= {t['qid'] for t in traces}}, ensure_ascii=False, indent=1) + "\n```")
        sections.append(f"### {variant} 선 길 기여\n\n```\n" + json.dumps(
            {g: graph_contribution(run_dir, variant, BASE[1], BASE[0], qs) for g, qs in group_sets.items()
             if qs <= {t['qid'] for t in traces}}, ensure_ascii=False, indent=1) + "\n```")
        sections.append(f"### {variant} path\n\n" + arch.path_table(run_dir, variant))
    out = RUNS["cf-relgraph"] / "report-tables.md"
    out.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(out.read_text())




def evidence_claims(ctx, evidence):
    """근거 묶음 label → 근거 구간과 겹치는 claim 행 번호들."""
    out = {}
    for group in evidence:
        rows = set()
        for span in group["spans"]:
            rows.update(ctx.covering(span["doc_id"], span["start"], span["end"]))
        out[group["label"]] = rows
    return out


def position_and_chars(units, row_ids, ctx):
    """units 에서 row_ids 중 처음 나오는 단위의 (1부터 센 순위, 그 앞까지 글자 합). 없으면 (None, None)."""
    chars = 0
    for rank, u in enumerate(units, start=1):
        if u.get("unit_id") in {ctx.ids[i] for i in row_ids}:
            return rank, chars
        chars += u["end"] - u["start"]
    return None, None


def diagnose(variant, qids, gold):
    import numpy as np

    cf_runs = importlib.import_module("23_cf_runs")
    relgraph = importlib.import_module("23_cf_relgraph")
    ctx = cf_runs.claim_ctx_units(arch, LAB / "runs/23-cf-units/idx/emb-claim-ctx.npy")
    graph = relgraph.RelGraph(arch, ctx)
    run_dir = RUNS[variant]
    traces = {t["qid"]: t for t in read_jsonl(run_dir / "trace.jsonl")}
    retrieval = {r["qid"]: r["units"] for r in read_jsonl(run_dir / "retrieval.jsonl")}
    base_units = {r["qid"]: r["units"] for r in read_jsonl(BASE[1] / "retrieval.jsonl")}
    mine_detail, base_detail = arch.read_detail(run_dir, variant), arch.read_detail(BASE[1], BASE[0])
    questions = [q for q in arch.read_questions() if q.qid in qids]
    qvecs = arch.embed_questions(questions)
    rows = []
    for q, qvec in zip(questions, qvecs):
        hub_ids = traces[q.qid]["linked"]
        edge_rows, graph_ranked = graph.ranking(qvec, hub_ids)
        graph_rank = {u["unit_id"]: n for n, u in enumerate(graph_ranked, start=1)}
        full_ctx = [i for i, _ in ctx.search(qvec)]
        ctx_rank = {ctx.ids[i]: n for n, i in enumerate(full_ctx, start=1)}
        found_mine = {f["label"] for f in mine_detail[q.qid, "5000자"]["found"]}
        found_mine_2500 = {f["label"] for f in mine_detail[q.qid, "2500자"]["found"]}
        found_base = {f["label"] for f in base_detail[q.qid, "5000자"]["found"]}
        found_base_2500 = {f["label"] for f in base_detail[q.qid, "2500자"]["found"]}
        for label, claim_rows in evidence_claims(ctx, gold[q.qid]["evidence"]).items():
            claim_ids = [ctx.ids[i] for i in claim_rows]
            g_ranks = [graph_rank[c] for c in claim_ids if c in graph_rank]
            final_rank, final_chars = position_and_chars(retrieval[q.qid], claim_rows, ctx)
            base_rank, base_chars = position_and_chars(base_units[q.qid], claim_rows, ctx)
            graph_before = None
            if final_rank:
                graph_before = sum(u["path"].startswith("relgraph") for u in retrieval[q.qid][:final_rank - 1])
            rows.append({"qid": q.qid, "label": label, "hubs": hub_ids, "edges": len(edge_rows), "graph_claims": len(graph_ranked),
                         "evidence_claims": len(claim_ids), "touched": bool(g_ranks), "graph_rank": min(g_ranks) if g_ranks else None,
                         "ctx_rank": min((ctx_rank[c] for c in claim_ids), default=None),
                         "final_rank": final_rank, "final_chars_before": final_chars, "graph_units_before": graph_before,
                         "base_rank": base_rank, "base_chars_before": base_chars,
                         "found_5000": label in found_mine, "found_2500": label in found_mine_2500,
                         "base_found_5000": label in found_base, "base_found_2500": label in found_base_2500})
    return rows


def median(values):
    values = sorted(v for v in values if v is not None)
    return values[len(values) // 2] if values else None


def diagnosis_summary(rows):
    with_claims = [r for r in rows if r["evidence_claims"]]
    touched = [r for r in with_claims if r["touched"]]
    lost_2500 = [r for r in with_claims if r["base_found_2500"] and not r["found_2500"]]
    gained_2500 = [r for r in with_claims if r["found_2500"] and not r["base_found_2500"]]
    return {
        "evidence_groups": len(rows), "groups_with_evidence_claim": len(with_claims),
        "touched_by_hub_edge": len(touched), "touched_ratio": round(len(touched) / len(with_claims), 3) if with_claims else None,
        "median_edges_per_question": median(r["edges"] for r in rows),
        "median_graph_claims_per_question": median(r["graph_claims"] for r in rows),
        "touched_graph_rank_median": median(r["graph_rank"] for r in touched),
        "touched_graph_rank_le_10": sum(r["graph_rank"] <= 10 for r in touched),
        "touched_graph_rank_le_30": sum(r["graph_rank"] <= 30 for r in touched),
        "touched_ctx_rank_median": median(r["ctx_rank"] for r in touched),
        "untouched_ctx_rank_median": median(r["ctx_rank"] for r in with_claims if not r["touched"]),
        "touched_found_5000": sum(r["found_5000"] for r in touched), "touched_base_found_5000": sum(r["base_found_5000"] for r in touched),
        "untouched_found_5000": sum(r["found_5000"] for r in with_claims if not r["touched"]),
        "untouched_base_found_5000": sum(r["base_found_5000"] for r in with_claims if not r["touched"]),
        "lost_at_2500_vs_base": len(lost_2500),
        "lost_2500_median_graph_units_before": median(r["graph_units_before"] for r in lost_2500),
        "lost_2500_median_base_rank": median(r["base_rank"] for r in lost_2500),
        "lost_2500_median_final_rank": median(r["final_rank"] for r in lost_2500),
        "gained_at_2500_vs_base": len(gained_2500),
    }


def diagnose_main():
    gold, group_sets = groups()
    out = {}
    for variant in RUNS:
        for group in ("alias·범위·근거 있음 (주)", "fact·범위 (참고)"):
            rows = diagnose(variant, group_sets[group], gold)
            write_rows = RUNS["cf-relgraph"] / f"diagnosis-{variant}-{'alias' if group.startswith('alias') else 'fact'}.jsonl"
            write_rows.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            out[f"{variant} / {group}"] = diagnosis_summary(rows)
    (RUNS["cf-relgraph"] / "diagnosis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    diagnose_main() if sys.argv[1:] == ["diagnose"] else main()
