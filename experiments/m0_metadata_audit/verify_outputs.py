"""Recompute stored diagnostic predictions from plain JSON model parameters."""
import argparse
import json
from pathlib import Path
import numpy as np
from run import sha, write_json

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
assert run.drive.upper() == "E:"
metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
rows = [json.loads(line) for line in (run / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
for filename, key in [("protocol.json", "protocol_sha256"), ("selection.json", "selection_sha256"), ("observations.jsonl", "observations_sha256"), ("predictions.json", "predictions_sha256")]:
    assert sha(run / filename) == metrics[key], f"Hash mismatch: {filename}"
checks = {}
for name, model in metrics["feature_sets"].items():
    X = np.log1p(np.array([[r[k] for k in model["fields"]] for r in rows]))
    transformed = (X - np.array(model["scaler_mean"])) / np.array(model["scaler_scale"])
    logits = transformed @ np.array(model["coef"])[0] + model["intercept"][0]
    p = 1 / (1 + np.exp(-logits))
    saved = {r["sample_id"]: r["prob_fake"] for r in predictions if r["feature_set"] == name}
    error = max(abs(float(v) - saved[r["sample_id"]]) for r, v in zip(rows, p))
    assert error < 1e-12, f"Prediction mismatch: {name}"
    audits = [(r["label_fake"], float(v)) for r, v in zip(rows, p) if r["role"] == "audit"]
    neg = [v for y, v in audits if y == 0]
    pos = [v for y, v in audits if y == 1]
    auc = sum((a > b) + .5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))
    assert abs(auc - model["roles"]["audit"]["auc"]) < 1e-12
    checks[name] = {"max_probability_error": error, "pairwise_auc": auc, "passed": True}
write_json(run / "verification.json", {"checks": checks, "verifier_sha256": sha(__file__), "kind": "numerical verification by same implementer, not independent scientific review"})
hashes = {p.name: sha(p) for p in sorted(run.iterdir()) if p.is_file() and p.name != "artifact_hashes.json"}
write_json(run / "artifact_hashes.json", hashes)
print(json.dumps(checks, indent=2))
