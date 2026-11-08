import json
import math
import random
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB = Path(__file__).parent
SEED = 0
WORKERS = 8
SYSTEM_PROMPT = "You are a helpful AI assistant."

ABSPYRAMID_PROMPTS = {
    "noun": 'Identify the hypernym of a specific noun and provide a "Yes" or "No" response. Hypernyms are words with a broad meaning, which more specific words fall under. In the sentence [HEAD], does the meaning of [CONCEPT] encompass [INSTANCE]?',
    "verb": 'Identify the hypernym of a specific verb and provide a "Yes" or "No" response. Hypernyms are words with a broad meaning, which more specific words fall under. In the sentence [HEAD], does the meaning of [CONCEPT] encompass [INSTANCE]?',
    "event": 'Identify abstract descriptions of specific sentences, and provide a "Yes" or "No" response. Can we consider [CONCEPT] as an abstract description of the sentence [HEAD]?',
}
STRICT_RULE = " Answer No if the concept is only a paraphrase of the sentence, or too general to tell it apart (e.g., 'event', 'behavior', 'go')."
ABSTRACTATOMIC_PROMPT = 'Given the event "[HEAD]," can "[INSTANCE]" be conceptualized as "[CONCEPT]"?Here, conceptualized means represented by a general concept. Answer \'Yes\' or \'No\' only without any other word.'


def split_marked(text, opening, closing):
    instance = re.search(re.escape(opening) + r"(.*?)" + re.escape(closing), text).group(1)
    head = text.replace(opening, "").replace(closing, "")
    return head, instance


def abspyramid_items(relation, rule=""):
    path = LAB / "inputs/abspyramid" / f"{relation}_dataset/test.json"
    for line in path.read_text().splitlines():
        row = json.loads(line)
        head, instance = split_marked(row["event"], "<", ">")
        prompt = (ABSPYRAMID_PROMPTS[relation] + rule).replace("[HEAD]", head).replace("[INSTANCE]", instance).replace("[CONCEPT]", row["concept"])
        yield {"id": row["id"], "head": head, "instance": instance, "concept": row["concept"], "gold": row["label"] == 1, "prompt": prompt}


def abstractatomic_items(rule=""):
    path = LAB / "inputs/abstractatomic/repo_stage2/stage2_combined.tst.jsonl"
    for number, line in enumerate(path.read_text().splitlines()):
        row = json.loads(line)
        head, instance = split_marked(row["head"], "[", "]")
        prompt = (ABSTRACTATOMIC_PROMPT + rule).replace("[HEAD]", head).replace("[INSTANCE]", instance).replace("[CONCEPT]", row["concept_text"])
        yield {"id": f"tst_{number}", "head": head, "instance": instance, "concept": row["concept_text"], "score": row["score"], "gold": row["score"] >= 3, "prompt": prompt}


def ask_haiku(prompt):
    completed = subprocess.run(
        ["claude", "-p", "--model", "haiku", "--tools", "", "--no-session-persistence",
         "--setting-sources", "", "--system-prompt", SYSTEM_PROMPT, "--output-format", "json"],
        input=prompt, capture_output=True, text=True, timeout=300,
    )
    reply = json.loads(completed.stdout)
    return reply["result"], reply.get("total_cost_usd", 0.0)


def read_yes_no(answer):
    words = re.findall(r"\b(yes|no)\b", answer.lower())
    return {"yes": True, "no": False}.get(words[0]) if words else None


def judge(item):
    answer, cost = ask_haiku(item["prompt"])
    return {**item, "answer": answer, "said_yes": read_yes_no(answer), "cost_usd": cost}


def wilson_interval(correct, total, z=1.96):
    p = correct / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return centre - half, centre + half


def summarize(name, judged):
    answered = [r for r in judged if r["said_yes"] is not None]
    correct = sum(r["said_yes"] == r["gold"] for r in answered)
    gold_yes = sum(r["gold"] for r in judged) / len(judged)
    low, high = wilson_interval(correct, len(judged))
    confusion = Counter((r["gold"], r["said_yes"]) for r in judged)
    print(f"\n== {name}: n={len(judged)}  unparsed={len(judged) - len(answered)}")
    print(f"accuracy        {100 * correct / len(judged):.2f}  (95% CI {100 * low:.1f}–{100 * high:.1f})")
    print(f"said Yes        {100 * sum(r['said_yes'] is True for r in judged) / len(judged):.2f}%")
    print(f"always-Yes acc  {100 * gold_yes:.2f}   always-No acc {100 * (1 - gold_yes):.2f}")
    print(f"gold Yes→said Yes {confusion[(True, True)]}  gold Yes→said No {confusion[(True, False)]}")
    print(f"gold No →said Yes {confusion[(False, True)]}  gold No →said No {confusion[(False, False)]}")
    wrong = [r for r in judged if r["said_yes"] != r["gold"]][:6]
    for r in wrong:
        print(f"  ✗ gold={'Yes' if r['gold'] else 'No '} said={r['answer'][:12]!r:14} [{r['instance']}] → {r['concept']!r} | {r['head'][:70]}")


def sample(items, size):
    pool = list(items)
    return random.Random(SEED).sample(pool, size)


def main():
    noun_n, verb_n, event_n, atomic_n = (int(x) for x in sys.argv[1:5])
    strict = sys.argv[5:] == ["strict"]
    event_rule = STRICT_RULE if strict else ""
    variant = "-strict" if strict else ""
    out_dir = LAB / "runs"
    tasks = {
        "abspyramid-noun": sample(abspyramid_items("noun"), noun_n),
        "abspyramid-verb": sample(abspyramid_items("verb"), verb_n),
        "abspyramid-event": sample(abspyramid_items("event", event_rule), event_n),
        "abstractatomic-event": sample(abstractatomic_items(event_rule), atomic_n),
    }
    total_cost = 0.0
    for name, items in tasks.items():
        if not items:
            continue
        with ThreadPoolExecutor(WORKERS) as pool:
            judged = list(pool.map(judge, items))
        out_path = out_dir / f"10-{name}{variant}.jsonl"
        out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in judged))
        total_cost += sum(r["cost_usd"] for r in judged)
        summarize(name, judged)
    print(f"\ntotal list-price cost ${total_cost:.4f}")


if __name__ == "__main__":
    main()
