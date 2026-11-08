"""bge-m3 를 CUDA sentence-transformers(fp16, 최대 8192 토큰)로 올려 HTTP 로 임베딩을 내준다.

    lab/.venv-emb/bin/python lab/embed_server.py            # 127.0.0.1:8765
    POST /embed {"texts": [...]}  ->  {"float32_b64": <n×dim float32 바이트의 base64>, "count": n, "dim": dim, "backend": "st-cuda-fp16"}
    GET  /health                  ->  {"ok": true, "backend": ..., "max_seq_length": 8192}

/health 는 계산 중에도 바로 답한다. 계산은 요청 하나씩 차례로 한다. 묶음 안에서는 토큰 길이로 정렬해 (최대 길이 × 개수) 가 TOKEN_BUDGET 을 넘지 않게 잘라 GPU 에 넣는다.
메모리가 모자라면 묶음을 반씩 나눠 다시 한다. 그 밖의 CUDA 오류가 나면 CUDA 문맥이 회복되지 않으므로 503 을 돌려준 뒤 프로세스를 끝낸다.
보통은 embed_client.py 가 부른다.
"""
import argparse
import base64
import json
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODEL_ID = "BAAI/bge-m3"
BACKEND = "st-cuda-fp16"
MAX_SEQ_LENGTH = 8192
TOKEN_BUDGET = 131072
MAX_BATCH = 256


def load_model():
    model = SentenceTransformer(MODEL_ID, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = MAX_SEQ_LENGTH
    return model


def token_batches(model, texts):
    lengths = [min(len(ids), MAX_SEQ_LENGTH) for ids in model.tokenizer(texts, add_special_tokens=True, truncation=False)["input_ids"]]
    order = sorted(range(len(texts)), key=lambda i: lengths[i])
    batch = []
    for i in order:
        if batch and (len(batch) + 1) * lengths[i] > TOKEN_BUDGET or len(batch) == MAX_BATCH:
            yield batch
            batch = []
        batch.append(i)
    if batch:
        yield batch


def encode_batch(model, texts):
    try:
        return model.encode(texts, batch_size=len(texts), normalize_embeddings=True, convert_to_numpy=True,
                            show_progress_bar=False).astype(np.float32)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        if len(texts) == 1:
            raise
        half = len(texts) // 2
        return np.concatenate([encode_batch(model, texts[:half]), encode_batch(model, texts[half:])])


def encode(model, texts):
    matrix = np.zeros((len(texts), model.get_sentence_embedding_dimension()), dtype=np.float32)
    for batch in token_batches(model, texts):
        matrix[batch] = encode_batch(model, [texts[i] for i in batch])
    return matrix


def make_handler(model):
    gpu = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._reply(200, {"ok": True, "backend": BACKEND, "model": MODEL_ID, "max_seq_length": model.max_seq_length})
            else:
                self._reply(404, {"error": "unknown path"})

        def do_POST(self):
            if self.path != "/embed":
                self._reply(404, {"error": "unknown path"})
                return
            texts = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["texts"]
            started = time.monotonic()
            try:
                with gpu:
                    matrix = encode(model, texts)
            except torch.cuda.OutOfMemoryError as error:
                torch.cuda.empty_cache()
                self._reply(503, {"error": f"CUDA out of memory even for one text: {error}"})
                return
            except RuntimeError as error:
                if "CUDA error" not in str(error):
                    raise
                self._reply(503, {"error": f"CUDA context broken, server exits for restart: {error}"})
                print(f"{time.strftime('%F %T')} CUDA 오류로 끝낸다 (감시 루프가 다시 띄운다): {error}", flush=True)
                os._exit(1)
            self._reply(200, {"float32_b64": base64.b64encode(matrix.tobytes()).decode("ascii"), "count": matrix.shape[0],
                              "dim": matrix.shape[1], "backend": BACKEND, "seconds": round(time.monotonic() - started, 3)})

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="bge-m3 CUDA 임베딩 서버")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    model = load_model()
    print(f"{BACKEND} {MODEL_ID} on {torch.cuda.get_device_name()} · http://{args.host}:{args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(model)).serve_forever()


if __name__ == "__main__":
    main()
