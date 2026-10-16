"""Real-vs-real control on existing frozen DINO features (CPU, read-only).

If 224-resized DINOv2 features of *real* clips predict native resolution,
frame rate or source collection, then format/source identity survives the
resize and any real-vs-fake score on these pools is confounded by it.
"""
import argparse
import json
import re
import sqlite3
from fractions import Fraction
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def feat(path):
    x = np.load(path).astype(np.float64)          # 8 x 768
    d = np.abs(np.diff(x, axis=0)).mean(0)
    return np.concatenate([x.mean(0), d])


def cv_auc(X, y, groups, seeds=(17, 29, 43)):
    aucs = []
    for s in seeds:
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=s)
        score = np.zeros(len(y))
        for tr, te in cv.split(X, y, groups):
            m = make_pipeline(StandardScaler(),
                              LogisticRegression(C=0.1, max_iter=3000))
            m.fit(X[tr], y[tr])
            score[te] = m.predict_proba(X[te])[:, 1]
        aucs.append(roc_auc_score(y, score))
    return round(float(np.mean(aucs)), 4), round(float(np.std(aucs)), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.catalog}?mode=ro", uri=True)
    meta = {r[0]: r[1:] for r in con.execute(
        "select sha256,width,height,average_fps,relative_path from assets")}
    rows = []
    for line in open(a.index):
        r = json.loads(line)
        m = meta.get(r["input_sha256"])
        if m is None:
            continue
        w, h, fps, rel = m
        stem = Path(rel).stem
        rows.append({"label": r["label"], "gen": r["generator"],
                     "role": r["selection_role"], "w": w, "h": h,
                     "fps": float(Fraction(fps)) if fps else np.nan,
                     "group": re.split(r"-Scene-", stem)[0],
                     "path": r["feature_path"]})
    results = {}

    def run(name, sub, target):
        y = np.array([target(r) for r in sub])
        keep = y >= 0
        sub = [r for r, k in zip(sub, keep) if k]
        y = y[keep]
        X = np.stack([feat(r["path"]) for r in sub])
        g = np.array([r["group"] for r in sub])
        auc = cv_auc(X, y, g)
        results[name] = {"n": int(len(y)), "n_pos": int(y.sum()),
                         "n_groups": int(len(set(g))),
                         "auc_mean_sd_3seeds": auc}
        print(name, results[name], flush=True)

    robo_real = [r for r in rows if r["gen"] == "real"]
    run("robovid_real_native720_vs_other", robo_real,
        lambda r: int(r["h"] == 720))
    run("robovid_real_fps_ge29_vs_le25.5", robo_real,
        lambda r: 1 if r["fps"] >= 29 else (0 if r["fps"] <= 25.5 else -1))
    aegis_real = [r for r in rows if r["gen"] in ("real_dvf", "real_youtube")]
    run("aegis_real_dvf_vs_youtube", aegis_real,
        lambda r: int(r["gen"] == "real_dvf"))
    aegis_fake = [r for r in rows if r["gen"] in ("kling", "sora")]
    run("aegis_fake_kling_vs_sora", aegis_fake,
        lambda r: int(r["gen"] == "kling"))
    aegis = [r for r in rows if r["role"] == "external_holdout"]
    run("aegis_real_vs_fake_within_pool_cv", aegis,
        lambda r: int(r["label"] == "fake"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "real_vs_real.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
