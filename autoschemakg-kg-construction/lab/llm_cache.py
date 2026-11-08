"""claude -p 호출을 디스크 캐시·동시성 상한·재시도·비용 집계로 감싼다.

    from llm_cache import ClaudeClient
    client = ClaudeClient("haiku")                       # 또는 "opus"
    reply = client.ask(prompt, system="짧은 지시", tag="judge")
    replies = client.ask_many(prompts, system=..., tag=...)  # 순서 유지, 동시 max_concurrency
    print(client.usage_line())

캐시 키는 (모델, system, prompt) 의 sha256 이다. 끝내 실패한 호출은 캐시에 남기지 않아 다시 돌리면 그것만 다시 부른다.
"""
import hashlib
import json
import os
import subprocess
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CACHE = Path(__file__).parent / "runs/23-cache/llm"
DEFAULT_SYSTEM = "Follow the user's instructions exactly. Reply with only what is asked, no commentary."


@dataclass
class Reply:
    text: str
    metadata: dict
    cache_hit: bool


class LLMCallFailed(RuntimeError):
    pass


class CallStats:
    def __init__(self):
        self._lock = threading.Lock()
        self.by_tag = defaultdict(lambda: defaultdict(float))
        self._seen_prompts = set()

    def add(self, tag, **counts):
        with self._lock:
            for key, value in counts.items():
                self.by_tag[tag][key] += value

    def add_recorded(self, tag, prompt_key, seconds, cost_usd):
        with self._lock:
            if prompt_key in self._seen_prompts:
                return
            self._seen_prompts.add(prompt_key)
            counts = self.by_tag[tag]
            counts["unique_prompts"] += 1
            counts["recorded_seconds"] += seconds
            counts["recorded_cost_usd"] += cost_usd

    def snapshot(self):
        with self._lock:
            return {tag: dict(counts) for tag, counts in self.by_tag.items()}


def usage_line(stats):
    total = lambda key: sum(s.get(key, 0) for s in stats.values())
    return (f"서로 다른 프롬프트 {total('unique_prompts'):.0f}개(이번 실행에 새로 부름 {total('calls'):.0f}) · "
            f"처음 부를 때 걸린 초 합 {total('recorded_seconds'):.0f}초 · ${total('recorded_cost_usd'):.3f} · "
            f"실패한 시도 {total('failed_attempts'):.0f} · 재시도 끝에 포기 {total('failed_calls'):.0f}")


class ClaudeClient:
    def __init__(self, model="haiku", cache_dir=DEFAULT_CACHE, max_concurrency=10, attempts=3, timeout=300.0):
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrency = max_concurrency
        self.slots = threading.BoundedSemaphore(max_concurrency)
        self.attempts = attempts
        self.timeout = timeout
        self.stats = CallStats()

    def cache_path(self, prompt, system):
        key = json.dumps({"model": self.model, "system": system, "prompt": prompt}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json"

    def _run_once(self, prompt, system):
        command = ["claude", "-p", "--model", self.model, "--tools", "", "--no-session-persistence",
                   "--setting-sources", "", "--output-format", "json", "--system-prompt", system]
        completed = subprocess.run(command, input=prompt, capture_output=True, text=True, timeout=self.timeout, cwd=self.cache_dir)
        if completed.returncode != 0:
            raise LLMCallFailed(f"exit {completed.returncode}: {(completed.stderr or completed.stdout)[:300]}")
        try:
            reply = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise LLMCallFailed(f"broken CLI JSON envelope: {completed.stdout[:300]}") from error
        if reply.get("is_error"):
            raise LLMCallFailed(f"CLI error: {str(reply.get('result'))[:300]}")
        if not str(reply.get("result", "")).strip():
            raise LLMCallFailed("empty reply")
        return reply

    def ask(self, prompt, system=DEFAULT_SYSTEM, tag="default"):
        path = self.cache_path(prompt, system)
        if path.exists():
            entry = json.loads(path.read_text(encoding="utf-8"))
            self.stats.add(tag, cache_hits=1)
            self.stats.add_recorded(tag, path.name, entry["seconds"], entry["cost_usd"])
            return Reply(entry["result"], dict(entry["metadata"]), True)

        problems = []
        with self.slots:
            for attempt in range(1, self.attempts + 1):
                started = time.monotonic()
                try:
                    reply = self._run_once(prompt, system)
                except (LLMCallFailed, subprocess.TimeoutExpired) as error:
                    problems.append(str(error))
                    self.stats.add(tag, failed_attempts=1, seconds=time.monotonic() - started)
                    if attempt < self.attempts:
                        time.sleep(2 ** attempt)
                    continue
                seconds = time.monotonic() - started
                break
            else:
                self.stats.add(tag, failed_calls=1)
                raise LLMCallFailed(f"claude -p failed {self.attempts} times: {problems}")

        usage = reply.get("usage", {})
        metadata = {
            "prompt_tokens": usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "finish_reason": "stop" if reply.get("stop_reason") in (None, "end_turn") else reply.get("stop_reason"),
        }
        entry = {"model": self.model, "purpose": tag, "prompt": prompt, "result": reply["result"], "metadata": metadata,
                 "seconds": round(seconds, 2), "cost_usd": reply.get("total_cost_usd", 0.0), "attempts": len(problems) + 1}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".tmp{os.getpid()}.{threading.get_ident()}")
        temporary.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
        self.stats.add(tag, calls=1, seconds=seconds, cost_usd=entry["cost_usd"], prompt_tokens=metadata["prompt_tokens"],
                       completion_tokens=metadata["completion_tokens"])
        self.stats.add_recorded(tag, path.name, seconds, entry["cost_usd"])
        return Reply(reply["result"], dict(metadata), False)

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
