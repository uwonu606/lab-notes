import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

LAB = Path(__file__).parent
spec = spec_from_file_location("wiki_ab", LAB / "11_wiki_ab.py")
wiki_ab = module_from_spec(spec)
spec.loader.exec_module(wiki_ab)

MODEL = "llama3.1:8b"
ANCHOR_FLOOR = wiki_ab.ANCHOR_FLOOR
DROP = "버린다"
NEW_TYPE = "새 종류:"
DIRECT = "문장 직접:"
FILE_ANSWER = "wiki 에 넣는다"


@dataclass(frozen=True)
class ReviewItem:
    id: str
    kind: str
    title: str
    body: list
    options: list


def item_id(kind, subject):
    return f"{kind}-{hashlib.sha1(subject.encode()).hexdigest()[:6]}"


def load_state(wiki_dir):
    path = wiki_dir / "state.json"
    return json.loads(path.read_text()) if path.exists() else {"source": {}, "types": None, "answers": [], "decisions": {}}


def save_state(wiki_dir, state):
    (wiki_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))


def read_checked(review_path):
    if not review_path.exists():
        return {}
    checked, current = {}, None
    for line in review_path.read_text().splitlines():
        heading = re.match(r"## (\S+) ·", line)
        if heading:
            current = heading.group(1)
            continue
        option = re.match(r"- \[[xX]\] (.+)", line)
        if current and option:
            checked[current] = option.group(1).strip()
    return checked


def option_value(choice):
    if choice.startswith(DIRECT):
        number = re.search(r"\d+", choice[len(DIRECT):])
        return f"문장 {number.group(0)}" if number else None
    return choice.split(":", 1)[0].strip() if choice.startswith("문장 ") else choice


def anchor_items(events, sentences):
    items = []
    for event in events:
        scored = sorted(((SequenceMatcher(None, wiki_ab.squash(event), wiki_ab.squash(s)).ratio(), i) for i, s in enumerate(sentences, 1)), reverse=True)
        best_score, _ = scored[0]
        if best_score >= ANCHOR_FLOOR:
            continue
        options = [f"문장 {i}: {sentences[i - 1]}" for _, i in scored[:3]] + [f"{DIRECT} ", DROP]
        items.append(ReviewItem(item_id("anchor", event), "anchor", f"사건의 문장 번호 (가장 닮은 정도 {best_score:.2f})", [f"사건: {event}"], options))
    return items


def type_items(types, schema_types):
    return [
        ReviewItem(item_id("type", entity), "type", f"엔티티 종류 (LLM 답: {label})", [f"엔티티: {entity}"], schema_types + [f"{NEW_TYPE} ", f"추출 조각이라 {DROP}"])
        for entity, label in sorted(types.items()) if label not in schema_types
    ]


def answer_items(answers, sentences):
    items = []
    for answer in answers:
        cited = [f"[문장 {n}] {sentences[n - 1]}" for n in answer["cited"] if 1 <= n <= len(sentences)]
        body = [f"질문: {answer['q']}", f"답: {answer['reply']}", "근거 문장:"] + [f"  {c}" for c in cited or ["  (번호 없음)"]]
        items.append(ReviewItem(answer["id"], "answer", "답을 wiki 에 넣을까", body, [FILE_ANSWER, DROP]))
    return items


def resolve(state, graph, sentences, schema_types):
    events = sorted(n for n, k in graph.kind.items() if k == "event")
    entities = sorted(n for n, k in graph.kind.items() if k == "entity")
    items = anchor_items(events, sentences) + type_items(state["types"], schema_types) + answer_items(state["answers"], sentences)
    decided = state["decisions"]
    pending = [item for item in items if item.id not in decided]

    anchors, dropped = {}, set()
    for event in events:
        index, score = wiki_ab.anchor_of(event, sentences)
        decision = decided.get(item_id("anchor", event))
        if score >= ANCHOR_FLOOR:
            anchors[event] = (index, "코드")
        elif decision == DROP:
            dropped.add(event)
        elif decision:
            anchors[event] = (int(decision.split()[1]), "사람")

    types = {}
    for entity in entities:
        label = state["types"].get(entity, "?")
        decision = decided.get(item_id("type", entity))
        if label in schema_types:
            types[entity] = label
        elif decision and decision.endswith(DROP):
            dropped.add(entity)
        elif decision and decision.startswith(NEW_TYPE):
            types[entity] = decision[len(NEW_TYPE):].strip()
        elif decision:
            types[entity] = decision

    filed = [a for a in state["answers"] if decided.get(a["id"]) == FILE_ANSWER]
    return pending, anchors, types, dropped, filed


def event_text(event, anchors, sentences):
    index, by = anchors[event]
    return f"{event} [문장 {index}{' · 사람 확인' if by == '사람' else ''}]"


def render(graph, sentences, anchors, types, dropped, filed):
    pages = {}
    shown_events = {e for e in anchors if e not in dropped}
    for entity, label in sorted(types.items()):
        lines = [f"# {entity}", f"종류: {label}"]
        relations = [f"- {h} —{r}→ {t}" for h, r, t in graph.entity_edges if entity in (h, t) and not {h, t} & dropped]
        if relations:
            lines += ["## 관계"] + relations
        events = sorted(e for e, ps in graph.participation.items() if entity in ps and e in shown_events)
        if events:
            lines += ["## 사건"] + [f"- {event_text(e, anchors, sentences)}" for e in events]
        answers = [a for a in filed if entity in a["q"] or entity in a["reply"]]
        if answers:
            lines += ["## 답 기록"] + [f"- [{a['q']}](답/{a['id']}.md)" for a in answers]
        pages[entity] = "\n".join(lines)
    relation_lines = [f"- {event_text(h, anchors, sentences)} —{r}→ {event_text(t, anchors, sentences)}"
                      for h, r, t in graph.event_edges if h in shown_events and t in shown_events]
    if relation_lines:
        pages["_사건관계"] = "# 사건 사이 관계\n" + "\n".join(relation_lines)
    for answer in filed:
        cited = "\n".join(f"- [문장 {n}] {sentences[n - 1]}" for n in answer["cited"] if 1 <= n <= len(sentences))
        pages[f"답/{answer['id']}"] = f"# {answer['q']}\n\n{answer['reply']}\n\n## 근거 문장\n{cited or '- (번호 없음)'}"
    return pages


