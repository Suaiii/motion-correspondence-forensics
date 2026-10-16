"""Path-based DINO feature extraction and dense baseline for video_evidence_v1.

Subcommands:
  verify  validate the frozen manifest/selection contract without torch
  extract decode native frames and write a hash-locked DINO feature cache
  train   fit a calibration-selected logistic baseline on that cache

The adapter is deliberately separate from the historical ms/vc2 scripts.
It never edits the project DAG or the input manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def native_pts_seconds(row: dict):
    """Convert manifest integer PTS into the seconds used by ffprobe decoder metadata."""
    import numpy as np

    probe = row.get("ffprobe") or {}
    pts = probe.get("pts")
    if not isinstance(pts, list):
        raise ValueError("manifest native pts missing")
    time_base = probe.get("time_base")
    if isinstance(time_base, str) and "/" in time_base:
        num, den = time_base.split("/", 1)
        scale = float(num) / float(den)
    else:
        pts_time = probe.get("pts_time")
        if isinstance(pts_time, list) and len(pts_time) == len(pts):
            return np.asarray(pts_time, dtype=np.float64)
        scale = 1.0
    return np.asarray(pts, dtype=np.float64) * scale


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def rows_from_selection(path: Path) -> list[dict]:
    obj = read(path)
    rows = obj.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("selection rows are missing")
    return rows


def verify_contract(selection_path: Path, manifest_path: Path | None = None) -> dict:
    selection = read(selection_path)
    rows = rows_from_selection(selection_path)
    if manifest_path is not None:
        observed = sha(manifest_path)
        if observed != selection.get("manifest_sha256"):
            raise ValueError(f"manifest hash mismatch: {observed} != {selection.get('manifest_sha256')}")
    ids = [r.get("sample_id") for r in rows]
    hashes = [r.get("sha256") for r in rows]
    if any(not x for x in ids + hashes):
        raise ValueError("sample_id and sha256 are required")
    if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
        raise ValueError("selection contains duplicate sample_id or sha256")
    roles = {r.get("selection_role") for r in rows}
    required = {"fit", "calibration", "in_domain_audit", "external_holdout"}
    if not required <= roles:
        raise ValueError(f"missing selection roles: {sorted(required - roles)}")
    groups = {role: {r["sample_id"] for r in rows if r.get("selection_role") == role} for role in roles}
    for role, group in groups.items():
        for other, other_group in groups.items():
            if role < other and group & other_group:
                raise ValueError(f"sample overlap {role}/{other}")
    bad_pts = []
    frame_budget_exclusions = []
    for r in rows:
        probe = r.get("ffprobe") or {}
        pts = probe.get("pts")
        if not probe.get("native_pts_complete") or not probe.get("native_pts_monotonic"):
            bad_pts.append((r["sample_id"], "incomplete_or_nonmonotonic"))
        if not isinstance(pts, list) or len(pts) < 5:
            bad_pts.append((r["sample_id"], "fewer_than_5_pts"))
        elif len(pts) < 8:
            frame_budget_exclusions.append(r["sample_id"])
    if bad_pts:
        raise ValueError(f"native PTS contract failed for {len(bad_pts)} rows")
    return {
        "selection_sha256": sha(selection_path),
        "manifest_sha256": selection.get("manifest_sha256"),
        "rows": len(rows),
        "role_counts": dict(Counter(r["selection_role"] for r in rows)),
        "generator_counts": {
            f"{role}:{generator}": n
            for (role, generator), n in Counter((r["selection_role"], r.get("generator")) for r in rows).items()
        },
        "native_8_frame_exclusions": frame_budget_exclusions,
        "verified": True,
    }


def cmd_verify(args) -> None:
    result = verify_contract(args.selection, args.manifest)
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False))


def cmd_extract(args) -> None:
    verify_contract(args.selection, args.manifest)
    sys.path[:0] = [str(args.runtime)]
    import numpy as np
    import torch
    from torch.utils.data import DataLoader, Dataset
    from index16_decode import decode
    from forensics.backbones import dinov2

    rows = rows_from_selection(args.selection)
    root = args.run_dir
    root.mkdir(parents=True, exist_ok=False)
    (root / "records").mkdir(); (root / "features").mkdir()
    weight_hash = sha(args.weights)
    revision = subprocess.check_output(["git", "-C", str(args.model_repo), "rev-parse", "HEAD"], text=True).strip()
    lock = {
        "selection_sha256": sha(args.selection), "manifest_sha256": read(args.selection)["manifest_sha256"],
        "script_sha256": sha(Path(__file__)), "decoder_sha256": sha(Path(args.runtime) / "index16_decode.py"),
        "weights_sha256": weight_hash, "model_revision": revision, "model": "dinov2_vitb14",
        "sampling": "center 8 native frames; center square crop; area resize 224; native PTS preserved",
        "device": args.device, "video_batch": args.video_batch, "workers": args.workers,
        "scope": "video_evidence_v1 dense baseline feature cache; no mechanism gate",
    }
    save(root / "lock.json", lock)

    class Videos(Dataset):
        def __len__(self): return len(rows)
        def __getitem__(self, i):
            row = rows[i]
            try:
                if sha(Path(row["path"])) != row["sha256"]:
                    raise ValueError("input hash changed")
                frames, meta = decode(row["path"], {"frames": 8, "size": 224})
                expected = native_pts_seconds(row)
                if len(expected) >= 8:
                    observed = np.asarray(meta["pts"], dtype=float)
                    # ffprobe JSON values and cv2/ffprobe values can differ by a
                    # few ulps; reject physical-time changes at 1 microsecond.
                    if np.max(np.abs(observed - expected[(len(expected)-8)//2:(len(expected)-8)//2+8])) > 1e-6:
                        raise ValueError("native PTS sampling differs from manifest")
                return row, frames, meta, None
            except Exception as exc:
                return row, None, None, f"{type(exc).__name__}: {exc}"

    def collate(batch): return batch
    torch.set_num_threads(1); torch.manual_seed(20261005)
    model = dinov2(args.model_repo, args.weights, weight_hash, args.device, "dinov2_vitb14")
    loader = DataLoader(Videos(), batch_size=args.video_batch, num_workers=args.workers,
                        collate_fn=collate, multiprocessing_context="spawn" if args.workers else None)
    mean = torch.tensor([.485, .456, .406], device=args.device)[None, :, None, None]
    std = torch.tensor([.229, .224, .225], device=args.device)[None, :, None, None]
    completed = []
    started = time.monotonic()
    for batch in loader:
        valid = []
        for row, frames, meta, err in batch:
            key = hashlib.sha256(row["sample_id"].encode()).hexdigest()
            record_path = root / "records" / f"{key}.json"
            if err:
                out = {**row, "status": "error", "reason": err}
                save(record_path, out); completed.append(out); continue
            valid.append((row, frames, meta, record_path))
        if not valid: continue
        arr = np.concatenate([v[1] for v in valid])
        x = torch.from_numpy(arr[..., ::-1].copy()).permute(0, 3, 1, 2).to(args.device).float() / 255
        x = (x - mean) / std
        with torch.inference_mode(), torch.autocast(args.device, dtype=torch.bfloat16):
            values = model(x).float().cpu().numpy().reshape(len(valid), 8, -1)
        if not np.isfinite(values).all(): raise ValueError("nonfinite DINO features")
        for j, (row, _frames, meta, record_path) in enumerate(valid):
            key = hashlib.sha256(row["sample_id"].encode()).hexdigest()
            feature = root / "features" / f"{key}.npy"
            with feature.with_suffix(".npy.tmp").open("wb") as f: np.save(f, values[j])
            os.replace(feature.with_suffix(".npy.tmp"), feature)
            out = {**row, "status": "ok", "sampling": meta,
                   "feature_file": str(feature.relative_to(root)), "feature_sha256": sha(feature),
                   "shape": list(values[j].shape)}
            save(record_path, out); completed.append(out)
        save(root / "progress.json", {"completed": len(completed), "requested": len(rows),
                                        "wall_seconds": time.monotonic() - started})
    summary = {"complete": len(completed) == len(rows), "requested": len(rows),
               "completed": len(completed), "status_counts": dict(Counter(x["status"] for x in completed)),
               "wall_seconds": time.monotonic() - started, "classification_metrics_computed": False}
    save(root / "summary.json", summary)
    if not summary["complete"]: raise RuntimeError("feature extraction incomplete")
    print(json.dumps(summary, ensure_ascii=False))


def cmd_train(args) -> None:
    verify_contract(args.selection, args.manifest)
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss, roc_auc_score
    from sklearn.preprocessing import StandardScaler
    rows = rows_from_selection(args.selection); root = args.features
    records = []
    for row in rows:
        key = hashlib.sha256(row["sample_id"].encode()).hexdigest()
        rec = read(root / "records" / f"{key}.json")
        if rec.get("status") != "ok": raise ValueError(f"feature record not ok: {row['sample_id']}")
        feature = root / rec["feature_file"]
        if sha(feature) != rec["feature_sha256"]: raise ValueError("feature hash changed")
        z = np.load(feature, allow_pickle=False).astype(np.float64)
        if z.shape != (8, 768) or not np.isfinite(z).all(): raise ValueError("invalid feature shape")
        z /= np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-12)
        delta = np.abs(np.diff(z, axis=0))
        pts = native_pts_seconds(row)
        start = (len(pts) - 8) // 2
        dt = np.diff(pts[start:start + 8])
        if not np.isfinite(dt).all() or np.any(dt <= 0):
            raise ValueError(f"invalid native dt: {row['sample_id']}")
        records.append({**row, "x": np.r_[z.mean(0), delta.mean(0),
                                             (delta / dt[:, None]).mean(0)]})
    x = np.asarray([r["x"] for r in records], dtype=np.float64)
    y = np.asarray([r["label_fake"] for r in records], dtype=int)
    role = np.asarray([r["selection_role"] for r in records])
    arms = {"semantic": np.arange(768), "semantic_delta": np.arange(1536), "semantic_velocity": np.arange(2304)}
    fit = role == "fit"; cal = role == "calibration"
    results = []
    for arm, cols in arms.items():
        scaler = StandardScaler().fit(x[fit][:, cols]); xx = scaler.transform(x[:, cols])
        best = None
        for c in (0.1, 1.0, 10.0):
            model = LogisticRegression(C=c, max_iter=500, solver="lbfgs", class_weight="balanced").fit(xx[fit], y[fit])
            loss = float(log_loss(y[cal], model.predict_proba(xx[cal])[:, 1]))
            if best is None or loss < best[0]: best = (loss, c, model)
        loss, c, model = best; prob = model.predict_proba(xx)[:, 1]
        metric = {}
        for cohort in ("in_domain_audit", "held_generator_audit", "external_holdout"):
            mask = role == cohort
            n_fake = int(y[mask].sum()); two_class = 0 < n_fake < int(mask.sum())
            metric[cohort] = {"n": int(mask.sum()), "n_fake": n_fake,
                              "auc": float(roc_auc_score(y[mask], prob[mask])) if two_class else None,
                              "auc_undefined_single_class": bool(mask.sum()) and not two_class,
                              "bce": float(log_loss(y[mask], prob[mask], labels=[0, 1])) if mask.sum() else None,
                              "mean_prob_fake": float(prob[mask].mean()) if mask.sum() else None}
        results.append({"arm": arm, "selected_C": c, "calibration_bce": loss, "metrics": metric})
    out = {"complete": True, "formal_gate_passed": False, "selection_sha256": sha(args.selection),
           "feature_lock_sha256": sha(root / "lock.json"), "results": results,
           "scope": "dense baseline only; no mechanism acceptance"}
    save(args.output / "results.json", out); print(json.dumps(out, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("verify"); v.add_argument("--selection", type=Path, required=True); v.add_argument("--manifest", type=Path); v.add_argument("--output", type=Path, required=True); v.set_defaults(func=cmd_verify)
    e = sub.add_parser("extract"); e.add_argument("--selection", type=Path, required=True); e.add_argument("--manifest", type=Path, required=True); e.add_argument("--run-dir", type=Path, required=True); e.add_argument("--runtime", type=Path, required=True); e.add_argument("--model-repo", type=Path, required=True); e.add_argument("--weights", type=Path, required=True); e.add_argument("--device", default="cuda"); e.add_argument("--workers", type=int, default=4); e.add_argument("--video-batch", type=int, default=8); e.set_defaults(func=cmd_extract)
    t = sub.add_parser("train"); t.add_argument("--selection", type=Path, required=True); t.add_argument("--manifest", type=Path, required=True); t.add_argument("--features", type=Path, required=True); t.add_argument("--output", type=Path, required=True); t.set_defaults(func=cmd_train)
    args = ap.parse_args(); args.func(args)


if __name__ == "__main__": main()
