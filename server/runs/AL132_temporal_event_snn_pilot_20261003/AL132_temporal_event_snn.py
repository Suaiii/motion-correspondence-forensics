"""AL132 development pilot: paired temporal residual SNN screen.

The script is intentionally self-contained. It uses only an already present
development manifest and writes every input, split, source hash and result to
one immutable run directory. Its result is development evidence, not a paper
claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn


SEEDS = (11, 23, 37, 53)
NFRAMES = 16
SIZE = 64


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def auc(y: np.ndarray, score: np.ndarray) -> float:
    y = np.asarray(y, dtype=np.int64)
    score = np.asarray(score, dtype=np.float64)
    pos = score[y == 1]
    neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1)
    # Tie correction by average rank.
    vals, first, counts = np.unique(score[order], return_index=True, return_counts=True)
    for f, c in zip(first, counts):
        if c > 1:
            idx = order[f : f + c]
            ranks[idx] = (2 * (f + 1) + c - 1) / 2
    rpos = ranks[y == 1].sum()
    return float((rpos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def read_gray(path: Path, nframes: int = NFRAMES, size: int = SIZE) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 2:
        cap.release()
        raise RuntimeError(f"too few frames {path} total={total}")
    ids = np.linspace(0, total - 1, nframes).round().astype(int)
    frames = []
    for i in ids:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            raise RuntimeError(f"decode failure {path} frame={i}")
        frame = cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0)
    cap.release()
    return np.stack(frames, axis=0)


def event_features(frames: np.ndarray) -> np.ndarray:
    d = frames[1:] - frames[:-1]
    # Eight-by-eight spatial cells; signed and absolute residuals share input.
    h = d.shape[-1] // 8
    cells = d.reshape(d.shape[0], 8, h, 8, h).mean(axis=(2, 4))
    abs_cells = np.abs(d).reshape(d.shape[0], 8, h, 8, h).mean(axis=(2, 4))
    return np.concatenate([cells, abs_cells], axis=-1).astype(np.float32)


def select_manifest(manifest_path: Path, out_path: Path) -> list[dict]:
    rows = [json.loads(x) for x in manifest_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    # Deterministic, label-only selection is frozen before any model score.
    rows = sorted(rows, key=lambda r: (int(r.get("label_fake", -1)), r.get("sample_id", ""), r.get("sha256", "")))
    real = [r for r in rows if int(r.get("label_fake", -1)) == 0]
    fake = [r for r in rows if int(r.get("label_fake", -1)) == 1]
    if len(real) < 80 or len(fake) < 80:
        raise RuntimeError(f"need >=80 real/fake, got {len(real)}/{len(fake)}")
    chosen = sorted(real[:80] + fake[:80], key=lambda r: r["sample_id"])
    for r in chosen:
        r = r
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in chosen) + "\n", encoding="utf-8")
    return chosen


class DenseHead(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim * 2, 32), nn.GELU(), nn.Linear(32, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = torch.cat([x.mean(1), x.abs().mean(1)], -1)
        return self.net(z).squeeze(-1)


class VanillaLIF(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.inp = nn.Linear(dim, 32)
        self.head = nn.Linear(32, 1)
        self.alpha = 0.82
        self.theta = 0.25

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        u = torch.zeros(x.size(0), 32, device=x.device)
        states = []
        for t in range(x.size(1)):
            v = self.alpha * u + (1 - self.alpha) * torch.tanh(self.inp(x[:, t]))
            s = torch.sigmoid(12.0 * (v - self.theta))
            u = v - self.theta * s
            states.append(s)
        return self.head(torch.stack(states, 1).mean(1)).squeeze(-1)


class DualTimescaleResidualLIF(nn.Module):
    """Candidate: fast/slow soft LIF plus an unsupervised disagreement gate."""

    def __init__(self, dim: int):
        super().__init__()
        self.inp = nn.Linear(dim, 32)
        self.gate = nn.Linear(2, 1)
        # pooled fast spike, pooled slow spike, and the scalar disagreement gate
        self.head = nn.Sequential(nn.Linear(3, 24), nn.GELU(), nn.Linear(24, 1))
        self.alpha_fast = 0.55
        self.alpha_slow = 0.90
        self.theta = 0.25

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        uf = torch.zeros(x.size(0), 32, device=x.device)
        us = torch.zeros_like(uf)
        out = []
        for t in range(x.size(1)):
            z = torch.tanh(self.inp(x[:, t]))
            vf = self.alpha_fast * uf + (1 - self.alpha_fast) * z
            vs = self.alpha_slow * us + (1 - self.alpha_slow) * z
            sf = torch.sigmoid(12.0 * (vf - self.theta))
            ss = torch.sigmoid(12.0 * (vs - self.theta))
            uf = vf - self.theta * sf
            us = vs - self.theta * ss
            disagreement = torch.stack([sf.mean(-1), ss.mean(-1)], -1)
            g = torch.sigmoid(self.gate(disagreement))
            out.append(torch.cat([g * sf.mean(-1, keepdim=True), ss.mean(-1, keepdim=True), g], -1))
        return self.head(torch.stack(out, 1).mean(1)).squeeze(-1)


def transform(x: np.ndarray, kind: str, seed: int) -> np.ndarray:
    if kind == "normal":
        return x
    if kind == "static":
        return np.repeat(x[:1], x.shape[0], axis=0)
    rng = np.random.default_rng(seed)
    if kind == "shuffle":
        return x[rng.permutation(x.shape[0])]
    if kind == "reverse":
        return x[::-1]
    raise ValueError(kind)


def split_indices(rows: list[dict], seed: int) -> tuple[np.ndarray, np.ndarray]:
    groups = sorted({r.get("source_group", r.get("sample_id")) for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    cut = max(1, int(len(groups) * 0.7))
    fit = set(groups[:cut])
    train = np.array([i for i, r in enumerate(rows) if r.get("source_group", r.get("sample_id")) in fit])
    test = np.array([i for i, r in enumerate(rows) if r.get("source_group", r.get("sample_id")) not in fit])
    return train, test


def train_model(model: nn.Module, x: torch.Tensor, y: torch.Tensor, train: np.ndarray, seed: int) -> None:
    torch.manual_seed(seed)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    idx = torch.as_tensor(train, dtype=torch.long, device=x.device)
    for _ in range(18):
        perm = idx[torch.randperm(len(idx), device=x.device)]
        for b in perm.split(16):
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(x[b]), y[b])
            loss.backward()
            opt.step()


def fit_eval(features: np.ndarray, rows: list[dict], device: str, out: Path) -> dict:
    y_np = np.array([int(r["label_fake"]) for r in rows], dtype=np.float32)
    y = torch.tensor(y_np, dtype=torch.float32, device=device)
    x = torch.tensor(features, dtype=torch.float32, device=device)
    # Fit standardization on each training fold only; same transformed input for all models.
    all_results = []
    model_names = ["candidate_dual_lif", "vanilla_lif", "dense_head"]
    controls = ["normal", "static", "shuffle", "reverse"]
    for seed in SEEDS:
        train, test = split_indices(rows, seed)
        mu = x[train].mean((0, 1), keepdim=True)
        sd = x[train].std((0, 1), keepdim=True).clamp_min(1e-4)
        xn = (x - mu) / sd
        for name in model_names:
            torch.manual_seed(seed)
            model = {"candidate_dual_lif": DualTimescaleResidualLIF(x.shape[-1]), "vanilla_lif": VanillaLIF(x.shape[-1]), "dense_head": DenseHead(x.shape[-1])}[name].to(device)
            train_model(model, xn, y, train, seed)
            model.eval()
            with torch.no_grad():
                normal_score = torch.sigmoid(model(xn[test])).detach().cpu().numpy()
            rec = {"seed": seed, "model": name, "n_train": int(len(train)), "n_test": int(len(test)), "auc_normal": auc(y_np[test], normal_score)}
            for kind in controls[1:]:
                transformed = np.stack([transform(x[i], kind, seed + i) for i in test], axis=0)
                xt = (torch.tensor(transformed, dtype=torch.float32, device=device) - mu) / sd
                with torch.no_grad():
                    score = torch.sigmoid(model(xt)).detach().cpu().numpy()
                rec["auc_" + kind] = auc(y_np[test], score)
            all_results.append(rec)
    out.write_text(json.dumps({"rows": all_results}, indent=2), encoding="utf-8")
    return {"rows": all_results}


def summarize(result: dict, rows: list[dict], out: Path) -> dict:
    records = result["rows"]
    by_seed = {}
    for r in records:
        by_seed.setdefault(r["seed"], {})[r["model"]] = r
    paired = []
    for seed, vals in sorted(by_seed.items()):
        c = vals["candidate_dual_lif"]["auc_normal"]
        b = max(vals[n]["auc_normal"] for n in ("vanilla_lif", "dense_head"))
        paired.append({"seed": seed, "candidate_auc": c, "strongest_baseline_auc": b, "delta": c - b})
    deltas = np.array([r["delta"] for r in paired], dtype=float)
    # Small deterministic t interval is a descriptive pilot interval; the formal protocol uses cluster bootstrap later.
    mean = float(deltas.mean())
    if len(deltas) > 1:
        se = float(deltas.std(ddof=1) / np.sqrt(len(deltas)))
        ci = [mean - 2.776 * se, mean + 2.776 * se]
    else:
        ci = [float("nan"), float("nan")]
    source_counts = {}
    for r in rows:
        source_counts[r.get("source", "unknown")] = source_counts.get(r.get("source", "unknown"), 0) + 1
    fake_gens = sorted({r.get("generator") for r in rows if int(r.get("label_fake", -1)) == 1})
    summary = {"paired": paired, "mean_delta": mean, "descriptive_95_ci": ci, "positive_seed_count": int((deltas > 0).sum()), "n_seeds": len(deltas), "source_counts": source_counts, "fake_generators": fake_gens, "formal_gate": False, "status": "pilot_not_formal"}
    if mean >= 0.03 and ci[0] > 0 and int((deltas > 0).sum()) >= 4:
        summary["status"] = "conditional_screen_positive_needs_cluster_bootstrap_and_external_review"
    else:
        summary["status"] = "no_go_pilot_gate"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=Path("/root/autodl-tmp/cvpr27/data/mech4fps_manifest_fixed.jsonl"))
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=False)
    start = time.time()
    meta = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "argv": list(os.sys.argv), "torch": torch.__version__, "cuda": torch.cuda.is_available(), "device": args.device, "seeds": SEEDS, "nframes": NFRAMES, "size": SIZE}
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    selected_path = args.run_dir / "manifest.jsonl"
    rows = select_manifest(args.manifest, selected_path)
    rows_by_id = {r["sample_id"]: r for r in rows}
    feats = []
    errors = []
    for i, row in enumerate(rows):
        try:
            fpath = Path("/root/autodl-tmp/cvpr27/data") / row["path"]
            frames = read_gray(fpath)
            feats.append(event_features(frames))
        except Exception as exc:
            errors.append({"sample_id": row.get("sample_id"), "error": repr(exc)})
    if errors:
        (args.run_dir / "decode_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        raise RuntimeError(f"decode errors {len(errors)}; refusing silent imputation")
    x = np.stack(feats).astype(np.float32)
    np.save(args.run_dir / "features.npy", x)
    result = fit_eval(x, rows, args.device if torch.cuda.is_available() else "cpu", args.run_dir / "results.json")
    summary = summarize(result, rows, args.run_dir / "summary.json")
    hashes = {p.name: sha256_file(p) for p in args.run_dir.iterdir() if p.is_file()}
    hashes["source_script_sha256"] = sha256_file(Path(__file__))
    hashes["source_manifest_sha256"] = sha256_file(args.manifest)
    (args.run_dir / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["elapsed_seconds"] = time.time() - start
    meta["summary_status"] = summary["status"]
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
