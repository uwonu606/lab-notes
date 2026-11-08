import json
import re
import sys
from statistics import mean

STOPWORDS = {"a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "or", "is", "was", "be", "by", "with", "personx", "persony", "peoplex", "s"}


def words(text):
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS}


def overlap(row):
    concept = words(row["concept"])
    return len(concept & words(row["head"])) / len(concept) if concept else 0.0


def describe(label, rows):
    if not rows:
        print(f"  {label:34} n=0")
        return
    shares = [overlap(r) for r in rows]
    any_shared = sum(s > 0 for s in shares) / len(rows)
    concept_len = mean(len(words(r["concept"])) for r in rows)
    print(f"  {label:34} n={len(rows):3}  mean overlap {mean(shares):.2f}  any shared word {100 * any_shared:5.1f}%  concept words {concept_len:.1f}")


for name in sys.argv[1:]:
    before = [json.loads(l) for l in open(f"runs/10-{name}.jsonl")]
    after = [json.loads(l) for l in open(f"runs/10-{name}-strict.jsonl")]
    print(f"== {name}")
    describe("gold Yes (all)", [r for r in before if r["gold"]])
    describe("gold No (all)", [r for r in before if not r["gold"]])
    describe("gold Yes, Yes→No (newly wrong)", [y for x, y in zip(before, after) if y["gold"] and x["said_yes"] and not y["said_yes"]])
    describe("gold Yes, Yes→Yes (kept)", [y for x, y in zip(before, after) if y["gold"] and x["said_yes"] and y["said_yes"]])
    describe("gold No, Yes→No (fixed)", [y for x, y in zip(before, after) if not y["gold"] and x["said_yes"] and not y["said_yes"]])
