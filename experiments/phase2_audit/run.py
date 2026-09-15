"""Bounded CPU audit of existing feature evidence; never changes old artifacts."""
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import sklearn
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
CFG = Path(__file__).with_name('protocol.json')
OUT = ROOT / 'research-runs/phase2_evidence_audit_20260914'
LEGACY = ROOT / 'research-runs/alignment_gate_v1'
EXTERNAL = ROOT / 'research-runs/comgenvid_videos_20260914/correspondence_features_150.jsonl'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def auc(y, s):
    pos = y == 1
    n = int(pos.sum())
    if n == 0 or n == len(y):
        raise ValueError('AUROC requires both labels')
    return float((rankdata(s)[pos].sum() - n * (n + 1) / 2) / (n * (len(y) - n)))


def matrix(rows, arms):
    x = np.array([np.concatenate([r['features'][a] for a in arms]) for r in rows])
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite features')
    return x


def estimator(c):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=3000, random_state=17))


def cluster_draw(rows, rng):
    strata = defaultdict(lambda: defaultdict(list))
    for i, r in enumerate(rows):
        strata[(r['source'], r['label_fake'])][r['group_id']].append(i)
    selected = []
    for groups in strata.values():
        values = list(groups.values())
        for j in rng.integers(0, len(values), len(values)):
            selected.extend(values[j])
    return np.array(selected)


def shuffle_within_source(rows, rng):
    strata = defaultdict(list)
    for i, r in enumerate(rows):
        strata[(r['source'], r['label_fake'])].append(i)
    order = np.arange(len(rows))
    for indices in strata.values():
        order[indices] = rng.permutation(indices)
    return order


