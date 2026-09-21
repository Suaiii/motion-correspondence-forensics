"""AL76: prespecified filename-root sensitivity audit (metadata only)."""
import hashlib, json, re, urllib.request
from datetime import datetime
from pathlib import Path

URLS = {
    "train": "https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/main/data_splits/train.jsonl",
    "val": "https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/main/data_splits/val.jsonl",
}


def g1(s):
    m = re.fullmatch(r"([A-Za-z0-9_-]{11})_([0-9]+)_([0-9]+)to([0-9]+)\.mp4", s)
    return m.group(1) if m and int(m.group(4)) > int(m.group(3)) else None


def g2(s):
    p = (s[:-4] if s.endswith(".mp4") else s).split("_")
    if len(p) < 3 or not p[-2].isdigit() or "to" not in p[-1]:
        return None
    a, b = p[-1].split("to", 1)
    return "_".join(p[:-2]) if a.isdigit() and b.isdigit() and int(b) > int(a) else None


def g3(s):
    r = g2(s)
    return r if r and len(r) == 11 and re.fullmatch(r"[A-Za-z0-9_-]{11}", r) else None


def g4(s):
    r = g2(s)
    return r.split("_", 1)[0] if r else None


def main():
    data = {}
    receipts = []
    for split, url in URLS.items():
        req = urllib.request.Request(url, headers={"User-Agent": "cvpr27-planagent-root-sensitivity/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            blob = response.read(12 * 1024 * 1024)
            receipts.append({"split": split, "url": url, "status": response.status,
                             "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
        data[split] = [json.loads(line)["Video_id"] for line in blob.splitlines() if line.strip()]
    results = {}
    for name, fn in {"G1_AL72": g1, "G2_right_parse": g2,
                     "G3_right_parse_11char": g3, "G4_first_token_upper_bound": g4}.items():
        groups = {"train": {}, "val": {}}
        for split, ids in data.items():
            for item in ids:
                root = fn(item)
                if root:
                    groups[split].setdefault(root, []).append(item)
        shared = sorted(set(groups["train"]) & set(groups["val"]))
        results[name] = {
            "train_valid_rows": sum(map(len, groups["train"].values())),
            "val_valid_rows": sum(map(len, groups["val"].values())),
            "train_roots": len(groups["train"]), "val_roots": len(groups["val"]),
            "shared_roots": len(shared),
            "train_shared_rows": sum(len(groups["train"][r]) for r in shared),
            "val_shared_rows": sum(len(groups["val"][r]) for r in shared),
            "shared_root_digest": hashlib.sha256("\n".join(shared).encode()).hexdigest(),
            "witnesses": [{"root": r, "train": sorted(groups["train"][r])[:2],
                           "val": sorted(groups["val"][r])[:2]} for r in shared[:10]],
        }
    print(json.dumps({"task_id": "AL76", "ran_at": datetime.now().astimezone().isoformat(),
                      "receipts": receipts, "results": results,
                      "scope": "metadata-only; no test/media/model/server/GPU"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
