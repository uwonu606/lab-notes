"""안 5 용어집 노드 PPR: entry·개념·claim·문서 그래프에서 질문 entry 와 claim-ctx 상위 claim 을 시작점으로 PPR 을 돌려 claim 순위를 낸다.

    .venv-hr2/bin/python 23_arch_a5.py run       # runs/23-arch-a5-pprglossary/ 에 두 판을 쓰고 채점
    .venv-hr2/bin/python 23_arch_a5.py report    # 승패·그래프가 일했나·쏠림 표 (markdown)

설정값은 runs/23-arch-a5-pprglossary/CONFIG.md 에 실행 전에 적었다.
"""
import argparse
import hashlib
import importlib
import json
import time
from collections import Counter, defaultdict
from statistics import mean, median
from typing import NamedTuple

import numpy as np

import embed_client

arch = importlib.import_module("23_arch_common")
b2 = importlib.import_module("23_arch_b2")
glossary_tag = importlib.import_module("23_glossary_tag")

RUN_NAME = "a5-pprglossary"
RUN_DIR = arch.RUNS / f"23-arch-{RUN_NAME}"
class VariantSpec(NamedTuple):
    with_concepts: bool
    linker: str
    entry_flow_by_degree: bool = False


VARIANTS = {"a5-pprglossary": VariantSpec(True, "glyph"), "a5-pprglossary-noconcept": VariantSpec(False, "glyph"),
            "a5-pprglossary-haikulink": VariantSpec(True, "haiku"), "a5-pprglossary-degnorm": VariantSpec(True, "glyph", entry_flow_by_degree=True)}
HAIKU_LINKS = arch.RUNS / "23-arch-a1-glossary/trace.jsonl"
HAIKU_LINK_VARIANT = "a1-glossary"
CLAIM_CTX_DIR = b2.RUN_DIR
CLAIM_CTX_VARIANT = "claim-ctx"
CLAIM_TAGS = RUN_DIR / "claim-entries.json"

DAMPING = 0.5
CLAIM_SEEDS = 200
CLAIM_SEED_SHARE = 0.5
MAX_ITERATIONS = 100
TOLERANCE = 1e-10
TRACE_TOP = 10
FALLBACK_PATH = arch.path("fallback=claim-ctx", unit="claim")
EMPTY_LINK_REASONS = ("no-entry", "only-common")


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glossary_fingerprint():
    return {"glossary_sha256": file_sha256(glossary_tag.GLOSSARY_DIR / "glossary.json"),
            "hierarchy_sha256": file_sha256(glossary_tag.GLOSSARY_DIR / "hierarchy.json"),
            "tagger_sha256": file_sha256(arch.LAB / "23_glossary_tag.py")}


def claim_entries(tagger, claims):
    """claim unit_id → 태그된 entry id 목록(흔한 entry 포함). 용어집·태거가 같으면 디스크 캐시를 쓴다."""
    fingerprint = glossary_fingerprint()
    if CLAIM_TAGS.exists():
        cached = json.loads(CLAIM_TAGS.read_text())
        if cached["fingerprint"] == fingerprint and list(cached["tags"]) == claims.ids:
            return cached["tags"], 0.0
    started = time.monotonic()
    tags = {r["unit_id"]: [e["id"] for e in tagger.tag_span(r["doc_id"], r["start"], r["end"])["entries"]] for r in claims.rows}
    seconds = round(time.monotonic() - started, 1)
    CLAIM_TAGS.write_text(json.dumps({"fingerprint": fingerprint, "tags": tags}, ensure_ascii=False))
    return tags, seconds


