"""ollama 작은 모델 호출을 디스크 캐시·동시성 상한·재시도·호출 초 기록으로 감싼다. llm_cache.ClaudeClient 와 같은 꼴이다.

    from ollama_cache import OllamaClient
    client = OllamaClient("qwen3:8b")                     # thinking 끔, temperature 0, num_ctx 8192, num_predict 1024, 동시 1
    slots = OllamaClient("qwen3:8b", num_predict=256, json_output=True)   # ollama format="json" 구조화 출력
    reply = client.ask(prompt, system="짧은 지시", tag="answer")
    replies = client.ask_many(prompts, system=..., tag=...)  # 순서 유지, 동시 max_concurrency
    print(client.usage_line())

캐시 키는 (모델, options, format, system, prompt) 의 sha256 이다. 질문별 초는 23_arch_common.llm_record(client, prompt, system) 로 읽는다.
입력이 num_ctx 에 다 들어가지 않으면 ollama 가 앞을 잘라 버리므로, prompt_eval_count 가 num_ctx - num_predict 에 닿으면
다시 시도하지 않고 ContextOverflow 로 실패한다. 출력이 num_predict 에서 끊긴 답은 metadata.finish_reason "length" 로 남긴다
(같은 입력은 같은 답이라 다시 불러도 소용없다). 끝내 실패한 호출은 캐시에 남기지 않는다.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llm_cache import CallStats, LLMCallFailed, Reply

DEFAULT_CACHE = Path(__file__).parent / "runs/23-cache/ollama"
DEFAULT_SYSTEM = "Follow the user's instructions exactly. Reply with only what is asked, no commentary."
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.S)


class ContextOverflow(LLMCallFailed):
    pass


def usage_line(stats):
    total = lambda key: sum(s.get(key, 0) for s in stats.values())
    return (f"서로 다른 프롬프트 {total('unique_prompts'):.0f}개(이번 실행에 새로 부름 {total('calls'):.0f}) · "
            f"처음 부를 때 걸린 초 합 {total('recorded_seconds'):.0f}초 · 입력 토큰 {total('prompt_tokens'):.0f} · 출력 토큰 {total('completion_tokens'):.0f} · "
            f"실패한 시도 {total('failed_attempts'):.0f} · 재시도 끝에 포기 {total('failed_calls'):.0f}")


class OllamaClient:
    def __init__(self, model="qwen3:8b", num_ctx=8192, num_predict=1024, json_output=False, cache_dir=DEFAULT_CACHE,
                 max_concurrency=1, attempts=3, timeout=900.0, keep_alive="30m"):
        self.model = model
        self.format = "json" if json_output else None
        self.options = {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict, "seed": 0}
        self.keep_alive = keep_alive
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrency = max_concurrency
        self.slots = threading.BoundedSemaphore(max_concurrency)
        self.attempts = attempts
        self.timeout = timeout
        self.stats = CallStats()

    def cache_path(self, prompt, system):
        key = json.dumps({"model": self.model, "options": self.options, "format": self.format, "think": False, "system": system, "prompt": prompt},
                         ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json"

    def _run_once(self, prompt, system):
        body = {"model": self.model, "stream": False, "think": False, "keep_alive": self.keep_alive, "options": self.options,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if self.format:
            body["format"] = self.format
        request = urllib.request.Request(OLLAMA_URL, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                reply = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LLMCallFailed(f"ollama: {error}") from error
        if reply.get("error"):
            raise LLMCallFailed(f"ollama error: {reply['error']}")
        prompt_tokens = reply.get("prompt_eval_count", 0)
        if prompt_tokens >= self.options["num_ctx"] - self.options["num_predict"]:
            raise ContextOverflow(f"입력 {prompt_tokens} 토큰이 num_ctx {self.options['num_ctx']} - num_predict {self.options['num_predict']} 에 닿았다 (잘렸을 수 있다)")
        text = THINK_BLOCK.sub("", reply.get("message", {}).get("content", "")).strip()
        if not text:
            raise LLMCallFailed("empty reply")
        return text, reply

    def ask(self, prompt, system=DEFAULT_SYSTEM, tag="default"):
        path = self.cache_path(prompt, system)
        if path.exists():
            entry = json.loads(path.read_text(encoding="utf-8"))
            self.stats.add(tag, cache_hits=1)
            self.stats.add_recorded(tag, path.name, entry["seconds"], 0.0)
            return Reply(entry["result"], dict(entry["metadata"]), True)

        problems = []
        with self.slots:
            for attempt in range(1, self.attempts + 1):
                started = time.monotonic()
                try:
                    text, reply = self._run_once(prompt, system)
                except ContextOverflow:
                    self.stats.add(tag, failed_calls=1)
                    raise
                except LLMCallFailed as error:
                    problems.append(str(error))
                    self.stats.add(tag, failed_attempts=1, seconds=time.monotonic() - started)
                    if attempt < self.attempts:
                        time.sleep(2 ** attempt)
                    continue
                seconds = time.monotonic() - started
                break
            else:
                self.stats.add(tag, failed_calls=1)
                raise LLMCallFailed(f"ollama {self.model} failed {self.attempts} times: {problems}")

        metadata = {
            "prompt_tokens": reply.get("prompt_eval_count", 0),
            "completion_tokens": reply.get("eval_count", 0),
            "finish_reason": reply.get("done_reason", ""),
            "prompt_eval_seconds": reply.get("prompt_eval_duration", 0) / 1e9,
            "eval_seconds": reply.get("eval_duration", 0) / 1e9,
            "load_seconds": reply.get("load_duration", 0) / 1e9,
        }
        entry = {"model": self.model, "options": self.options, "format": self.format, "purpose": tag, "prompt": prompt, "system": system, "result": text,
                 "metadata": metadata, "seconds": round(seconds, 2), "cost_usd": 0.0, "attempts": len(problems) + 1}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".tmp{os.getpid()}.{threading.get_ident()}")
        temporary.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
        self.stats.add(tag, calls=1, seconds=seconds, prompt_tokens=metadata["prompt_tokens"], completion_tokens=metadata["completion_tokens"])
        self.stats.add_recorded(tag, path.name, seconds, 0.0)
        return Reply(text, dict(metadata), False)

    def ask_many(self, prompts, system=DEFAULT_SYSTEM, tag="default"):
        """실패한 호출 자리에는 LLMCallFailed 객체가 들어간다."""
        def one(prompt):
            try:
                return self.ask(prompt, system, tag)
            except LLMCallFailed as error:
                return error

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            return list(pool.map(one, prompts))

    def usage_line(self):
        return usage_line(self.stats.snapshot())
