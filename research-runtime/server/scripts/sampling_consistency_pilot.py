"""GPU development screen of paired sampling consistency; not a novelty claim.

Frozen DINO caches only; no final data. Six equal-size heads, five fixed seeds,
two generator holdouts, calibration-only checkpoint selection. No walltime cap.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score, log_loss
import torch
from torch import nn
from torch.nn import functional as F


ARMS = ['semantic_duplicate', 'time_std', 'time_delta', 'two_view_erm', 'paired_consistency', 'shuffled_consistency']
SEEDS = [17, 29, 43, 59, 71]


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(tmp, p)


def make_head():
    return nn.Sequential(nn.Linear(1536, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 1))


def stats(z):
    z = z.astype(np.float64)
    z /= np.maximum(np.linalg.norm(z, axis=-1, keepdims=True), 1e-12)
    return z.mean(0), np.abs(np.diff(z, axis=0)).mean(0), z.std(0)


def balanced_weights(rows):
    counts = Counter(r['group'] for r in rows)
    y = np.array([r['label_fake'] for r in rows])
    w = np.array([1 / counts[r['group']] for r in rows], dtype=np.float32)
    for label in (0, 1):
        w[y == label] *= len(y) / 2 / w[y == label].sum()
    return w


def auc(y, scores):
    n = int(y.sum())
    return float((rankdata(scores)[y == 1].sum() - n * (n + 1) / 2) / (n * (len(y) - n)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); started = time.monotonic()
    root = a.output; root.mkdir(parents=True, exist_ok=True)
    parent = a.base / 'runs/paired_dino_time_v1'
    cache = a.base / 'runs/time_matched_dino_v1'
    protocol = dict(scope='exposed one-real-source development pilot; formal training gate remains closed',
        script_sha256=sha(__file__), parent_manifest_sha256=sha(parent / 'manifest.json'),
        time_lock_sha256=sha(cache / 'lock.json'), arms=ARMS, seeds=SEEDS, holdouts=['ms', 'vc2'],
        model='1536 -> Linear256 -> GELU -> Dropout0.1 -> Linear1, all arms same parameter count',
        epochs=40, batch_size=1024, optimizer='AdamW lr=0.001 weight_decay=0.01',
        selection='minimum unweighted time-view calibration BCE over 40 epochs; earliest wins ties',
        standardization='fit only; for two-view arms mean/std fitted on both fit views',
        consistency='1.0 * class/ancestor weighted squared logit difference, alongside mean BCE of two views',
        shuffle='fixed within source/label fit-only permutation; no calibration/audit pairing shuffle',
        split='reuse frozen ancestor-proxy split; whole held generator excluded from fitting and calibration',
        semantic_control='duplicate semantic 768-vector to match input dimensions and head parameter count',
        std_control='concatenate mean and unordered per-coordinate frame standard deviation',
        final_access=False, formal_training_released=False, walltime_cap=None,
        torch=torch.__version__, numpy=np.__version__, device=torch.cuda.get_device_name(0),
        limitations=['Views differ in coverage and sampling, not only FPS.',
                    'Timing/source metadata still separate labels; this is a nuisance-response experiment.',
                    'Paired consistency and invariant representations have prior art; no novelty claim.',
                    'Same architecture does not imply equal training FLOPs: two-view arms process two views.',
                    'One real source and exposed proxy-grouped data cannot establish formal generalization.'])
    if (root / 'protocol.json').exists():
        assert read(root / 'protocol.json') == protocol
    else:
        save(root / 'protocol.json', protocol)
    for rel, digest in read(parent / 'artifact_hashes.json').items():
        assert sha(parent / rel) == digest
    rows = read(parent / 'manifest.json')
    records = {r['sample_id']: r for r in (read(f) for f in (cache / 'records').glob('*.json'))}
    native, timed, unordered, semantic = [], [], [], []
    for r in rows:
        q = records[r['sample_id']]
        assert q['sha256'] == r['sha256'] and sha(r['feature_file']) == r['feature_sha256']
        path = cache / q['time_feature_file']
        assert sha(path) == r['time_feature_sha256']
        mn, dn, _ = stats(np.load(r['feature_file'], allow_pickle=False)[4:12])
        mt, dt, st = stats(np.load(path, allow_pickle=False))
        native.append(np.r_[mn, dn]); timed.append(np.r_[mt, dt])
        unordered.append(np.r_[mt, st]); semantic.append(np.r_[mt, mt])
    arrays = {k: np.asarray(v, dtype=np.float32) for k, v in [('native', native), ('time', timed), ('std', unordered), ('semantic', semantic)]}
    del native, timed, unordered, semantic, records
    print('Validated cached features', len(rows), flush=True)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    torch.cuda.reset_peak_memory_stats()
    y = np.array([r['label_fake'] for r in rows], dtype=np.float32)
    source = np.array([r['source'] for r in rows]); role = np.array([r['role'] for r in rows])
    device_arrays = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
    target = torch.from_numpy(y).cuda()
    summaries = []
    for held in protocol['holdouts']:
        fit = np.flatnonzero((source != held) & (role == 'fit'))
        cal = np.flatnonzero((source != held) & (role == 'calibration'))
        audit = np.flatnonzero(((source == held) | (source == 'vript')) & (role == 'audit'))
        fit_groups = {rows[i]['group'] for i in fit}
        assert not fit_groups & {rows[i]['group'] for i in np.r_[cal, audit]}
        assert not {rows[i]['group'] for i in cal} & {rows[i]['group'] for i in audit}
        w = torch.from_numpy(balanced_weights([rows[i] for i in fit])).cuda()
        fit_t = torch.tensor(fit, device='cuda'); cal_t = torch.tensor(cal, device='cuda')
        audit_t = torch.tensor(audit, device='cuda')
        labels_fit = target[fit_t]
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            partner = fit.copy()
            for src in np.unique(source[fit]):
                ix = np.flatnonzero(source[fit] == src)
                partner[ix] = rng.permutation(fit[ix])
            partner_t = torch.tensor(partner, device='cuda')
            for arm in ARMS:
                name = held + '_' + str(seed) + '_' + arm
                folder = root / name
                if (folder / 'complete.json').exists():
                    for rel, digest in read(folder / 'hashes.json').items():
                        assert sha(folder / rel) == digest
                    summaries.append(read(folder / 'complete.json')); continue
                folder.mkdir(exist_ok=True)
                two = arm in ('two_view_erm', 'paired_consistency', 'shuffled_consistency')
                key = 'semantic' if arm == 'semantic_duplicate' else 'std' if arm == 'time_std' else 'time'
                x = device_arrays[key]
                scale_data = torch.cat([x[fit_t], device_arrays['native'][fit_t]], 0) if two else x[fit_t]
                mean = scale_data.mean(0); scale = scale_data.std(0, correction=0).clamp_min(1e-6)
                xt = (x - mean) / scale
                xn = (device_arrays['native'] - mean) / scale
                torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
                net = make_head().cuda()
                optimizer = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.01)
                # Separate generator gives every arm identical sample order per seed.
                generator = torch.Generator(device='cuda').manual_seed(seed)
                best = float('inf'); best_epoch = None; history = []
                train_start = time.monotonic()
                for epoch in range(40):
                    net.train(); order = torch.randperm(len(fit), device='cuda', generator=generator)
                    for batch in order.split(1024):
                        ids = fit_t[batch]; wt = w[batch]
                        optimizer.zero_grad(set_to_none=True)
                        # Concatenate views for equal dropout treatment and efficient GEMMs.
                        if two:
                            paired_ids = partner_t[batch] if arm == 'shuffled_consistency' else ids
                            logits = net(torch.cat([xt[ids], xn[paired_ids]], 0)).ravel()
                            lt, ln = logits.chunk(2)
                            loss = .5 * (F.binary_cross_entropy_with_logits(lt, target[ids], reduction='none') +
                                F.binary_cross_entropy_with_logits(ln, target[paired_ids], reduction='none'))
                            if arm != 'two_view_erm':
                                loss = loss + (lt - ln).square()
                        else:
                            lt = net(xt[ids]).ravel()
                            loss = F.binary_cross_entropy_with_logits(lt, target[ids], reduction='none')
                        loss = (loss * wt).mean(); loss.backward(); optimizer.step()
                    net.eval()
                    with torch.no_grad():
                        cal_logits = net(xt[cal_t]).ravel()
                        cal_loss = float(F.binary_cross_entropy_with_logits(cal_logits, target[cal_t]))
                    assert np.isfinite(cal_loss)
                    history.append(cal_loss)
                    if cal_loss < best:
                        best = cal_loss; best_epoch = epoch + 1
                        torch.save(dict(model={k: v.detach().cpu() for k, v in net.state_dict().items()},
                            mean=mean.cpu(), scale=scale.cpu(), epoch=best_epoch), folder / 'best.pt')
                checkpoint = torch.load(folder / 'best.pt', weights_only=True)
                net.load_state_dict(checkpoint['model']); net.eval()
                with torch.no_grad():
                    logits = net(xt[audit_t]).ravel().cpu().numpy()
                    native_logits = net(xn[audit_t]).ravel().cpu().numpy() if key == 'time' else None
                probabilities = expit(logits)
                np.savez_compressed(folder / 'predictions.npz', ids=audit, labels=y[audit], logits=logits,
                    native_logits=native_logits if native_logits is not None else np.array([]))
                summary = dict(held_generator=held, seed=seed, arm=arm, selected_epoch=best_epoch,
                    calibration_bce=best, auc=float(roc_auc_score(y[audit], probabilities)),
                    audit_bce=float(log_loss(y[audit], probabilities)), n=len(audit),
                    parameters=sum(p.numel() for p in net.parameters()), training_seconds=time.monotonic()-train_start,
                    view_probability_mae=float(np.abs(probabilities-expit(native_logits)).mean()) if native_logits is not None else None)
                save(folder / 'history.json', dict(calibration_bce=history))
                save(folder / 'complete.json', summary)
                save(folder / 'hashes.json', {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'hashes.json'})
                summaries.append(summary)
                save(root / 'progress.json', dict(completed=len(summaries), total=60, latest=summary, elapsed_seconds=time.monotonic()-started))
                print(json.dumps(summary), flush=True)
    # Pair the same ancestor draws across all arms, using seed-mean predictions.
    comparisons = []
    means = []
    for held in protocol['holdouts']:
        arm_scores = {}
        for arm in ARMS:
            loaded = [np.load(root / (held + '_' + str(seed) + '_' + arm) / 'predictions.npz') for seed in SEEDS]
            ids = loaded[0]['ids']; yy = loaded[0]['labels']
            assert all(np.array_equal(v['ids'], ids) for v in loaded)
            arm_scores[arm] = np.mean([expit(v['logits']) for v in loaded], axis=0)
            values = [r['auc'] for r in summaries if r['held_generator'] == held and r['arm'] == arm]
            means.append(dict(held_generator=held, arm=arm, seed_auc_mean=float(np.mean(values)),
                seed_auc_std=float(np.std(values, ddof=1)), seed_ensemble_auc=auc(yy, arm_scores[arm])))
        from verify_paired_time import cluster_draws
        draws = cluster_draws([rows[i] for i in ids], np.random.default_rng(20260917))
        pairs = [('paired_consistency', k) for k in ARMS if k != 'paired_consistency']
        samples = {b: [] for _, b in pairs}
        for _ in range(2000):
            ix = next(draws); primary = auc(yy[ix], arm_scores['paired_consistency'][ix])
            for _, base in pairs:
                samples[base].append(primary - auc(yy[ix], arm_scores[base][ix]))
        for _, base in pairs:
            differences = [next(r['auc'] for r in summaries if r['held_generator']==held and r['seed']==s and r['arm']=='paired_consistency') -
                next(r['auc'] for r in summaries if r['held_generator']==held and r['seed']==s and r['arm']==base) for s in SEEDS]
            comparisons.append(dict(held_generator=held, comparison='paired_consistency - ' + base,
                ensemble_delta=auc(yy, arm_scores['paired_consistency']) - auc(yy, arm_scores[base]),
                ensemble_paired_cluster_ci95=np.quantile(samples[base], [.025, .975]).tolist(),
                seed_paired_deltas=differences, seeds_positive=sum(v > 0 for v in differences)))
    report = dict(complete=True, total_fits=len(summaries), seconds=time.monotonic()-started,
        peak_gpu_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
        results=summaries, aggregates=means, comparisons=comparisons, formal_claim_released=False,
        uncertainty='CI conditions on five fitted heads averaged in probability space; seed deltas separately reported; no multiplicity correction',
        next_gate='Do not accept candidate unless it beats all controls in both holdouts and survives new-source/timing tests.')
    save(root / 'report.json', report)
    save(root / 'artifact_hashes.json', {p.name: sha(p) for p in root.iterdir() if p.is_file() and p.name != 'artifact_hashes.json'})
    print('COMPLETE ' + str(report['seconds']), flush=True)


if __name__ == '__main__':
    main()