class GlossaryGraph:
    """노드 순서는 claim(claim 단위 행 순서 그대로) → 문서 → entry → 개념. 선은 방향 없음·무게 1.
    entry_flow_by_degree 면 entry 가 이웃 하나로 보내는 몫을 1/차수² 로 줄인다(나머지는 샌다)."""

    def __init__(self, tagger, claims, tags, with_concepts, entry_flow_by_degree=False):
        self.tagger = tagger
        self.claim_count = len(claims)
        self.keys = [("claim", unit_id) for unit_id in claims.ids]
        doc_ids = sorted({r["doc_id"] for r in claims.rows})
        self.keys += [("doc", d) for d in doc_ids]
        self.graph_entries = sorted(eid for eid, e in tagger.entries.items() if not e.get("common"))
        self.keys += [("entry", eid) for eid in self.graph_entries]
        if with_concepts:
            self.keys += [("concept", nid) for nid in sorted(tagger.nodes)]
        self.index = {key: i for i, key in enumerate(self.keys)}

        pairs = []
        for i, r in enumerate(claims.rows):
            pairs.append((i, self.index["doc", r["doc_id"]]))
            pairs += [(i, self.index["entry", eid]) for eid in tags[r["unit_id"]] if ("entry", eid) in self.index]
        if with_concepts:
            for eid in self.graph_entries:
                pairs += [(self.index["entry", eid], self.index["concept", p]) for p in tagger.entries[eid].get("parents", [])
                          if ("concept", p) in self.index]
            for nid, node in tagger.nodes.items():
                pairs += [(self.index["concept", nid], self.index["concept", p]) for p in node.get("parents", []) if ("concept", p) in self.index]
        pairs = np.unique(np.asarray(pairs, dtype=np.int64), axis=0)
        self.src = np.concatenate([pairs[:, 0], pairs[:, 1]])
        self.dst = np.concatenate([pairs[:, 1], pairs[:, 0]])
        self.degree = np.bincount(self.src, minlength=len(self.keys)).astype(np.float64)
        order = np.argsort(self.src, kind="stable")
        self.neighbor_ids = self.dst[order]
        self.neighbor_offsets = np.concatenate([[0], np.cumsum(self.degree.astype(np.int64))])
        self.out_share = np.divide(1.0, self.degree, out=np.zeros_like(self.degree), where=self.degree > 0)
        if entry_flow_by_degree:
            entry_nodes = [self.index["entry", eid] for eid in self.graph_entries]
            self.out_share[entry_nodes] *= self.out_share[entry_nodes]

    def __len__(self):
        return len(self.keys)

    def neighbors(self, i):
        return self.neighbor_ids[self.neighbor_offsets[i]:self.neighbor_offsets[i + 1]]

    def ppr(self, seed):
        """(점수, 반복 수). 차수 0 인 노드는 퍼뜨리지 않는다."""
        rank = seed.copy()
        for iteration in range(1, MAX_ITERATIONS + 1):
            spread = np.bincount(self.dst, weights=(rank * self.out_share)[self.src], minlength=len(self))
            updated = (1 - DAMPING) * seed + DAMPING * spread
            if np.abs(updated - rank).sum() < TOLERANCE:
                return updated, iteration
            rank = updated
        return rank, MAX_ITERATIONS

    def degree_stats(self):
        by_kind = defaultdict(list)
        for key, d in zip(self.keys, self.degree):
            by_kind[key[0]].append(int(d))
        stats = {kind: {"nodes": len(ds), "isolated": sum(d == 0 for d in ds), "min": min(ds), "median": median(ds),
                        "mean": round(mean(ds), 2), "p90": int(np.percentile(ds, 90)), "max": max(ds)} for kind, ds in by_kind.items()}
        entry_rows = [(int(self.degree[self.index["entry", eid]]), eid) for eid in self.graph_entries]
        stats["top_entries"] = [{"entry": self.tagger.entries[eid]["canonical"], "degree": d} for d, eid in sorted(entry_rows, reverse=True)[:15]]
        stats["edges"] = int(len(self.src) // 2)
        return stats

    def explain_claim(self, i, rank, seed):
        """claim 점수에서 시작점 몫, 문서 이웃 몫, 가장 큰 기여 entry 이웃과 그 몫."""
        neighbors = self.neighbors(i)
        flows = DAMPING * rank[neighbors] * self.out_share[neighbors]
        total = rank[i]
        entry_flows = [(float(f), self.keys[n][1]) for n, f in zip(neighbors, flows) if self.keys[n][0] == "entry"]
        best = max(entry_flows, default=(0.0, None))
        return {"unit_id": self.keys[i][1], "score": float(total), "seed_share": round(float((1 - DAMPING) * seed[i] / total), 3),
                "doc_share": round(float(sum(f for n, f in zip(neighbors, flows) if self.keys[n][0] == "doc") / total), 3),
                "entry_share": round(sum(f for f, _ in entry_flows) / total, 3),
                "top_entry": self.tagger.entries[best[1]]["canonical"] if best[1] else None, "top_entry_share": round(best[0] / total, 3)}


def path_label(canonical):
    return canonical.translate(str.maketrans({">": "_", "|": "_", "=": "_"}))


def link_question(tagger, question):
    tagged = tagger.tag_text(question)["entries"]
    linked = [e for e in tagged if not e["common"]]
    return linked, [e["canonical"] for e in tagged if e["common"]]


def haiku_links(tagger, questions):
    """arch-glossary 의 a1 Haiku 링크(link.usable)를 글자 매칭과 같은 모양으로. qid → (linked, dropped_common, 그 밖 기록)."""
    rows = {t["qid"]: t["link"] for t in arch.read_jsonl(HAIKU_LINKS) if t["variant"] == HAIKU_LINK_VARIANT}
    missing = [q.qid for q in questions if q.qid not in rows]
    if missing:
        raise RuntimeError(f"{HAIKU_LINKS} 에 a1 링크가 없는 문항 {len(missing)}개 (예 {missing[:3]}). a1 이 끝난 뒤 다시 돌린다")
    links = {}
    for q in questions:
        link = rows[q.qid]
        known = [eid for eid in link["usable"] if eid in tagger.entries and not tagger.entries[eid].get("common")]
        linked = [{"id": eid, "canonical": tagger.entries[eid]["canonical"], "matches": []} for eid in known]
        dropped = [tagger.entries[eid]["canonical"] if eid in tagger.entries else eid for eid in link.get("dropped_common", [])]
        links[q.qid] = (linked, dropped, {"link_failed": bool(link.get("link_failed")), "unknown_ids": len(link["usable"]) - len(known)})
    return links


def seed_vector(graph, linked, ctx_top):
    seed = np.zeros(len(graph))
    entry_nodes = [graph.index["entry", e["id"]] for e in linked]
    seed[entry_nodes] += (1 - CLAIM_SEED_SHARE) / len(entry_nodes)
    cosines = np.asarray([max(score, 0.0) for _, score in ctx_top])
    seed[[i for i, _ in ctx_top]] += CLAIM_SEED_SHARE * cosines / cosines.sum()
    return seed


def fill_with_claim_ctx(own, ctx, ctx_ranking):
    own = arch.fill_budget(own)
    if arch.chars_of(own) >= arch.MIN_BUDGET and len(own) >= arch.MIN_UNITS:
        return own, 0
    taken = {u["unit_id"] for u in own}
    extra = [ctx.as_unit(i, s, FALLBACK_PATH) for i, s in ctx_ranking if ctx.ids[i] not in taken]
    filled = arch.fill_budget(own + extra)
    return filled, len(filled) - len(own)


def retrieve(graph, ctx, linked, dropped_common, ctx_ranking):
    if not linked:
        units = arch.fill_budget([ctx.as_unit(i, s, FALLBACK_PATH) for i, s in ctx_ranking])
        return units, {"fallback_reason": "only-common" if dropped_common else "no-entry", "seeds": {"entries": 0, "claims": 0}, "iterations": 0, "top_claims": []}
    seed = seed_vector(graph, linked, ctx_ranking[:CLAIM_SEEDS])
    rank, iterations = graph.ppr(seed)
    claim_rank = rank[:graph.claim_count]
    order = [int(i) for i in np.argsort(-claim_rank, kind="stable") if claim_rank[i] > 0]
    unit_path = arch.path("ppr:glossary=" + "|".join(path_label(e["canonical"]) for e in linked), unit="claim")
    units, fallback_units = fill_with_claim_ctx([ctx.as_unit(i, claim_rank[i], unit_path) for i in order], ctx, ctx_ranking)
    return units, {"fallback_reason": "budget-short" if fallback_units else None,
                   "seeds": {"entries": len(linked), "claims": min(CLAIM_SEEDS, len(ctx_ranking))}, "iterations": iterations,
                   "reached_claims": len(order), "top_claims": [graph.explain_claim(i, rank, seed) for i in order[:TRACE_TOP]]}


def kept_rows_of_other_variants(name, chosen):
    path = RUN_DIR / name
    return [r for r in arch.read_jsonl(path) if r["variant"] not in chosen] if path.exists() else []


def run(chosen):
    tagger = glossary_tag.GlossaryTagger()
    claims = arch.load_units("claim")
    ctx, _ = b2.claim_ctx_units()
    if ctx.ids != claims.ids:
        raise ValueError("claim-ctx 벡터 순서가 claim 단위와 다르다")
    tags, tag_seconds = claim_entries(tagger, claims)
    questions = arch.read_questions()
    qvecs = arch.embed_questions(questions)
    links = {"glyph": {q.qid: (*link_question(tagger, q.question), {}) for q in questions}}
    if any(VARIANTS[v].linker == "haiku" for v in chosen):
        links["haiku"] = haiku_links(tagger, questions)

    result = arch.Run(RUN_NAME)
    result.retrieval = kept_rows_of_other_variants("retrieval.jsonl", chosen)
    result.traces = kept_rows_of_other_variants("trace.jsonl", chosen)
    report_path = RUN_DIR / "run-report.json"
    earlier = json.loads(report_path.read_text())["variants"] if report_path.exists() else {}
    report = {"claim_tag_seconds": tag_seconds, **glossary_fingerprint(), "gold_sha256": arch.sha256_of(arch.GOLD),
              "variants": {v: r for v, r in earlier.items() if v not in chosen}}
    for variant in chosen:
        spec = VARIANTS[variant]
        linker = spec.linker
        started = time.monotonic()
        graph = GlossaryGraph(tagger, claims, tags, spec.with_concepts, spec.entry_flow_by_degree)
        build_seconds = round(time.monotonic() - started, 1)
        started = time.monotonic()
        for q, qvec in zip(questions, qvecs):
            linked, dropped_common, link_notes = links[linker][q.qid]
            ctx_ranking = ctx.search(qvec)
            units, trace = retrieve(graph, ctx, linked, dropped_common, ctx_ranking)
            result.add(q.qid, variant, units, fallback=trace.pop("fallback_reason"), linker=linker, **link_notes,
                       dropped_common=dropped_common, dropped_common_count=len(dropped_common),
                       linked=[{"id": e["id"], "canonical": e["canonical"], "aliases": sorted({m["matched"] for m in e["matches"]}),
                                "ambiguous": any(m["ambiguous"] for m in e["matches"])} for e in linked],
                       llm={"calls": 0}, **trace)
        report["variants"][variant] = {"graph_build_seconds": build_seconds, "query_seconds": round(time.monotonic() - started, 1),
                                       "degree": graph.degree_stats()}
    result.write()
    print(result.score())
    report["embed_stats"] = embed_client.stats
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))


