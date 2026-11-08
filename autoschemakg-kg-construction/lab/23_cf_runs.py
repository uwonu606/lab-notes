"""9단계 검색 판 cf-orig·cf-claimctx 와 사내화 단위 벡터.

    .venv-hr2/bin/python 23_cf_runs.py vectors [--kinds claim-ctx fixed section claim doc]  # runs/23-cf-units/idx/emb-<kind>.npy
    .venv-hr2/bin/python 23_cf_runs.py orig        # runs/23-cf-orig/: 원래 말뭉치 + 8단계 claim-ctx 벡터, questions-orig.jsonl 로 채점
    .venv-hr2/bin/python 23_cf_runs.py claimctx    # runs/23-cf-claimctx/: 사내화 말뭉치 claim-ctx, questions-cf.jsonl 로 채점
    .venv-hr2/bin/python 23_cf_runs.py check       # cf-orig 가 8단계 claim-ctx 와 같은지, 옮긴 정답이 맞는지
    .venv-hr2/bin/python 23_cf_runs.py report      # 정답 묶음·구심점·언어·유형별 표와 같은 문항 승패 (markdown)

claim-ctx 임베딩 글은 8단계(23_arch_b2.claim_context_text)와 같은 꼴이다: "{문서 title}\\n[{부모 절 section_type}] {claim text}".
판마다 NET_CORPUS·NET_GOLD 를 23_arch_common 을 읽기 전에 정한다.
"""
import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path

LAB = Path(__file__).parent
CF_GOLD_DIR = "inputs/net-corpus-cf/gold"
B2_DIR = LAB / "runs/23-arch-b2-mix"
STAGE8_VECTORS = B2_DIR / "idx/emb-claim-ctx.npy"
CF_IDX = LAB / "runs/23-cf-units/idx"
DEPTH = 400
MODES_ENV = {"orig": {"NET_CORPUS": "orig", "NET_GOLD": f"{CF_GOLD_DIR}/questions-orig.jsonl"},
             "claimctx": {"NET_CORPUS": "cf", "NET_GOLD": f"{CF_GOLD_DIR}/questions-cf.jsonl"},
             "vectors": {"NET_CORPUS": "cf"}}


def claim_context_text(claim, section_of, title_of):
    return f"{title_of[claim['doc_id']]}\n[{section_of[claim['parent_section']]['section_type']}] {claim['text']}"


def embed_rows(texts):
    import numpy as np
    import embed_client

    matrix = np.asarray(embed_client.embed(texts), dtype=np.float32)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def build_vectors(arch, kinds):
    import numpy as np
    import embed_client

    CF_IDX.mkdir(parents=True, exist_ok=True)
    report_path = CF_IDX / "embed-report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    for kind in kinds:
        rows = arch.read_jsonl(arch.UNITS_DIR / f"{'claim' if kind == 'claim-ctx' else kind}.jsonl")
        if kind == "claim-ctx":
            section_of = {r["unit_id"]: r for r in arch.read_jsonl(arch.UNITS_DIR / "section.jsonl")}
            title_of = {d["doc_id"]: d["title"] for d in arch.read_docs().values()}
            texts = [claim_context_text(r, section_of, title_of) for r in rows]
        else:
            texts = [r["text"] for r in rows]
        before = embed_client.stats["requested_texts"]
        started = time.monotonic()
        matrix = embed_rows(texts)
        np.save(CF_IDX / f"emb-{kind}.npy", matrix)
        (CF_IDX / f"emb-{kind}.ids.json").write_text(json.dumps([r["unit_id"] for r in rows], ensure_ascii=False))
        report[kind] = {"rows": len(rows), "new_texts": embed_client.stats["requested_texts"] - before,
                        "seconds": round(time.monotonic() - started, 1), "backend": embed_client.stats.get("backend"),
                        "units_sha256": arch.sha256_of(arch.UNITS_DIR / f"{'claim' if kind == 'claim-ctx' else kind}.jsonl")}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
        print(kind, report[kind], flush=True)


