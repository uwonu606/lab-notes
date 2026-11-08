import importlib.abc
import os
import importlib.util
import json
import logging
import sys
import types
from pathlib import Path

LAB = Path(__file__).parent
SRC = LAB / "runs/23-hr2-src/src"
CACHE = LAB / "runs/23-cache"
LLM_CACHE = CACHE / "llm"
IMPORT_ONLY_PACKAGES = {"torch", "transformers", "vllm", "openai", "litellm", "boto3", "botocore", "tiktoken",
                        "outlines", "gritlm", "sentence_transformers", "chromadb", "requests"}
SETTINGS_FILE = "settings.json"


class ImportOnlyModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def refuse(*args, **kwargs):
            raise RuntimeError(f"{self.__name__}.{name} is a stub: this run must not reach that backend")

        stub = type(name, (), {"__init__": refuse, "__call__": refuse})
        setattr(self, name, stub)
        return stub


class ImportOnlyFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] in IMPORT_ONLY_PACKAGES:
            return importlib.util.spec_from_loader(fullname, self, is_package=True)
        return None

    def create_module(self, spec):
        return ImportOnlyModule(spec.name)

    def exec_module(self, module):
        module.__path__ = []


sys.meta_path.append(ImportOnlyFinder())
os.environ.setdefault("TQDM_DISABLE", "1")
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(LAB))
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from hipporag import HippoRAG
from hipporag.embedding_model.Ollama import OllamaEmbeddingModel
from hipporag.llm.claude_cli import ClaudeCLILLM
from hipporag.utils.config_utils import BaseConfig
from hipporag.utils.misc_utils import Chunk
import embed_client
from llm_cache import ClaudeClient, usage_line

EMBEDDER = embed_client.MODEL


def read_chunks(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def read_questions(path):
    text = Path(path).read_text()
    rows = json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]
    return [{"id": str(r.get("id", r.get("qid"))), "question": r["question"]} for r in rows]


def default_settings(model="haiku", unicode_gate=True, synonym_threshold=0.8, workers=10, prompt_style="roles", embed_backend=None):
    return {"model": model, "synonymy_edge_unicode_gate": unicode_gate, "synonymy_edge_sim_threshold": synonym_threshold,
            "json_ensure_ascii": False, "openie_raise_on_failure": False, "workers": workers, "prompt_style": prompt_style,
            "embed_backend": embed_client.backend_of(embed_backend).name}


def save_settings(out_dir, settings):
    path = Path(out_dir) / SETTINGS_FILE
    if path.exists() and load_settings(out_dir) != settings:
        raise SystemExit(f"{path} 에 다른 설정이 있다: {load_settings(out_dir)}. 새 out_dir 를 쓴다.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=1))


def load_settings(out_dir):
    return {"prompt_style": "transcript", "embed_backend": "ollama"} | json.loads((Path(out_dir) / SETTINGS_FILE).read_text())


def open_hipporag(out_dir, settings, retrieval_top_k=200, rebuild_graph=False):
    config = BaseConfig(
        save_dir=str(Path(out_dir) / "hipporag"),
        llm_name=f"claude-{settings['model']}",
        embedding_model_name=f"ollama/{EMBEDDER}",
        openie_mode="online",
        openie_max_workers=settings["workers"],
        synonymy_edge_sim_threshold=settings["synonymy_edge_sim_threshold"],
        synonymy_edge_unicode_gate=settings["synonymy_edge_unicode_gate"],
        json_ensure_ascii=settings["json_ensure_ascii"],
        openie_raise_on_failure=settings["openie_raise_on_failure"],
        retrieval_top_k=retrieval_top_k,
        save_openie=False,
        force_index_from_scratch=rebuild_graph,
    )
    llm = ClaudeCLILLM(config, ClaudeClient(settings["model"], cache_dir=LLM_CACHE, max_concurrency=settings["workers"]),
                       prompt_style=settings["prompt_style"])
    embedder = OllamaEmbeddingModel(config, lambda texts: embed_client.embed(texts, backend=settings["embed_backend"]))
    hipporag = HippoRAG(global_config=config, extraction_llm=llm, embedding_model=embedder,
                        index_identity=f"claude-cli:{settings['model']}+ollama:{EMBEDDER}")
    return hipporag, llm, embedder


SPAN_FIELDS = ("doc_id", "start", "end")


def as_documents(chunks):
    return [Chunk(content=c["text"], source_id=c["id"], metadata={k: c[k] for k in SPAN_FIELDS if k in c}) for c in chunks]
