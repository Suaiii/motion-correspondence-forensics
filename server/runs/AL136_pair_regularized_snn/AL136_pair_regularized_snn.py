"""AL136: pair-group anti-content regularized causal LIF pilot.

Real and generated rows sharing a prompt suffix form a pre-registered pair.
Pair IDs are used only in the training loss; inference reads one video only.
The pair regularizer aligns hidden embeddings and forces paired logits to be
opposite, testing whether content can be removed without leaking labels.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

BASE = Path(__file__).resolve().parent.parent / "AL132_temporal_event_snn" / "AL132_temporal_event_snn.py"
_base_ns = {"__name__": "al132_base"}
exec(BASE.read_text(encoding="utf-8"), _base_ns)
globals().update({k: v for k, v in _base_ns.items() if not k.startswith("__")})


def pair_key(r: dict) -> str:
    """Return the frozen cross-label content key from the manifest contract.

    The real row stores the generation prompt in ``prompt_group`` while its
    matched fake row stores that same identifier in ``source_group``.  Using
    a single fallback order for both labels silently produced the wrong
    intersection for fake rows, so the label-specific fields are explicit.
    """
    label = int(r.get("label_fake", -1))
    field = "source_group" if label == 1 else "prompt_group"
    value = r.get(field) or ""
    return value.split(":", 1)[-1]


def select_pairs(manifest_path: Path, out_path: Path) -> list[dict]:
    rows = [json.loads(x) for x in manifest_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    real = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 0}
    fake = {pair_key(r): r for r in rows if int(r.get("label_fake", -1)) == 1}
    keys = sorted(set(real) & set(fake))
    if len(keys) < 50:
        raise RuntimeError(f"need >=50 paired prompt suffixes, got {len(keys)}")
    chosen = []
    for j, k in enumerate(keys):
        rr = dict(real[k]); ff = dict(fake[k])
        rr["pair_id"] = k; ff["pair_id"] = k
        chosen.extend([rr, ff])
    chosen.sort(key=lambda r: (r["pair_id"], int(r["label_fake"])))
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in chosen) + "\n", encoding="utf-8")
    return chosen


class PairRegLIF(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.inp = nn.Linear(dim, 32)
        self.head = nn.Linear(32, 1)
        self.embed = nn.Linear(32, 16)
        self.alpha = 0.82
        self.theta = 0.25

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        u = torch.zeros(x.size(0), 32, device=x.device)
        states = []
        for t in range(x.size(1)):
            z = torch.tanh(self.inp(x[:, t]))
            v = self.alpha * u + (1 - self.alpha) * z
            s = torch.sigmoid(12.0 * (v - self.theta))
            u = v - self.theta * s
            states.append(s)
        h = torch.stack(states, 1).mean(1)
        return self.head(h).squeeze(-1), self.embed(h)


def pair_split(rows: list[dict], seed: int) -> tuple[np.ndarray, np.ndarray]:
    keys = sorted({r["pair_id"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    cut = max(1, int(round(0.7 * len(keys))))
    fit = set(keys[:cut])
    train = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] in fit], dtype=int)
    test = np.asarray([i for i, r in enumerate(rows) if r["pair_id"] not in fit], dtype=int)
    return train, test


def train_pair(model: PairRegLIF, x: torch.Tensor, y: torch.Tensor, rows: list[dict], train: np.ndarray, seed: int, regularize: bool) -> None:
    torch.manual_seed(seed)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    bce = nn.BCEWithLogitsLoss()
    idx = torch.as_tensor(train, dtype=torch.long, device=x.device)
    pairs = {}
    for i in train:
        pairs.setdefault(rows[i]["pair_id"], []).append(int(i))
    pair_indices = [v for v in pairs.values() if len(v) == 2]
    for _ in range(22):
        opt.zero_grad(set_to_none=True)
        logits, emb = model(x[idx])
        loss = bce(logits, y[idx])
        if regularize:
            terms = []
            for ids in pair_indices:
                loc = torch.as_tensor([list(train).index(i) for i in ids], dtype=torch.long, device=x.device)
                # A pair has one real and one fake; anti-symmetric logits and aligned content embeddings.
                terms.append((logits[loc].sum()) ** 2 + 0.2 * ((emb[loc[0]] - emb[loc[1]]) ** 2).mean())
            if terms:
                loss = loss + 0.5 * torch.stack(terms).mean()
        loss.backward()
        opt.step()


def run(args: argparse.Namespace) -> None:
    args.run_dir.mkdir(parents=True, exist_ok=False)
    start = time.time()
    rows = select_pairs(args.manifest, args.run_dir / "manifest.jsonl")
    feats, errors = [], []
    for row in rows:
        try:
            feats.append(event_features(read_gray(Path("/root/autodl-tmp/cvpr27/data") / row["path"])))
        except Exception as exc:
            errors.append({"sample_id": row.get("sample_id"), "error": repr(exc)})
    if errors:
        (args.run_dir / "decode_errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
        raise RuntimeError(f"decode errors {len(errors)}")
    features = np.stack(feats).astype(np.float32)
    np.save(args.run_dir / "features.npy", features)
    y_np = np.asarray([int(r["label_fake"]) for r in rows], dtype=np.float32)
    y = torch.tensor(y_np, dtype=torch.float32, device=args.device)
    x0 = torch.tensor(features, dtype=torch.float32, device=args.device)
    records = []
    for seed in SEEDS:
        train, test = pair_split(rows, seed)
        mu = x0[train].mean((0, 1), keepdim=True)
        sd = x0[train].std((0, 1), keepdim=True).clamp_min(1e-4)
        x = (x0 - mu) / sd
        for name, reg in [("pair_reg_lif", True), ("vanilla_lif", False)]:
            torch.manual_seed(seed)
            model = PairRegLIF(x.shape[-1]).to(args.device)
            train_pair(model, x, y, rows, train, seed, reg)
            model.eval()
            with torch.no_grad():
                score = torch.sigmoid(model(x[test])[0]).detach().cpu().numpy()
            rec = {"seed": seed, "model": name, "n_train": int(len(train)), "n_test": int(len(test)), "auc_normal": auc(y_np[test], score)}
            for kind in ("static", "shuffle", "reverse"):
                transformed = np.stack([transform(features[i], kind, seed + i) for i in test], axis=0)
                xt = (torch.tensor(transformed, dtype=torch.float32, device=args.device) - mu) / sd
                with torch.no_grad():
                    sc = torch.sigmoid(model(xt)[0]).detach().cpu().numpy()
                rec["auc_" + kind] = auc(y_np[test], sc)
            records.append(rec)
    (args.run_dir / "results.json").write_text(json.dumps({"rows": records}, indent=2), encoding="utf-8")
    paired = []
    for seed in SEEDS:
        a = next(r for r in records if r["seed"] == seed and r["model"] == "pair_reg_lif")
        b = next(r for r in records if r["seed"] == seed and r["model"] == "vanilla_lif")
        paired.append({"seed": seed, "candidate_auc": a["auc_normal"], "baseline_auc": b["auc_normal"], "delta": a["auc_normal"] - b["auc_normal"]})
    ds = np.asarray([r["delta"] for r in paired], dtype=float); mean = float(ds.mean()); se = float(ds.std(ddof=1) / np.sqrt(len(ds))); ci = [mean - 2.776 * se, mean + 2.776 * se]
    summary = {"paired": paired, "mean_delta": mean, "descriptive_95_ci": ci, "positive_seed_count": int((ds > 0).sum()), "n_seeds": len(ds), "pair_count": len({r["pair_id"] for r in rows}), "source_counts": {k: sum(r.get("source") == k for r in rows) for k in sorted({r.get("source") for r in rows})}, "status": "no_go_pair_pilot_gate", "formal_gate": False}
    (args.run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {"finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "elapsed_seconds": time.time() - start, "torch": torch.__version__, "cuda": torch.cuda.is_available(), "device": args.device, "seeds": SEEDS, "pair_contract": "prompt_suffix real/fake exact pairs; pair id used only in training loss"}
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
