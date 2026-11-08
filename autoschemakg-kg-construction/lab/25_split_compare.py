"""두 판을 같은 문항에서 맞대어, 예산마다 재현율이 갈린 문항의 승패와 부호 검정 p 를 낸다. 덮기 판정은 23_score.py 의 것을 그대로 쓴다.

    python3 25_split_compare.py runs/25-split/retrieval.jsonl runs/25-split/gold.jsonl harness mdheader-pseudo [다른 판 쌍 ...]
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("score23", Path(__file__).parent / "23_score.py")
score23 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score23)


def recalls(retrieval, gold):
    table = {}
    for row in score23.read_jsonl(retrieval):
        qid = str(row["qid"])
        if qid not in gold:
            continue
        table.setdefault(row["variant"], {})[qid] = {name: score23.judge(cut(row["units"]), gold[qid]["items"])["recall"]
                                                    for name, cut in score23.modes(score23.TOP_K)}
    return table


def main():
    retrieval, gold_path, *names = sys.argv[1:]
    gold = {q: g for q, g in score23.read_gold(gold_path).items() if g["items"]}
    table = recalls(retrieval, gold)
    for left, right in zip(names[::2], names[1::2]):
        cells = []
        for mode, _ in score23.modes(score23.TOP_K):
            wins = sum(table[left][q][mode] > table[right][q][mode] for q in gold)
            losses = sum(table[left][q][mode] < table[right][q][mode] for q in gold)
            cells.append(f"{mode} {wins}승 {losses}패 p={score23.sign_test(wins, losses):.2f}")
        print(f"{left} 대 {right}: " + " · ".join(cells))


if __name__ == "__main__":
    main()
