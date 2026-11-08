"""9단계 공유 질문 연결: 질문 → 구심점 카드. 글자 매칭 + bge-m3 카드 후보 20개 → 작은 모델(qwen3:8b)이 고른다.

    import importlib
    link = importlib.import_module("23_cf_link")
    linker = link.Linker(link.read_cards())               # inputs/net-corpus/relglossary/hubs.json
    links = linker.link_many([("S01-sg01", "질문 글"), ...])  # [Link]: text_hubs(글자 매칭만), hubs(작은 모델 선택), candidates·candidate_scores
    text_only = link.text_match("질문 글", linker.cards)       # 작은 모델 없이 글자 매칭만 (카드 id 목록)
    prompt_part = link.render_cards(linker.cards_of(links[0].hubs))  # "[G1] 이름 (별칭…; 종류…)\n- 박아 둔 사실" 꼴

    .venv-hr2/bin/python 23_cf_link.py inputs/net-corpus-cf/gold/questions-alias.jsonl    # runs/23-cf-link/questions-alias.jsonl
    .venv-hr2/bin/python 23_cf_link.py <질문 jsonl> --scope inputs/net-corpus-cf/gold/scope.txt   # 범위 문항만
    .venv-hr2/bin/python 23_cf_link.py <질문 jsonl> --score                                # gold_hubs 로 정밀도·재현율

연결은 질문 글만 본다. gold_hubs 는 score_links 만 읽는다.
"""
import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

import embed_client
from llm_cache import LLMCallFailed
from ollama_cache import OllamaClient

LAB = Path(__file__).parent
HUBS = LAB / "inputs/net-corpus/relglossary/hubs.json"
PROMPT = LAB / "prompts/cf-link.txt"
OUT_DIR = LAB / "runs/23-cf-link"
CANDIDATES = 20
ASCII_WORD_EDGE = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"
SHORT_ACRONYM = 5


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    aliases: tuple
    kind: str
    facts: tuple
    public_names: tuple

    @property
    def surfaces(self):
        return tuple(s for s in dict.fromkeys((self.name, *self.aliases, *self.public_names)) if len(s.strip()) >= 2)

    def text(self, handle=None):
        head = f"[{handle}] " if handle else ""
        aliases = ", ".join(self.aliases) or "없음"
        return f"{head}{self.name} (별칭: {aliases}; 종류: {self.kind})\n" + "\n".join(f"- {fact}" for fact in self.facts)


def render_cards(cards, prefix="G"):
    """답·슬롯 프롬프트에 넣는 카드 묶음. 번호는 [G1]부터 넣은 순서대로다."""
    return "\n\n".join(card.text(f"{prefix}{n}") for n, card in enumerate(cards, start=1))


def card_from_row(row):
    """rel-glossary 꼴(internal_name·internal_aliases·type·public_name·public_aliases)과 처음 제안한 꼴(name·aliases·kind·public) 둘 다.
    facts 는 text 만 쓴다. source_claims 의 claim id 는 원래 doc_id 라 공개 이름을 품는다."""
    public = row.get("public") or {"name": row.get("public_name"), "aliases": row.get("public_aliases", [])}
    facts = tuple(f["text"] if isinstance(f, dict) else str(f) for f in row.get("facts", []))
    return Card(id=row["id"], name=row.get("internal_name") or row["name"],
                aliases=tuple(row.get("internal_aliases", row.get("aliases", []))), kind=row.get("type") or row.get("kind", ""),
                facts=facts, public_names=tuple(n for n in [public.get("name"), *(public.get("aliases") or [])] if n))


def read_cards(path=HUBS):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [card_from_row(row) for row in (data["hubs"] if isinstance(data, dict) else data)]


def surface_pattern(surface):
    """ASCII 는 낱말 경계로 본다. 모두 대문자인 짧은 약어(BIRD, FRR, KT)는 대소문자를 가린다: 소문자 bird·kt 는 다른 낱말이다."""
    escaped = re.escape(surface)
    if not surface.isascii():
        return re.compile(escaped, re.I)
    case = 0 if surface.isupper() and len(surface) <= SHORT_ACRONYM else re.I
    return re.compile(ASCII_WORD_EDGE.format(escaped), case)


def text_match(question, cards):
    """질문 글에 카드의 사내 이름·별칭·공개 이름이 글자로 있는 카드 id, 카드 순."""
    return [c.id for c in cards if any(surface_pattern(s).search(question) for s in c.surfaces)]


@dataclass
class Link:
    qid: str
    text_hubs: list
    candidates: list
    candidate_scores: list
    hubs: list = field(default_factory=list)
    reply: str = ""
    error: str = ""
    seconds: float = 0.0
    cached: bool = False


def link_prompt(question, candidate_cards):
    listing = render_cards(candidate_cards, prefix="H")
    return f"[질문]\n{question}\n\n[카드 후보]\n{listing}"


def parse_choice(text, candidate_ids):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"JSON 이 없다: {text[:200]}")
    picked = json.loads(match.group(0)).get("hubs", [])
    handles = {f"H{n}": cid for n, cid in enumerate(candidate_ids, start=1)}
    return list(dict.fromkeys(handles[h] for h in picked if h in handles))


