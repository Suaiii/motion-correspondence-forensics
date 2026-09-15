#!/usr/bin/env python3
"""Read-only audit of RoboVid-SM v02 and held-out ReStraV evaluations."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\AAGenvid")
MANIFEST = ROOT / "Dataset/RoboVid-SM/manifests/real_manifest_v02_random.jsonl"
SPLIT = ROOT / "Dataset/RoboVid-SM/v02/splits/split_manifest.csv"
REPORT = ROOT / "main/reports/robovid_sm_v02"


def source(path: str) -> str:
    value = path.lower()
    if "openai_sora" in value:
        return "openai_sora"
    if "opensora" in value:
        return "opensora"
    if "t2vz" in value:
        return "t2vz"
    return "unknown"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def key(path: str, label: int) -> tuple[int, str]:
    return label, Path(path).name


def metrics(y: np.ndarray, prob_real: np.ndarray, threshold: float) -> dict[str, float | int]:
    pred = (prob_real >= threshold).astype(int)
    accuracy = float(np.mean(pred == y))
    recalls = [float(np.mean(pred[y == label] == label)) for label in (0, 1)]
    order = np.argsort(prob_real, kind="mergesort")
    sorted_scores = prob_real[order]
    ranks = np.empty(len(prob_real), dtype=float)
    start = 0
    while start < len(prob_real):
        end = start + 1
        while end < len(prob_real) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    auc = (float(ranks[y == 1].sum()) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return {
        "n": int(len(y)),
        "accuracy": round(accuracy, 6),
        "balanced_accuracy": round(float(np.mean(recalls)), 6),
        "auc_real_positive": round(auc, 6),
    }


def main() -> int:
    manifest_rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    split_rows = read_csv(SPLIT)
    split_sources: dict[str, Counter] = defaultdict(Counter)
    for row in split_rows:
        split_sources[row["split"]][source(row["fake_file"])] += 1

    print("DATASET")
    print(json.dumps({
        "pairs": len(manifest_rows),
        "unique_fake": len({row["fake_file"] for row in manifest_rows}),
        "unique_real": len({row["real_file"] for row in manifest_rows}),
        "source_type": Counter(row.get("source_type") for row in manifest_rows),
        "semantic_score": Counter(str(row.get("semantic_score")) for row in manifest_rows),
        "fake_sources_by_split": {name: dict(counts) for name, counts in split_sources.items()},
    }, ensure_ascii=False, indent=2, default=dict))

    clean_heldout_rows = read_csv(REPORT / "restrav_clean/restrav_test_predictions.csv")
    heldout = {key(row["path"], int(row["true_label"])) for row in clean_heldout_rows}
    threshold = float(np.load(REPORT / "restrav_clean/best_tau.npy"))
    print("\nRESTRAV_PROTOCOL")
    print(json.dumps({
        "feature_pool": 400,
        "clean_heldout": len(heldout),
        "clean_train_inferred": 400 - len(heldout),
        "cross_target_rows": 400,
        "cross_target_training_identity_overlap": 400 - len(heldout),
        "threshold": threshold,
    }, indent=2))

    candidates = {
        "osn_wechat": REPORT / "restrav_cross_wechat_from_clean/restrav_cross_predictions.csv",
        "osn_whatsapp": REPORT / "restrav_cross_whatsapp_from_clean/restrav_cross_predictions.csv",
        "osn_legacy": REPORT / "restrav_cross_osn_from_clean/restrav_cross_predictions.csv",
        "codec_only": REPORT / "restrav_cross_codec_only_from_clean/restrav_cross_predictions.csv",
        "codec_pure": REPORT / "restrav_cross_codec_pure_from_clean/restrav_cross_predictions.csv",
        "geo_only": REPORT / "restrav_cross_geo_only_from_clean/restrav_cross_predictions.csv",
        "geometric_reformat": REPORT / "restrav_cross_douyin_l3_from_clean/restrav_cross_predictions.csv",
    }
    print("\nHELDOUT_RECALCULATION")
    for name, path in candidates.items():
        if not path.exists():
            continue
        rows = read_csv(path)
        y_all = np.array([int(row["true_label"]) for row in rows], dtype=int)
        p_all = np.array([float(row["prob_real"]) for row in rows], dtype=float)
        selected = [row for row in rows if key(row["path"], int(row["true_label"])) in heldout]
        y = np.array([int(row["true_label"]) for row in selected], dtype=int)
        prob = np.array([float(row["prob_real"]) for row in selected], dtype=float)
        print(json.dumps({
            "condition": name,
            "reported_full_target": metrics(y_all, p_all, threshold),
            "identity_heldout_only": metrics(y, prob, threshold),
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
