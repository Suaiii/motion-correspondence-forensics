"""Frozen, bounded, local-only source audit and metadata shortcut probe."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "protocol.json"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_prefix(path):
    return re.sub(r"-Scene-\d+$", "", Path(path).stem)


def select_records(rows, seed):
    rng = random.Random(seed)
    real = defaultdict(set)
    fake = {name: set() for name in ("opensora", "t2vz")}
    for row in rows:
        real[source_prefix(row["real_file"])].add(row["real_file"])
        if row["fake_source"] in fake:
            fake[row["fake_source"]].add(row["fake_file"])
    selected = []
    prefix_pool = sorted(real)
    rng.shuffle(prefix_pool)
    assert len(prefix_pool) >= 60
    role_for_real = ["fit"] * 36 + ["calibration"] * 12 + ["audit"] * 12
    for prefix, role in zip(prefix_pool[:60], role_for_real):
        path = rng.choice(sorted(real[prefix]))
        selected.append({"path": path, "label_fake": 0, "source": "vript", "group_id": "vript:" + prefix, "role": role})
    for generator, pool in fake.items():
        pool = sorted(pool)
        rng.shuffle(pool)
        assert len(pool) >= 30
        roles = ["fit"] * 18 + ["calibration"] * 6 + ["audit"] * 6
        for path, role in zip(pool[:30], roles):
            selected.append({"path": path, "label_fake": 1, "source": generator, "group_id": generator + ":" + Path(path).stem, "role": role})
    for i, row in enumerate(selected):
        row["sample_id"] = f"S{i:03d}"
    return selected


def validate_records(records, require_digest=False):
    ids = [r["sample_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate sample id")
    for field in ("group_id", "path") + (("sha256",) if require_digest else ()):
        used = {}
        for row in records:
            key = row[field]
            if key in used:
                raise ValueError(f"duplicate {field}: {row['sample_id']} and {used[key]}")
            used[key] = row["sample_id"]
    counts = Counter((r["role"], r["label_fake"]) for r in records)
    for role, expected in [("fit", 36), ("calibration", 12), ("audit", 12)]:
        if counts[(role, 0)] != expected or counts[(role, 1)] != expected:
            raise ValueError(f"incorrect role count: {role}")


def prepare(run):
    if run.exists():
        raise FileExistsError(f"Refusing to overwrite run: {run}")
    config = load_json(PROTOCOL)
    source = Path(config["source_manifest"])
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = select_records(rows, config["seed"])
    validate_records(selected)
    if any(Path(r["path"]).drive.upper() != "E:" or not Path(r["path"]).is_file() for r in selected):
        raise ValueError("Missing or non-E-drive selected input")
    run.mkdir(parents=True)
    shutil.copyfile(PROTOCOL, run / "protocol.json")
    shutil.copyfile(__file__, run / "runner_snapshot.py")
    write_json(run / "selection.json", selected)
    write_json(run / "run_lock.json", {
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha(run / "protocol.json"), "selection_sha256": sha(run / "selection.json"),
        "source_manifest_sha256": sha(source), "code_sha256": sha(__file__),
        "python": sys.executable, "python_version": platform.python_version(),
        "role": "M0 diagnostic; all historical sources development only",
    })
    print(f"PREPARED {len(selected)} videos; roles fixed before decoding or fitting", flush=True)


def verify(run):
    lock = load_json(run / "run_lock.json")
    for name, key in [("protocol.json", "protocol_sha256"), ("selection.json", "selection_sha256")]:
        if sha(run / name) != lock[key]:
            raise ValueError(f"Run lock mismatch: {name}")
    if sha(__file__) != lock["code_sha256"]:
        raise ValueError("Runner code changed since preparation; use a new versioned run")
    return load_json(run / "protocol.json"), load_json(run / "selection.json")


def ahash(frame):
    import cv2
    small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (8, 8)).astype(float)
    bits = small > small.mean()
    value = sum(int(bit) << i for i, bit in enumerate(bits.ravel()))
    return f"{value:016x}"


def probe_video(row):
    import cv2
    import numpy as np
    started = time.perf_counter()
    path = Path(row["path"])
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    try:
        if not cap.isOpened():
            raise ValueError("Cannot open video")
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or n <= 0 or width <= 0 or height <= 0 or not np.isfinite(fps):
            raise ValueError("Invalid metadata")
        ok, frame = cap.read()
        if not ok:
            raise ValueError("First frame cannot decode")
        first = ahash(frame)
        target = min(n - 1, round(fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        ok, frame = cap.read()
        if not ok:
            raise ValueError("Second probe frame cannot decode")
        second = ahash(frame)
        fourcc_value = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc = "".join(chr((fourcc_value >> (8 * i)) & 255) for i in range(4))
    finally:
        cap.release()
    size = path.stat().st_size
    return dict(row, fps=fps, frame_count=n, duration_sec=n / fps, width=width, height=height,
                aspect_ratio=width / height, file_bytes=size, bytes_per_second=size / (n / fps),
                fourcc=fourcc, ahash_first=first, ahash_second=second,
                sha256=sha(path), probe_seconds=round(time.perf_counter() - started, 4))


def probe(run):
    import cv2
    config, selected = verify(run)
    cv2.setNumThreads(1)
    output = run / "observations.jsonl"
    if output.exists():
        raise FileExistsError("Refusing to overwrite observations")
    started = time.perf_counter()
    failures = []
    observations = []
    with output.open("w", encoding="utf-8") as handle:
        for i, row in enumerate(selected):
            if time.perf_counter() - started > config["budget"]["max_decode_seconds"]:
                failures.append({"sample_id": row["sample_id"], "error": "Total decode budget exceeded; remaining samples not run"})
                break
            try:
                item = probe_video(row)
                observations.append(item)
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                handle.flush()
            except Exception as exc:
                failures.append({"sample_id": row["sample_id"], "error": repr(exc)})
            if (i + 1) % 10 == 0:
                print(f"PROBED {i + 1}/{len(selected)}; failures={len(failures)}", flush=True)
    candidates = []
    for i, a in enumerate(observations):
        for b in observations[i + 1:]:
            if a["role"] == b["role"]:
                continue
            distances = [(int(a[k], 16) ^ int(b[k], 16)).bit_count() for k in ("ahash_first", "ahash_second")]
            if max(distances) <= 4:
                candidates.append({"a": a["sample_id"], "b": b["sample_id"], "hamming": distances, "status": "candidate only; not verified duplicate"})
    write_json(run / "probe_receipt.json", {"count": len(observations), "failures": failures, "near_duplicate_candidates": candidates,
               "wall_seconds": round(time.perf_counter() - started, 3), "observations_sha256": sha(output),
               "no_pixels_saved": True, "decode_scope": "two probe frames, not full-stream validation"})
    if failures or len(observations) != len(selected):
        raise RuntimeError("Probe incomplete; no fitting allowed")
    validate_records(observations, require_digest=True)
    print("PROBE COMPLETE; unique byte hashes; near-duplicate candidates:", len(candidates), flush=True)


def evaluate(run):
    import numpy as np
    import sklearn
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score, roc_auc_score, confusion_matrix
    from sklearn.preprocessing import StandardScaler
    config, selected = verify(run)
    receipt = load_json(run / "probe_receipt.json")
    if receipt["failures"] or receipt["count"] != len(selected) or sha(run / "observations.jsonl") != receipt["observations_sha256"]:
        raise ValueError("Probe failed or changed")
    rows = [json.loads(line) for line in (run / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
    validate_records(rows, require_digest=True)
    if [r["sample_id"] for r in rows] != [r["sample_id"] for r in selected]:
        raise ValueError("Selection order mismatch")
    if receipt["near_duplicate_candidates"]:
        raise ValueError("Near-duplicate candidates need review before fitting")
    if (run / "metrics.json").exists():
        raise FileExistsError("Refusing to overwrite metrics")
    y = np.array([r["label_fake"] for r in rows])
    masks = {role: np.array([r["role"] == role for r in rows]) for role in ("fit", "calibration", "audit")}
    summaries, predictions = {}, []
    for name, fields in config["feature_sets"].items():
        X = np.log1p(np.array([[r[k] for k in fields] for r in rows], dtype=float))
        if not np.isfinite(X).all():
            raise ValueError("Nonfinite metadata")
        scaler = StandardScaler().fit(X[masks["fit"]])
        X = scaler.transform(X)
        model = LogisticRegression(C=config["fit"]["C"], max_iter=config["fit"]["max_iter"], random_state=config["seed"]).fit(X[masks["fit"]], y[masks["fit"]])
        probs = model.predict_proba(X)[:, 1]
        thresholds = np.linspace(*config["threshold"]["grid"])
        scores = [balanced_accuracy_score(y[masks["calibration"]], probs[masks["calibration"]] >= t) for t in thresholds]
        best = max(scores)
        threshold = min((float(t) for t, s in zip(thresholds, scores) if abs(s - best) < 1e-12), key=lambda t: (abs(t - .5), t))
        by_role = {}
        for role, mask in masks.items():
            truth, prob = y[mask], probs[mask]
            pred = prob >= threshold
            by_role[role] = {"n": int(mask.sum()), "auc": float(roc_auc_score(truth, prob)), "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
                             "confusion_matrix_real_fake": confusion_matrix(truth, pred, labels=[0, 1]).tolist()}
            for row, score in zip((r for r in rows if r["role"] == role), prob):
                predictions.append({"feature_set": name, "sample_id": row["sample_id"], "role": role, "group_id": row["group_id"], "label_fake": row["label_fake"], "prob_fake": float(score), "threshold": threshold})
        truth, prob = y[masks["audit"]], probs[masks["audit"]]
        rng = np.random.default_rng(config["bootstrap"]["seed"])
        negative, positive = np.where(truth == 0)[0], np.where(truth == 1)[0]
        aucs = []
        for _ in range(config["bootstrap"]["replicates"]):
            sampled = np.concatenate([rng.choice(negative, len(negative), replace=True), rng.choice(positive, len(positive), replace=True)])
            aucs.append(roc_auc_score(truth[sampled], prob[sampled]))
        summaries[name] = {"fields": fields, "threshold": threshold, "roles": by_role,
                           "audit_auc_percentile95": np.quantile(aucs, [.025, .975]).tolist(),
                           "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
                           "coef": model.coef_.tolist(), "intercept": model.intercept_.tolist()}
    write_json(run / "predictions.json", predictions)
    write_json(run / "metrics.json", {"experiment_id": config["experiment_id"], "kind": "metadata shortcut diagnostic only",
               "sklearn_version": sklearn.__version__, "feature_sets": summaries, "bootstrap_caveat": "Small development audit set; interval does not represent generator or dataset uncertainty.",
               "protocol_sha256": sha(run / "protocol.json"), "selection_sha256": sha(run / "selection.json"),
               "observations_sha256": sha(run / "observations.jsonl"), "predictions_sha256": sha(run / "predictions.json")})
    lines = ["# M0 元信息捷径检查", "", "本次为开发数据诊断，不是新视频取证算法结果。标签 1 为 fake。样本与协议在解码和拟合前固定。", "",
             "| 特征 | 校准 AUROC | 审计 AUROC | 审计 BAcc | 审计 AUROC 95%区间 |", "|---|---:|---:|---:|---|"]
    for name, item in summaries.items():
        low, high = item["audit_auc_percentile95"]
        lines.append(f"| {name} | {item['roles']['calibration']['auc']:.4f} | {item['roles']['audit']['auc']:.4f} | {item['roles']['audit']['balanced_accuracy']:.4f} | [{low:.4f}, {high:.4f}] |")
    lines.extend(["", "120 条视频：60 real、30 OpenSora、30 t2vz；fit/calibration/audit=72/24/24。real 每个原视频前缀最多一条；fake 仅以路径和字节哈希初步去重，prompt/父生成视频映射仍缺失。", "",
                  "推断边界：高分仅提示数据元属性与标签相关，不能量化具体神经检测器利用了多少捷径。阈值来自 calibration；所有三种预设特征均报告，未按 audit 分数选择模型。", "",
                  "校验：所选文件 SHA256 无重复，两时点 average hash 无跨角色候选（阈值≤4）；这不是完整语义或内容去重。仅解码两个时点，不代表每个视频全流无损坏。", "",
                  "下一步：据元数据分布设计内容保留的采样/编码控制，并保留原始轨道；匹配失败应报告，不通过筛样把检测问题人为变容易。"])
    (run / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, result in summaries.items():
        print(name, "audit", result["roles"]["audit"], "CI", result["audit_auc_percentile95"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "probe", "evaluate"])
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if run.drive.upper() != "E:" or Path(sys.executable).drive.upper() != "E:":
        raise ValueError("All research execution and output must use E:")
    if Path(os.environ.get("TEMP", "")).drive.upper() != "E:":
        raise ValueError("Use research-runtime/enter.ps1 to route temporary files")
    {"prepare": prepare, "probe": probe, "evaluate": evaluate}[args.command](run)


if __name__ == "__main__":
    main()
