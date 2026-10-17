"""Metadata-only shortcut probe (CPU, read-only inputs).

Question: how well can container/timing metadata alone (no pixels) separate
real from generated clips in each existing data pool?  High AUROC means the
pool cannot support a claim that a detector learned generation evidence.

Inputs are opened read-only; outputs go only to --out.
"""
import argparse
import json
import sqlite3
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

FEATURES = ["fps", "frames", "duration", "width", "height", "aspect",
            "pixels", "file_size", "bitrate", "tb_den"]


def fnum(x):
    try:
        return float(Fraction(str(x)))
    except (ValueError, ZeroDivisionError, TypeError):
        return np.nan


def derive(fps, frames, width, height, size, tb):
    fps, frames = fnum(fps), fnum(frames)
    width, height, size = fnum(width), fnum(height), fnum(size)
    dur = frames / fps if fps and fps > 0 else np.nan
    tb_den = fnum(str(tb).split("/")[-1]) if tb else np.nan
    return {
        "fps": fps, "frames": frames, "duration": dur,
        "width": width, "height": height,
        "aspect": width / height if height else np.nan,
        "pixels": width * height, "file_size": size,
        "bitrate": size * 8 / dur if dur and dur > 0 else np.nan,
        "tb_den": tb_den,
    }


def load_v1(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute("select * from assets where variant='clean'"):
        d = derive(r["average_fps"], r["native_frame_count"], r["width"],
                   r["height"], r["file_size"], r["time_base"])
        d.update(package=r["package"], label=r["label"],
                 generator=r["generator"] or "real", source=r["source"],
                 group=r["clean_identity_group"] or r["asset_id"])
        rows.append(d)
    return rows


def load_ext(path):
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("status") != "qc_pass":
                continue
            p = r["ffprobe"]
            d = derive(p.get("avg_frame_rate"), p.get("nb_frames") or
                       p.get("frame_count_probed"), p.get("width"),
                       p.get("height"), r.get("file_size"), p.get("time_base"))
            d.update(package="AIGVDBench_ext", label=r["label"],
                     generator=r.get("generator") or "real",
                     source=r.get("source"),
                     group=r.get("source_video_id_candidate") or r["asset_id"])
            rows.append(d)
    return rows


def is_fake(label):
    return 0 if str(label).lower() in ("real", "0", "false") else 1


def univariate(X, y):
    out = {}
    for j, name in enumerate(FEATURES):
        col = X[:, j]
        ok = ~np.isnan(col)
        if ok.sum() < 10 or len(set(y[ok])) < 2:
            out[name] = None
            continue
        a = roc_auc_score(y[ok], col[ok])
        out[name] = round(max(a, 1 - a), 4)
    return out


def cv_gbdt(X, y, groups, seed=17):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    score = np.full(len(y), np.nan)
    for tr, te in cv.split(X, y, groups):
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=200,
                                           random_state=seed)
        m.fit(X[tr], y[tr])
        score[te] = m.predict_proba(X[te])[:, 1]
    return round(roc_auc_score(y, score), 4)


def probe(rows, name):
    y = np.array([is_fake(r["label"]) for r in rows])
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    groups = np.array([str(r["group"]) for r in rows])
    res = {"pool": name, "n": int(len(y)), "n_fake": int(y.sum()),
           "generators": dict(Counter(r["generator"] for r in rows)),
           "univariate_auc": univariate(X, y),
           "gbdt_all_meta_cv_auc": cv_gbdt(X, y, groups)}
    per_gen = {}
    for g in sorted({r["generator"] for r in rows if is_fake(r["label"])}):
        idx = np.array([(not is_fake(r["label"])) or r["generator"] == g
                        for r in rows])
        if idx.sum() < 40 or y[idx].sum() < 10:
            per_gen[g] = {"n_fake": int(y[idx].sum()), "auc": None}
            continue
        per_gen[g] = {"n_fake": int(y[idx].sum()),
                      "auc": cv_gbdt(X[idx], y[idx], groups[idx])}
    res["per_generator_gbdt_cv_auc"] = per_gen
    med = {}
    for lab in (0, 1):
        sub = X[y == lab]
        med["fake" if lab else "real"] = {
            f: (None if np.all(np.isnan(sub[:, j]))
                else round(float(np.nanmedian(sub[:, j])), 3))
            for j, f in enumerate(FEATURES)}
    res["medians"] = med
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1-catalog", required=True)
    ap.add_argument("--ext-manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    v1 = load_v1(a.v1_catalog)
    ext = load_ext(a.ext_manifest)
    pools = {}
    for pkg in sorted({r["package"] for r in v1}):
        pools[pkg] = [r for r in v1 if r["package"] == pkg]
    pools["AIGVDBench_ext"] = ext
    results = [probe(rows, k) for k, rows in pools.items()
               if len({is_fake(r["label"]) for r in rows}) == 2]
    (out / "results.json").write_text(json.dumps(results, indent=1))
    for r in results:
        print(json.dumps({k: r[k] for k in ("pool", "n", "n_fake",
                                            "generators",
                                            "gbdt_all_meta_cv_auc",
                                            "per_generator_gbdt_cv_auc",
                                            "univariate_auc")}))


if __name__ == "__main__":
    main()
