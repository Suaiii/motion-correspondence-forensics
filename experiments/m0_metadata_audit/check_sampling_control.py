"""Apply the proposed sampling contract to audited metadata, no new detector fit."""
import argparse
import json
import sys
from pathlib import Path
from run import sha, write_json

code_root = Path(__file__).resolve().parents[2] / "research-code"
sys.path.insert(0, str(code_root))
from sampling import fixed_rate_plan

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", type=Path, required=True)
args = parser.parse_args()
run = args.run_dir.resolve()
rows = [json.loads(line) for line in (run / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
plans, errors = [], []
for row in rows:
    try:
        plan = fixed_rate_plan(row["frame_count"], row["fps"])
        plans.append({"sample_id": row["sample_id"], "source": row["source"], "indices": plan.indices, "delta_times": plan.delta_times})
    except ValueError as exc:
        errors.append({"sample_id": row["sample_id"], "error": str(exc)})
result = {"control": "Nominal-CFR target 4fps, 2sec, half-open interval, no repeat-last",
          "scope": "Metadata-level feasibility check; not a new dataset split and not decoded PTS verification.",
          "n": len(rows), "accepted_plans": len(plans), "failures": errors,
          "all_accepted_have_8_unique_indices": all(len(set(p["indices"])) == 8 for p in plans),
          "sampler_sha256": sha(code_root / "sampling.py"), "observations_sha256": sha(run / "observations.jsonl"), "plans": plans}
write_json(run / "sampling_control.json", result)
print(json.dumps({k: v for k, v in result.items() if k != 'plans'}, indent=2))