def claim_ctx_units(arch, vectors_path):
    import numpy as np

    claims = arch.read_jsonl(arch.UNITS_DIR / "claim.jsonl")
    ids = json.loads(vectors_path.with_suffix(".ids.json").read_text())
    if ids != [r["unit_id"] for r in claims]:
        raise ValueError(f"{vectors_path} 의 ids 가 {arch.UNITS_DIR}/claim.jsonl 순서와 다르다")
    return arch.Units("claim", claims, np.load(vectors_path))


def run_claimctx(arch, name, variant, vectors_path, run_dir):
    import embed_client

    questions = arch.read_questions()
    qvecs = arch.embed_questions(questions)
    ctx = claim_ctx_units(arch, vectors_path)
    run = arch.Run(name, run_dir=run_dir)
    for q, qvec in zip(questions, qvecs):
        ranked = ctx.dense_units(qvec, path_stages=("dense=claim-ctx",), top=DEPTH)
        run.add(q.qid, variant, arch.fill_budget(ranked), stage_counts={"dense=claim-ctx": DEPTH}, empty_stages=[], llm={"calls": 0})
    run.write()
    print(run.score())
    (run.dir / "run-report.json").write_text(json.dumps({
        "variant": variant, "docs": str(arch.DOCS.relative_to(LAB)), "docs_sha256": arch.sha256_of(arch.DOCS),
        "gold": str(arch.GOLD.relative_to(LAB)), "gold_sha256": arch.sha256_of(arch.GOLD),
        "units_dir": str(arch.UNITS_DIR.relative_to(LAB)), "vectors": str(vectors_path.relative_to(LAB)),
        "vectors_sha256": arch.sha256_of(vectors_path), "questions": len(questions), "embed_stats": embed_client.stats},
        ensure_ascii=False, indent=1))


