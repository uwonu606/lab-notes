import json
import sys


def flip_rate(pairs):
    kept_yes = [(x, y) for x, y in pairs if y["gold"] and x["said_yes"]]
    flipped = sum(not y["said_yes"] for _, y in kept_yes)
    wrong_yes = [(x, y) for x, y in pairs if not y["gold"] and x["said_yes"]]
    fixed = sum(not y["said_yes"] for _, y in wrong_yes)
    return f"gold Yes said Yes→No {flipped}/{len(kept_yes)}   gold No said Yes→No {fixed}/{len(wrong_yes)}"


for name in sys.argv[1:]:
    before = [json.loads(l) for l in open(f"runs/10-{name}.jsonl")]
    after = [json.loads(l) for l in open(f"runs/10-{name}-strict.jsonl")]
    pairs = list(zip(before, after))
    whole = [p for p in pairs if p[1]["instance"].strip() == p[1]["head"].strip()]
    span = [p for p in pairs if p[1]["instance"].strip() != p[1]["head"].strip()]
    print(f"== {name}")
    print(f"  instance = whole sentence  n={len(whole):3}  {flip_rate(whole)}")
    print(f"  instance = span in it      n={len(span):3}  {flip_rate(span)}")
