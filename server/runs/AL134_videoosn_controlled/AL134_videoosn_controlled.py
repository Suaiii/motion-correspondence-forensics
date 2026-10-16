"""AL134 controlled same-source sanity check built from the AL132 runner.

Only the manifest selection and grouped split differ: the run is restricted to
the 20 rows whose source is videoOSN_raw, where both real and fake rows exist.
This cannot establish a formal result, but it removes the AL132 source-label
confound for one small development check.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

BASE = Path(__file__).resolve().parent.parent / "AL132_temporal_event_snn" / "AL132_temporal_event_snn.py"
_base_ns = {"__name__": "al132_base"}
exec(BASE.read_text(encoding="utf-8"), _base_ns)
globals().update({k: v for k, v in _base_ns.items() if not k.startswith("__")})


def select_manifest(manifest_path: Path, out_path: Path) -> list[dict]:
    rows = [json.loads(x) for x in manifest_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    chosen = [r for r in rows if r.get("source") == "videoOSN_raw"]
    chosen = sorted(chosen, key=lambda r: (int(r.get("label_fake", -1)), r.get("sample_id", "")))
    if len(chosen) != 20 or sum(int(r["label_fake"]) for r in chosen) != 10:
        raise RuntimeError(f"expected 20 videoOSN_raw rows with 10 fake, got {len(chosen)}")
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in chosen) + "\n", encoding="utf-8")
    return chosen


def split_indices(rows: list[dict], seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train, test = [], []
    for label in (0, 1):
        ids = [i for i, r in enumerate(rows) if int(r["label_fake"]) == label]
        ids = np.asarray(ids, dtype=int)
        rng.shuffle(ids)
        cut = max(1, int(round(len(ids) * 0.7)))
        train.extend(ids[:cut].tolist())
        test.extend(ids[cut:].tolist())
    return np.asarray(sorted(train), dtype=int), np.asarray(sorted(test), dtype=int)


def main_controlled() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=False)
    start = time.time()
    meta = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(os.sys.argv), "torch": torch.__version__, "cuda": torch.cuda.is_available(), "device": args.device, "seeds": SEEDS, "source_restriction": "videoOSN_raw", "nframes": NFRAMES, "size": SIZE}
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    selected_path = args.run_dir / "manifest.jsonl"
    rows = select_manifest(args.manifest, selected_path)
    feats, errors = [], []
    for row in rows:
        try:
            feats.append(event_features(read_gray(Path("/root/autodl-tmp/cvpr27/data") / row["path"])))
        except Exception as exc:
            errors.append({"sample_id": row.get("sample_id"), "error": repr(exc)})
    if errors:
        (args.run_dir / "decode_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        raise RuntimeError(f"decode errors {len(errors)}")
    x = np.stack(feats).astype(np.float32)
    np.save(args.run_dir / "features.npy", x)
    result = fit_eval(x, rows, args.device if torch.cuda.is_available() else "cpu", args.run_dir / "results.json")
    summary = summarize(result, rows, args.run_dir / "summary.json")
    summary["source_control"] = "constant source videoOSN_raw; source-only predictor is undefined/constant"
    summary["n_rows"] = len(rows)
    summary["formal_gate"] = False
    summary["status"] = "controlled_pilot_not_formal"
    (args.run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    hashes = {p.name: sha256_file(p) for p in args.run_dir.iterdir() if p.is_file()}
    hashes["wrapper_script_sha256"] = sha256_file(Path(__file__))
    hashes["base_script_sha256"] = sha256_file(BASE)
    hashes["source_manifest_sha256"] = sha256_file(args.manifest)
    (args.run_dir / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["elapsed_seconds"] = time.time() - start
    meta["summary_status"] = summary["status"]
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main_controlled()