def check(arch):
    """1) cf-orig 의 pub 문항 retrieval·detail 이 8단계 claim-ctx 와 같은가. 2) cf-orig 결과를 사내화 위치로 옮겨 questions-cf 의 pub 으로 채점해도 같은가."""
    import subprocess

    cf = importlib.import_module("23_cf_layer")
    layer = cf.Layer.load()
    stage8 = {r["qid"]: r for r in arch.read_jsonl(B2_DIR / "retrieval.jsonl") if r["variant"] == "claim-ctx"}
    orig_dir = LAB / "runs/23-cf-orig"
    mine = {r["qid"]: r for r in arch.read_jsonl(orig_dir / "retrieval.jsonl")}
    same_units = sum([(u["doc_id"], u["start"], u["end"]) for u in mine[q]["units"]] == [(u["doc_id"], u["start"], u["end"]) for u in r["units"]]
                     for q, r in stage8.items())
    d8 = {(r["qid"], r["mode"]): r["recall"] for r in arch.read_jsonl(B2_DIR / "detail.jsonl") if r["variant"] == "claim-ctx"}
    do = {(r["qid"], r["mode"]): r["recall"] for r in arch.read_jsonl(orig_dir / "detail.jsonl")}
    same_recall = sum(do.get(k) == v for k, v in d8.items())
    moved_dir = LAB / "runs/23-cf-orig/moved"
    moved_dir.mkdir(exist_ok=True)
    moved = [{**r, "units": [dict(zip(("doc_id", "start", "end"), layer.map_span(u["doc_id"], u["start"], u["end"])),
                                  score=u["score"], path=u["path"]) for u in r["units"]]}
             for r in mine.values() if not r["qid"].startswith("F")]
    arch.write_jsonl(moved_dir / "retrieval.jsonl", moved)
    gold_cf = LAB / CF_GOLD_DIR / "questions-cf.jsonl"
    subprocess.run([sys.executable, str(arch.SCORER), "retrieval.jsonl", str(gold_cf), "--detail", "detail.jsonl"],
                   cwd=moved_dir, check=True, capture_output=True, text=True)
    dm = {(r["qid"], r["mode"]): r["recall"] for r in arch.read_jsonl(moved_dir / "detail.jsonl")}
    moved_same = sum(dm.get(k) == v for k, v in d8.items())
    differ = sorted({k[0] for k, v in d8.items() if dm.get(k) != v})
    result = {"stage8_questions": len(stage8), "same_units": same_units, "detail_rows": len(d8), "same_recall": same_recall,
              "moved_same_recall": moved_same, "moved_differs_qids": differ}
    (moved_dir / "check.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def recall_by_qid(run_dir, variant):
    rows = [json.loads(line) for line in (Path(run_dir) / "detail.jsonl").read_text().splitlines() if line.strip()]
    return {(r["qid"], r["mode"]): r["recall"] for r in rows if r["variant"] == variant}


def gold_rows(path):
    return {r["qid"]: r for r in map(json.loads, (LAB / path).read_text().splitlines())}


def recall_table(recalls, qids_by_group, modes):
    lines = ["| 묶음 | 문항 | " + " | ".join(modes) + " |", "|---|---|" + "---|" * len(modes)]
    for label, qids in qids_by_group:
        cells = [f"{sum(recalls[q, m] for q in qids) / len(qids):.3f}" if qids else "-" for m in modes]
        lines.append(f"| {label} | {len(qids)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def versus_table(pairs_by_group, mine, base, modes, sign_test):
    """pairs: (내 qid, 기준 qid). 칸은 이김·짐(p)."""
    lines = ["| 묶음 | 문항 | " + " | ".join(modes) + " |", "|---|---|" + "---|" * len(modes)]
    for label, pairs in pairs_by_group:
        cells = []
        for m in modes:
            diffs = [mine[a, m] - base[b, m] for a, b in pairs]
            win, loss = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            cells.append(f"{win}승 {loss}패 (p={sign_test(win, loss):.2f})")
        lines.append(f"| {label} | {len(pairs)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def report(arch):
    """cf-orig·cf-claimctx 의 정답 묶음·구심점 닿음·유형·언어별 재현율과, 같은 문항(alias 는 pub_qid) 승패."""
    sign_test = arch._scorer().sign_test
    modes = list(arch.MODES)
    cf_gold = {q: r for q, r in gold_rows(f"{CF_GOLD_DIR}/questions-cf.jsonl").items() if r["evidence"]}
    orig_gold = {q: r for q, r in gold_rows(f"{CF_GOLD_DIR}/questions-orig.jsonl").items() if r["evidence"]}
    cfc = recall_by_qid(LAB / "runs/23-cf-claimctx", "cf-claimctx")
    org = recall_by_qid(LAB / "runs/23-cf-orig", "cf-orig")
    out = []
    by = lambda gold, pred: sorted(q for q, r in gold.items() if pred(r))
    sets = [("pub", lambda r: r["set"] == "pub"), ("pub · hub_touch", lambda r: r["set"] == "pub" and r["hub_touch"]),
            ("pub · 질문에 구심점", lambda r: r["set"] == "pub" and bool(r["gold_hubs"])),
            ("alias", lambda r: r["set"] == "alias"), ("fact", lambda r: r["set"] == "fact")]
    out += ["### 재현율: cf-orig (원래 말뭉치)", recall_table(org, [(n, by(orig_gold, f)) for n, f in sets if not n.startswith("alias")], modes)]
    out += ["### 재현율: cf-claimctx (사내화 말뭉치)", recall_table(cfc, [(n, by(cf_gold, f)) for n, f in sets], modes)]
    out += ["### cf-claimctx 언어별", recall_table(cfc, [(f"{s} · {lang}", by(cf_gold, lambda r, s=s, lang=lang: r["set"] == s and r["lang"] == lang))
                                                     for s in ("pub", "alias", "fact") for lang in ("ko", "en")], modes)]
    types = sorted({r["type"] for r in cf_gold.values()})
    out += ["### cf-claimctx 유형별 (pub · alias)", recall_table(cfc, [(f"{s} · {t}", by(cf_gold, lambda r, s=s, t=t: r["set"] == s and r["type"] == t))
                                                                 for s in ("pub", "alias") for t in types if t != "fact"], modes)]
    pub_q = by(cf_gold, lambda r: r["set"] == "pub")
    alias_pairs = [(q, cf_gold[q]["pub_qid"]) for q in by(cf_gold, lambda r: r["set"] == "alias")]
    fact_q = by(cf_gold, lambda r: r["set"] == "fact")
    out += ["### 같은 문항 승패 (왼쪽이 이기면 승)", versus_table([
        ("pub: cf-claimctx 대 cf-orig", [(q, q) for q in pub_q]),
        ("pub hub_touch: cf-claimctx 대 cf-orig", [(q, q) for q in pub_q if cf_gold[q]["hub_touch"]]),
        ("alias(cf) 대 pub(cf-orig) — 빈틈", alias_pairs),
        ("fact: cf-claimctx 대 cf-orig", [(q, q) for q in fact_q])], {**cfc}, {**org}, modes, sign_test)]
    out += ["### 같은 사내화 말뭉치에서 alias 대 pub (cf-claimctx)", versus_table([("alias 대 pub", alias_pairs)], cfc, cfc, modes, sign_test)]
    labels_path = LAB / CF_GOLD_DIR / "labels.jsonl"
    if labels_path.exists():
        traced = {r["qid"]: r["trace_hint"] for r in map(json.loads, labels_path.read_text().splitlines())}
        groups = [(f"{s} · 흔적 {'있음' if t else '없음'}", by(cf_gold, lambda r, s=s, t=t: r["set"] == s and traced[r["qid"]] == t))
                  for s in ("pub", "alias", "fact") for t in (True, False)]
        out += ["### cf-claimctx 근거·near 문서의 정체 흔적(labels.jsonl trace_hint)별", recall_table(cfc, groups, modes)]
        orig_groups = [(f"pub · 흔적 {'있음' if t else '없음'}", by(orig_gold, lambda r, t=t: r["set"] == "pub" and traced[r["qid"]] == t))
                       for t in (True, False)]
        out += ["### cf-orig 흔적별 (pub)", recall_table(org, orig_groups, modes)]
    scope_path = LAB / CF_GOLD_DIR / "scope.txt"
    if scope_path.exists():
        scope = [line.split("\t")[0].strip() for line in scope_path.read_text().splitlines() if line.strip()]
        in_scope = [q for q in scope if q in cf_gold]
        groups = [("scope 전체", in_scope), ("scope · alias", [q for q in in_scope if cf_gold[q]["set"] == "alias"]),
                  ("scope · fact", [q for q in in_scope if cf_gold[q]["set"] == "fact"])]
        out += [f"### scope.txt ({len(scope)}문항 중 근거 있는 {len(in_scope)}) — cf-claimctx", recall_table(cfc, groups, modes)]
        orig_twins = [("scope · alias 의 pub_qid", [cf_gold[q]["pub_qid"] for q in groups[1][1]]), ("scope · fact", groups[2][1])]
        out += ["### scope.txt — cf-orig (alias 는 짝 pub 문항으로)", recall_table(org, orig_twins, modes)]
    return "\n\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="9단계 cf-orig·cf-claimctx 판과 사내화 단위 벡터.")
    parser.add_argument("command", choices=["vectors", "orig", "claimctx", "check", "report"])
    parser.add_argument("--kinds", nargs="+", default=["claim-ctx", "fixed"])
    args = parser.parse_args()
    for key, value in MODES_ENV.get(args.command, {"NET_CORPUS": "orig"}).items():
        os.environ[key] = value
    sys.path.insert(0, str(LAB))
    arch = importlib.import_module("23_arch_common")
    if args.command == "vectors":
        build_vectors(arch, args.kinds)
    elif args.command == "orig":
        run_claimctx(arch, "orig", "cf-orig", STAGE8_VECTORS, LAB / "runs/23-cf-orig")
    elif args.command == "claimctx":
        run_claimctx(arch, "claimctx", "cf-claimctx", CF_IDX / "emb-claim-ctx.npy", LAB / "runs/23-cf-claimctx")
    elif args.command == "report":
        print(report(arch))
    else:
        print(json.dumps(check(arch), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
