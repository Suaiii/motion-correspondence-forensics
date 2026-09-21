"""AL72: bounded public metadata audit. No media, test split, models or SSH.

Run from the canonical repository root. Output is written once, never overwritten.
Parent identifiers are filename-derived candidates, not verified visual ancestry.
"""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research-plan/reviews/AL72_EVIDENCE_20260922.json"
ORDER = ROOT / "research-plan/AL72_CANDIDATE_ROOT_SPLIT_AUDIT_20260922.md"
PRIOR = ROOT / "research-plan/reviews/AL71_SPLIT_INTEGRITY_RECORD_20260922.json"
API = "https://api.github.com/repos/LongMa-2025/AIGVDBench/commits/main"
PATTERN = r"^(?P<root>[A-Za-z0-9_-]{11})_(?P<scene>[0-9]+)_(?P<start>[0-9]+)to(?P<end>[0-9]+)\.mp4$"
CONFIG = {
    "filename_pattern": PATTERN,
    "case_sensitive": True,
    "valid_interval": "end > start; units and semantic meaning unverified",
    "max_requests": 4,
    "max_file_bytes": 12 * 1024 * 1024,
    "max_total_bytes": 24 * 1024 * 1024,
    "witness_limit": 10,
    "unknown_policy": "retain unmatched identifiers; do not infer a parent",
    "test_media_model_ssh_access": False,
}


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def stable_digest(obj):
    return digest(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def audit():
    if OUT.exists():
        raise FileExistsError(f"Refuse to overwrite {OUT}")
    start = now()
    wall = time.perf_counter()
    cpu = time.process_time()
    requests = []
    evidence = {
        "task_id": "AL72", "started_at": start, "executor": "planagent",
        "source_sha256": digest(Path(__file__).read_bytes()),
        "work_order_sha256": digest(ORDER.read_bytes()),
        "prior_record_sha256": digest(PRIOR.read_bytes()),
        "config": CONFIG, "config_sha256": stable_digest(CONFIG),
        "requests": requests, "scope": "public train/val metadata only",
        "independent_scientific_review": False,
    }
    consumed = 0

    def get(url, limit):
        nonlocal consumed
        if len(requests) >= CONFIG["max_requests"]:
            raise RuntimeError("Request cap reached")
        cap = min(limit, CONFIG["max_total_bytes"] - consumed)
        if cap <= 0:
            raise RuntimeError("Byte cap reached")
        rec = {"url": url, "started_at": now(), "byte_cap": cap}
        requests.append(rec)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cvpr27-public-metadata-audit/1.0"})
            with urllib.request.urlopen(req, timeout=25) as response:
                declared = response.headers.get("Content-Length")
                rec.update(status=response.status, final_url=response.geturl(),
                           content_length_header=declared)
                if declared is not None and int(declared) > cap:
                    raise RuntimeError("Declared response exceeds byte cap; body not read")
                blob = response.read(cap)
                consumed += len(blob)
                rec.update(bytes_read=len(blob), sha256=digest(blob), finished_at=now())
                if len(blob) == cap:
                    raise RuntimeError("Exact byte cap reached; completeness unknown")
                return blob
        except Exception as exc:
            rec.update(error=repr(exc), finished_at=now())
            raise

    try:
        commit = json.loads(get(API, 1024 * 1024))
        revision = commit["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Invalid Git revision")
        evidence["git_revision"] = revision
        evidence["commit_date"] = commit["commit"]["committer"]["date"]
        base = "https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/" + revision
        readme = get(base + "/README.md", 1024 * 1024)
        evidence["readme_sha256"] = digest(readme)
        evidence["readme_public_split_section_present"] = b"Dataset Split" in readme
        prior = json.loads(PRIOR.read_bytes())
        results = {}
        grouped = {}
        root_sets_second_path = {}
        ids_by_split = {}
        for split in ("train", "val"):
            blob = get(base + f"/data_splits/{split}.jsonl", CONFIG["max_file_bytes"])
            ids = []
            groups = defaultdict(list)
            unknown = []
            errors = []
            all_keys = Counter()
            blank_lines = 0
            missing_id = 0
            invalid_intervals = 0
            for lineno, line in enumerate(blob.splitlines(), 1):
                if not line.strip():
                    blank_lines += 1
                    continue
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError) as exc:
                    errors.append({"line": lineno, "error_type": type(exc).__name__})
                    continue
                if not isinstance(row, dict):
                    errors.append({"line": lineno, "error_type": "not_an_object"})
                    continue
                all_keys.update(row.keys())
                video_id = row.get("Video_id")
                if not isinstance(video_id, str) or not video_id:
                    missing_id += 1
                    continue
                ids.append(video_id)
                match = re.fullmatch(PATTERN, video_id)
                if not match:
                    unknown.append(video_id)
                    continue
                parsed = match.groupdict()
                a, b = int(parsed["start"]), int(parsed["end"])
                if b <= a:
                    invalid_intervals += 1
                    unknown.append(video_id)
                    continue
                groups[parsed["root"]].append({"id": video_id, "scene": int(parsed["scene"]),
                                               "start": a, "end": b})
            # Independent tuple/sorted path for checking group-count arithmetic.
            pairs = []
            for video_id in sorted(set(ids)):
                m = re.fullmatch(PATTERN, video_id)
                if m and int(m["end"]) > int(m["start"]):
                    pairs.append((m["root"], video_id))
            second_roots = sorted({r for r, _ in pairs})
            if second_roots != sorted(groups):
                raise AssertionError("Group enumeration mismatch")
            root_sets_second_path[split] = set(second_roots)
            counts = Counter(ids)
            parsed_n = sum(map(len, groups.values()))
            results[split] = {
                "bytes": len(blob), "sha256": digest(blob),
                "matches_AL71_sha256": digest(blob) == prior["files"][split]["sha256"],
                "line_count": len(blob.splitlines()), "blank_lines": blank_lines,
                "parse_errors": errors, "missing_id": missing_id,
                "id_rows": len(ids), "unique_ids": len(counts),
                "duplicate_id_occurrences": sum(n - 1 for n in counts.values()),
                "field_presence": dict(all_keys),
                "grammar_valid_rows": parsed_n, "grammar_unknown_rows": len(unknown),
                "invalid_interval_rows": invalid_intervals,
                "grammar_coverage_fraction": [parsed_n, len(ids)],
                "candidate_roots": len(groups), "unknown_examples": unknown[:3],
                "candidate_roots_digest": stable_digest(sorted(groups)),
                "all_ids_sha256": digest("\n".join(sorted(set(ids))).encode()),
            }
            ids_by_split[split] = set(ids)
            grouped[split] = groups
        shared = sorted(set(grouped["train"]) & set(grouped["val"]))
        second_shared = root_sets_second_path["train"].intersection(root_sets_second_path["val"])
        if set(shared) != second_shared:
            raise AssertionError("Shared-root enumeration mismatch")
        involved = {s: sum(len(grouped[s][r]) for r in shared) for s in ("train", "val")}
        witnesses = []
        for r in shared[:CONFIG["witness_limit"]]:
            witnesses.append({"candidate_root": r,
                              "train": sorted(grouped["train"][r], key=lambda v: v["id"])[0],
                              "val": sorted(grouped["val"][r], key=lambda v: v["id"])[0],
                              "train_rows": len(grouped["train"][r]),
                              "val_rows": len(grouped["val"][r])})
        evidence.update(
            status="completed_metadata_calculation", splits=results,
            exact_id_intersection=len(ids_by_split["train"] & ids_by_split["val"]),
            shared_candidate_roots=len(shared), shared_root_digest=stable_digest(shared),
            rows_with_shared_candidate_root=involved, witnesses=witnesses,
            second_path_counts_agree=True,
            limitation="Root semantics and visual ancestry remain unverified; filenames alone do not establish leakage or label correctness.",
        )
    except Exception as exc:
        evidence.update(status="failed", error=repr(exc))
    evidence.update(finished_at=now(), total_http_body_bytes_read=consumed,
                    wall_seconds=time.perf_counter() - wall,
                    process_cpu_seconds=time.process_time() - cpu,
                    python=sys.version.split()[0])
    with OUT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": evidence["status"], "record_sha256": digest(OUT.read_bytes()),
                      "shared_candidate_roots": evidence.get("shared_candidate_roots"),
                      "rows_with_shared_candidate_root": evidence.get("rows_with_shared_candidate_root"),
                      "splits": evidence.get("splits"), "error": evidence.get("error")}, ensure_ascii=False))
    return 1 if evidence["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(audit())
