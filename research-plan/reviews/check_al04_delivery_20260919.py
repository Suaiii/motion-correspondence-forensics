"""Read the frozen AL04 delivery and recompute certificates, without rerunning LPs."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '2'
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN = SOURCE / 'research-runs/algorithm_search_20260918'
COMMIT = '29373fa'

def sha(value):
    return hashlib.sha256(value).hexdigest()

def projections(g):
    return np.stack((g.sum(axis=2), g.sum(axis=0), g.sum(axis=1)))

manifest = json.loads((RUN / 'AL04_artifact_manifest.json').read_text(encoding='utf-8'))
validation = json.loads((RUN / 'AL04_validation.json').read_text(encoding='utf-8'))
freeze = json.loads((RUN / 'AL04_freeze.json').read_text(encoding='utf-8'))
cases = json.loads((RUN / 'AL04_cases.json').read_text(encoding='utf-8'))['cases']
assert len(cases) == len(validation['rows'])
assert len({c['id'] for c in cases}) == len(cases)
rows = {row['id']: row for row in validation['rows']}
file_checks = []
for entry in manifest['files']:
    raw = (SOURCE / entry['path']).read_bytes()
    committed = subprocess.check_output(['git', 'show', COMMIT + ':' + entry['path']], cwd=SOURCE)
    assert sha(raw) == sha(committed) == entry['sha256']
    assert len(raw) == entry['bytes']
    file_checks.append({'path': entry['path'], 'sha256': sha(raw), 'disk_and_commit_match': True})
for path, digest in freeze['files'].items():
    committed = subprocess.check_output(['git', 'show', validation['git_revision'] + ':' + path], cwd=SOURCE)
    assert sha(committed) == digest == sha((SOURCE / path).read_bytes())
assert datetime.fromisoformat(freeze['frozen_at_utc']) < datetime.fromisoformat(validation['observed_at_utc'])
subprocess.check_call(['git', 'merge-base', '--is-ancestor', validation['git_revision'], COMMIT], cwd=SOURCE)
errors = {'objective': 0., 'single_masses': 0., 'joint_witness': 0., 'ordinary_tensor': 0., 'complete_pair_law': 0.}
counts = {'reference_rows': 0, 'coverage_rejections': 0, 'information_rows': 0, 'ordinary_baselines': 0}
certificates = []
for case in cases:
    raw = dict(case)
    digest = raw.pop('input_record_sha256')
    assert sha(json.dumps(raw, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) == digest
    row = rows[case['id']]
    assert row['input_sha256'] == digest
    if case['kind'] == 'HJ':
        q = np.asarray(case['q'])
        m = q.shape[1]
        if case['expected'] == 'reject':
            assert row['distance'] is None and not row['reference_called']
            assert row['domain'] == case['domain_reason']
            counts['coverage_rejections'] += 1
            continue
        counts['reference_rows'] += 1
        g = np.asarray(row['fitted_gamma'])
        assert g.min() >= -1e-9
        errors['objective'] = max(errors['objective'], abs(abs(projections(g)-q).sum()/3-row['distance']))
        errors['single_masses'] = max(errors['single_masses'], *(abs(g.sum(axes)-1/m).max() for axes in ((1,2),(0,2),(0,1))))
        if 'witness' in case:
            witness = np.asarray(case['witness'])
            assert witness.min() >= 0
            errors['joint_witness'] = max(errors['joint_witness'], abs(projections(witness)-q).max())
        if case['expected'] == 'positive':
            violation = np.trace(q[0]) + np.trace(q[1]) + 1 - np.trace(q[2]) - 2
            lower = 2*violation/3
            assert violation > 0 and row['distance'] >= lower-1e-8
            assert abs(lower-case['distance_lower_bound']) < 1e-12
            certificates.append({'id': case['id'], 'event_bound': float(lower), 'reported_distance': row['distance']})
    elif case['kind'] == 'information_law':
        counts['information_rows'] += 1
        a, b = map(np.asarray, case['probabilities'])
        states = np.asarray(case['states'])
        atoms = np.array([[x[0],x[1],x[1],x[2],x[0],x[2]] for x in states])
        assert len(np.unique(atoms, axis=0)) == len(states)
        assert np.array_equal(atoms, row['observation_tuple_atoms'])
        gap = abs(projections(a.reshape(2,2,2))-projections(b.reshape(2,2,2))).max()
        errors['complete_pair_law'] = max(errors['complete_pair_law'], gap)
        assert abs(.5*abs(a-b).sum()-row['joint_observation_tuple_total_variation']) < 1e-12
    else:
        counts['ordinary_baselines'] += 1
        assert row['candidate_score'] is None and row['candidate_status'] == 'pending'
        z = np.asarray(case['payload']); w = np.asarray(row['w'])
        assert w.min() >= 0 and abs(w.sum()-1) < 1e-10
        masses = [w.sum(axis=(1,2)), w.sum(axis=(0,2)), w.sum(axis=(0,1))]
        means = [masses[t] @ z[t] for t in range(3)]
        # Explicit sum avoids the implementation's einsum contraction.
        tensor = np.zeros((z.shape[2],)*3)
        for i,j,k in np.ndindex(w.shape):
            tensor += w[i,j,k]*np.multiply.outer(np.multiply.outer(z[0,i]-means[0], z[1,j]-means[1]), z[2,k]-means[2])
        errors['ordinary_tensor'] = max(errors['ordinary_tensor'], abs(tensor-np.asarray(row['ordinary_tensor'])).max())
assert max(errors.values()) < 1e-8, errors
out = {'reviewed_at_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': COMMIT,
       'freeze_commit': validation['git_revision'], 'file_checks': file_checks,
       'freeze_precedes_execution': True, 'frozen_commit_matches': True,
       'counts': counts, 'recomputed_max_errors': {k:float(v) for k,v in errors.items()},
       'event_certificates': certificates, 'review_scope': 'frozen protocol and archived arithmetic only',
       'ht_integration': 'not_run_pending_preserved', 'lp_rerun': False,
       'server_access': False, 'gpu_used': False, 'scientific_breakthrough': False}
destination = ROOT / 'research-plan/reviews/AL04_DELIVERY_CHECK_20260919.json'
with destination.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, ensure_ascii=False, indent=2); f.write('\n')
print(json.dumps({'output': str(destination), 'counts': counts, 'max_errors': out['recomputed_max_errors']}, ensure_ascii=False))
