"""Build a versioned selection after deterministic decoder quality failures.

This is a mechanical, label-blind repair for rows whose completed extraction
record is ``QualityExclusion: black_frames``.  It never edits the frozen
selection and refuses unknown error classes or an empty role.  The resulting
selection is descriptive baseline input only until independently reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--records", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    original = json.loads(args.selection.read_text(encoding="utf-8"))
    rows = original.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SystemExit("selection_rows_missing")
    excluded: list[dict] = []
    kept: list[dict] = []
    record_errors = {}
    for row in rows:
        key = hashlib.sha256(row["sample_id"].encode()).hexdigest()
        record = json.loads((args.records / f"{key}.json").read_text(encoding="utf-8"))
        if record.get("status") == "ok":
            kept.append(row)
            continue
        reason = record.get("reason", "")
        if reason != "QualityExclusion: black_frames":
            raise SystemExit(f"unexpected_error:{row['sample_id']}:{reason}")
        excluded.append({
            "sample_id": row["sample_id"],
            "sha256": row["sha256"],
            "selection_role": row["selection_role"],
            "reason": reason,
        })
        record_errors[row["sample_id"]] = reason

    role_counts = Counter(r["selection_role"] for r in kept)
    original_role_counts = Counter(r["selection_role"] for r in rows)
    if set(role_counts) != set(original_role_counts):
        raise SystemExit(f"role_removed:{sorted(set(original_role_counts)-set(role_counts))}")
    out = dict(original)
    out["rows"] = kept
    out["counts"] = dict(role_counts)
    out["quality_excluded_rows"] = excluded
    out["quality_exclusion_contract"] = {
        "rule": "remove only completed decoder records with exact reason QualityExclusion: black_frames",
        "label_blind": True,
        "source_selection_sha256": sha(args.selection),
        "record_error_count": len(excluded),
        "record_error_reason_counts": dict(Counter(record_errors.values())),
        "frozen_selection_unchanged": True,
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "rows": len(kept), "excluded": len(excluded),
                      "role_counts": dict(role_counts), "output_sha256": sha(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
