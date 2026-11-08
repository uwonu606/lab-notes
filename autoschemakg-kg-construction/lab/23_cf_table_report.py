"""9단계 cf-table 보고용 표: 범위 문항에서 판마다 묶음(alias 주 비교, fact 참고)·유형·언어별 재현율, cf-table 대 다른 판의 같은 문항 승패, 통신사 문항 사례.
정답(questions-cf.jsonl)은 여기서만 읽는다. NET_CORPUS=cf 로 돌린다.

    NET_CORPUS=cf .venv-hr2/bin/python 23_cf_table_report.py --scope inputs/net-corpus-cf/gold/scope.txt \
        --run cf-table=runs/23-cf-table:cf-table --run cf-claimctx=runs/23-cf-claimctx:cf-claimctx ...
"""
import argparse
import importlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

arch = importlib.import_module("23_arch_common")

MODES = ("@5", "1000자", "2500자", "5000자")
FOCUS = ("2500자", "5000자")
CARRIER_HUBS = {"kt", "lg-uplus", "sk-telecom"}


def parse_run(text):
    label, rest = text.split("=", 1)
    run_dir, variant = rest.rsplit(":", 1)
    return label, Path(run_dir), variant


def read_scope(path):
    return {line.split("\t")[0].strip() for line in Path(path).read_text().splitlines() if line.strip()}


def recall_table(details, groups):
    labels = list(details)
    lines = ["| 묶음 | 문항 | 예산 | " + " | ".join(labels) + " |", "|---|---|---|" + "---|" * len(labels)]
    for name, qids in groups:
        for mode in (MODES if name.startswith("alias 전체") else FOCUS):
            cells = [f"{mean(details[l][q, mode]['recall'] for q in qids):.3f}" if all((q, mode) in details[l] for q in qids) else "-" for l in labels]
            lines.append(f"| {name} | {len(qids)} | {mode} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def win_loss(mine, other, qids, mode, sign_test):
    shared = [q for q in qids if (q, mode) in mine and (q, mode) in other]
    win = sum(mine[q, mode]["recall"] > other[q, mode]["recall"] for q in shared)
    loss = sum(mine[q, mode]["recall"] < other[q, mode]["recall"] for q in shared)
    return f"{win}승 {loss}패 (p={sign_test(win, loss):.2f})"


def main():
    parser = argparse.ArgumentParser(description="cf-table 과 다른 9단계 검색 판을 범위 문항에서 견준다")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--run", action="append", required=True, help="이름=폴더:variant, 첫 번째가 cf-table")
    args = parser.parse_args()

    runs = [parse_run(r) for r in args.run]
    gold = {str(r["qid"]): r for r in arch.read_jsonl(arch.GOLD)}
    scope = read_scope(args.scope)
    qids = [q for q in scope if gold[q].get("evidence")]
    details = {label: arch.read_detail(run_dir, variant) for label, run_dir, variant in runs}
    sign_test = arch._scorer().sign_test

    alias = sorted(q for q in qids if gold[q]["set"] == "alias")
    fact = sorted(q for q in qids if gold[q]["set"] == "fact")
    groups = [("alias 전체", alias)]
    groups += [(f"alias {t}", sorted(q for q in alias if gold[q]["type"] == t)) for t in sorted({gold[q]["type"] for q in alias})]
    groups += [(f"alias {lang}", sorted(q for q in alias if gold[q]["lang"] == lang)) for lang in ("ko", "en")]
    groups += [("fact 전체(참고)", fact)] + [(f"fact {lang}(참고)", sorted(q for q in fact if gold[q]["lang"] == lang)) for lang in ("ko", "en")]
    groups = [(n, g) for n, g in groups if g]
    print(f"범위 {len(scope)}문항 중 근거 있는 {len(qids)}(alias {len(alias)}, fact {len(fact)})\n")
    print("### 재현율\n")
    print(recall_table(details, groups))

    mine_label = runs[0][0]
    print(f"\n### {mine_label} 대 다른 판 문항 승패\n")
    print("| 상대 | 묶음 | " + " | ".join(MODES) + " |\n|---|---|" + "---|" * len(MODES))
    for label, _, _ in runs[1:]:
        for name, group in [("alias", alias), ("alias ko", [q for q in alias if gold[q]["lang"] == "ko"]),
                            ("alias en", [q for q in alias if gold[q]["lang"] == "en"]), ("fact(참고)", fact)]:
            if group:
                cells = [win_loss(details[mine_label], details[label], group, mode, sign_test) for mode in MODES]
                print(f"| {label} | {name} | " + " | ".join(cells) + " |")

    print(f"\n### {mine_label} 찾은 근거의 path\n")
    print(arch.path_table(runs[0][1], runs[0][2]))

    traces = {t["qid"]: t for t in arch.read_jsonl(runs[0][1] / "trace.jsonl")}
    carrier = sorted(q for q in scope if CARRIER_HUBS & set(gold[q].get("gold_hubs") or []))
    print("\n### 통신사 구심점 문항\n")
    for q in carrier:
        scores = ", ".join(f"{l} {details[l][q, '5000자']['recall']:.2f}" for l, _, _ in runs if (q, "5000자") in details[l])
        slots = json.dumps((traces.get(q) or {}).get("parsed"), ensure_ascii=False)[:300]
        print(f"- `{q}` ({gold[q]['set']}, {gold[q]['type']}): 5000자 {scores or '근거 없음'} · 슬롯 {slots} · 단계 {json.dumps((traces.get(q) or {}).get('stage_counts'), ensure_ascii=False)[:200]}")


if __name__ == "__main__":
    main()
