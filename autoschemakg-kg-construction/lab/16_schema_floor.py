import ast
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LAB = Path(__file__).parent
SCHEMA_QUALITY = LAB / "repos/AutoSchemaKG/EvaluateKGC/SchemaQuality"
DATA = SCHEMA_QUALITY / "data"
OLLAMA_CHAT = "http://localhost:11434/api/chat"
SEED = 0
UNRELATED_WORDS = [
    "banana", "violin", "cloud", "pebble", "umbrella", "spoon", "glacier", "carpet", "lantern", "tulip",
    "sneeze", "marble", "kettle", "zebra", "velvet", "comet", "pillow", "cactus", "whistle", "ladder",
]

sys.path.insert(0, str(SCHEMA_QUALITY))
import utils as official  # noqa: E402

_score_bert = official.score_bert


def score_bert_on_available_device(*args, **kwargs):
    import torch
    kwargs["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    kwargs["batch_size"] = 256
    return _score_bert(*args, **kwargs)


official.score_bert = score_bert_on_available_device


def official_prompts():
    tree = ast.parse((SCHEMA_QUALITY / "conceptualization_contextulized_api.py").read_text())
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and node.targets[0].id.endswith("_PROMPT")
    }


def read_triples(dataset):
    predecessors, successors = {}, {}
    for line in (DATA / dataset / "test.txt").read_text(encoding="utf-8").splitlines():
        h, r, t = line.strip().split("\t")
        if dataset == "YAGO43kET":
            h, t = " ".join(h.split("_")), " ".join(t.split("_"))
        triple = " ".join([h, r, t])
        predecessors.setdefault(t, []).append(triple)
        predecessors.setdefault(h, [])
        successors.setdefault(h, []).append(triple)
        successors.setdefault(t, [])
    return predecessors, successors


def entity_items(dataset, rng):
    predecessors, successors = read_triples(dataset)
    gold = {}
    for line in (DATA / dataset / "node_type_test.txt").read_text(encoding="utf-8").splitlines():
        entity, concept = line.strip().split("\t")
        if dataset == "YAGO43kET":
            entity = " ".join(entity.split("_"))
            types = [concept.split("_")[-1]]
        else:
            types = concept.split("/")[-1:]
        if entity in predecessors:
            gold.setdefault(entity, []).extend(types)
    items = []
    for entity, types in gold.items():
        neighbors = rng.sample(predecessors[entity], min(3, len(predecessors[entity])))
        neighbors += rng.sample(successors[entity], min(3, len(successors[entity])))
        items.append({"item": entity, "gold": sorted(set(types)), "context": ", ".join(neighbors)})
    return items


def relation_items():
    gold = {}
    for line in (DATA / "FB15kRT" / "test.txt").read_text(encoding="utf-8").splitlines():
        _, r, _ = line.strip().split("\t")
        for part in r.split("."):
            gold.setdefault(part.split("/")[-1], []).extend(part.split("/")[1:-1])
    return [{"item": name, "gold": sorted(set(types))} for name, types in gold.items()]


def event_items():
    gold = {}
    for line in (DATA / "wikihow" / "node_type_test.txt").read_text(encoding="utf-8").splitlines():
        event, concept = line.strip().split("\t")
        gold.setdefault(event, []).append(concept)
    return [{"item": event, "gold": sorted(set(types))} for event, types in gold.items()]


TASKS = {
    "FB15kET": ("ENTITY_PROMPT", lambda rng: entity_items("FB15kET", rng)),
    "YAGO43kET": ("ENTITY_PROMPT", lambda rng: entity_items("YAGO43kET", rng)),
    "wikihow": ("EVENT_PROMPT", lambda rng: event_items()),
    "FB15kRT": ("RELATION_PROMPT", lambda rng: relation_items()),
}


def fill(prompt, item):
    return (prompt.replace("[ENTITY]", item["item"]).replace("[CONTEXT]", item.get("context", ""))
            .replace("[EVENT]", item["item"]).replace("[RELATION]", item["item"]))


