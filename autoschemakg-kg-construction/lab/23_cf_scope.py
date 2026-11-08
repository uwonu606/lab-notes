"""9단계 작은 모델 단계(연결·다시 쓰기·슬롯·답)가 함께 쓰는 문항 범위를 inputs/net-corpus-cf/gold/scope.txt 에 낸다.

규칙(team-lead 결정, runs/23-cf-answer/CONFIG.md): fact 문항은 sha256(qid) 순 앞 40개까지, 나머지 자리를
hub_touch 인 alias 문항으로 sha256(qid) 순으로 채워 80 에 맞춘다. 순서가 qid 만으로 정해지므로 GPU 시간이 늘면
--size 를 키워 같은 순서로 뒤를 이어 붙이고, 앞의 목록은 그대로 남는다.

--retrieval: 검색 단계(연결·다시 쓰기·슬롯)만 넓힌 scope-retrieval.txt 를 낸다(team-lead 결정). scope.txt 80문항을 그 순서대로
앞에 두고, 근거가 있는 alias 문항 가운데 scope 밖의 것을 sha256(qid) 순으로 뒤에 붙인다. 답 판은 scope.txt 그대로다.
"""
import argparse
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).parent
GOLD_DIR = LAB / "inputs/net-corpus-cf/gold"
SIZE = 80
FACT_CAP = 40


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def hash_order(qids):
    return sorted(qids, key=lambda q: hashlib.sha256(q.encode("utf-8")).hexdigest())


def scope(fact_rows, alias_rows, size=SIZE, fact_cap=FACT_CAP):
    if any("hub_touch" not in r for r in alias_rows):
        raise SystemExit("questions-alias.jsonl 에 hub_touch 칸이 없는 행이 있다 (cf-layer 가 정답과 함께 낸다)")
    facts = hash_order([str(r["qid"]) for r in fact_rows])[:fact_cap]
    touching = hash_order([str(r["qid"]) for r in alias_rows if r.get("hub_touch")])
    return [("fact", q) for q in facts] + [("alias", q) for q in touching[:size - len(facts)]]


def retrieval_scope(answer_scope, alias_rows):
    taken = {qid for _, qid in answer_scope}
    extra = hash_order([str(r["qid"]) for r in alias_rows if r.get("evidence") and str(r["qid"]) not in taken])
    return answer_scope + [("alias", q) for q in extra]


def write_scope(path, picked):
    path.write_text("".join(f"{qid}\t{kind}\n" for kind, qid in picked), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="fact·hub_touch alias 문항에서 작은 모델 문항 범위를 고른다.")
    parser.add_argument("--gold-dir", default=str(GOLD_DIR))
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--retrieval", action="store_true", help="scope.txt 뒤에 근거 있는 alias 를 붙인 scope-retrieval.txt 를 낸다")
    args = parser.parse_args()
    gold = Path(args.gold_dir)
    fact_rows, alias_rows = read_jsonl(gold / "questions-fact.jsonl"), read_jsonl(gold / "questions-alias.jsonl")
    picked = scope(fact_rows, alias_rows, args.size)
    if args.retrieval:
        wide = retrieval_scope(picked, alias_rows)
        write_scope(gold / "scope-retrieval.txt", wide)
        print(f"scope-retrieval.txt: {len(wide)}문항 (scope {len(picked)} + 근거 있는 alias {len(wide) - len(picked)})")
        return
    write_scope(gold / "scope.txt", picked)
    touching = sum(bool(r.get("hub_touch")) for r in alias_rows)
    print(f"scope.txt: {len(picked)}문항 (fact {sum(k == 'fact' for k, _ in picked)}/{len(fact_rows)}, "
          f"hub_touch alias {sum(k == 'alias' for k, _ in picked)}/{touching})")


if __name__ == "__main__":
    main()
