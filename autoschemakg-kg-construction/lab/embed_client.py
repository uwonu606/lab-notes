"""bge-m3 임베딩을 모든 스크립트가 같은 백엔드·같은 캐시·같은 줄로 부르게 한다.

    from embed_client import embed
    vectors = embed(["문장 하나", "문장 둘"])   # list[list[float]], 입력 순서 그대로, L2 정규화

백엔드는 둘이다. 기본은 DEFAULT_BACKEND(st-cuda) 이고, 환경 변수 EMBED_BACKEND 나 embed(texts, backend=...) 로 고른다.
한 색인·한 비교 안에서는 백엔드를 섞지 않는다. 두 백엔드 벡터의 cosine 은 평균 1.0000, 최솟값 0.9992 다(200개, 2026-10-13).
  ollama   Ollama /api/embed, 옵션 {"num_ctx": 8192, "num_batch": 8192} 고정
  st-cuda  embed_server.py (lab/.venv-emb, sentence-transformers fp16, 최대 8192 토큰). 서버가 떠 있어야 한다
캐시는 runs/23-cache/emb/ 의 sqlite 이고 키는 (백엔드, 모델, 옵션, 텍스트) 의 sha256 이다. ollama 키는 백엔드를 나누기 전 형식 그대로다.
요청은 백엔드마다 runs/23-cache/<잠금 파일> 을 fcntl.flock 으로 잡은 동안 묶음(batch_size) 하나씩만 보낸다. 그래서 여러 프로세스가 묶음 단위로 번갈아 쓴다.
벡터는 float32 로 담고, 새로 받은 값도 float32 를 거쳐 돌려준다.
"""
import argparse
import base64
import fcntl
import hashlib
import http.client
import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from array import array
from dataclasses import dataclass
from pathlib import Path

MODEL = "bge-m3"
CACHE_ROOT = Path(__file__).parent / "runs/23-cache"
CACHE_DB = CACHE_ROOT / "emb" / f"{MODEL}.sqlite"
TIMEOUT = 600.0
ATTEMPTS = 5


@dataclass(frozen=True)
class Backend:
    name: str
    url: str
    options: dict
    batch_size: int
    lock_file: Path
    key_prefix: str

    def body(self, texts):
        if self.name == "ollama":
            return {"model": MODEL, "input": texts, "options": self.options}
        return {"texts": texts}

    def vectors(self, reply):
        if self.name == "ollama":
            return reply["embeddings"]
        flat = array("f", base64.b64decode(reply["float32_b64"]))
        return [flat[i * reply["dim"]:(i + 1) * reply["dim"]] for i in range(reply["count"])]


BACKENDS = {
    # Ollama cuts embedding input at num_batch (2048 by default) unless num_batch is raised with num_ctx,
    # and reloads the model whenever a call's options differ from the loaded ones.
    "ollama": Backend("ollama", "http://localhost:11434/api/embed", {"num_ctx": 8192, "num_batch": 8192}, 16,
                      CACHE_ROOT / f"{MODEL}.lock", ""),
    "st-cuda": Backend("st-cuda", "http://127.0.0.1:8765/embed", {"dtype": "float16", "max_seq_length": 8192}, 256,
                       CACHE_ROOT / f"{MODEL}-st-cuda.lock", "st-cuda\n"),
}
DEFAULT_BACKEND = "st-cuda"
OPTIONS = BACKENDS["ollama"].options

stats = {"backend": None, "requested_texts": 0, "cached_texts": 0, "requests": 0, "lock_wait_seconds": 0.0, "request_seconds": 0.0}
SERVER = Path(__file__).parent / "embed_server.py"
SERVER_PYTHON = Path(__file__).parent / ".venv-emb/bin/python"
SERVER_LOG = CACHE_ROOT / "embed_server.log"
HEALTH_URL = "http://127.0.0.1:8765/health"
HEALTH_TIMEOUT = 180


def backend_of(name=None):
    return BACKENDS[name or os.environ.get("EMBED_BACKEND") or DEFAULT_BACKEND]


