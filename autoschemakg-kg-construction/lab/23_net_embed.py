import argparse
import json
import time
from pathlib import Path

import numpy as np

import embed_client

LAB = Path(__file__).parent
UNITS = LAB / "runs/23-net-units"


def main():
    parser = argparse.ArgumentParser(description="단위 jsonl 의 text 를 embed_client(bge-m3)로 임베딩해 idx/emb-<이름>.npy(L2 정규화)와 같은 순서의 unit_id 목록을 낸다. 벡터는 embed_client 캐시로 이어진다.")
    parser.add_argument("units", nargs="*", default=[str(UNITS / f"{n}.jsonl") for n in ("fixed", "section", "claim", "doc")])
    parser.add_argument("--out", default=str(UNITS / "idx"))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "embed-report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    backend = embed_client.backend_of()
    for path in map(Path, args.units):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        before = dict(embed_client.stats)
        started = time.monotonic()
        matrix = np.asarray(embed_client.embed([r["text"] for r in rows], backend=backend.name), dtype=np.float32)
        matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
        np.save(out / f"emb-{path.stem}.npy", matrix)
        (out / f"emb-{path.stem}.ids.json").write_text(json.dumps([r["unit_id"] for r in rows], ensure_ascii=False))
        delta = {k: round(v - before[k], 1) for k, v in embed_client.stats.items() if isinstance(v, (int, float))}
        report[path.stem] = {"units": len(rows), "cached_texts": delta["cached_texts"], "requested_texts": delta["requested_texts"],
                             "seconds": round(time.monotonic() - started, 1), "lock_wait_seconds": delta["lock_wait_seconds"],
                             "model": embed_client.MODEL, "backend": embed_client.stats["backend"], "options": backend.options, "dim": int(matrix.shape[1])}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1))
        print(f"{path.stem}: 단위 {len(rows)} · 캐시 {delta['cached_texts']:.0f} · 새로 {delta['requested_texts']:.0f} · {report[path.stem]['seconds']}초 (잠금 대기 {delta['lock_wait_seconds']}초)", flush=True)


if __name__ == "__main__":
    main()
