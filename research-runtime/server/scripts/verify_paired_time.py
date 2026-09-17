"""Replay frozen paired heads, cluster uncertainty and residual timing controls.

Only diagnostic timing heads are fitted. Main feature heads remain frozen.
All large inputs and outputs stay on the research server.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.special import expit
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def auc(y, p):
    n = int(y.sum())
    return float((rankdata(p)[y == 1].sum() - n * (n + 1) / 2) / (n * (len(y) - n)))


def cluster_draws(rows, rng):
    strata = defaultdict(lambda: defaultdict(list))
    for i, row in enumerate(rows):
        strata[(row['source'], row['label_fake'])][row['group']].append(i)
    groups = [list(s.values()) for s in strata.values()]
    while True:
        yield np.concatenate([np.concatenate([g[j] for j in rng.integers(len(g), size=len(g))]) for g in groups])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--time-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replicates', type=int, default=2000)
    a = parser.parse_args()
    start = time.monotonic()
    a.output.mkdir(parents=True, exist_ok=False)
    assert a.replicates >= 1000
    for rel, digest in read(a.root / 'artifact_hashes.json').items():
        assert sha(a.root / rel) == digest, rel
    protocol = read(a.root / 'protocol.json')
    assert sha(a.time_cache / 'lock.json') == protocol['time_cache_lock_sha256']
    assert read(a.time_cache / 'summary.json')['complete']
    rows = read(a.root / 'manifest.json')
    preds = read(a.root / 'predictions.json')
    results = read(a.root / 'results.json')['results']
    models = read(a.root / 'models.json')
    index = {r['sample_id']: i for i, r in enumerate(rows)}
    assert len(index) == len(rows)
    records = {r['sample_id']: r for r in (read(p) for p in (a.time_cache / 'records').glob('*.json'))}
    # Reconstruct the stored heads' exact input independently of training code.
    matrices = {arm: [] for arm in protocol['arms']}
    for row in rows:
        feature = Path(row['feature_file'])
        assert sha(feature) == row['feature_sha256']
        timed = records[row['sample_id']]
        assert timed['sha256'] == row['sha256']
        tp = a.time_cache / timed['time_feature_file']
        assert sha(tp) == row['time_feature_sha256'] == timed['time_feature_sha256']
        # Native frame intervals may vary. Read full PTS from original record.
        original = feature.parent.parent / 'records' / (feature.stem + '.json')
        assert sha(original) == row['record_sha256']
        native = read(original)
        for prefix, z, dt in [
            ('native_', np.load(feature, allow_pickle=False)[4:12].astype(np.float64), np.diff(native['sampling']['pts'][4:12])),
            ('time_', np.load(tp, allow_pickle=False).astype(np.float64), np.diff(timed['sampling']['pts']))
        ]:
            assert z.shape == (8, 768) and np.isfinite(z).all() and (dt > 0).all()
            z /= np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-12)
            delta = np.abs(np.diff(z, axis=0))
            mean = z.mean(0)
            matrices[prefix + 'semantic'].append(mean)
            matrices[prefix + 'delta'].append(np.r_[mean, delta.mean(0)])
            matrices[prefix + 'velocity'].append(np.r_[mean, (delta / dt[:, None]).mean(0)])
    matrices = {k: np.asarray(v, dtype=np.float32) for k, v in matrices.items()}
    print('Feature integrity and reconstruction complete', flush=True)
    replay = []
    comparisons = []
    probes = []
    probe_artifacts = []
    for held in protocol['holdouts']:
        arms = {}
        for arm in protocol['arms']:
            head = models[held + '/' + arm]
            # Preserve float32 sklearn transform rounding from original run.
            x = matrices[arm].copy()
            x -= np.asarray(head['mean'])
            x /= np.asarray(head['scale'])
            prob = expit((x @ np.asarray(head['coef']).T).ravel() + head['intercept'][0])
            for cohort in ('in_domain_audit', 'held_generator_audit'):
                stored = sorted([r for r in preds if r['held_generator'] == held and r['arm'] == arm and r['cohort'] == cohort], key=lambda r: r['sample_id'])
                ids = [index[r['sample_id']] for r in stored]
                y = np.array([r['label_fake'] for r in stored])
                old_p = np.array([r['prob_fake'] for r in stored])
                max_error = float(np.max(np.abs(prob[ids] - old_p)))
                assert max_error < 1e-6, (held, arm, max_error)
                expected = next(r for r in results if r['held_generator'] == held and r['arm'] == arm)['metrics'][cohort]
                assert abs(auc(y, old_p) - expected['auc']) < 1e-12
                replay.append(dict(held_generator=held, arm=arm, cohort=cohort, max_probability_error=max_error))
                if cohort == 'held_generator_audit':
                    arms[arm] = stored
        reference = arms['time_semantic']
        assert all([r['sample_id'] for r in value] == [r['sample_id'] for r in reference] for value in arms.values())
        y = np.array([r['label_fake'] for r in reference])
        scores = {arm: np.array([r['prob_fake'] for r in value]) for arm, value in arms.items()}
        contrasts = {
            'time_delta_minus_semantic': {'time_delta': 1, 'time_semantic': -1},
            'time_velocity_minus_semantic': {'time_velocity': 1, 'time_semantic': -1},
            'native_delta_minus_semantic': {'native_delta': 1, 'native_semantic': -1},
            'delta_gain_time_minus_native': {'time_delta': 1, 'time_semantic': -1, 'native_delta': -1, 'native_semantic': 1},
        }
        draws = cluster_draws(reference, np.random.default_rng(20260917))
        samples = {name: [] for name in contrasts}
        observed = {arm: auc(y, value) for arm, value in scores.items()}
        for _ in range(a.replicates):
            ix = next(draws)
            boot = {arm: auc(y[ix], value[ix]) for arm, value in scores.items()}
            for name, weights in contrasts.items():
                samples[name].append(sum(weights[k] * boot[k] for k in weights))
        for name, weights in contrasts.items():
            comparisons.append(dict(held_generator=held, comparison=name,
                delta=sum(weights[k] * observed[k] for k in weights),
                ci95=np.quantile(samples[name], [.025, .975]).tolist(),
                replicates=a.replicates, n=len(reference), groups=len({r['group'] for r in reference})))
        fit = [r for r in rows if r['source'] != held and r['role'] == 'fit']
        cal = [r for r in rows if r['source'] != held and r['role'] == 'calibration']
        assert not {r['group'] for r in fit} & {r['group'] for r in cal + reference}
        assert not {r['group'] for r in cal} & {r['group'] for r in reference}
        yf = np.array([r['label_fake'] for r in fit]); yc = np.array([r['label_fake'] for r in cal])
        multiplicity = Counter(r['group'] for r in fit)
        weights = np.array([1 / multiplicity[r['group']] for r in fit])
        for label in (0, 1):
            weights[yf == label] *= len(yf) / 2 / weights[yf == label].sum()
        for name, fields in [('native_interval', ['median_dt']), ('time_interval', ['time_median_dt']),
                             ('time_interval_and_jitter', ['time_median_dt', 'time_dt_std', 'time_max_timing_error'])]:
            def timing(items):
                return np.array([[np.log(max(r[f], 1e-9)) for f in fields] for r in items])
            xf = timing(fit); xc = timing(cal); xa = timing(reference)
            scaler = StandardScaler().fit(xf)
            best = None
            for c in protocol['C_grid']:
                model = LogisticRegression(C=c, max_iter=1000).fit(scaler.transform(xf), yf, sample_weight=weights)
                loss = log_loss(yc, model.predict_proba(scaler.transform(xc))[:, 1])
                if best is None or loss < best[0]:
                    best = loss, c, model
            loss, c, model = best
            p = model.predict_proba(scaler.transform(xa))[:, 1]
            probes.append(dict(held_generator=held, probe=name, auc=roc_auc_score(y, p), selected_C=c,
                calibration_bce=loss, selected_converged=bool(model.n_iter_.max() < 1000),
                source_medians={src: {f: float(np.median([r[f] for r in rows if r['source'] == src])) for f in fields} for src in ('vript', 'ms', 'vc2')}))
            probe_artifacts.append(dict(held_generator=held, probe=name, fields=fields,
                mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(), coef=model.coef_.tolist(), intercept=model.intercept_.tolist(),
                sample_ids=[r['sample_id'] for r in reference], probabilities=p.tolist()))
        print('Completed holdout', held, flush=True)
    report = dict(status='pass', script_sha256=sha(__file__), parent_artifact_index_sha256=sha(a.root / 'artifact_hashes.json'),
        seconds=time.monotonic() - start, replay=replay, comparisons=comparisons, timing_probes=probes,
        bootstrap='paired source/label-stratified ancestor-proxy cluster percentile bootstrap; fixed trained heads',
        seed=20260917, main_heads_refitted=False, formal_claim_released=False,
        limits=['One real source, exposed development data and unverified ancestry proxies.',
                'Intervals are conditional on frozen heads; no training-seed uncertainty or multiplicity correction.',
                'Available timing information does not prove a feature classifier uses it.',
                'Nearest-frame time grids can retain source-dependent intervals and jitter.'])
    save(a.output / 'report.json', report)
    save(a.output / 'timing_models_predictions.json', probe_artifacts)
    save(a.output / 'artifact_hashes.json', {p.name: sha(p) for p in a.output.iterdir() if p.is_file()})
    print(json.dumps({k: report[k] for k in ('status', 'seconds', 'comparisons', 'timing_probes')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