def cache_key(text, backend=None):
    backend = backend_of(backend) if not isinstance(backend, Backend) else backend
    return hashlib.sha256(f"{backend.key_prefix}{MODEL}\n{json.dumps(backend.options, sort_keys=True)}\n{text}".encode("utf-8")).hexdigest()


def _connect():
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CACHE_DB, timeout=120)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector BLOB)")
    return connection


def _cached(connection, keys):
    found = {}
    for start in range(0, len(keys), 500):
        part = keys[start:start + 500]
        rows = connection.execute(f"SELECT key, vector FROM vectors WHERE key IN ({','.join('?' * len(part))})", part)
        found.update((key, array("f", vector).tolist()) for key, vector in rows)
    return found


def _request(backend, texts):
    body = json.dumps(backend.body(texts)).encode("utf-8")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(backend.url, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return backend.vectors(json.loads(response.read()))
        except urllib.error.URLError as error:
            if attempt == ATTEMPTS:
                if backend.name == "st-cuda" and isinstance(getattr(error, "reason", None), ConnectionRefusedError):
                    raise RuntimeError("embed_server.py 가 떠 있지 않다: python3 lab/embed_client.py --start") from error
                raise
        except (TimeoutError, ConnectionError, http.client.HTTPException):
            if attempt == ATTEMPTS:
                raise
        time.sleep(10 * attempt)


def _request_holding_lock(backend, texts):
    backend.lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(backend.lock_file, "a") as lock:
        waited = time.monotonic()
        fcntl.flock(lock, fcntl.LOCK_EX)
        started = time.monotonic()
        try:
            vectors = _request(backend, texts)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    stats["lock_wait_seconds"] += started - waited
    stats["request_seconds"] += time.monotonic() - started
    stats["requests"] += 1
    return vectors


def _note_backend(name):
    used = set(filter(None, (stats["backend"] or "").split("+"))) | {name}
    stats["backend"] = "+".join(sorted(used))


def embed(texts, backend=None):
    """stats["backend"] 에 이 프로세스가 쓴 백엔드 이름이 쌓인다. 둘을 섞어 썼으면 "ollama+st-cuda" 가 된다."""
    backend = backend_of(backend)
    _note_backend(backend.name)
    texts = list(texts)
    keys = [cache_key(t, backend) for t in texts]
    connection = _connect()
    try:
        found = _cached(connection, keys)
        stats["cached_texts"] += sum(k in found for k in keys)
        missing = list(dict.fromkeys(t for t, k in zip(texts, keys) if k not in found))
        for start in range(0, len(missing), backend.batch_size):
            batch = missing[start:start + backend.batch_size]
            vectors = _request_holding_lock(backend, batch)
            rows = [(cache_key(t, backend), array("f", v).tobytes()) for t, v in zip(batch, vectors)]
            connection.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?)", rows)
            connection.commit()
            found.update((k, array("f", blob).tolist()) for k, blob in rows)
            stats["requested_texts"] += len(batch)
    finally:
        connection.close()
    return [found[k] for k in keys]


def server_health():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=HEALTH_TIMEOUT) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return None


def start_server(wait_seconds=180):
    if server_health():
        return server_health()
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with open(SERVER_LOG, "a") as log:
        subprocess.Popen([str(SERVER_PYTHON), str(SERVER)], stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                         cwd=SERVER.parent, env={**os.environ, "HF_HUB_OFFLINE": "1"})
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        time.sleep(3)
        if server_health():
            return server_health()
    return None


def main():
    parser = argparse.ArgumentParser(description="st-cuda 임베딩 서버 상태를 보거나 띄운다.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--health", action="store_true", help="서버가 답하면 0, 아니면 1 로 끝난다")
    action.add_argument("--start", action="store_true", help="꺼져 있으면 띄우고 답할 때까지 기다린다")
    args = parser.parse_args()
    health = server_health() if args.health else start_server()
    print(json.dumps(health, ensure_ascii=False) if health else f"embed_server 응답 없음 ({HEALTH_URL}). 로그: {SERVER_LOG}")
    raise SystemExit(0 if health else 1)


if __name__ == "__main__":
    main()
