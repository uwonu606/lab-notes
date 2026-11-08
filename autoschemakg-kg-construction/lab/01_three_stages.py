import ast
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PROMPT_FILE = Path(__file__).parent / "repos/AutoSchemaKG/atlas_rag/llm_generator/prompt/triple_extraction_prompt.py"


def load_literal(name):
    module = ast.parse(PROMPT_FILE.read_text())
    for node in module.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == name:
            return ast.literal_eval(node.value)
    raise KeyError(name)


TRIPLE_INSTRUCTIONS = load_literal("TRIPLE_INSTRUCTIONS")

STAGES = ["entity_relation", "event_entity", "event_relation"]
SEED = int(os.environ.get("SEED", "0"))
OLLAMA_CHAT = "http://localhost:11434/api/chat"


def clean_text(text):
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ").replace(";", ",")
    return re.sub(r"\s+", " ", text.replace("\x00", "")).strip()


def ask(model, stage, passage):
    instructions = TRIPLE_INSTRUCTIONS["en"]
    body = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.7, "seed": SEED},
        "messages": [
            {"role": "system", "content": instructions["system"]},
            {"role": "user", "content": instructions[stage] + "\n" + passage},
        ],
    }
    request = urllib.request.Request(OLLAMA_CHAT, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read())["message"]["content"]


def parse_or_empty(raw):
    start, end = raw.find("["), raw.rfind("]")
    try:
        return json.loads(raw[start : end + 1]), "ok"
    except ValueError:
        return [], "parse failed -> empty list"


def triples_of(stage, items):
    for item in items:
        if not isinstance(item, dict):
            continue
        if stage == "event_entity":
            event = clean_text(str(item.get("Event", "")))
            for entity in item.get("Entity", []) or []:
                yield ("event", event, "is participated by", "entity", clean_text(str(entity)))
        else:
            kind = "entity" if stage == "entity_relation" else "event"
            yield (kind, clean_text(str(item.get("Head", ""))), clean_text(str(item.get("Relation", ""))),
                   kind, clean_text(str(item.get("Tail", ""))))


def main(passage_path, model, out_path):
    passage = Path(passage_path).read_text()
    record = {"model": model, "passage": passage, "stages": {}}
    node_kind, node_stages = {}, {}
    for number, stage in enumerate(STAGES, 1):
        raw = ask(model, stage, passage)
        items, status = parse_or_empty(raw)
        triples = [t for t in triples_of(stage, items) if t[1] and t[4]]
        record["stages"][stage] = {"raw": raw, "status": status, "triples": triples}
        print(f"\n=== stage {number}: {stage} ({status}, {len(triples)} triples)")
        for head_kind, head, relation, tail_kind, tail in triples:
            print(f"  [{head_kind}] {head}  --{relation}-->  [{tail_kind}] {tail}")
            for kind, node in ((head_kind, head), (tail_kind, tail)):
                node_kind.setdefault(node, kind)
                node_stages.setdefault(node, set()).add(number)

    print("\n=== visited_nodes: 노드 = 문자열 그대로. 오른쪽은 그 문자열을 낸 단계")
    for node in sorted(node_kind, key=lambda n: (node_kind[n], n)):
        print(f"  {node_kind[node]:6} {sorted(node_stages[node])}  {node}")

    events_2 = {n for n, s in node_stages.items() if node_kind[n] == "event" and 2 in s}
    events_3 = {n for n, s in node_stages.items() if node_kind[n] == "event" and 3 in s}
    entities_1 = {n for n, s in node_stages.items() if node_kind[n] == "entity" and 1 in s}
    entities_2 = {n for n, s in node_stages.items() if node_kind[n] == "entity" and 2 in s}
    print("\n=== 단계 사이에서 같은 노드로 합쳐진 수")
    print(f"  이벤트: 단계2 {len(events_2)}개, 단계3 {len(events_3)}개, 둘 다 {len(events_2 & events_3)}개")
    print(f"  엔티티: 단계1 {len(entities_1)}개, 단계2 {len(entities_2)}개, 둘 다 {len(entities_1 & entities_2)}개")
    print(f"  전체 노드 {len(node_kind)}개")
    record["nodes"] = {n: {"kind": node_kind[n], "stages": sorted(node_stages[n])} for n in node_kind}
    Path(out_path).write_text(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
