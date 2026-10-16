"""AL140: frozen DINOv2 trajectory with causal LIF head.

This pilot is independent of the raw frame-difference features used in
AL132/134/136/138. DINOv2 is frozen; the candidate learns only a causal LIF
readout over per-frame semantic velocity. Pair IDs are used only for the
group-disjoint split, never at inference.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time

import cv2
import numpy as np
import torch
from torch import nn

SEEDS = [11, 23, 37, 53, 71]
REPO = Path("/root/autodl-tmp/cvpr27/models/dinov2-7764ea0f912e53c92e82eb78a2a1631e92725fc8")
WEIGHTS = Path("/root/autodl-tmp/cvpr27/models/dinov2_vitb14_pretrain.pth")
DATA_ROOT = Path("/root/autodl-tmp/cvpr27/data")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pair_key(row: dict) -> str:
    field = "source_group" if int(row.get("label_fake", -1)) == 1 else "prompt_group"
    return (row.get(field) or "").split(":", 1)[-1]


def select_pairs(manifest: Path, out: Path) -> list[dict]:
    rows = [json.loads(x) for x in manifest.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    real = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 0}
    fake = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 1}
    keys = sorted(set(real) & set(fake))
    if len(keys) < 50:
        raise RuntimeError(f"need >=50 pairs, got {len(keys)}")
    chosen = []
    for key in keys:
        rr, ff = dict(real[key]), dict(fake[key])
        rr["pair_id"] = key
        ff["pair_id"] = key
        chosen.extend([rr, ff])
    chosen.sort(key=lambda r: (r["pair_id"], int(r["label_fake"])))
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in chosen) + "\n", encoding="utf-8")
    return chosen


def decode(row: dict) -> tuple[dict, np.ndarray | None, str | None]:
    try:
        path = DATA_ROOT / row["path"]
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError("open_failed")
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total < 8:
            cap.release()
            raise RuntimeError("too_few_frames")
        ids = np.linspace(0, total - 1, 8).round().astype(int)
        wanted = set(int(i) for i in ids)
        frames = []
        for j in range(int(ids[-1]) + 1):
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"decode_failed_{j}")
            if j in wanted:
                h, w = frame.shape[:2]
                side = min(h, w)
                frame = frame[(h - side) // 2:(h - side) // 2 + side, (w - side) // 2:(w - side) // 2 + side]
                frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
                frames.append(frame[:, :, ::-1].copy())
        cap.release()
        if len(frames) != 8:
            raise RuntimeError("frame_count_mismatch")
        return row, np.stack(frames).astype(np.uint8), None
    except Exception as exc:
        return row, None, repr(exc)


def split(rows: list[dict], seed: int) -> tuple[np.ndarray, np.ndarray]:
    keys = sorted({r["pair_id"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    cut = max(1, int(round(0.7 * len(keys))))
    fit = set(keys[:cut])
    train = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] in fit], dtype=int)
    test = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] not in fit], dtype=int)
    return train, test


def transform_semantic(x: np.ndarray, kind: str, seed: int) -> np.ndarray:
    if kind == "normal":
        return x
    if kind == "static":
        return np.repeat(x[:, :1], x.shape[1], axis=1)
    if kind == "reverse":
        return x[:, ::-1]
    if kind == "shuffle":
        out = x.copy()
        rng = np.random.default_rng(seed)
        for i in range(len(out)):
            out[i] = out[i, rng.permutation(out.shape[1])]
        return out
    raise ValueError(kind)


def velocity(x: np.ndarray) -> np.ndarray:
    return x[:, 1:] - x[:, :-1]


class DinoLIF(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.inp = nn.Linear(dim, 64)
        self.head = nn.Linear(64, 1)
        self.alpha = 0.82
        self.theta = 0.25

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        u = torch.zeros(x.shape[0], 64, device=x.device)
        states = []
        for t in range(x.shape[1]):
            z = torch.tanh(self.inp(x[:, t]))
            v = self.alpha * u + (1.0 - self.alpha) * z
            s = torch.sigmoid(12.0 * (v - self.theta))
            u = v - self.theta * s
            states.append(s)
        return self.head(torch.stack(states, 1).mean(1)).squeeze(-1)


class DenseVelocity(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim * 2, 64), nn.GELU(), nn.Linear(64, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([x.mean(1), x.abs().mean(1)], dim=-1)).squeeze(-1)


class DenseSemantic(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim, 64), nn.GELU(), nn.Linear(64, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x.mean(1)).squeeze(-1)


def train_model(model: nn.Module, x: torch.Tensor, y: torch.Tensor, train: np.ndarray, seed: int) -> None:
    torch.manual_seed(seed)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss = nn.BCEWithLogitsLoss()
    idx = torch.as_tensor(train, dtype=torch.long, device=x.device)
    for _ in range(18):
        perm = idx[torch.randperm(len(idx), device=x.device)]
        for b in perm.split(16):
            opt.zero_grad(set_to_none=True)
            z = loss(model(x[b]), y[b])
            z.backward()
            opt.step()


def metrics(model: nn.Module, sem: np.ndarray, vel: np.ndarray, mu: torch.Tensor, sd: torch.Tensor,
            test: np.ndarray, y: np.ndarray, device: str, seed: int, use_velocity: bool) -> dict:
    out = {}
    for kind in ("normal", "static", "shuffle", "reverse"):
        sem_k = transform_semantic(sem, kind, seed) if kind != "normal" else sem
        arr = velocity(sem_k) if use_velocity else sem_k
        arr = arr[test]
        xt = (torch.tensor(arr, dtype=torch.float32, device=device) - mu) / sd
        with torch.no_grad():
            p = torch.sigmoid(model(xt)).detach().cpu().numpy()
        out["auc_" + kind] = float(auc(y[test], p))
    return out


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
    vals, first, counts = np.unique(score[order], return_index=True, return_counts=True)
    for f, c in zip(first, counts):
        if c > 1:
            idx = order[f:f + c]
            ranks[idx] = (2 * (f + 1) + c - 1) / 2
    n1 = len(pos)
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * len(neg)))


def run(args: argparse.Namespace) -> None:
    args.run_dir.mkdir(parents=True, exist_ok=False)
    start = time.time()
    rows = select_pairs(args.manifest, args.run_dir / "manifest.jsonl")
    with ThreadPoolExecutor(max_workers=8) as pool:
        decoded = list(pool.map(decode, rows))
    good, errors = [], []
    for row, frames, err in decoded:
        if err:
            errors.append({"sample_id": row.get("sample_id"), "error": err})
        else:
            good.append((row, frames))
    if errors:
        (args.run_dir / "decode_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        raise RuntimeError(f"decode errors {len(errors)}")
    torch.set_num_threads(4)
    torch.manual_seed(20261004)
    model = torch.hub.load(str(REPO), "dinov2_vitb14", source="local", pretrained=False).cuda().eval()
    model.load_state_dict(torch.load(WEIGHTS, map_location="cpu", weights_only=True))
    mean = torch.tensor([0.485, 0.456, 0.406], device="cuda")[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225], device="cuda")[None, :, None, None]
    frame_features = []
    for j in range(0, len(good), 16):
        arr = np.concatenate([frames for _, frames in good[j:j + 16]], axis=0)
        xx = torch.from_numpy(arr).permute(0, 3, 1, 2).cuda().float() / 255.0
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            zz = model((xx - mean) / std).float().cpu().numpy().reshape(len(good[j:j + 16]), 8, 768)
        frame_features.extend(zz)
    features = np.asarray(frame_features, dtype=np.float32)
    np.save(args.run_dir / "features.npy", features)
    y_np = np.asarray([int(r["label_fake"]) for r, _ in good], dtype=np.float32)
    y = torch.tensor(y_np, dtype=torch.float32, device="cuda")
    sem = features / np.maximum(np.linalg.norm(features, axis=-1, keepdims=True), 1e-12)
    records, paired = [], []
    for seed in SEEDS:
        train, test = split(rows, seed)
        mu_sem = torch.tensor(sem[train].mean((0, 1), keepdims=True), device="cuda")
        sd_sem = torch.tensor(sem[train].std((0, 1), keepdims=True).clip(min=1e-4), device="cuda")
        v = velocity(sem)
        mu_v = torch.tensor(v[train].mean((0, 1), keepdims=True), device="cuda")
        sd_v = torch.tensor(v[train].std((0, 1), keepdims=True).clip(min=1e-4), device="cuda")
        sem_n = (torch.tensor(sem, device="cuda") - mu_sem) / sd_sem
        vel_n = (torch.tensor(v, device="cuda") - mu_v) / sd_v
        lif = DinoLIF(v.shape[-1]).cuda()
        train_model(lif, vel_n, y, train, seed)
        lif_m = metrics(lif, sem, v, mu_v, sd_v, test, y_np, "cuda", seed, True)
        rec_l = {"seed": seed, "model": "dino_velocity_lif", **lif_m}
        records.append(rec_l)
        dense_v = DenseVelocity(v.shape[-1]).cuda()
        train_model(dense_v, vel_n, y, train, seed)
        dense_vm = metrics(dense_v, sem, v, mu_v, sd_v, test, y_np, "cuda", seed, True)
        rec_d = {"seed": seed, "model": "dino_velocity_dense", **dense_vm}
        records.append(rec_d)
        dense_s = DenseSemantic(sem.shape[-1]).cuda()
        train_model(dense_s, sem_n, y, train, seed)
        dense_sm = metrics(dense_s, sem, v, mu_sem, sd_sem, test, y_np, "cuda", seed, False)
        rec_s = {"seed": seed, "model": "dino_semantic_dense", **dense_sm}
        records.append(rec_s)
        strongest = max(rec_d["auc_normal"], rec_s["auc_normal"])
        paired.append({"seed": seed, "candidate_auc": rec_l["auc_normal"], "strongest_baseline_auc": strongest, "delta": rec_l["auc_normal"] - strongest})
    (args.run_dir / "results.json").write_text(json.dumps({"rows": records}, indent=2), encoding="utf-8")
    ds = np.asarray([r["delta"] for r in paired], dtype=float)
    mean_delta = float(ds.mean())
    se = float(ds.std(ddof=1) / np.sqrt(len(ds)))
    ci = [mean_delta - 2.776 * se, mean_delta + 2.776 * se]
    summary = {"paired": paired, "mean_delta": mean_delta, "descriptive_95_ci": ci, "positive_seed_count": int((ds > 0).sum()), "n_seeds": len(ds), "pair_count": len({r["pair_id"] for r in rows}), "source_counts": {k: sum(r.get("source") == k for r in rows) for k in sorted({r.get("source") for r in rows})}, "status": "no_go_dino_snn_pair_pilot_gate", "formal_gate": False, "weights_sha256": sha(WEIGHTS), "repo_revision": subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {"finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "elapsed_seconds": time.time() - start, "torch": torch.__version__, "cuda": torch.cuda.is_available(), "device": "cuda:0", "seeds": SEEDS, "contract": "frozen DINOv2 per-frame semantic trajectory; causal LIF over velocity; pair-group split only"}
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    hashes = {p.name: sha(p) for p in args.run_dir.iterdir() if p.is_file()}
    hashes["source_script_sha256"] = sha(Path(__file__))
    hashes["source_manifest_sha256"] = sha(args.manifest)
    hashes["weights_sha256"] = sha(WEIGHTS)
    (args.run_dir / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    run(args)