def ask_once(model, prompt):
    body = {"model": model, "stream": False, "options": {"seed": SEED},
            "messages": [{"role": "user", "content": prompt}]}
    request = urllib.request.Request(OLLAMA_CHAT, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())["message"]["content"]


def ask(model, prompt, attempts=3):
    for attempt in range(attempts):
        try:
            answer = ask_once(model, prompt)
            if answer.strip(" ?\n"):
                return answer
        except urllib.error.HTTPError:
            if attempt == attempts - 1:
                raise
        time.sleep(30)
    raise RuntimeError(f"{model} returned no usable answer")


def official_parse(answer):
    return [x.strip().lower() for x in answer.split("\n")[-1].split(",") if x.strip()]


def predictions(dataset, items, model, cache_path):
    cached = {}
    if cache_path.exists():
        cached = {r["item"]: r for r in map(json.loads, cache_path.read_text().splitlines())}
    prompt = official_prompts()[TASKS[dataset][0]]
    with cache_path.open("a") as out:
        for item in items:
            if item["item"] not in cached:
                answer = ask(model, fill(prompt, item))
                cached[item["item"]] = {"item": item["item"], "answer": answer, "pred": official_parse(answer)}
                out.write(json.dumps(cached[item["item"]], ensure_ascii=False) + "\n")
                out.flush()
    return [cached[item["item"]]["pred"] or ["None"] for item in items]


def derange(lists, rng):
    order = list(range(len(lists)))
    while any(i == j for i, j in enumerate(order)):
        rng.shuffle(order)
    return [lists[j] for j in order]


def random_vocabulary_words(rng, size=5000):
    from transformers import AutoTokenizer
    vocab = AutoTokenizer.from_pretrained("roberta-large").get_vocab()
    words = sorted(t[1:] for t in vocab if t.startswith("\u0120") and t[1:].isalpha() and t[1:].islower() and len(t) > 5)
    return rng.sample(words, size)


def conditions(items, real, rng):
    vocabulary = random_vocabulary_words(rng)
    gold = [item["gold"] for item in items]
    llm = {} if real is None else {
        "LLM (official prompt)": real,
        "LLM, another item's answer": derange(real, rng),
    }
    return {
        "gold itself": gold,
        **llm,
        "another item's gold type": derange(gold, rng),
        "unrelated words x3": [rng.sample(UNRELATED_WORDS, 3) for _ in items],
        "random vocabulary words x5": [rng.sample(vocabulary, 5) for _ in items],
        "constant 'thing'": [["thing"] for _ in items],
    }


def evaluate(gold, pred):
    _, recalls, _ = official.get_bert_score(gold, pred)
    coverage = official.get_bert_global_recall(gold, pred)
    return 100 * recalls.mean(), 100 * coverage


def main(model, sample_size, out_prefix):
    rows = []
    for dataset in TASKS:
        rng = random.Random(SEED)
        items = TASKS[dataset][1](rng)
        items = rng.sample(items, sample_size)
        real = None if model == "none" else predictions(dataset, items, model, Path(f"{out_prefix}-pred-{dataset}.jsonl"))
        for name, pred in conditions(items, real, rng).items():
            bs_r, bs_c = evaluate([i["gold"] for i in items], pred)
            rows.append({"dataset": dataset, "condition": name, "BS-R": bs_r, "BS-C": bs_c,
                         "example": {"item": items[0]["item"], "gold": items[0]["gold"], "pred": pred[0]}})
            print(f"{dataset:10} {name:28} BS-R {bs_r:6.2f}  BS-C {bs_c:6.2f}", flush=True)
    Path(f"{out_prefix}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print("\nfour-cell average (as in ACL Table 7)")
    for name in dict.fromkeys(r["condition"] for r in rows):
        cells = [r for r in rows if r["condition"] == name]
        bs_r = sum(r["BS-R"] for r in cells) / len(cells)
        bs_c = sum(r["BS-C"] for r in cells) / len(cells)
        print(f"{name:28} BS-R {bs_r:6.2f}  BS-C {bs_c:6.2f}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
