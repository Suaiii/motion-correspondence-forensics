"""Revalidate a transferred v1 bundle and build queryable CPU-only indexes.

The frozen source manifest and existing training selections remain unchanged.
Run on the server with --root /srv/video_evidence_v1 and a new --output path.
This verifies file bytes and archived PTS; it does not fit or score a model.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from fractions import Fraction

EXPECTED_MANIFEST = "0687ca7b63d95776d341a3702a13ec96594fa9f323ca41c1714fd7d57f557d47"
EXPECTED_ARCHIVE = "5c6267f99827de3ea7dc26111410c9d6c2dd47facd0c2c4a213eb06aa5900719"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_path(text):
    value = text.replace("\\", "/")
    if value.startswith("E:/AAGenvid/"):
        value = value[len("E:/AAGenvid/"):]
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or ":" in value:
        raise ValueError("unsafe relative path: " + text)
    return p.as_posix()


def check_row(task):
    root, row = task
    rel = relative_path(row["relative_path"])
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError("path escapes package: " + rel)
    record = {"relative_path": rel, "expected_sha256": row["sha256"]}
    try:
        record["size"] = path.stat().st_size
        record["observed_sha256"] = digest(path)
        record["file_ok"] = (record["size"] == row["file_size"]
                             and record["observed_sha256"] == row["sha256"])
    except OSError as exc:
        record.update(file_ok=False, error=str(exc))
    p = row.get("ffprobe") or {}
    pts = p.get("pts") or []
    record["pts_nonempty_integer"] = bool(pts) and all(type(x) is int for x in pts)
    record["pts_nondecreasing"] = record["pts_nonempty_integer"] and all(a <= b for a, b in zip(pts, pts[1:]))
    record["pts_strict_increase"] = record["pts_nonempty_integer"] and all(a < b for a, b in zip(pts, pts[1:]))
    record["pts_count_matches"] = len(pts) == p.get("frame_count_probed")
    seq_hash = hashlib.sha256(json.dumps(pts, separators=(",", ":")).encode()).hexdigest()
    record["pts_sequence_hash_matches"] = seq_hash == p.get("native_pts_sequence_sha256")
    try:
        record["positive_time_base"] = Fraction(p["time_base"]) > 0
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        record["positive_time_base"] = False
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--verify-archive", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    manifest = root / "v1_manifest.jsonl"
    actual_manifest = digest(manifest)
    if actual_manifest != EXPECTED_MANIFEST:
        raise ValueError("frozen manifest SHA mismatch")
    rows = []
    offsets = []
    with manifest.open("rb") as f:
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                break
            if line.strip():
                rows.append(json.loads(line))
                offsets.append(pos)
    if len(rows) != 9236:
        raise ValueError("unexpected v1 row count")
    checks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool, (out / "file_verification.jsonl").open("w", encoding="utf-8") as receipt:
        for i, rec in enumerate(pool.map(check_row, ((root, r) for r in rows)), 1):
            receipt.write(json.dumps(rec, separators=(",", ":")) + "\n")
            checks.append(rec)
            if i % 1000 == 0 or i == len(rows):
                print(json.dumps({"stage": "hash_verification", "checked": i, "total": len(rows)}), flush=True)
    required = ["file_ok", "pts_nonempty_integer", "pts_nondecreasing", "pts_count_matches", "pts_sequence_hash_matches", "positive_time_base"]
    failed = [c for c in checks if not all(c[k] for k in required)]
    archive = root / "video_evidence_v1_complete.tar"
    archive_record = {"path": str(archive), "exists": archive.is_file(), "verified": False}
    if args.verify_archive and archive.is_file():
        print(json.dumps({"stage": "archive_hash"}), flush=True)
        archive_record.update(bytes=archive.stat().st_size, sha256=digest(archive))
        archive_record["verified"] = (archive_record["sha256"] == EXPECTED_ARCHIVE and archive_record["bytes"] == 23997983232)
    if failed or (args.verify_archive and not archive_record["verified"]):
        write_json(out / "failure.json", {"manifest_sha256": actual_manifest, "failed_rows": failed, "archive": archive_record})
        raise SystemExit("integrity failed; indexes not published")

    by_rel = {r["relative_path"]: r for r in rows}
    if len(by_rel) != len(rows):
        raise ValueError("duplicate relative paths")
    by_sha = collections.defaultdict(list)
    by_identity = collections.defaultdict(list)
    for row in rows:
        by_sha[row["sha256"]].append(row)
        by_identity[(row["package"], row["label"], row["sample_id"])].append(row)

    # Only explicit source manifests create parent links. Names alone are not proof.
    parent_links = {}
    link_errors = []
    source_provenance = root / "provenance_20261008"
    if source_provenance.is_dir():
        for name in ("wechat_osn_manifest.csv", "whatsapp_osn_manifest.csv", "degraded_manifest.csv"):
            source_file = source_provenance / name
            if not source_file.is_file():
                continue
            source_hash = digest(source_file)
            with source_file.open(encoding="utf-8-sig", newline="") as f:
                for record in csv.DictReader(f):
                    try:
                        child = relative_path(record["output_video"])
                        parent = relative_path(record["input_video"])
                    except (KeyError, ValueError) as exc:
                        link_errors.append({"source": name, "error": str(exc)})
                        continue
                    if child not in by_rel:
                        continue
                    if parent not in by_rel or record.get("status") not in {"ok", "exists"}:
                        link_errors.append({"source": name, "child": child, "parent": parent, "status": record.get("status")})
                        continue
                    a, b = by_rel[parent], by_rel[child]
                    if (a["label"], a["split"]) != (b["label"], b["split"]):
                        link_errors.append({"source": name, "child": child, "reason": "label_or_split_mismatch"})
                        continue
                    link = {"parent_relative_path": parent, "parent_sha256": a["sha256"], "child_sha256": b["sha256"], "source_file": name, "source_sha256": source_hash, "status": "source_manifest_link_bytes_verified_recipe_not_replayed"}
                    if child in parent_links and parent_links[child]["parent_sha256"] != a["sha256"]:
                        raise ValueError("conflicting parent evidence")
                    parent_links[child] = link

    columns = ["asset_id", "path", "relative_path", "sha256", "file_size", "package", "sample_id", "split", "label", "generator", "generator_family", "variant", "source", "license_status", "ancestor_status", "content_pairing", "time_base", "native_frame_count", "native_pts_strict_increase", "width", "height", "codec", "average_fps", "clean_identity_group", "parent_sha256", "parent_evidence_status", "generator_evidence_status", "manifest_byte_offset"]
    integer_columns = {"file_size", "native_frame_count", "native_pts_strict_increase", "width", "height", "manifest_byte_offset"}
    conn = sqlite3.connect(out / "catalog.sqlite")
    conn.execute("CREATE TABLE assets (" + ",".join(c + (" INTEGER" if c in integer_columns else " TEXT") + (" PRIMARY KEY" if c == "asset_id" else "") for c in columns) + ")")
    sql = "INSERT INTO assets VALUES (" + ",".join("?" for _ in columns) + ")"
    coverage = collections.Counter()
    with (out / "manifest.remote.jsonl").open("w", encoding="utf-8") as full, (out / "catalog.jsonl").open("w", encoding="utf-8") as compact:
        for row, checked, offset in zip(rows, checks, offsets):
            remote = dict(row, local_path=row["path"], path=str(root / row["relative_path"]))
            full.write(json.dumps(remote, ensure_ascii=False, separators=(",", ":")) + "\n")
            p = row["ffprobe"]
            identity = json.dumps([row["package"], row["label"], row["sample_id"]], separators=(",", ":"))
            link = parent_links.get(row["relative_path"], {})
            cat = {c: row.get(c) for c in columns}
            cat.update(asset_id=hashlib.sha256(row["relative_path"].encode()).hexdigest(), path=remote["path"], time_base=p["time_base"], native_frame_count=len(p["pts"]), native_pts_strict_increase=int(checked["pts_strict_increase"]), width=p.get("width"), height=p.get("height"), codec=p.get("codec_name"), average_fps=p.get("avg_frame_rate"), clean_identity_group=hashlib.sha256(identity.encode()).hexdigest(), parent_sha256=link.get("parent_sha256"), parent_evidence_status=link.get("status", "clean" if row["variant"] == "clean" else "unverified"), generator_evidence_status="inherited_label_release_or_filename_not_sample_generation_receipt", manifest_byte_offset=offset)
            conn.execute(sql, [cat.get(c) for c in columns])
            compact.write(json.dumps(cat, ensure_ascii=False, separators=(",", ":")) + "\n")
            coverage[(row["package"], row["split"], row["variant"], row["label"], row["generator"])] += 1
    conn.execute("CREATE INDEX filter_cells ON assets(package,split,variant,label,generator)")
    conn.execute("CREATE INDEX identity_groups ON assets(clean_identity_group)")
    conn.execute("CREATE INDEX file_hashes ON assets(sha256)")
    conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)")
    conn.executemany("INSERT INTO metadata VALUES (?,?)", [("source_manifest_sha256", actual_manifest), ("source_manifest", str(manifest)), ("scope", "operational_inventory_not_scientific_gate")])
    conn.commit()
    sqlite_ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    with (out / "coverage.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["package", "split", "variant", "label", "generator", "count"])
        writer.writerows([*key, count] for key, count in sorted(coverage.items()))
    with (out / "parent_links.jsonl").open("w", encoding="utf-8") as f:
        for child, link in sorted(parent_links.items()):
            f.write(json.dumps(dict(child_relative_path=child, **link), separators=(",", ":")) + "\n")
    split_collisions = [{"sha256": sha, "splits": sorted({r["split"] for r in group}), "paths": [r["relative_path"] for r in group]} for sha, group in by_sha.items() if len({r["split"] for r in group}) > 1]
    identity_collisions = [{"group": list(key), "splits": sorted({r["split"] for r in group})} for key, group in by_identity.items() if len({r["split"] for r in group}) > 1]
    clean_duplicates = [{"sha256": sha, "paths": [r["relative_path"] for r in group if r["variant"] == "clean"]} for sha, group in by_sha.items() if sum(r["variant"] == "clean" for r in group) > 1]
    write_json(out / "duplicate_audit.json", {"cross_split_sha_collisions": split_collisions, "cross_split_identity_collisions": identity_collisions, "clean_duplicate_hash_groups": clean_duplicates, "limit": "byte identity and inherited sample identity only; not perceptual or ancestor independence"})
    feature_root = root / "runs/dino_features"
    feature_status = collections.Counter()
    feature_errors = []
    for record in sorted((feature_root / "records").glob("*.json")):
        data = json.loads(record.read_text())
        feature_status[data.get("status", "missing_status")] += 1
        if data.get("status") != "ok":
            feature_errors.append({"record": str(record), "sample_id": data.get("sample_id"), "error": data.get("error"), "reason": data.get("reason")})
    write_json(out / "existing_feature_errors.json", {"status_counts": dict(feature_status), "errors": feature_errors, "scope": "inventory_only_not_feature_validation_or_new_extraction"})
    metadata_hashes = {str(p.relative_to(root)): digest(p) for p in sorted(source_provenance.rglob("*")) if p.is_file()} if source_provenance.is_dir() else {}
    summary = {
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "endpoint": "connect.westc.seetacloud.com:22647", "root": str(root), "manifest_sha256": actual_manifest,
        "script_sha256": digest(__file__), "row_count": len(rows), "file_hash_verified": sum(c["file_ok"] for c in checks),
        "total_video_bytes": sum(r["file_size"] for r in rows), "unique_file_sha256_count": len(by_sha),
        "clean_rows": sum(r["variant"] == "clean" for r in rows), "derived_rows": sum(r["variant"] != "clean" for r in rows),
        "clean_unique_file_sha256_count": len({r["sha256"] for r in rows if r["variant"] == "clean"}),
        "inherited_identity_groups": len(by_identity), "identity_is_ancestor_proof": False,
        "native_pts_checks_passed": len(rows) - len(failed), "strictly_increasing_pts_rows": sum(c["pts_strict_increase"] for c in checks),
        "parent_links_with_source_manifest": len(parent_links), "derived_parent_link_missing": sum(r["variant"] != "clean" and r["relative_path"] not in parent_links for r in rows), "parent_link_errors": link_errors,
        "cross_split_exact_hash_collisions": len(split_collisions), "cross_split_sample_identity_collisions": len(identity_collisions),
        "source_counts": dict(collections.Counter(r["source"] for r in rows)), "variant_counts": dict(collections.Counter(r["variant"] for r in rows)),
        "clean_generator_counts": dict(collections.Counter(r["generator"] for r in rows if r["variant"] == "clean")),
        "license_status_counts": dict(collections.Counter(r["license_status"] for r in rows)), "ancestor_status_counts": dict(collections.Counter(r["ancestor_status"] for r in rows)),
        "existing_feature_status_counts": dict(feature_status), "archive": archive_record, "metadata_sha256": metadata_hashes,
        "sqlite_integrity": sqlite_ok, "disk_free_bytes": shutil.disk_usage(root).free,
        "operational_inventory_ready": sqlite_ok == "ok", "scientific_gate_passed": False, "new_training_started": False,
        "pts_validation_scope": "archived native integer PTS rechecked against hash-matching media; no fresh full decoder pass",
        "elapsed_seconds": time.monotonic() - start,
    }
    artifact_names = ["manifest.remote.jsonl", "catalog.jsonl", "catalog.sqlite", "coverage.tsv", "file_verification.jsonl", "duplicate_audit.json", "parent_links.jsonl", "existing_feature_errors.json"]
    summary["artifacts"] = {name: {"bytes": (out/name).stat().st_size, "sha256": digest(out/name)} for name in artifact_names}
    write_json(out / "receipt.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
