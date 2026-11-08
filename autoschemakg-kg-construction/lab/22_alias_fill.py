import json
import re
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np

LAB = Path(__file__).parent
CACHE = LAB / "runs/22-cache"
METHODS = ("fixed1000", "lumber:exaone3.5:2.4b", "lumber:gemma4:e2b-it-qat", "fixed896", "fixed610", "heading")
ALIAS_MODELS = ("exaone3.5:2.4b", "gemma4:e2b-it-qat")
PEEKED_FORMS = {"t02": ["rebase"], "t03": ["amend"], "t07": ["UFET", "ultra-fine typing"]}
MAX_ALIAS_CHARS = 40
ALIAS_PROMPT = """아래 용어를 문서 작성자들이 다르게 적을 수 있는 이름을 모두 나열하라. 약어, 줄임말, 다른 언어 표기, 흔히 쓰는 짧은 이름을 포함한다. 한 줄에 이름 하나만 적고 설명은 붙이지 마라.

용어: {name}
"""


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tc = load("topic_chunking", LAB / "21_topic_chunking.py")
sg, kgd = tc.sg, tc.kgd


def structure_targets():
    return json.loads(sg.STRUCTURE.read_text())


def entry_for(target, entries, canonical_of):
    name = sg.short_name(target["target"])
    canonical = canonical_of.get(sg.surface_key(name))
    if canonical:
        return next(e for e in entries if e["canonical"] == canonical)
    return {"canonical": name, "type": None, "aliases": [], "definition": ""}


def parse_aliases(content, name):
    forms = []
    for line in content.splitlines():
        form = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip("`'\"“”‘’*").strip()
        if not form or form.endswith(":") or len(form) > MAX_ALIAS_CHARS:
            continue
        if sg.surface_key(form) != sg.surface_key(name) and form not in forms:
            forms.append(form)
    return forms


def propose_aliases(model, target, entry):
    path = CACHE / f"{model.replace(':', '_')}-{target['id']}.json"
    if path.exists():
        return json.loads(path.read_text())["aliases"]
    prompt = ALIAS_PROMPT.format(name=entry["canonical"])
    if entry["definition"]:
        prompt += f"뜻: {entry['definition']}\n"
    body = {"model": model, "stream": False, "options": {"temperature": 0, "num_ctx": 4096},
            "messages": [{"role": "user", "content": prompt}]}
    content = kgd.distractor.post("/api/chat", body)["message"]["content"]
    aliases = parse_aliases(content, entry["canonical"])
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": model, "target": target["id"], "prompt": prompt, "raw": content, "aliases": aliases}, ensure_ascii=False, indent=1))
    return aliases


def with_added_forms(added):
    entries, canonical_of = sg.read_glossary()
    glossary = [dict(e, aliases=list(e["aliases"])) for e in entries]
    for target in structure_targets():
        entry = entry_for(target, glossary, canonical_of)
        if entry not in glossary:
            glossary.append(entry)
        entry["aliases"] += [f for f in added.get(target["id"], []) if f not in entry["aliases"]]
    return glossary


def added_forms_by_variant():
    entries, canonical_of = sg.read_glossary()
    variants = {"기존": {}, "답을 본 판": PEEKED_FORMS}
    for model in ALIAS_MODELS:
        variants[f"{model} 제안"] = {t["id"]: propose_aliases(model, t, entry_for(t, entries, canonical_of)) for t in structure_targets()}
        kgd.single_post("/api/generate", {"model": model, "keep_alive": 0})
    return variants


def evaluate():
    original_glossary = sg.GLOSSARY
    added = added_forms_by_variant()
    variants = {name: with_added_forms(forms) for name, forms in added.items()}
    units, _ = tc.gold_units("structure")
    encoder = kgd.distractor.OllamaEncoder(kgd.CACHE / "embeddings.json")
    chunked = {}
    for method in METHODS:
        chunks = tc.all_chunks(method)
        chunked[method] = (chunks, encoder.encode([c["text"] for c in chunks]))

    print("=== 대상별로 더한 별칭")
    entries, canonical_of = sg.read_glossary()
    for target in structure_targets():
        entry = entry_for(target, entries, canonical_of)
        print(f"  {target['id']} {target['target']}  — 기존 {[entry['canonical'], *entry['aliases']]}")
        for name, forms in added.items():
            if name != "기존":
                print(f"      {name:24} + {[f for f in forms.get(target['id'], []) if f not in entry['aliases']]}")

    rows = {}
    for name, glossary in variants.items():
        path = LAB / f"runs/22-glossary-{name.replace(' ', '_').replace(':', '_')}.json"
        path.write_text(json.dumps(glossary, ensure_ascii=False, indent=1))
        sg.GLOSSARY = path
        for method, (chunks, vectors) in chunked.items():
            rows[name, method] = tc.structure_scores(chunks, vectors, encoder, units)
    sg.GLOSSARY = original_glossary

    print("\n=== 구조 질문 10개 — 정밀도 / 재현율 / 가져온 글자 수")
    for kind in ("실", "실+임베딩"):
        print(f"\n  [{kind}]")
        print(f"  {'나누기':26}" + "".join(f"{name:>30}" for name in variants))
        for method in METHODS:
            cells = [f"{np.mean([r[kind][0] for r in rows[n, method]]):.2f} / {np.mean([r[kind][1] for r in rows[n, method]]):.2f} / {int(np.mean([r[kind][2] for r in rows[n, method]])):>6}" for n in variants]
            print(f"  {method:26}" + "".join(f"{c:>30}" for c in cells))

    print("\n=== 대상별 실 재현율 (정밀도) — fixed1000")
    print(f"  {'대상':6}" + "".join(f"{name:>26}" for name in variants))
    for i, target in enumerate(structure_targets()):
        cells = [f"{rows[n, 'fixed1000'][i]['실'][1]:.2f} ({rows[n, 'fixed1000'][i]['실'][0]:.2f})" for n in variants]
        print(f"  {target['id']:6}" + "".join(f"{c:>26}" for c in cells))
    (LAB / "runs/22-eval.jsonl").write_text("\n".join(json.dumps({"glossary": n, "method": m, "structure": r}, ensure_ascii=False) for (n, m), r in rows.items()) + "\n")


if __name__ == "__main__":
    {"evaluate": evaluate}[sys.argv[1]](*sys.argv[2:])
