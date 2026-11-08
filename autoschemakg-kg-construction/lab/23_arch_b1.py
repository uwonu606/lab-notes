import argparse
import importlib
import json
import subprocess
import sys

arch = importlib.import_module("23_arch_common")

HR2_INDEX = arch.RUNS / "23-net-hr2/idx"
VARIANTS = "dense,hr2,hr2-nofilter"


def staged_path(hr2_path):
    if hr2_path == "dense-fallback":
        return arch.FALLBACK_PATH
    return arch.path(hr2_path, unit="fixed")


def main():
    parser = argparse.ArgumentParser(description="B1: 넷 HippoRAG 2 색인으로 23_hr2_retrieve.py 를 돌리고 7단계 형식(path 에 unit, fallback 표기, 5000자 담기)으로 바꾼다.")
    parser.add_argument("--index", default=str(HR2_INDEX))
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--reuse-raw", action="store_true", help="이미 받은 hr2-raw.jsonl 로 변환만 다시 한다")
    args = parser.parse_args()

    run = arch.Run("b1-hr2")
    questions = arch.read_questions()
    raw = run.dir / "hr2-raw.jsonl"
    if not args.reuse_raw:
        questions_only = run.dir / "questions-only.jsonl"
        arch.write_questions_only(questions_only, questions)
        subprocess.run([sys.executable, str(arch.LAB / "23_hr2_retrieve.py"), str(questions_only), args.index, str(raw),
                        "--variants", VARIANTS, "--top-k", str(args.top_k)], cwd=arch.LAB, check=True)
    for row in arch.read_jsonl(raw):
        units = arch.fill_budget([{**u, "path": staged_path(u["path"])} for u in row["units"]])
        if row["variant"] == "dense":
            run.add(row["qid"], "dense", units, empty_stages=[], llm={"calls": 0})
            continue
        filtered = row["filter"].get("generated") is not None
        run.add(row["qid"], row["variant"], units, graph=row["graph"], seeds=len(row["seeds"]), phrase_seeds=row.get("phrase_seeds"),
                passage_mass=row.get("passage_mass"), phrase_mass=row.get("phrase_mass"), filter=row["filter"],
                empty_stages=[] if row["graph"] else ["ppr"], llm={"calls": int(filtered)})
    run.write()
    print(run.score())
    report = json.loads(raw.with_suffix(".report.json").read_text())
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