def main():
    start = time.monotonic()
    cfg = read(CFG)
    if OUT.exists():
        raise FileExistsError('Preserve existing run; choose a new version explicitly')
    OUT.mkdir(parents=True)
    def budget():
        if time.monotonic() - start > cfg['budget']['max_wall_seconds']:
            raise TimeoutError('CPU diagnostic budget exceeded')
    inputs = [CFG, Path(__file__), LEGACY/'probes.json', LEGACY/'manifest.json', LEGACY/'protocol.json', EXTERNAL]
    input_hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    (OUT/'input_lock.json').write_text(json.dumps(input_hashes, indent=2), encoding='utf-8')
    manifest = read(LEGACY/'manifest.json')
    features = defaultdict(dict)
    for r in read(LEGACY/'probes.json')['predictions']:
        if r['condition'] == 'clean':
            features[r['sample_id']][r['probe']] = r['features']
    rows = [{**m, 'features': features[m['sample_id']]} for m in manifest]
    splits = {role: [r for r in rows if r['role'] == role] for role in ['fit', 'calibration', 'audit']}
    external = []
    for line in EXTERNAL.read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        match = re.fullmatch(r'(.+)_\d+_\d+\.mp4', r['filename']) if r['source_model'] == 'MSVD' else None
        external.append({**r, 'sample_id': r['source_model']+':'+r['filename'],
                         'source': r['source_model'], 'group_id': r['source_model']+':'+(match[1] if match else r['filename'])})
    assert len({r['sha256'] for r in external}) == len(external)
    assert not ({r['sha256'] for r in external} & {r['sha256'] for r in rows})
    for a, b in [('fit', 'calibration'), ('fit', 'audit'), ('calibration', 'audit')]:
        assert not ({r['group_id'] for r in splits[a]} & {r['group_id'] for r in splits[b]})
    assert read(LEGACY/'protocol.json')['sampling'].items() >= cfg['sampling'].items()
    fit, cal = splits['fit'], splits['calibration']
    yf, yc = [np.array([r['label_fake'] for r in rr]) for rr in [fit, cal]]
    cohorts = {'audit': splits['audit'], 'external': external}
    for source in ['Sora', 'VEO3']:
        cohorts['external_'+source] = [r for r in external if r['source'] in ['MSVD', source]]
    scores, models, selections = {}, {}, {}
    for arm, columns in cfg['arms'].items():
        budget()
        x, xc = matrix(fit, columns), matrix(cal, columns)
        trials = []
        for c in cfg['C_grid']:
            model = estimator(c).fit(x, yf)
            trials.append({'C': c, 'calibration_auc': auc(yc, model.predict_proba(xc)[:, 1])})
        best = max(trials, key=lambda t: t['calibration_auc'])
        model = estimator(best['C']).fit(x, yf)
        models[arm], selections[arm] = model, {'selected': best, 'trials': trials, 'input_features': x.shape[1], 'linear_parameters': x.shape[1]+1}
        for name, rr in cohorts.items():
            scores.setdefault(name, {})[arm] = model.predict_proba(matrix(rr, columns))[:, 1]
    results = {}
    for name, rr in cohorts.items():
        y = np.array([r['label_fake'] for r in rr])
        point = {a: auc(y, s) for a, s in scores[name].items()}
        boots = defaultdict(list)
        rng = np.random.default_rng(cfg['seed'])
        for _ in range(cfg['bootstrap_replicates']):
            budget()
            ix = cluster_draw(rr, rng)
            aa = {a: auc(y[ix], s[ix]) for a, s in scores[name].items()}
            for a, val in aa.items():
                boots[a].append(val)
                if a != 'fusion':
                    boots['fusion_minus_'+a].append(aa['fusion']-val)
        results[name] = {'n': len(rr), 'source_counts': dict(Counter(r['source'] for r in rr)),
                         'parent_clusters': len({r['group_id'] for r in rr}), 'auc': point,
                         'cluster_bootstrap_ci95': {a: np.quantile(v, [.025, .975]).tolist() for a, v in boots.items()}}
    # This corrects the original global shuffle that also destroyed label/source information.
    rng = np.random.default_rng(cfg['seed'])
    audit = splits['audit']
    ya = np.array([r['label_fake'] for r in audit])
    fc, ff, ac, af = [matrix(rr, [a]) for rr, a in [(fit,'correct'),(fit,'fractional'),(audit,'correct'),(audit,'fractional')]]
    permutation = defaultdict(list)
    for _ in range(cfg['permutations']):
        budget()
        it, ia = shuffle_within_source(fit, rng), shuffle_within_source(audit, rng)
        model = estimator(selections['fusion']['selected']['C']).fit(np.c_[fc, ff[it]], yf)
        permutation['fit_shuffle_only'].append(auc(ya, model.predict_proba(np.c_[ac, af])[:,1]))
        permutation['fit_and_audit_shuffle'].append(auc(ya, model.predict_proba(np.c_[ac, af[ia]])[:,1]))
    target = results['audit']['auc']['fusion']
    perm_report = {k: {'mean': float(np.mean(v)), 'sd': float(np.std(v, ddof=1)),
                      'quantile95': np.quantile(v, [.025,.975]).tolist(),
                      'fraction_at_least_matched': (1+sum(t >= target for t in v))/(1+len(v)), 'values': v}
                   for k, v in permutation.items()}
    payload = {'status': 'completed_retrospective_diagnostic', 'protocol': cfg,
               'selection': selections, 'results': results, 'source_conditional_shuffle': perm_report,
               'environment': {'numpy': np.__version__, 'sklearn': sklearn.__version__},
               'wall_seconds': time.monotonic()-start}
    (OUT/'results.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    predictions = [{'cohort': name, 'sample_id': r['sample_id'], 'group_id': r['group_id'],
                    'source': r['source'], 'label_fake': r['label_fake'],
                    'scores': {a: float(s[i]) for a,s in scores[name].items()}}
                   for name, rr in cohorts.items() for i,r in enumerate(rr)]
    (OUT/'predictions.json').write_text(json.dumps(predictions, indent=2), encoding='utf-8')
    state = {a: {'C': selections[a]['selected']['C'], 'mean': m[0].mean_.tolist(), 'scale': m[0].scale_.tolist(),
                 'coef': m[1].coef_.tolist(), 'intercept': m[1].intercept_.tolist()} for a,m in models.items()}
    (OUT/'models.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    assert input_hashes == {str(p.relative_to(ROOT)): digest(p) for p in inputs}, 'Inputs changed during run'
    hashes = {p.name: digest(p) for p in OUT.iterdir() if p.is_file()}
    (OUT/'artifact_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(json.dumps({'results': results, 'shuffle': {k:{kk:vv for kk,vv in v.items() if kk!='values'} for k,v in perm_report.items()}, 'wall_seconds':payload['wall_seconds']}, indent=2))


if __name__ == '__main__':
    main()
