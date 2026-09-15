"""Export candidate review evidence; no automatic duplicate verdicts."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from run import sha, write_json

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
assert run.drive.upper() == "E:"
receipt = json.loads((run / "probe_receipt.json").read_text(encoding="utf-8"))
assert sha(run / "observations.jsonl") == receipt["observations_sha256"]
rows = {r["sample_id"]: r for r in (json.loads(line) for line in (run / "observations.jsonl").read_text(encoding="utf-8").splitlines())}
ids = sorted({c[k] for c in receipt["near_duplicate_candidates"] for k in ("a", "b")})
out = run / "candidate_review"
out.mkdir(exist_ok=True)
stats = []
for sample in ids:
    row = rows[sample]
    cap = cv2.VideoCapture(row["path"], cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    for second in (0, min(1.0, (row["frame_count"] - 1) / row["fps"]), max(0, row["duration_sec"] * .5)):
        frame_index = min(row["frame_count"] - 1, round(second * row["fps"]))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {sample} frame {frame_index}")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filename = f"{sample}_frame{frame_index}.png"
        cv2.imencode('.png', frame)[1].tofile(str(out / filename))
        stats.append({"sample_id": sample, "frame_index": frame_index, "mean_gray": float(gray.mean()), "std_gray": float(gray.std()),
                      "min_gray": int(gray.min()), "max_gray": int(gray.max()), "below5_fraction": float(np.mean(gray < 5)), "evidence": filename})
    cap.release()
write_json(out / "frame_stats.json", stats)
print(json.dumps(stats, indent=2))