def render_review(pending):
    lines = ["# 검토 대기", "", "맞는 칸 하나의 `[ ]` 를 `[x]` 로 바꾸고 `build` 를 다시 돌린다. 새 종류와 문장 직접은 콜론 뒤에 이름이나 번호를 적는다.", ""]
    for item in pending:
        lines += [f"## {item.id} · {item.title}"] + item.body + [f"- [ ] {o}" for o in item.options] + [""]
    if not pending:
        lines.append("검토할 것이 없다.")
    return "\n".join(lines)


def render_index(types, pending, filed):
    by_type = {}
    for entity, label in types.items():
        by_type.setdefault(label, []).append(entity)
    lines = ["# 목차"]
    for label in sorted(by_type):
        lines += [f"## {label}"] + [f"- [{e}]({e}.md)" for e in sorted(by_type[label])]
    if filed:
        lines += ["## 답 기록"] + [f"- [{a['q']}](답/{a['id']}.md)" for a in filed]
    lines += ["", f"검토 대기 {len(pending)}건 → [REVIEW.md](REVIEW.md)"]
    return "\n".join(lines)


def write_wiki(wiki_dir, pages, review, index):
    for old in wiki_dir.rglob("*.md"):
        if old.name not in {"검토기록.md"}:
            old.unlink()
    for title, text in pages.items():
        path = wiki_dir / f"{title}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
    (wiki_dir / "REVIEW.md").write_text(review + "\n")
    (wiki_dir / "index.md").write_text(index + "\n")


def log_decisions(wiki_dir, newly):
    if not newly:
        return
    with (wiki_dir / "검토기록.md").open("a") as log:
        for item_key, choice in newly.items():
            log.write(f"- {date.today()} {item_key} → {choice}\n")


def build(wiki_dir, run_path=None, passage_path=None):
    wiki_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(wiki_dir)
    if run_path:
        state["source"] = {"run": run_path, "passage": passage_path}
    graph = wiki_ab.load_graph(state["source"]["run"])
    sentences = wiki_ab.split_sentences(Path(state["source"]["passage"]).read_text())
    schema_types = [l[2:].strip() for l in (LAB / "inputs/SCHEMA.md").read_text().splitlines() if l.startswith("- ")]
    if state["types"] is None:
        state["types"] = {e: labels[0] for e, labels in wiki_ab.type_labels(graph, MODEL, schema_types).items()}

    checked = {key: option_value(choice) for key, choice in read_checked(wiki_dir / "REVIEW.md").items()
               if key not in state["decisions"] and not choice.rstrip().endswith(NEW_TYPE)}
    newly = {key: value for key, value in checked.items() if value}
    state["decisions"].update(newly)
    log_decisions(wiki_dir, newly)

    pending, anchors, types, dropped, filed = resolve(state, graph, sentences, schema_types)
    pages = render(graph, sentences, anchors, types, dropped, filed)
    write_wiki(wiki_dir, pages, render_review(pending), render_index(types, pending, filed))
    save_state(wiki_dir, state)
    print(f"{wiki_dir}: 페이지 {len(pages)} · 검토 대기 {len(pending)} · 이번에 반영한 결정 {len(newly)} · 넣은 답 {len(filed)}")
    for kind in ("anchor", "type", "answer"):
        print(f"  대기 {kind:6} {sum(i.kind == kind for i in pending)}")


def ask(wiki_dir, question):
    pages = sorted(p for p in wiki_dir.rglob("*.md") if p.name not in {"REVIEW.md", "검토기록.md"})
    wiki_text = "\n\n".join(p.read_text() for p in pages)
    prompt = (
        "아래는 어떤 문서로 만든 wiki 페이지들이다. 이 페이지만 보고 질문에 한국어로 짧게 답하라. "
        "답의 근거가 된 줄에 붙은 [문장 N] 번호를 답 끝에 그대로 적어라. 페이지에 없으면 '모른다'고 답하라.\n\n"
        f"{wiki_text}\n\n질문: {question}"
    )
    reply = wiki_ab.ask_counted("answer", MODEL, prompt, temperature=0.0).strip()
    cited = sorted({int(n) for n in re.findall(r"문장\s*(\d+)", reply)})
    state = load_state(wiki_dir)
    answer_key = item_id("answer", question + reply)
    if all(a["id"] != answer_key for a in state["answers"]):
        state["answers"].append({"id": answer_key, "q": question, "reply": reply, "cited": cited})
    save_state(wiki_dir, state)
    print(f"질문: {question}\n답: {reply}\n근거 번호: {cited}")
    build(wiki_dir)


if __name__ == "__main__":
    command, wiki_dir = sys.argv[1], Path(sys.argv[2])
    if command == "build":
        build(wiki_dir, *sys.argv[3:5])
    elif command == "ask":
        ask(wiki_dir, sys.argv[3])
