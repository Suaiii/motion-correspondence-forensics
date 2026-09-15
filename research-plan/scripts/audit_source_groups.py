"""Audit source-prefix overlap without modifying source data or running models."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

DEFAULT = Path(r"E:\AAGenvid\Dataset\RoboVid-SM\v02\splits\split_manifest.csv")


def audit(path: Path) -> dict:
    raw = path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    grouped = {}
    for split in ("train", "val", "test"):
        selected = [r for r in rows if r["split"] == split]
        ids = [re.sub(r"-Scene-\d+$", "", r["vript_clip_id"]) for r in selected]
        grouped[split] = ids
    intersections = []
    for a, b in combinations(grouped, 2):
        shared = set(grouped[a]) & set(grouped[b])
        intersections.append({
            "a": a, "b": b, "shared_prefix_count": len(shared),
            "a_affected_clips": sum(k in shared for k in grouped[a]),
            "b_affected_clips": sum(k in shared for k in grouped[b]),
        })
    source_counts = {}
    for split in grouped:
        source_counts[split] = dict(Counter(
            "openai_sora" if "openai_sora" in r["fake_file"].lower()
            else "opensora" if "opensora" in r["fake_file"].lower()
            else "t2vz" if "t2vz" in r["fake_file"].lower() else "unknown"
            for r in rows if r["split"] == split
        ))
    return {
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(path.resolve()),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "method": "Remove trailing -Scene-[digits] from vript_clip_id; compare sets across splits",
        "limitation": "Filename-prefix proxy, not verified original metadata or content deduplication",
        "random_seed": None, "network_calls": 0, "model_runs": 0,
        "splits": {s: {"real_clips": len(v), "source_prefixes": len(set(v))} for s, v in grouped.items()},
        "intersections": intersections, "fake_generator_counts": source_counts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.manifest)
    result = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
