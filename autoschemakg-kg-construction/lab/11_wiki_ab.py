import json
import random
import time
import urllib.error
import re
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(__file__).parent
spec = spec_from_file_location("concepts", LAB / "03_concepts.py")
concepts = module_from_spec(spec)
spec.loader.exec_module(concepts)

OLLAMA_CHAT = concepts.OLLAMA_CHAT
ANCHOR_FLOOR = 0.5


@dataclass
class Ledger:
    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0


LEDGERS = defaultdict(Ledger)


def post_with_retry(body, attempts=3):
    for attempt in range(attempts):
        request = urllib.request.Request(OLLAMA_CHAT, json.dumps(body).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if attempt == attempts - 1:
                raise
            print(f"  (Ollama {error.code}, {attempt + 1}번째 재시도)", file=sys.stderr)
            time.sleep(10)


def ask_counted(stage, model, prompt, temperature=0.7):
    body = {
        "model": model, "stream": False, "options": {"temperature": temperature, "seed": concepts.SEED},
        "messages": [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": prompt}],
    }
    reply = post_with_retry(body)
    ledger = LEDGERS[stage]
    ledger.calls += 1
    ledger.prompt_tokens += reply.get("prompt_eval_count", 0)
    ledger.output_tokens += reply.get("eval_count", 0)
    return reply["message"]["content"]


@dataclass(frozen=True)
class Variant:
    labels: str
    anchor: str
    blurb: str


VARIANTS = {
    "A": Variant("concepts", "none", "공식: 개념 이름표"),
    "A0": Variant("none", "none", "이름표 없음"),
    "B": Variant("types", "number", "종류 목록 + 문장 번호"),
    "Bq": Variant("types", "quote", "종류 목록 + 문장 번호 + 원문 인용"),
}


@dataclass
class Graph:
    kind: dict
    edges: list
    entity_edges: list
    participation: dict
    event_edges: list


def load_graph(run_path):
    kind, edges = concepts.load_graph(run_path)
    entity_edges, event_edges = [], []
    participation = defaultdict(set)
    for head, relation, tail in edges:
        if kind[head] == "entity" and kind[tail] == "entity":
            entity_edges.append((head, relation, tail))
        elif kind[head] == "event" and kind[tail] == "entity":
            participation[head].add(tail)
        elif kind[head] == "event" and kind[tail] == "event":
            event_edges.append((head, relation, tail))
    return Graph(kind, edges, entity_edges, participation, event_edges)


def split_sentences(passage):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", passage) if s.strip()]


def squash(text):
    return re.sub(r"[\s.,!?`'\"()]", "", text)


def anchor_of(event, sentences):
    scored = [(SequenceMatcher(None, squash(event), squash(s)).ratio(), i) for i, s in enumerate(sentences, 1)]
    score, index = max(scored)
    return index, score


def concept_labels(graph, model):
    concepts.ask = lambda m, prompt: ask_counted("labels:concepts", m, prompt)
    rng = random.Random(concepts.SEED)
    return {node: concepts.concepts_of(model, node, graph.kind[node], graph.edges, rng)[2] for node in sorted(graph.kind)}


def type_labels(graph, model, schema_types):
    entities = sorted(n for n, k in graph.kind.items() if k == "entity")
    context = {e: [f"{h} {r} {t}" for h, r, t in graph.entity_edges if e in (h, t)][:2] for e in entities}
    listing = "\n".join(f"- {e}: {'; '.join(context[e]) or '(no relation)'}" for e in entities)
    prompt = (
        "Assign each entity exactly one type from this list: " + ", ".join(schema_types) + ".\n"
        "If none fits, write \"?\". Reply with only a JSON object mapping entity to type.\n\n" + listing
    )
    raw = ask_counted("labels:types", model, prompt, temperature=0.0)
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        chosen = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        chosen = {}
    return {e: [chosen.get(e, "?") if chosen.get(e) in schema_types else f"?({chosen.get(e)})"] for e in entities}


def labels_for(variant, graph, model, schema_types, cache):
    if variant.labels == "none":
        return {}
    if variant.labels not in cache:
        cache[variant.labels] = concept_labels(graph, model) if variant.labels == "concepts" else type_labels(graph, model, schema_types)
    return cache[variant.labels]


def event_line(event, variant, sentences):
    if variant.anchor == "none":
        return event
    index, score = anchor_of(event, sentences)
    warning = "" if score >= ANCHOR_FLOOR else f" ⚠ 원문과 거리 {score:.2f}"
    if variant.anchor == "number":
        return f"{event} [문장 {index}]{warning}"
    return f"{event} [문장 {index}: \"{sentences[index - 1]}\"]{warning}"


def render_wiki(variant, graph, labels, sentences):
    pages = {}
    for entity in sorted(n for n, k in graph.kind.items() if k == "entity"):
        lines = [f"# {entity}"]
        if entity in labels:
            lines.append(("종류: " if variant.labels == "types" else "개념: ") + ", ".join(labels[entity]))
        relations = [f"- {h} —{r}→ {t}" for h, r, t in graph.entity_edges if entity in (h, t)]
        if relations:
            lines += ["## 관계"] + relations
        events = sorted(e for e, ps in graph.participation.items() if entity in ps)
        if events:
            lines.append("## 사건")
            for event in events:
                lines.append(f"- {event_line(event, variant, sentences)}")
                if event in labels and variant.labels == "concepts":
                    lines.append(f"  - 개념: {', '.join(labels[event])}")
        pages[entity] = "\n".join(lines)
    if graph.event_edges:
        lines = ["# 사건 사이 관계"]
        for h, r, t in graph.event_edges:
            lines.append(f"- {event_line(h, variant, sentences)} —{r}→ {event_line(t, variant, sentences)}")
        pages["_사건관계"] = "\n".join(lines)
    if variant.labels == "concepts":
        members = defaultdict(list)
        for node, node_labels in labels.items():
            for label in node_labels:
                members[label].append(node)
        shared = {c: m for c, m in members.items() if len(m) > 1}
        pages["_개념"] = "# 개념 (둘 이상이 나눈 것)\n" + "\n".join(f"- {c}: {' / '.join(m)}" for c, m in sorted(shared.items()))
    return pages


def answer(variant_name, wiki_text, question, model):
    prompt = (
        "아래는 어떤 문서로 만든 wiki 페이지들이다. 이 페이지만 보고 질문에 한국어로 짧게 답하라. "
        "근거가 된 줄을 그대로 옮겨 붙여라. 페이지에 없으면 '모른다'고 답하라.\n\n"
        f"{wiki_text}\n\n질문: {question}"
    )
    return ask_counted(f"answer:{variant_name}", model, prompt, temperature=0.0)


def key_hits(reply, key_groups):
    return sum(any(k in reply for k in group) for group in key_groups), len(key_groups)


def main(run_path, passage_path, model, out_dir):
    out_dir = Path(out_dir)
    graph = load_graph(run_path)
    sentences = split_sentences(Path(passage_path).read_text())
    schema_types = [l[2:].strip() for l in (LAB / "inputs/SCHEMA.md").read_text().splitlines() if l.startswith("- ")]
    questions = json.loads((LAB / "inputs/11-questions.json").read_text())[passage_path]
    cache, report = {}, {"run": run_path, "passage": passage_path, "sentences": sentences, "variants": {}}

    for name, variant in VARIANTS.items():
        labels = labels_for(variant, graph, model, schema_types, cache)
        pages = render_wiki(variant, graph, labels, sentences)
        wiki_dir = out_dir / f"wiki-{name}"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        for title, text in pages.items():
            (wiki_dir / f"{title}.md").write_text(text + "\n")
        wiki_text = "\n\n".join(pages.values())
        answers = []
        for item in questions:
            reply = answer(name, wiki_text, item["q"], model)
            hit, total = key_hits(reply, item["keys"])
            answers.append({"q": item["q"], "reply": reply, "hit": hit, "total": total})
        anchors = [anchor_of(e, sentences) for e, k in graph.kind.items() if k == "event"] if variant.anchor != "none" else []
        report["variants"][name] = {"blurb": variant.blurb, "pages": len(pages), "wiki_chars": len(wiki_text), "answers": answers,
                                    "weak_anchors": sum(s < ANCHOR_FLOOR for _, s in anchors), "anchored_events": len(anchors)}

    report["ledgers"] = {stage: vars(ledger) for stage, ledger in LEDGERS.items()}
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"== {passage_path}  (추출: {run_path}, 원문 문장 {len(sentences)}개, 사건 점 {sum(k == 'event' for k in graph.kind.values())}개)")
    print("\n-- 비용 (추출 뒤 단계, Ollama 토큰)")
    for stage, ledger in LEDGERS.items():
        print(f"  {stage:18} 호출 {ledger.calls:3}  입력 {ledger.prompt_tokens:6}  출력 {ledger.output_tokens:6}")
    print("\n-- 판마다")
    for name, v in report["variants"].items():
        score = sum(a["hit"] for a in v["answers"]), sum(a["total"] for a in v["answers"])
        anchor_note = f"  원문과 먼 사건 {v['weak_anchors']}/{v['anchored_events']}" if v["anchored_events"] else ""
        print(f"  {name:3} {v['blurb']:22} 페이지 {v['pages']:2}  글자 {v['wiki_chars']:5}  핵심어 {score[0]}/{score[1]}{anchor_note}")
    print("\n-- 답")
    for index, item in enumerate(questions):
        print(f"\n  Q{index + 1}. {item['q']}")
        for name, v in report["variants"].items():
            a = v["answers"][index]
            print(f"    {name:3} [{a['hit']}/{a['total']}] {' '.join(a['reply'].split())[:220]}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
