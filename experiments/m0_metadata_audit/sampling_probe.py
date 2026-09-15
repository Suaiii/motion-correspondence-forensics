"""Audit sampling indices and a straight-trajectory null; never runs DINOv2."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from run import sha, write_json

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
assert run.drive.upper() == "E:"
receipt = json.loads((run / "probe_receipt.json").read_text(encoding="utf-8"))
assert sha(run / "observations.jsonl") == receipt["observations_sha256"]
rows = [json.loads(line) for line in (run / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
source = Path(r"E:\AAGenvid\external_repos\ReStraV\dinov2_features.py")
records = []
for row in rows:
    fps, n = row["fps"], row["frame_count"]
    duration = n / fps
    start, end = max(0.0, duration / 2 - 1.0), min(duration, duration / 2 + 1.0)
    for T in (8, 24):
        # Mirrors the inspected OpenCV/numpy fallback, without importing its online-loading module.
        indices = np.clip(np.linspace(int(start * fps), int(end * fps), T).round().astype(int), 0, n - 1)
        delta = np.diff(indices).astype(float)
        # Null signal z(t) = t*v: every native step is a straight line, no generation artifact.
        # cosine_similarity returns zero when either displacement vector has zero norm.
        consecutive_nonzero = (delta[:-1] > 0) & (delta[1:] > 0)
        raw_cosine = np.where(consecutive_nonzero, 1.0, 0.0)
        unmasked_angles = np.rad2deg(np.arccos(raw_cosine))
        valid_angles = np.zeros(int(consecutive_nonzero.sum()))
        records.append({
            "sample_id": row["sample_id"], "source": row["source"], "T": T,
            "indices": indices.tolist(), "unique_indices": int(len(np.unique(indices))),
            "zero_step_fraction": float(np.mean(delta == 0)),
            "unmasked_straight_null_mean_degrees": float(unmasked_angles.mean()),
            "valid_angle_count": len(valid_angles),
            "valid_straight_null_mean_degrees": float(valid_angles.mean()) if len(valid_angles) else None,
        })
groups = defaultdict(list)
for r in records:
    groups[(r["source"], r["T"])].append(r)
summary = []
for (src, T), items in sorted(groups.items()):
    summary.append({"source": src, "T": T, "n": len(items),
                    "unique_index_range": [min(r["unique_indices"] for r in items), max(r["unique_indices"] for r in items)],
                    "mean_zero_step_fraction": float(np.mean([r["zero_step_fraction"] for r in items])),
                    "mean_unmasked_straight_null_degrees": float(np.mean([r["unmasked_straight_null_mean_degrees"] for r in items])),
                    "no_valid_angle_clips": sum(r["valid_angle_count"] == 0 for r in items)})
output = {
    "method": "Local ReStraV numpy fallback center-window index formula; T=8/24, window=2sec",
    "limitation": "This audits index repetition and synthetic straight embeddings, not actual DINOv2 curvature or historical backend selection.",
    "source_code": str(source), "source_code_sha256": sha(source),
    "probe_code_sha256": sha(__file__), "observations_sha256": sha(run / "observations.jsonl"),
    "summary": summary, "per_video": records,
}
write_json(run / "sampling_probe.json", output)
print(json.dumps(summary, indent=2))
