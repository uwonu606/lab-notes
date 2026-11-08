"""chain.sh 의 단계 사이 검사. 통과하면 0, 아니면 이유를 찍고 1 로 끝난다.

    .venv-hr2/bin/python 23_cf_chain_check.py links      # scope-retrieval.txt 문항이 연결 파일에 다 있고 실패가 0 인가
    .venv-hr2/bin/python 23_cf_chain_check.py answers S1  # runs/23-cf-answer/S1/answers.jsonl 이 scope.txt 80문항을 다 답했나
    .venv-hr2/bin/python 23_cf_chain_check.py grades S1   # grades.jsonl 채점 실패가 상한 이하인가
    .venv-hr2/bin/python 23_cf_chain_check.py retrieval runs/23-cf-relgraph cf-relgraph  # 답 판이 읽을 검색 결과가 scope.txt 를 다 덮나
    .venv-hr2/bin/python 23_cf_chain_check.py embcount    # 임베딩 캐시 행 수 (단계 앞뒤를 견주어 서버를 불렀는지 본다)
"""
import json
import sys
from pathlib import Path

LAB = Path(__file__).parent
GOLD_DIR = LAB / "inputs/net-corpus-cf/gold"
LINKS = [LAB / "runs/23-cf-link/questions-alias.jsonl", LAB / "runs/23-cf-link/questions-fact.jsonl"]
ANSWERS = LAB / "runs/23-cf-answer"
GRADE_FAILURES_ALLOWED = 2


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def scope(name):
    return [line.split("\t", 1)[0] for line in (GOLD_DIR / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def check_links():
    rows = {r["qid"]: r for path in LINKS for r in read_jsonl(path)}
    wanted = scope("scope-retrieval.txt")
    missing = [q for q in wanted if q not in rows]
    failed = [q for q in wanted if q in rows and rows[q]["error"]]
    return [f"연결 파일에 없는 문항 {len(missing)}: {missing[:5]}"] * bool(missing) + [f"연결 실패 {len(failed)}: {failed[:5]}"] * bool(failed)


def check_answers(label):
    rows = {r["qid"]: r for r in read_jsonl(ANSWERS / label / "answers.jsonl")}
    wanted = scope("scope.txt")
    missing = [q for q in wanted if q not in rows]
    failed = [q for q in wanted if q in rows and rows[q].get("answer") is None]
    return [f"{label}: 답이 없는 문항 {len(missing)}"] * bool(missing) + [f"{label}: 답 실패 {len(failed)}: {failed[:5]}"] * bool(failed)


def check_grades(label):
    failed = [r["qid"] for r in read_jsonl(ANSWERS / label / "grades.jsonl") if "correctness" not in r]
    return [f"{label}: 채점 실패 {len(failed)} > {GRADE_FAILURES_ALLOWED}: {failed[:5]}"] * (len(failed) > GRADE_FAILURES_ALLOWED)


def check_retrieval(run_dir, variant):
    path = LAB / run_dir / "retrieval.jsonl"
    if not path.exists():
        return [f"{path} 가 없다"]
    have = {r["qid"] for r in read_jsonl(path) if r["variant"] == variant}
    missing = [q for q in scope("scope.txt") if q not in have]
    return [f"{run_dir} {variant}: scope.txt 문항 {len(missing)}개가 없다: {missing[:5]}"] * bool(missing)


def embedding_rows():
    import sqlite3
    sys.path.insert(0, str(LAB))
    import embed_client
    with sqlite3.connect(embed_client.CACHE_DB, timeout=120) as connection:
        table = connection.execute("select name from sqlite_master where type='table'").fetchone()[0]
        return connection.execute(f"select count(*) from {table}").fetchone()[0]


def main():
    command, *args = sys.argv[1:]
    if command == "embcount":
        print(embedding_rows())
        return
    problems = {"links": check_links, "answers": check_answers, "grades": check_grades, "retrieval": check_retrieval}[command](*args)
    for p in problems:
        print(f"검사 실패: {p}")
    print("검사 통과" if not problems else "", flush=True)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