def unit_ids_within(units, budget):
    kept, total = [], 0
    for u in units:
        if total >= budget:
            break
        kept.append(u["unit_id"])
        total += u["end"] - u["start"]
    return kept


def changed_questions(variant):
    """claim-ctx 와 담은 claim 이 달라진 문항의 승패. 예산마다 (달라진 문항, 이김, 짐, 같음)."""
    mine = {r["qid"]: r["units"] for r in arch.read_jsonl(RUN_DIR / "retrieval.jsonl") if r["variant"] == variant}
    base = {r["qid"]: r["units"] for r in arch.read_jsonl(CLAIM_CTX_DIR / "retrieval.jsonl") if r["variant"] == CLAIM_CTX_VARIANT}
    detail_mine, detail_base = arch.read_detail(RUN_DIR, variant), arch.read_detail(CLAIM_CTX_DIR, CLAIM_CTX_VARIANT)
    budgets = {"@5": None, "1000자": 1000, "2500자": 2500, "5000자": 5000}
    rows = {}
    for mode, budget in budgets.items():
        cell = {"changed": 0, "win": 0, "loss": 0, "tie": 0}
        for qid, units in mine.items():
            if (qid, mode) not in detail_mine:
                continue
            pick = (lambda us: [u["unit_id"] for u in us[:5]]) if budget is None else (lambda us: unit_ids_within(us, budget))
            if set(pick(units)) == set(pick(base[qid])):
                continue
            cell["changed"] += 1
            diff = detail_mine[qid, mode]["recall"] - detail_base[qid, mode]["recall"]
            cell["win" if diff > 0 else "loss" if diff < 0 else "tie"] += 1
        rows[mode] = cell
    return rows


