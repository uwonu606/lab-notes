import argparse
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
VARIANTS = {
    "dense": None,
    "hr2": {"index": "main", "filter": True, "passage_weight": 0.05},
    "hr2-nofilter": {"index": "main", "filter": False, "passage_weight": 0.05},
    "hr2-pw0.2": {"index": "main", "filter": True, "passage_weight": 0.2},
    "hr2-pw1.0": {"index": "main", "filter": True, "passage_weight": 1.0},
    "hr2-nofilter-pw1.0": {"index": "main", "filter": False, "passage_weight": 1.0},
    "hr2-asciigate": {"index": "ascii", "filter": True, "passage_weight": 0.05},
}


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = load("hr2_common", LAB / "23_hr2_common.py")


class OpenedIndex:
    def __init__(self, out_dir, questions, top_k):
        self.settings = common.load_settings(out_dir)
        self.hipporag, self.llm, _ = common.open_hipporag(out_dir, self.settings, retrieval_top_k=top_k)
        self.hipporag.prepare_retrieval_objects()
        self.hipporag.get_query_embeddings([q["question"] for q in questions])
        self.passage_vertices = np.array(self.hipporag.passage_node_idxs)
        self.key_of_source = {m["source_id"]: key for key, m in self.hipporag.chunk_metadata.items()}
        self.reset_trace = {}
        self._trace_ppr_reset()

    def _trace_ppr_reset(self):
        run_ppr = self.hipporag.run_ppr

        def traced(reset_prob, damping=0.5):
            reset = np.where(np.isnan(reset_prob) | (reset_prob < 0), 0, reset_prob)
            passage_mass = float(reset[self.passage_vertices].sum())
            phrase_reset = reset.copy()
            phrase_reset[self.passage_vertices] = 0
            seed_keys = [self.hipporag.graph.vs[int(v)]["name"] for v in np.flatnonzero(phrase_reset > 0)]
            self.reset_trace.update(phrase_mass=float(phrase_reset.sum()), passage_mass=passage_mass,
                                    phrase_seeds=len(seed_keys), seed_keys=seed_keys)
            return run_ppr(reset_prob, damping)

        self.hipporag.run_ppr = traced

    def unit(self, key, score, path):
        meta = self.hipporag.chunk_metadata[key]
        start = meta.get("start", 0)
        end = meta.get("end", start + len(self.hipporag.chunk_embedding_store.get_row(key)["content"]))
        return {"doc_id": meta.get("doc_id", meta["source_id"]), "start": start, "end": end, "score": float(score),
                "path": path, "unit_id": meta["source_id"]}

    def dense(self, question, top_k):
        order, scores = self.hipporag.dense_passage_retrieval(question)
        return [self.unit(self.hipporag.passage_node_keys[i], score, "dense") for i, score in zip(order[:top_k], scores)]

    def ppr_path(self, key, seed_keys):
        linked = [self.hipporag.entity_embedding_store.get_row(seed)["content"] for seed in seed_keys
                  if key in self.hipporag.ent_node_to_chunk_ids.get(seed, ())]
        return "ppr:phrase=" + "|".join(linked) if linked else "ppr:passage"

    def filter_trace(self, question):
        hipporag = self.hipporag
        _, kept, log = hipporag.rerank_facts(question, hipporag.get_fact_scores(question))
        candidates = log["facts_before_rerank"]
        trace = {"candidates": len(candidates), "kept": len(kept), "error": log.get("error")}
        if not hipporag.global_config.recognition_memory_filter or not candidates:
            return trace
        rerank = hipporag.rerank_filter
        response = rerank.llm_call(question, json.dumps({"fact": [list(c) for c in candidates]}, ensure_ascii=rerank.ensure_ascii))
        printed = io.StringIO()
        with redirect_stdout(printed):
            generated = rerank.parse_filter(response)
        known = {str(list(c)) for c in candidates}
        trace.update(parse_failed="Error parsing" in printed.getvalue(), generated=len(generated),
                     invented=sum(str(list(g)) not in known for g in generated))
        return trace

    def configure(self, variant):
        self.hipporag.global_config.recognition_memory_filter = variant["filter"]
        self.hipporag.global_config.passage_node_weight = variant["passage_weight"]

    def graph_search(self, question, top_k):
        self.reset_trace.clear()
        solution = self.hipporag.retrieve([question], num_to_retrieve=top_k)[0]
        seed_keys = self.reset_trace.pop("seed_keys", [])
        keys = [self.key_of_source[m["source_id"]] for m in solution.doc_metadata]
        paths = [self.ppr_path(k, seed_keys) for k in keys] if solution.graph_seeds else ["dense-fallback"] * len(keys)
        return {"units": [self.unit(k, score, path) for k, score, path in zip(keys, solution.doc_scores, paths)],
                "graph": bool(solution.graph_seeds), "seeds": [list(s) for s in solution.graph_seeds], **self.reset_trace}


