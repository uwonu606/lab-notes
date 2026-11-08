"""7단계 아키텍처 판들이 함께 쓰는 읽기·dense 검색·글자 예산 담기·fallback·결과 쓰기·채점·B0 대비 승패.

    import importlib
    arch = importlib.import_module("23_arch_common")      # lab/ 에서 돌린다. numpy 가 있는 .venv-hr2/bin/python

    questions = arch.read_questions()                      # [Question(qid, question, lang)] — 정답 칸은 읽지 않는다
    fixed = arch.load_units("fixed")                       # 단위 행 + idx 벡터 (ids 순서 확인)
    qvecs = arch.embed_questions(questions)                # embed_client.embed, 캐시 공유
    run = arch.Run("a3-section")
    for q, qvec in zip(questions, qvecs):
        mine = [fixed.as_unit(i, s, arch.path("section=증상", unit="section")) for i, s in ...]
        units, used_fallback = arch.fill_with_fallback(mine, qvec)
        run.add(q.qid, "a3-section", units, fallback=used_fallback, stage_counts={...})
    run.write()                                            # retrieval.jsonl, trace.jsonl
    run.score()                                            # score.txt, detail.jsonl
    print(arch.report_tables(run.dir, "a3-section"))       # 유형별 표 + B0 대비 승패 + path 집계 (markdown)

NET_CORPUS=cf 로 띄우면 DOCS·UNITS_DIR·GOLD·판 폴더(runs/23-cf-<name>/)·기준 판(cf-claimctx)이 9단계 사내화 말뭉치 쪽으로 바뀐다.
NET_GOLD=<lab 기준 경로> 는 채점·질문 파일만 바꾼다. 둘 다 import 전에 정한다. 없으면 7·8단계 그대로다.

정답의 answer·answer_path·evidence 는 채점 쪽(23_score.py 와 detail.jsonl 을 읽는 report 함수)만 본다.
질문 유형(type)도 검색 코드에 넘기지 않고 보고 표에서만 읽는다.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from statistics import mean

import numpy as np

import embed_client

LAB = Path(__file__).parent
CORPUS = LAB / "inputs/net-corpus"
CF_CORPUS = LAB / "inputs/net-corpus-cf"
RUNS = LAB / "runs"
SCORER = LAB / "23_score.py"
CORPUS_SWITCH = os.environ.get("NET_CORPUS", "orig")
if CORPUS_SWITCH not in ("orig", "cf"):
    raise ValueError(f"NET_CORPUS 는 orig 나 cf 다: {CORPUS_SWITCH!r}")
IS_CF = CORPUS_SWITCH == "cf"
DOCS = (CF_CORPUS if IS_CF else CORPUS) / "docs.jsonl"
GOLD = LAB / os.environ["NET_GOLD"] if os.environ.get("NET_GOLD") else (
    CF_CORPUS / "gold/questions-cf.jsonl" if IS_CF else CORPUS / "gold/questions.jsonl")
UNITS_DIR = RUNS / ("23-cf-units" if IS_CF else "23-net-units")
IDX_DIR = UNITS_DIR / "idx"
RUN_PREFIX = "23-cf-" if IS_CF else "23-arch-"
B0_DIR = RUNS / ("23-cf-claimctx" if IS_CF else "23-arch-b0-dense")
B0_VARIANT = "cf-claimctx" if IS_CF else "dense"
UNIT_KINDS = ("fixed", "section", "claim", "doc")
MIN_BUDGET = 5000
MIN_UNITS = 5
MODES = ("@5", "1000자", "2500자", "5000자")
FALLBACK_PATH = "fallback=dense>unit=fixed"
GROUP_LABEL = {"type": "유형", "lang": "언어", "set": "정답 묶음", "hub_touch": "구심점 닿음"}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def read_docs(path=DOCS):
    return {row["doc_id"]: row for row in read_jsonl(path)}


def span_text(doc_id, start, end):
    return read_docs()[doc_id]["text"][start:end]


@dataclass(frozen=True)
class Question:
    qid: str
    question: str
    lang: str


def read_questions(path=GOLD):
    return [Question(str(row["qid"]), row["question"], row.get("lang", "")) for row in read_jsonl(path)]


def write_questions_only(path, questions):
    write_jsonl(path, [{"id": q.qid, "question": q.question} for q in questions])


def embed_questions(questions):
    texts = [q.question if isinstance(q, Question) else q for q in questions]
    return np.asarray(embed_client.embed(texts), dtype=np.float32)


class Units:
    def __init__(self, kind, rows, matrix):
        self.kind = kind
        self.rows = rows
        self.matrix = matrix
        self.ids = [r["unit_id"] for r in rows]
        self.index_of = {unit_id: i for i, unit_id in enumerate(self.ids)}
        self.by_doc = defaultdict(list)
        for i, r in enumerate(rows):
            self.by_doc[r["doc_id"]].append(i)

    def __len__(self):
        return len(self.rows)

    def scores(self, qvec, among=None):
        indices = np.arange(len(self.rows)) if among is None else np.asarray(sorted(self._indices(among)), dtype=np.int64)
        return indices, self.matrix[indices] @ np.asarray(qvec, dtype=np.float32)

    def search(self, qvec, among=None, top=None):
        """among 은 unit_id 나 행 번호의 모음이다. 점수 내림차순 [(행 번호, cosine)]."""
        indices, scores = self.scores(qvec, among)
        order = np.argsort(-scores, kind="stable")[:top]
        return [(int(indices[o]), float(scores[o])) for o in order]

    def _indices(self, among):
        return {self.index_of[a] if isinstance(a, str) else int(a) for a in among}

    def covering(self, doc_id, start, end):
        """[start, end) 와 겹치는 이 종류 단위의 행 번호, 문서 안 위치 순."""
        return [i for i in self.by_doc.get(doc_id, ()) if self.rows[i]["start"] < end and start < self.rows[i]["end"]]

    def as_unit(self, i, score, path):
        r = self.rows[i]
        return {"doc_id": r["doc_id"], "start": r["start"], "end": r["end"], "score": float(score), "path": path, "unit_id": r["unit_id"]}

    def dense_units(self, qvec, path_stages=("dense",), among=None, top=None):
        return [self.as_unit(i, s, path(*path_stages, unit=self.kind)) for i, s in self.search(qvec, among, top)]


@lru_cache(maxsize=None)
def load_units(kind):
    rows = read_jsonl(UNITS_DIR / f"{kind}.jsonl")
    vector_path = IDX_DIR / f"emb-{kind}.npy"
    if not vector_path.exists():
        raise FileNotFoundError(f"{vector_path} 가 아직 없다 (net-units 가 23_net_embed.py 로 만든다)")
    matrix = np.load(vector_path)
    vector_ids = json.loads((IDX_DIR / f"emb-{kind}.ids.json").read_text())
    row_ids = [r["unit_id"] for r in rows]
    if len(vector_ids) != matrix.shape[0]:
        raise ValueError(f"{kind}: 벡터 {matrix.shape[0]}행, ids {len(vector_ids)}개")
    if vector_ids != row_ids:
        if sorted(vector_ids) != sorted(row_ids):
            raise ValueError(f"{kind}: 벡터 ids 와 단위 jsonl 의 unit_id 집합이 다르다")
        position = {unit_id: n for n, unit_id in enumerate(vector_ids)}
        matrix = matrix[[position[u] for u in row_ids]]
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError(f"{kind}: 행 노름이 1 이 아니다 (최소 {norms.min():.4f}, 최대 {norms.max():.4f})")
    return Units(kind, rows, matrix.astype(np.float32, copy=False))


def stored_vectors_match_cache(kind, sample=16):
    """idx 벡터가 지금 embed_client 기본 백엔드로 같은 텍스트를 임베딩한 값과 맞는지 (최소 cosine, 새로 임베딩한 수)."""
    units = load_units(kind)
    picks = np.linspace(0, len(units) - 1, sample).astype(int)
    before = embed_client.stats["requested_texts"]
    fresh = np.asarray(embed_client.embed([units.rows[i]["text"] for i in picks]), dtype=np.float32)
    fresh /= np.linalg.norm(fresh, axis=1, keepdims=True)
    cosines = (fresh * units.matrix[picks]).sum(axis=1)
    return float(cosines.min()), embed_client.stats["requested_texts"] - before


def path(*stages, unit):
    return ">".join([*stages, f"unit={unit}"])


def chars_of(units):
    return sum(u["end"] - u["start"] for u in units)


def without_repeats(units):
    seen, kept = set(), []
    for u in units:
        span = (u["doc_id"], u["start"], u["end"])
        if span not in seen:
            seen.add(span)
            kept.append(u)
    return kept


def without_overlaps(units):
    """앞서 담은 단위와 글자 구간이 겹치는 단위를 뺀다 (claim 이 든 fixed 청크 같은 것)."""
    kept_by_doc, kept = defaultdict(list), []
    for u in units:
        spans = kept_by_doc[u["doc_id"]]
        if any(s < u["end"] and u["start"] < e for s, e in spans):
            continue
        spans.append((u["start"], u["end"]))
        kept.append(u)
    return kept


RRF_K = 60


def rrf(*rankings, k=RRF_K):
    """순위 순 단위 목록 여럿을 reciprocal rank fusion 으로 합친다. 같은 구간은 한 번만, 먼저 나온 목록의 path 를 남기고 score 를 RRF 값으로 바꾼다."""
    fused, first_seen = defaultdict(float), {}
    for ranking in rankings:
        for rank, u in enumerate(without_repeats(ranking), start=1):
            span = (u["doc_id"], u["start"], u["end"])
            fused[span] += 1.0 / (k + rank)
            first_seen.setdefault(span, u)
    order = sorted(fused, key=lambda span: -fused[span])
    return [{**first_seen[span], "score": fused[span]} for span in order]


def fill_budget(ranked, budget=MIN_BUDGET, min_units=MIN_UNITS):
    """순위 순 단위에서 같은 구간을 빼고, 글자 합이 budget 이상이고 min_units 개 이상이 될 때까지 앞에서 담는다."""
    kept, total = [], 0
    for u in without_repeats(ranked):
        if total >= budget and len(kept) >= min_units:
            break
        kept.append(u)
        total += u["end"] - u["start"]
    return kept


def fill_with_fallback(own, qvec, budget=MIN_BUDGET, min_units=MIN_UNITS):
    """안의 단위가 예산을 못 채우면 dense 고정 청크로 마저 채운다. (단위 목록, fallback 단위 수)."""
    own = fill_budget(own, budget, min_units)
    if chars_of(own) >= budget and len(own) >= min_units:
        return own, 0
    taken = {(u["doc_id"], u["start"], u["end"]) for u in own}
    extra = [u for u in load_units("fixed").dense_units(qvec, path_stages=("fallback=dense",))
             if (u["doc_id"], u["start"], u["end"]) not in taken]
    filled = fill_budget(own + extra, budget, min_units)
    return filled, len(filled) - len(own)


def llm_record(client, prompt, system):
    """ClaudeClient 캐시 항목에 남은 첫 호출의 초·비용. 동시 호출 중에도 질문별로 셀 수 있다."""
    entry_path = client.cache_path(prompt, system)
    if not entry_path.exists():
        return {"seconds": 0.0, "cost_usd": 0.0, "cached": False}
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    return {"seconds": entry["seconds"], "cost_usd": entry["cost_usd"], "cached": True}


class Run:
    """한 판의 폴더 runs/23-arch-<name>/ (NET_CORPUS=cf 면 runs/23-cf-<name>/) 에 retrieval.jsonl·trace.jsonl·score.txt·detail.jsonl 을 쓴다."""

    def __init__(self, name, run_dir=None):
        self.name = name
        self.dir = Path(run_dir) if run_dir else RUNS / f"{RUN_PREFIX}{name}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.retrieval = []
        self.traces = []

    def add(self, qid, variant, units, **trace):
        """trace 권장 칸: parsed, linked, stage_counts, empty_stages, fallback(단위 수), llm{calls,cost_usd,seconds}."""
        self.retrieval.append({"qid": qid, "variant": variant, "units": units})
        self.traces.append({"qid": qid, "variant": variant, "units": len(units), "chars": chars_of(units),
                            "fallback_units": sum(u["path"].startswith("fallback") for u in units), **trace})

    def write(self):
        write_jsonl(self.dir / "retrieval.jsonl", self.retrieval)
        write_jsonl(self.dir / "trace.jsonl", self.traces)

    def score(self):
        return score_run(self.dir)


GOLD_STAMP = "gold-sha256.txt"


def score_run(run_dir):
    """채점에 쓴 gold 의 sha256 을 gold-sha256.txt 에 남긴다. 채점 중에 gold 가 바뀌면 멈춘다."""
    gold_before = sha256_of(GOLD)
    completed = subprocess.run([sys.executable, str(SCORER), "retrieval.jsonl", str(GOLD.resolve()),
                                "--detail", "detail.jsonl"], cwd=run_dir, capture_output=True, text=True, check=True)
    if sha256_of(GOLD) != gold_before:
        raise RuntimeError("채점하는 동안 gold 가 바뀌었다. 다시 채점한다")
    (Path(run_dir) / "score.txt").write_text(completed.stdout)
    (Path(run_dir) / GOLD_STAMP).write_text(gold_before + "\n")
    return completed.stdout


def gold_stamp(run_dir):
    stamp = Path(run_dir) / GOLD_STAMP
    return stamp.read_text().strip() if stamp.exists() else None


def _scorer():
    spec = spec_from_file_location("score23", SCORER)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _question_groups(by="type", gold_path=GOLD):
    return {str(row["qid"]): row.get(by) for row in read_jsonl(gold_path)}


def read_detail(run_dir, variant):
    """{(qid, mode): detail 행}"""
    return {(r["qid"], r["mode"]): r for r in read_jsonl(Path(run_dir) / "detail.jsonl") if r["variant"] == variant}


def type_table(run_dir, variant, by="type"):
    """by 는 gold 의 묶음 칸: "type"(유형) 이나 "lang"(질문 언어)."""
    detail = read_detail(run_dir, variant)
    types = _question_groups(by)
    by_type = defaultdict(set)
    for qid, _ in detail:
        by_type[types[qid]].add(qid)
    lines = [f"| {GROUP_LABEL[by]} | 문항 | " + " | ".join(MODES) + " |", "|---|---|" + "---|" * len(MODES)]
    for t, qids in sorted(by_type.items()) + [("전체", set().union(*by_type.values()))]:
        cells = [f"{mean(detail[q, m]['recall'] for q in qids):.3f} ({sum(detail[q, m]['all'] for q in qids)})" for m in MODES]
        lines.append(f"| {t} | {len(qids)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def compare_with_b0(run_dir, variant, base_dir=B0_DIR, base_variant=B0_VARIANT, by="type"):
    """유형 × 방식마다 B0 대비 재현율이 높은 문항(이김)·낮은 문항(짐)·같은 문항과 부호 검정 p."""
    if gold_stamp(run_dir) != gold_stamp(base_dir):
        raise RuntimeError(f"{run_dir} 와 {base_dir} 가 다른 gold 로 채점됐다. 둘 다 score_run 으로 다시 채점한다")
    mine, base = read_detail(run_dir, variant), read_detail(base_dir, base_variant)
    sign_test = _scorer().sign_test
    types = _question_groups(by)
    rows = {}
    for (qid, mode), r in mine.items():
        if (qid, mode) not in base:
            continue
        diff = r["recall"] - base[qid, mode]["recall"]
        for t in (types[qid], "전체"):
            cell = rows.setdefault((t, mode), {"win": [], "loss": [], "tie": 0})
            if diff > 0:
                cell["win"].append(qid)
            elif diff < 0:
                cell["loss"].append(qid)
            else:
                cell["tie"] += 1
    for cell in rows.values():
        cell["p"] = sign_test(len(cell["win"]), len(cell["loss"]))
    return rows


def compare_table(run_dir, variant, base_dir=B0_DIR, base_variant=B0_VARIANT, by="type"):
    rows = compare_with_b0(run_dir, variant, base_dir, base_variant, by)
    order = sorted({t for t, _ in rows} - {"전체"}) + ["전체"]
    lines = [f"| {GROUP_LABEL[by]} | " + " | ".join(MODES) + " |", "|---|" + "---|" * len(MODES)]
    for t in order:
        cells = [f"{len(c['win'])}승 {len(c['loss'])}패 (p={c['p']:.2f})" if (c := rows.get((t, m))) else "-" for m in MODES]
        lines.append(f"| {t} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def first_stage(unit_path):
    return unit_path.split(">", 1)[0].split("=", 1)[0]


def unit_kind(unit_path):
    return next((stage.split("=", 1)[1] for stage in unit_path.split(">") if stage.startswith("unit=")), "(표기 없음)")


def path_counts(run_dir, variant, mode):
    """찾은 근거 묶음을 덮은 path 의 첫 단계 종류별 수, unit 종류별 수, fallback 단위만 덮은 묶음 수."""
    kinds, units, only_fallback = Counter(), Counter(), 0
    for (qid, m), r in read_detail(run_dir, variant).items():
        if m != mode:
            continue
        for found in r["found"]:
            stages = {first_stage(p) for p in found["paths"]}
            kinds.update(stages)
            units.update({unit_kind(p) for p in found["paths"]})
            only_fallback += stages == {"fallback"}
    return kinds, units, only_fallback


def path_table(run_dir, variant):
    lines = ["| 방식 | 첫 단계별 찾은 묶음 | unit 종류별 찾은 묶음 | fallback 만 찾은 묶음 |", "|---|---|---|---|"]
    for mode in MODES:
        kinds, units, only_fallback = path_counts(run_dir, variant, mode)
        lines.append(f"| {mode} | " + " · ".join(f"{k} {c}" for k, c in kinds.most_common()) + " | "
                     + " · ".join(f"{k} {c}" for k, c in units.most_common()) + f" | {only_fallback} |")
    return "\n".join(lines)


def trace_summary(run_dir, variant):
    traces = [t for t in read_jsonl(Path(run_dir) / "trace.jsonl") if t["variant"] == variant]
    return {"questions": len(traces),
            "fallback_questions": sum(t["fallback_units"] > 0 for t in traces),
            "all_fallback_questions": sum(t["fallback_units"] == t["units"] for t in traces),
            "mean_units": round(mean(t["units"] for t in traces), 1),
            "mean_chars": round(mean(t["chars"] for t in traces))}


def report_tables(run_dir, variant, base_dir=B0_DIR, base_variant=B0_VARIANT):
    parts = [f"### {variant} 유형별 재현율 (괄호는 묶음을 다 찾은 문항 수)", type_table(run_dir, variant)]
    if (Path(run_dir).resolve(), variant) != (Path(base_dir).resolve(), base_variant):
        parts += [f"### {variant} 대 B0 `{base_variant}` 문항 승패", compare_table(run_dir, variant, base_dir, base_variant)]
    parts += [f"### {variant} 찾은 근거의 path", path_table(run_dir, variant),
              f"trace: {json.dumps(trace_summary(run_dir, variant), ensure_ascii=False)}"]
    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="채점한 판의 유형별 표, B0 대비 승패, path 집계를 markdown 으로 낸다.")
    parser.add_argument("run_dir")
    parser.add_argument("variant")
    parser.add_argument("--base-dir", default=str(B0_DIR))
    parser.add_argument("--base-variant", default=B0_VARIANT)
    args = parser.parse_args()
    print(report_tables(Path(args.run_dir), args.variant, Path(args.base_dir), args.base_variant))


if __name__ == "__main__":
    main()
