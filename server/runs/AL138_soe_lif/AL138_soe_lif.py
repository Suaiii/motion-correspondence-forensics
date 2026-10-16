"""AL138: second-order event (SOE) causal LIF pilot.

The representation applies a causal temporal difference to the existing
frame-difference event tensor. This directly tests whether AL136's static
control failure can be removed without using pair IDs at inference.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

BASE = Path(__file__).resolve().parent.parent / "AL132_temporal_event_snn" / "AL132_temporal_event_snn.py"
_base_ns = {"__name__": "al132_base"}
exec(BASE.read_text(encoding="utf-8"), _base_ns)
globals().update({k: v for k, v in _base_ns.items() if not k.startswith("__")})

SEEDS = [11, 23, 37, 53, 71]


def pair_key(r: dict) -> str:
    label = int(r.get("label_fake", -1))
    field = "source_group" if label == 1 else "prompt_group"
    return (r.get(field) or "").split(":", 1)[-1]


def select_pairs(manifest_path: Path, out_path: Path) -> list[dict]:
    rows = [json.loads(x) for x in manifest_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    real = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 0}
    fake = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 1}
    keys = sorted(set(real) & set(fake))
    if len(keys) < 50:
        raise RuntimeError(f"need >=50 paired suffixes, got {len(keys)}")
    chosen = []
    for key in keys:
        rr, ff = dict(real[key]), dict(fake[key])
        rr["pair_id"] = key
        ff["pair_id"] = key
        chosen.extend([rr, ff])
    chosen.sort(key=lambda r: (r["pair_id"], int(r["label_fake"])))
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in chosen) + "\n", encoding="utf-8")
    return chosen


def pair_split(rows: list[dict], seed: int) -> tuple[np.ndarray, np.ndarray]:
    keys = sorted({r["pair_id"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    cut = max(1, int(round(0.7 * len(keys))))
    fit = set(keys[:cut])
    train = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] in fit], dtype=int)
    test = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] not in fit], dtype=int)
    return train, test


def second_order(feat: np.ndarray) -> np.ndarray:
    out = np.zeros_like(feat)
    out[1:] = feat[1:] - feat[:-1]
    return out


class SecondOrderLIF(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.inp = nn.Linear(dim, 32)
        self.head = nn.Linear(32, 1)
        self.alpha = 0.82
        self.theta = 0.25

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        u = torch.zeros(x.size(0), 32, device=x.device)
        prev = torch.zeros_like(x[:, 0])
        states = []
        for t in range(x.size(1)):
            z_in = x[:, t] - prev
            prev = x[:, t]
            z = torch.tanh(self.inp(z_in))
            v = self.alpha * u + (1 - self.alpha) * z
            s = torch.sigmoid(12.0 * (v - self.theta))
            u = v - self.theta * s
            states.append(s)
        return self.head(torch.stack(states, 1).mean(1)).squeeze(-1)


def train_model(model: nn.Module, x: torch.Tensor, y: torch.Tensor, train: np.ndarray, seed: int) -> None:
    torch.manual_seed(seed)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    idx = torch.as_tensor(train, dtype=torch.long, device=x.device)
    for _ in range(20):
        perm = idx[torch.randperm(len(idx), device=x.device)]
        for b in perm.split(16):
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(x[b]), y[b])
            loss.backward()
            opt.step()


def evaluate(model: nn.Module, raw: np.ndarray, second: np.ndarray, mu: torch.Tensor, sd: torch.Tensor,
             test: np.ndarray, y_np: np.ndarray, device: str, use_second: bool, seed: int) -> dict:
    base = second if use_second else raw
    normal = []
    for kind in ("normal", "static", "shuffle", "reverse"):
        transformed = np.stack([transform(base[i], kind, seed + int(i)) for i in test], axis=0) if kind != "normal" else base[test]
        xt = (torch.tensor(transformed, dtype=torch.float32, device=device) - mu) / sd
        with torch.no_grad():
            score = torch.sigmoid(model(xt)).detach().cpu().numpy()
        normal.append((kind, auc(y_np[test], score)))
    return dict(normal)


def run(args: argparse.Namespace) -> None:
    args.run_dir.mkdir(parents=True, exist_ok=False)
    start = time.time()
    rows = select_pairs(args.manifest, args.run_dir / "manifest.jsonl")
    feats, errors = [], []
    data_root = Path("/root/autodl-tmp/cvpr27/data")
    for row in rows:
        try:
            feats.append(event_features(read_gray(data_root / row["path"])))
        except Exception as exc:
            errors.append({"sample_id": row.get("sample_id"), "error": repr(exc)})
    if errors:
        (args.run_dir / "decode_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        raise RuntimeError(f"decode errors {len(errors)}")
    raw = np.stack(feats).astype(np.float32)
    second = np.stack([second_order(x) for x in raw]).astype(np.float32)
    np.save(args.run_dir / "features.npy", raw)
    np.save(args.run_dir / "second_order_features.npy", second)
    y_np = np.asarray([int(r["label_fake"]) for r in rows], dtype=np.float32)
    y = torch.tensor(y_np, dtype=torch.float32, device=args.device)
    raw_t = torch.tensor(raw, dtype=torch.float32, device=args.device)
    second_t = torch.tensor(second, dtype=torch.float32, device=args.device)
    records = []
    paired = []
    for seed in SEEDS:
        train, test = pair_split(rows, seed)
        mu_raw = raw_t[train].mean((0, 1), keepdim=True)
        sd_raw = raw_t[train].std((0, 1), keepdim=True).clamp_min(1e-4)
        mu_second = second_t[train].mean((0, 1), keepdim=True)
        sd_second = second_t[train].std((0, 1), keepdim=True).clamp_min(1e-4)
        raw_n = (raw_t - mu_raw) / sd_raw
        second_n = (second_t - mu_second) / sd_second
        base_model = VanillaLIF(raw.shape[-1]).to(args.device)
        train_model(base_model, raw_n, y, train, seed)
        base_metrics = evaluate(base_model, raw, second, mu_raw, sd_raw, test, y_np, args.device, False, seed)
        base_rec = {"seed": seed, "model": "vanilla_raw", "use_second": False, "auc_normal": base_metrics["normal"], "auc_static": base_metrics["static"], "auc_shuffle": base_metrics["shuffle"], "auc_reverse": base_metrics["reverse"], "n_train": int(len(train)), "n_test": int(len(test))}
        records.append(base_rec)
        second_base = VanillaLIF(second.shape[-1]).to(args.device)
        train_model(second_base, second_n, y, train, seed)
        sb_metrics = evaluate(second_base, raw, second, mu_second, sd_second, test, y_np, args.device, True, seed)
        sb_rec = {"seed": seed, "model": "vanilla_second", "use_second": True, "auc_normal": sb_metrics["normal"], "auc_static": sb_metrics["static"], "auc_shuffle": sb_metrics["shuffle"], "auc_reverse": sb_metrics["reverse"], "n_train": int(len(train)), "n_test": int(len(test))}
        records.append(sb_rec)
        candidate = SecondOrderLIF(second.shape[-1]).to(args.device)
        train_model(candidate, second_n, y, train, seed)
        cand_metrics = evaluate(candidate, raw, second, mu_second, sd_second, test, y_np, args.device, True, seed)
        cand_rec = {"seed": seed, "model": "soe_lif", "use_second": True, "auc_normal": cand_metrics["normal"], "auc_static": cand_metrics["static"], "auc_shuffle": cand_metrics["shuffle"], "auc_reverse": cand_metrics["reverse"], "n_train": int(len(train)), "n_test": int(len(test))}
        records.append(cand_rec)
        strongest = max(base_rec["auc_normal"], sb_rec["auc_normal"])
        paired.append({"seed": seed, "candidate_auc": cand_rec["auc_normal"], "strongest_baseline_auc": strongest, "delta": cand_rec["auc_normal"] - strongest})
    (args.run_dir / "results.json").write_text(json.dumps({"rows": records}, indent=2), encoding="utf-8")
    ds = np.asarray([r["delta"] for r in paired], dtype=float)
    mean = float(ds.mean())
    se = float(ds.std(ddof=1) / np.sqrt(len(ds)))
    ci = [mean - 2.776 * se, mean + 2.776 * se]
    summary = {"paired": paired, "mean_delta": mean, "descriptive_95_ci": ci, "positive_seed_count": int((ds > 0).sum()), "n_seeds": len(ds), "pair_count": len({r["pair_id"] for r in rows}), "source_counts": {k: sum(r.get("source") == k for r in rows) for k in sorted({r.get("source") for r in rows})}, "status": "no_go_soe_pair_pilot_gate", "formal_gate": False}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {"finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "elapsed_seconds": time.time() - start, "torch": torch.__version__, "cuda": torch.cuda.is_available(), "device": args.device, "seeds": SEEDS, "contract": "second-order causal difference of 15-step event tensor; pair-group split only for evaluation"}
    (args.run_dir / "launch_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    hashes = {p.name: sha256_file(p) for p in args.run_dir.iterdir() if p.is_file()}
    hashes["source_script_sha256"] = sha256_file(Path(__file__))
    hashes["base_script_sha256"] = sha256_file(BASE)
    hashes["source_manifest_sha256"] = sha256_file(args.manifest)
    (args.run_dir / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    run(args)

