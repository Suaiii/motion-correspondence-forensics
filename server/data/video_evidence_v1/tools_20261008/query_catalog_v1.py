"""Emit filtered compact JSONL rows without loading the full PTS manifest.

Example: python query_catalog.py --catalog catalog.sqlite --package
AAGenvid_RoboVidSM_v02 --split train --variant clean --limit 10
Optional --full-record seeks directly into the unchanged source manifest.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    for field in ("package", "split", "variant", "label", "generator"):
        parser.add_argument("--" + field)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--full-record", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 0:
        parser.error("limit must be nonnegative")
    conn = sqlite3.connect(args.catalog.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    where, params = [], []
    for field in ("package", "split", "variant", "label", "generator"):
        value = getattr(args, field)
        if value is not None:
            where.append(field + " = ?")
            params.append(value)
    sql = "SELECT * FROM assets" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY relative_path"
    if args.limit is not None:
        sql += " LIMIT ?"
        params.append(args.limit)
    original = None
    try:
        if args.full_record:
            manifest = conn.execute("SELECT value FROM metadata WHERE key='source_manifest'").fetchone()[0]
            original = Path(manifest).open("rb")
        for row in conn.execute(sql, params):
            result = dict(row)
            if original:
                original.seek(result["manifest_byte_offset"])
                source = json.loads(original.readline())
                result = dict(source, local_path=source["path"], path=row["path"])
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    except BrokenPipeError:
        sys.stdout = open("/dev/null" if sys.platform != "win32" else "NUL", "w")
    finally:
        if original:
            original.close()
        conn.close()


if __name__ == "__main__":
    main()
