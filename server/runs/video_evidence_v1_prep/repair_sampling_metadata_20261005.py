"""Repair a decoder metadata label after a completed 8-frame extraction.

The extraction code produced eight feature rows, but its record writer used a
stale ``center_16`` label.  This script refuses partial/inconsistent caches,
backs up every record, verifies every feature hash, and then changes only that
metadata field.  It is deliberately separate from model training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--expected-count", type=int, required=True)
    ap.add_argument("--backup-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    records_dir = args.run_dir / "records"
    records = sorted(records_dir.glob("*.json"))
    if len(records) != args.expected_count:
        raise SystemExit(f"record_count_mismatch:{len(records)}!={args.expected_count}")
    args.backup_dir.mkdir(parents=True, exist_ok=False)

    old_counts: dict[str, int] = {}
    new_counts: dict[str, int] = {}
    digest_lines: list[str] = []
    verified_features = 0
    skipped_error_records = 0
    for record_path in records:
        raw = record_path.read_bytes()
        before = hashlib.sha256(raw).hexdigest()
        row = json.loads(raw.decode("utf-8"))
        if row.get("status") != "ok":
            skipped_error_records += 1
            continue
        if row.get("shape") != [8, 768]:
            raise SystemExit(f"shape_mismatch:{record_path.name}:{row.get('shape')}")
        feature_path = args.run_dir / row["feature_file"]
        if not feature_path.exists():
            raise SystemExit(f"missing_feature:{record_path.name}")
        if sha256(feature_path) != row.get("feature_sha256"):
            raise SystemExit(f"feature_hash_mismatch:{record_path.name}")
        verified_features += 1

        old = row.get("sampling", {}).get("sampling_mode")
        old_counts[old] = old_counts.get(old, 0) + 1
        if old not in ("center_16_native_frames_no_time_resampling", "center_8_native_frames_no_time_resampling"):
            raise SystemExit(f"unexpected_sampling_mode:{record_path.name}:{old}")
        shutil.copy2(record_path, args.backup_dir / record_path.name)
        row["sampling"]["sampling_mode"] = "center_8_native_frames_no_time_resampling"
        new = row["sampling"]["sampling_mode"]
        new_counts[new] = new_counts.get(new, 0) + 1
        updated = json.dumps(row, ensure_ascii=False, indent=2) + "\n"
        record_path.write_text(updated, encoding="utf-8")
        after = hashlib.sha256(record_path.read_bytes()).hexdigest()
        digest_lines.append(f"{record_path.name}:{before}:{after}")

    digest = hashlib.sha256("\n".join(digest_lines).encode("utf-8")).hexdigest()
    receipt = {
        "status": "complete",
        "scope": "metadata_only_sampling_mode_repair_after_verified_8frame_extraction",
        "run_dir": str(args.run_dir),
        "record_count": len(records),
        "updated_record_count": verified_features,
        "skipped_error_record_count": skipped_error_records,
        "verified_feature_count": verified_features,
        "shape_required": [8, 768],
        "old_sampling_mode_counts": old_counts,
        "new_sampling_mode_counts": new_counts,
        "record_hash_transition_digest": digest,
        "backup_dir": str(args.backup_dir),
        "feature_files_modified": False,
        "training_started": False,
    }
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
