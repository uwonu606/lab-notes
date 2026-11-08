import ast
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB = Path(__file__).parent
OFFICIAL_DIR = LAB / "repos/AutoSchemaKG/EvaluateKGC/InfoPreservation"
CONTEXT_TYPES = ["empty", "passage", "entity", "event_only", "event"]
WORKERS = 12


def official_constant(file_name, constant_name):
    tree = ast.parse((OFFICIAL_DIR / file_name).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == constant_name:
            return node.value.value
    raise KeyError(constant_name)


MCQ_PROMPT = official_constant("question_generation.py", "MCQ_PROMPT")
MCQ_ANSWER_PROMPT = official_constant("answer_generation.py", "MCQ_ANSWER_PROMPT")


def ask_claude(prompt, model):
    completed = subprocess.run(
        ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
         "--setting-sources", "", "--output-format", "json"],
        input=prompt, capture_output=True, text=True, timeout=600,
    )
    reply = json.loads(completed.stdout)
    return reply["result"], reply.get("total_cost_usd", 0.0)


def kg_data_of(chunk):
    entity_relation = [x for x in chunk["entity_relation_dict"] if isinstance(x, dict) and {"Head", "Relation", "Tail"} <= x.keys()]
    event_entity = [x for x in chunk["event_entity_dict"] if isinstance(x, dict) and "Event" in x]
    event_relation = [x for x in chunk["event_relation_dict"] if isinstance(x, dict) and {"Head", "Relation", "Tail"} <= x.keys()]
    return {
        "id": chunk["id"],
        "passage": chunk["original_text"],
        "entity_relation_list": [f"{t['Head']}, {t['Relation']}, {t['Tail']}" for t in entity_relation],
        "event_entity_list": [f"{e['Event']}" for e in event_entity],
        "event_relation_list": [f"{t['Head']}, {t['Relation']}, {t['Tail']}" for t in event_relation],
    }


def contexts_of(kg_data, context_type):
    events = kg_data["event_entity_list"] + kg_data["event_relation_list"]
    return {
        "empty": "None",
        "passage": kg_data["passage"],
        "entity": "; ".join(kg_data["entity_relation_list"]),
        "event_only": "; ".join(events),
        "event": "; ".join(events + kg_data["entity_relation_list"]),
    }[context_type]


def decode_mcqs(response):
    fenced = response.split("```")[1] if "```" in response else response
    return json.loads(re.sub(r"^\s*json", "", fenced))


def official_letter(text):
    match = re.search(r"[A-D]", text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def passage_words_covered(passage, context):
    words = set(re.findall(r"\w+", passage))
    return len(words & set(re.findall(r"\w+", context))) / len(words) if words else 0.0


def generate(chunk_paths, generator, out_path):
    kg_data_list = [kg_data_of(json.loads(path.read_text())) for path in chunk_paths]
    kg_data_list = [d for d in kg_data_list if d["entity_relation_list"] or d["event_entity_list"]]

    def one(kg_data):
        answer, cost = ask_claude(MCQ_PROMPT.replace("{passage}", kg_data["passage"]), generator)
        try:
            return {**kg_data, "mcq_list": decode_mcqs(answer), "cost": cost}
        except (json.JSONDecodeError, IndexError):
            return {**kg_data, "mcq_list": None, "raw": answer, "cost": cost}

    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(one, kg_data_list))
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


def evaluate(mcq_path, answerer, out_prefix):
    rows = [json.loads(line) for line in mcq_path.read_text().splitlines()]
    rows = [r for r in rows if r["mcq_list"]]
    jobs = []
    for row in rows:
        for number, mcq in enumerate(row["mcq_list"]):
            if len(mcq.get("options", [])) != 4:
                continue
            for context_type in CONTEXT_TYPES:
                prompt = MCQ_ANSWER_PROMPT.format(
                    contexts=contexts_of(row, context_type), question=mcq["question"],
                    options_0=mcq["options"][0], options_1=mcq["options"][1],
                    options_2=mcq["options"][2], options_3=mcq["options"][3])
                jobs.append({"id": row["id"], "mcq": number, "context_type": context_type,
                             "gold": official_letter(mcq["answer"]), "prompt": prompt})

    def one(job):
        answer, cost = ask_claude(job["prompt"], answerer)
        return {**{k: v for k, v in job.items() if k != "prompt"}, "answer": answer, "cost": cost}

    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(one, jobs))
    Path(f"{out_prefix}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n")

    lines = [f"원문 {len(rows)}개, 문항 {len(results) // len(CONTEXT_TYPES)}개, 답한 모델 {answerer}"]
    for context_type in CONTEXT_TYPES:
        picked = [r for r in results if r["context_type"] == context_type]
        official = sum(official_letter(r["answer"]) == r["gold"] for r in picked)
        clean = sum(r["answer"].strip().upper()[:1] == r["gold"] for r in picked)
        lines.append(f"{context_type:10s} 정확도 {official / len(picked) * 100:.2f} ({official}/{len(picked)}), 답 첫 글자만 읽으면 {clean / len(picked) * 100:.2f}")
    for context_type in ["entity", "event_only", "event"]:
        coverage = [passage_words_covered(r["passage"], contexts_of(r, context_type)) for r in rows]
        length = [len(contexts_of(r, context_type)) / len(r["passage"]) for r in rows]
        lines.append(f"{context_type:10s} 원문 낱말 중 맥락에 있는 비율 평균 {sum(coverage) / len(coverage) * 100:.1f}%, 맥락 길이 / 원문 길이 평균 {sum(length) / len(length):.2f}")
    generation_cost = sum(r.get("cost", 0.0) for r in rows)
    answer_cost = sum(r["cost"] for r in results)
    lines.append(f"비용: 문항 만들기 ${generation_cost:.2f}, 답하기 ${answer_cost:.2f}")
    summary = "\n".join(lines)
    Path(f"{out_prefix}.txt").write_text(summary + "\n")
    print(summary)


def main():
    command, *args = sys.argv[1:]
    if command == "generate":
        cache_dir, generator, out_path = args
        generate(sorted(Path(cache_dir).glob("*_[0-9][0-9].json")), generator, Path(out_path))
    elif command == "evaluate":
        mcq_path, answerer, out_prefix = args
        evaluate(Path(mcq_path), answerer, out_prefix)


if __name__ == "__main__":
    main()
