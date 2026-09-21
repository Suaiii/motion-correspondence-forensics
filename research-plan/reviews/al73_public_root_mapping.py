"""AL73 bounded public repository tree/mapping audit; no media or test content."""
from collections import Counter
from datetime import datetime
import hashlib, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDER = ROOT / "research-plan/AL73_PUBLIC_ROOT_MAPPING_AUDIT_20260922.md"
AL72 = ROOT / "research-plan/reviews/AL72_EVIDENCE_20260922.json"
OUT = ROOT / "research-plan/reviews/AL73_EVIDENCE_20260922.json"
BASE = "https://api.github.com/repos/LongMa-2025/AIGVDBench"
TERMS = re.compile(r"(source|origin|metadata|lineage|ancestor|mapping|label|model|generator|split|readme)", re.I)
TEXT_EXT = {".md", ".json", ".jsonl", ".csv", ".txt", ".yaml", ".yml"}
CAP = 24 * 1024 * 1024


def sha(b):
    return hashlib.sha256(b).hexdigest()


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    body = 0
    requests = []
    ev = {
        "task_id": "AL73", "started_at": now(),
        "source_sha256": sha(Path(__file__).read_bytes()),
        "work_order_sha256": sha(ORDER.read_bytes()),
        "AL72_evidence_sha256": sha(AL72.read_bytes()),
        "scope": "bounded GitHub tree and mapping-like text metadata; no test/media/model/weights",
        "requests": [],
        "selection": {"max_requests": 4, "max_total_body_bytes": CAP,
                      "max_selected_files": 5, "max_file_bytes": 4 * 1024 * 1024,
                      "terms": TERMS.pattern},
    }

    def get(url, limit):
        nonlocal body
        if len(requests) >= 4:
            raise RuntimeError("request cap")
        cap = min(limit, CAP - body)
        if cap <= 0:
            raise RuntimeError("byte cap")
        rec = {"url": url, "started_at": now(), "cap": cap}
        requests.append(rec)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cvpr27-public-root-mapping/1.0", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=25) as response:
                declared = response.headers.get("Content-Length")
                rec.update(status=response.status, final_url=response.geturl(), content_length=declared)
                if declared and int(declared) > cap:
                    raise RuntimeError("declared body exceeds cap")
                blob = response.read(cap)
                body += len(blob)
                rec.update(bytes=len(blob), sha256=sha(blob), finished_at=now())
                return blob
        except Exception as exc:
            rec.update(status="error", error=repr(exc), finished_at=now())
            raise

    try:
        commit = json.loads(get(BASE + "/commits/main", 1024 * 1024))
        revision = commit["sha"]
        ev["revision"] = revision
        ev["commit_date"] = commit["commit"]["committer"]["date"]
        tree = json.loads(get(f"{BASE}/git/trees/{revision}?recursive=1", 6 * 1024 * 1024))
        entries = tree.get("tree", [])
        ev["tree_truncated"] = tree.get("truncated", False)
        ev["tree_entry_count"] = len(entries)
        selected = []
        for item in entries:
            path = item.get("path", "")
            ext = Path(path).suffix.lower()
            size = item.get("size", 0) or 0
            if item.get("type") == "blob" and TERMS.search(path) and ext in TEXT_EXT and "test.jsonl" not in path.lower() and size <= 4 * 1024 * 1024:
                selected.append(item)
        selected = sorted(selected, key=lambda x: (0 if Path(x["path"]).name.lower() in {"readme.md", "readme.txt"} else 1, x["path"]))[:5]
        ev["candidate_files"] = [{"path": x["path"], "size": x.get("size"), "sha": x.get("sha")} for x in selected]
        al72 = json.loads(AL72.read_text(encoding="utf-8"))
        roots = {w["candidate_root"] for w in al72.get("witnesses", [])}
        file_evidence = []
        for item in selected:
            url = f"https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/{revision}/{item['path']}"
            blob = get(url, 4 * 1024 * 1024)
            path = item["path"]
            summary = {"path": path, "declared_size": item.get("size"), "bytes": len(blob), "sha256": sha(blob), "top_keys": [], "rows": 0, "parse_errors": 0, "mapping_hits": 0, "root_hits": 0}
            text = blob.decode("utf-8", "replace")
            if Path(path).suffix.lower() in {".md", ".txt"}:
                summary["text_terms"] = {term: len(re.findall(term, text, re.I)) for term in ["source", "origin", "lineage", "ancestor", "generator", "model", "label", "split"]}
            else:
                rows = []
                if Path(path).suffix.lower() == ".jsonl":
                    for line in text.splitlines():
                        if not line.strip():
                            continue
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            summary["parse_errors"] += 1
                else:
                    try:
                        obj = json.loads(text)
                        rows = obj if isinstance(obj, list) else [obj]
                    except Exception:
                        summary["parse_errors"] += 1
                fields = Counter()
                for obj in rows:
                    if not isinstance(obj, dict):
                        continue
                    fields.update(obj.keys())
                    flat = json.dumps(obj, ensure_ascii=False)
                    if any(str(root) in flat for root in roots):
                        summary["root_hits"] += 1
                    if any(k in obj for k in ["ancestor", "ancestor_id", "origin", "source", "generator", "model", "label", "Video_id"]):
                        summary["mapping_hits"] += 1
                summary["rows"] = len(rows)
                summary["top_keys"] = sorted(fields)[:100]
            file_evidence.append(summary)
        ev.update(status="completed", selected_files=file_evidence,
                  root_witness_basis="AL72 witnesses only; no complete root set inferred",
                  conclusion="No verified visual-ancestor mapping is inferred from path names or aggregate fields; explicit fields remain schema evidence only.")
    except Exception as exc:
        ev.update(status="failed", error=repr(exc))
    ev.update(finished_at=now(), total_http_body_bytes_read=body)
    payload = json.dumps(ev, ensure_ascii=False, indent=2) + "\n"
    ev["record_sha256"] = sha(payload.encode())
    payload = json.dumps(ev, ensure_ascii=False, indent=2) + "\n"
    with OUT.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    print(json.dumps({"status": ev["status"], "record_sha256": sha(payload.encode()), "selected_files": len(ev.get("selected_files", [])), "error": ev.get("error")}, ensure_ascii=False))
    return 1 if ev["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