def main():
    parser = argparse.ArgumentParser(description="질문마다 변형별 상위 k 단위를 {qid, variant, units:[{doc_id,start,end,score,path}]} jsonl 로 낸다.")
    parser.add_argument("questions", help="{id, question} 목록 json 또는 jsonl")
    parser.add_argument("index_dir", help="23_hr2_index.py 의 out_dir (동의어 조건 패치판)")
    parser.add_argument("out", help="결과 jsonl")
    parser.add_argument("--ascii-index", help="--ascii-gate 로 만든 out_dir. 주면 hr2-asciigate 변형을 돈다")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    args = parser.parse_args()

    questions = common.read_questions(args.questions)
    names = [v for v in args.variants.split(",") if v != "hr2-asciigate" or args.ascii_index]
    indexes = {"main": OpenedIndex(args.index_dir, questions, args.top_k)}
    if args.ascii_index and "hr2-asciigate" in names:
        indexes["ascii"] = OpenedIndex(args.ascii_index, questions, args.top_k)

    rows, summary = [], {}
    for name in names:
        variant = VARIANTS[name]
        if variant is None:
            rows += [{"qid": q["id"], "variant": name, "units": indexes["main"].dense(q["question"], args.top_k)} for q in questions]
            continue
        index = indexes[variant["index"]]
        index.configure(variant)
        with ThreadPoolExecutor(max_workers=index.settings["workers"]) as pool:
            traces = list(pool.map(index.filter_trace, [q["question"] for q in questions]))
        for q, trace in zip(questions, traces):
            rows.append({"qid": q["id"], "variant": name, **index.graph_search(q["question"], args.top_k), "filter": trace})
        mine = [r for r in rows if r["variant"] == name]
        searched = [r for r in mine if r["graph"]]
        summary[name] = {
            "dense_fallback": sum(not r["graph"] for r in mine),
            "filter_parse_failed": sum(bool(r["filter"].get("parse_failed")) for r in mine),
            "filter_errors": sum(bool(r["filter"].get("error")) for r in mine),
            "filter_kept_mean": float(np.mean([r["filter"]["kept"] for r in mine])),
            "filter_invented": sum(r["filter"].get("invented", 0) for r in mine),
            "passage_share_mean": float(np.mean([r["passage_mass"] / (r["passage_mass"] + r["phrase_mass"]) for r in searched])) if searched else None,
            "phrase_mass_mean": float(np.mean([r["phrase_mass"] for r in searched])) if searched else None,
            "phrase_seeds_mean": float(np.mean([r["phrase_seeds"] for r in searched])) if searched else None,
        }
        s = summary[name]
        print(f"  {name:20} dense 로 간 질의 {s['dense_fallback']}/{len(mine)} · 필터 답 해석 실패 {s['filter_parse_failed']} · 필터 예외 {s['filter_errors']} · "
              f"남긴 트리플 평균 {s['filter_kept_mean']:.2f} · 후보에 없던 트리플 {s['filter_invented']} · "
              f"reset 중 passage 몫 {s['passage_share_mean'] if s['passage_share_mean'] is None else round(s['passage_share_mean'], 3)}", flush=True)

    Path(args.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    report = {"questions": len(questions), "top_k": args.top_k, "variants": summary,
              "llm_by_index": {key: index.llm.stats.snapshot() for key, index in indexes.items()}}
    Path(args.out).with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    for key, index in indexes.items():
        print(f"  필터 LLM ({key}): {common.usage_line(index.llm.stats.snapshot())}")


if __name__ == "__main__":
    main()
