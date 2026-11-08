import ast
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB = Path(__file__).parent
OFFICIAL = LAB / "repos/AutoSchemaKG/EvaluateKGC/TripleAccuracy/triple_acc.py"
OFFICIAL_FUNCTIONS = ["count_origin", "get_more", "count_more", "get_incorrect", "count_incorrect", "calculate"]
SYSTEM_PROMPT = "You are a helpful assistant."
STAGES = ["entity_relation", "event_entity", "event_relation"]
TRIPLE_TYPES = ["Entity-Entity", "Event-Entity", "Event-Event"]

LENIENT_SENTENCES = [
    "with an emphasis on general interpretations and broader meanings rather than strict details",
    "Accept general phrases, reasonable expressions, and contextual representations as correct, even if they are not strictly word-for-word accurate.",
    "Focus on capturing the essence of the relationships instead of precise details.",
    "If any relationships can be reasonably interpreted as correct, consider them so.",
    "All relationships should be accepted as correct unless they are explicitly unsupported by the text.",
    "Assume that every entity mentioned has a significant relevance to the events, either directly or indirectly.",
    "Recognize that general involvement, titles, and roles are valid entities, even if they appear redundant or lack explicit support.",
    "Approach the evaluation with a broad interpretation of connections and consider that all entities are relevant to the historical context.",
    "General or repeated entities should be considered correct.",
    "Similar or reasonable entities should be considered correct.",
    "Entities not central to specific events should be considered correct.",
    "Entities lack of explicit support or direct support should be considered correct.",
    "Titles and roles should be considered as correct entities, even with name redundancy.",
    "All entities should be accepted as correct unless they are explicitly unsupported by the event.",
    "Consider them all correct if they logically align with the information provided, even if they are not exact.",
    "If any relationships can be reasonably interpreted or inferred as correct, consider them so.",
    "Similar or reasonable expression should be considered correct.",
]
STRICT_RULE = "Mark an item incorrect if the text does not support it, including a reversed direction or a wrong relation type. "


def flexible_pattern(sentence):
    return r"\s*" + r"\s*".join(re.escape(word) for word in sentence.split())


def make_strict(content):
    for sentence in LENIENT_SENTENCES:
        content = re.sub(flexible_pattern(sentence), "", content)
    return re.sub(r"If (it )?is all correct", lambda m: STRICT_RULE + m.group(0), content, count=1)


def ask_judge(content, model):
    completed = subprocess.run(
        ["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence",
         "--setting-sources", "", "--system-prompt", SYSTEM_PROMPT, "--output-format", "json"],
        input=content, capture_output=True, text=True, timeout=600,
    )
    reply = json.loads(completed.stdout)
    return reply["result"], reply.get("total_cost_usd", 0.0)


def load_official(judge_log, model, strict):
    tree = ast.parse(OFFICIAL.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in OFFICIAL_FUNCTIONS]
    assert len(functions) == len(OFFICIAL_FUNCTIONS)

    def response(content):
        is_incorrect_call = content.startswith("I need you to help me evaluate")
        sent = make_strict(content) if strict and is_incorrect_call else content
        answer, cost = ask_judge(sent, model)
        judge_log.append({"prompt": sent, "answer": answer, "cost": cost})
        return answer

    namespace = {"re": re, "response": response}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(OFFICIAL), "exec"), namespace)
    return namespace


def extraction_dicts(run_path):
    run = json.loads(run_path.read_text())
    return run["passage"].strip(), [json.loads(run["stages"][stage]["raw"]) for stage in STAGES]


def judge_run(run_path, model, strict):
    judge_log = []
    official = load_official(judge_log, model, strict)
    text, (entity_relation, event_entity, event_relation) = extraction_dicts(run_path)
    lengths = official["count_origin"](entity_relation, event_entity, event_relation)
    more = official["count_more"](*official["get_more"](text, entity_relation, event_entity, event_relation))
    incorrect = official["count_incorrect"](*official["get_incorrect"](text, entity_relation, event_entity, event_relation))
    scores = [official["calculate"](n, wrong, missing) for n, wrong, missing in zip(lengths, incorrect, more)]
    return {"run": run_path.stem, "strict": strict, "lengths": lengths, "incorrect": incorrect, "more": more,
            "scores": scores, "judge_log": judge_log}


def mean_without_none(values):
    kept = [value for value in values if value is not None]
    return (sum(kept) / len(kept), len(kept)) if kept else (None, 0)


def summarize(results):
    lines = []
    for strict in (False, True):
        rows = [row for row in results if row["strict"] == strict]
        lines.append(f"== 채점 프롬프트: {'관대한 문장을 뺀 판' if strict else '공식 그대로'} ==")
        for row in rows:
            cells = []
            for kind, n, wrong, missing, (precision, recall, _) in zip(TRIPLE_TYPES, row["lengths"], row["incorrect"], row["more"], row["scores"]):
                shown = "None" if precision is None else f"{precision:.2f}"
                cells.append(f"{kind} {n}개 중 틀림 {wrong} 빠짐 {missing} P={shown}")
            lines.append(f"{row['run']:10s} " + " | ".join(cells))
        for index, kind in enumerate(TRIPLE_TYPES):
            precision, kept = mean_without_none([row["scores"][index][0] for row in rows])
            recall, _ = mean_without_none([row["scores"][index][1] for row in rows])
            total = sum(row["lengths"][index] for row in rows)
            wrong = sum(min(row["incorrect"][index], row["lengths"][index]) for row in rows)
            pooled = (total - wrong) / total if total else None
            shown_precision = "None" if precision is None else f"{precision * 100:.2f}"
            shown_recall = "None" if recall is None else f"{recall * 100:.2f}"
            lines.append(f"  {kind}: 공식 평균 P {shown_precision} (None 빼고 {kept}/{len(rows)}개 평균), R {shown_recall} / 모아 센 P {pooled * 100:.2f} ({total - wrong}/{total})")
        cost = sum(call["cost"] for row in rows for call in row["judge_log"])
        lines.append(f"  채점 비용 ${cost:.2f}")
    return "\n".join(lines)


def main():
    model, out_prefix, *run_names = sys.argv[1:]
    jobs = [(LAB / "runs" / f"{name}.json", strict) for name in run_names for strict in (False, True)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda job: judge_run(job[0], model, job[1]), jobs))
    Path(f"{out_prefix}.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in results) + "\n")
    summary = summarize(results)
    Path(f"{out_prefix}.txt").write_text(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main()