def concentration(variant, tags, common):
    """상위 5 claim 의 그래프 차수(문서 1 + 흔하지 않은 entry 수) 평균과, 여러 문항 상위 5 에 반복해 든 claim."""
    def degree(unit_id):
        return 1 + sum(eid not in common for eid in tags[unit_id])

    def top5(path, name):
        return {r["qid"]: [u["unit_id"] for u in r["units"][:5]] for r in arch.read_jsonl(path / "retrieval.jsonl") if r["variant"] == name}

    mine, base = top5(RUN_DIR, variant), top5(CLAIM_CTX_DIR, CLAIM_CTX_VARIANT)
    traces = {t["qid"]: t for t in arch.read_jsonl(RUN_DIR / "trace.jsonl") if t["variant"] == variant}
    graph_qids = [q for q, t in traces.items() if t["fallback"] not in EMPTY_LINK_REASONS]
    repeated = lambda picks: Counter(u for q in graph_qids for u in picks[q]).most_common(5)
    top_entry = Counter(c["top_entry"] for q in graph_qids for c in traces[q]["top_claims"][:5] if c["top_entry"])
    return {"corpus_mean_degree": round(mean(degree(u) for u in tags), 2),
            "top5_mean_degree": round(mean(degree(u) for q in graph_qids for u in mine[q]), 2),
            "claim_ctx_top5_mean_degree": round(mean(degree(u) for q in graph_qids for u in base[q]), 2),
            "graph_questions": len(graph_qids),
            "repeated_top5": repeated(mine), "claim_ctx_repeated_top5": repeated(base),
            "top5_seed_share_mean": round(mean(c["seed_share"] for q in graph_qids for c in traces[q]["top_claims"][:5]), 3),
            "top5_doc_share_mean": round(mean(c["doc_share"] for q in graph_qids for c in traces[q]["top_claims"][:5]), 3),
            "top5_entry_share_mean": round(mean(c["entry_share"] for q in graph_qids for c in traces[q]["top_claims"][:5]), 3),
            "top5_top_entry": top_entry.most_common(10)}