class Linker:
    def __init__(self, cards, client=None, top=CANDIDATES):
        self.cards = cards
        self.by_id = {c.id: c for c in cards}
        self.client = client or OllamaClient("qwen3:8b", num_predict=256, json_output=True)
        self.top = top
        self.system = PROMPT.read_text(encoding="utf-8")
        vectors = np.asarray(embed_client.embed([c.text() for c in cards]), dtype=np.float32)
        self.vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def cards_of(self, ids):
        return [self.by_id[i] for i in ids]

    def candidates(self, question, qvec):
        """(카드 id, cosine) — 글자 매칭 카드를 먼저, 나머지를 cosine 순으로 top 개(글자 매칭이 더 많으면 그만큼)."""
        cosine = self.vectors @ qvec
        matched = text_match(question, self.cards)
        ranked = [self.cards[i].id for i in np.argsort(-cosine, kind="stable")]
        index = {c.id: i for i, c in enumerate(self.cards)}
        picked = list(dict.fromkeys(matched + ranked))[:max(self.top, len(matched))]
        return [(cid, float(cosine[index[cid]])) for cid in picked]

    def link_many(self, questions):
        """questions: [(qid, 질문 글)]. 작은 모델 실패는 Link.error 에 남기고 hubs 는 비운다."""
        qvecs = np.asarray(embed_client.embed([q for _, q in questions]), dtype=np.float32)
        qvecs /= np.linalg.norm(qvecs, axis=1, keepdims=True)
        links = []
        for (qid, q), v in zip(questions, qvecs):
            scored = self.candidates(q, v)
            links.append(Link(qid, text_match(q, self.cards), [c for c, _ in scored], [round(s, 4) for _, s in scored]))
        prompts = [link_prompt(q, self.cards_of(l.candidates)) for (_, q), l in zip(questions, links)]
        for l, prompt, reply in zip(links, prompts, self.client.ask_many(prompts, system=self.system, tag="cf-link")):
            entry = self.client.cache_path(prompt, self.system)
            if entry.exists():
                l.seconds = json.loads(entry.read_text(encoding="utf-8"))["seconds"]
            if isinstance(reply, LLMCallFailed):
                l.error = str(reply)
                continue
            l.reply, l.cached = reply.text, reply.cache_hit
            try:
                l.hubs = parse_choice(reply.text, l.candidates)
            except (ValueError, json.JSONDecodeError) as error:
                l.error = str(error)
        return links


def score_links(links, gold_rows):
    """방법(text·model)마다 문항을 모아 센 정밀도·재현율, 정답 구심점이 있는 문항 중 다 맞힌 비율, 없는 문항 중 하나라도 고른 비율."""
    gold = {str(r["qid"]): set(r.get("gold_hubs") or []) for r in gold_rows}
    scores = {}
    for method, picked_of in (("text", lambda l: l.text_hubs), ("model", lambda l: l.hubs),
                              ("candidates", lambda l: l.candidates)):
        tp = fp = fn = exact = with_gold = empty_gold = false_on_empty = 0
        for l in links:
            truth, picked = gold[l.qid], set(picked_of(l))
            tp, fp, fn = tp + len(truth & picked), fp + len(picked - truth), fn + len(truth - picked)
            if truth:
                with_gold += 1
                exact += picked == truth
            else:
                empty_gold += 1
                false_on_empty += bool(picked)
        scores[method] = {"precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
                          "exact_share": exact / with_gold if with_gold else None, "questions_with_gold": with_gold,
                          "picked_on_empty_share": false_on_empty / empty_gold if empty_gold else None, "questions_without_gold": empty_gold}
    return scores


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def read_scope(path):
    return {line.split("\t", 1)[0] for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()}


def main():
    parser = argparse.ArgumentParser(description="질문 jsonl(qid, question)을 구심점 카드에 잇고 runs/23-cf-link/<이름>.jsonl 에 쓴다.")
    parser.add_argument("questions")
    parser.add_argument("--hubs", default=str(HUBS))
    parser.add_argument("--scope", help="qid<TAB>… 목록 파일. 주면 그 qid 만 잇는다")
    parser.add_argument("--score", action="store_true", help="같은 파일의 gold_hubs 로 연결 정확도를 낸다")
    args = parser.parse_args()
    rows = read_jsonl(args.questions)
    if args.scope:
        wanted = read_scope(args.scope)
        rows = [r for r in rows if str(r["qid"]) in wanted]
    linker = Linker(read_cards(args.hubs))
    links = linker.link_many([(str(r["qid"]), r["question"]) for r in rows])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{Path(args.questions).stem}.jsonl"
    out.write_text("".join(json.dumps(asdict(l), ensure_ascii=False) + "\n" for l in links), encoding="utf-8")
    print(f"{out}: {len(links)}문항 · 실패 {sum(bool(l.error) for l in links)} · {linker.client.usage_line()}")
    if args.score:
        print(json.dumps(score_links(links, rows), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