def link_summary(variant):
    traces = [t for t in arch.read_jsonl(RUN_DIR / "trace.jsonl") if t["variant"] == variant]
    return {"questions": len(traces), "no_entry": sum(t["fallback"] == "no-entry" for t in traces),
            "only_common": sum(t["fallback"] == "only-common" for t in traces),
            "dropped_common_total": sum(t["dropped_common_count"] for t in traces),
            "link_failed": sum(t.get("link_failed", False) for t in traces),
            "unknown_ids": sum(t.get("unknown_ids", 0) for t in traces),
            "budget_short": sum(t["fallback"] == "budget-short" for t in traces),
            "linked_mean": round(mean(len(t["linked"]) for t in traces), 2),
            "ambiguous_questions": sum(any(e["ambiguous"] for e in t["linked"]) for t in traces),
            "dropped_common_questions": sum(bool(t["dropped_common"]) for t in traces),
            "iterations_max": max(t["iterations"] for t in traces)}


def report():
    tags = json.loads(CLAIM_TAGS.read_text())["tags"]
    common = {eid for eid, e in glossary_tag.GlossaryTagger().entries.items() if e.get("common")}
    present = {r["variant"] for r in arch.read_jsonl(RUN_DIR / "trace.jsonl")}
    for variant in [v for v in VARIANTS if v in present]:
        print(arch.report_tables(RUN_DIR, variant))
        print(f"\n### {variant} 언어별\n\n" + arch.type_table(RUN_DIR, variant, by="lang"))
        print(f"\n### {variant} 대 B0 언어별\n\n" + arch.compare_table(RUN_DIR, variant, by="lang"))
        for by in ("type", "lang"):
            print(f"\n### {variant} 대 claim-ctx ({by})\n\n" + arch.compare_table(RUN_DIR, variant, CLAIM_CTX_DIR, CLAIM_CTX_VARIANT, by=by))
        print(f"\n### {variant} 그래프가 일했나\n\n" + json.dumps(changed_questions(variant), ensure_ascii=False))
        print("\n" + json.dumps(link_summary(variant), ensure_ascii=False))
        print("\n" + json.dumps(concentration(variant, tags, common), ensure_ascii=False) + "\n")
    for other in [v for v in VARIANTS if v in present and v != "a5-pprglossary"]:
        print(f"\n### a5-pprglossary 대 {other}\n\n" + arch.compare_table(RUN_DIR, "a5-pprglossary", RUN_DIR, other))


def main():
    parser = argparse.ArgumentParser(description="안 5 용어집 노드 PPR 판을 돌리거나(run) 보고 표를 낸다(report).")
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--variants", default=",".join(VARIANTS), help="run 이 다시 쓸 판. 나머지 판의 행은 그대로 둔다")
    args = parser.parse_args()
    run(args.variants.split(",")) if args.command == "run" else report()


if __name__ == "__main__":
    main()
