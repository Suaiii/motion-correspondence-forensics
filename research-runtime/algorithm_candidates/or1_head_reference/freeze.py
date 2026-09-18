"""Create immutable AL27 receipt without importing NumPy or evaluating objectives."""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'research-runs/algorithm_search_20260918'
SOURCE = Path(__file__).resolve().parent
MAIN = Path('E:/aNB/TECH/脉冲神经网络')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (OUT / ('AL27_' + name + '.json')).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def main():
    assert sha(MAIN/'research-plan/WORK_PLAN.md') == '5cc4f7b994c79853913cecb8d1bad9a46156f584fd33ca4712aee85c7b3fc8ec'
    assert sha(MAIN/'research-plan/AL27_FULL_HEAD_REFERENCE_CPU_20260919.md') == 'e1b016aa6cbeb4d3fb8a6801bd2e54f286b8970e278f1b44b4fad804e0e56c34'
    t = [[(1, 1, -2)[i % 3] if i // 3 == j else 0 for j in range(4)] for i in range(12)]
    z0 = [F(x) for x in (1, 1, 0) * 4]
    panels = []
    for name in ['aligned', 'full_rank', 'symmetric']:
        delta = []
        if name == 'full_rank':
            delta = [[F(int(i == j), 4) for i in range(12)] for j in range(12)]
        else:
            for j in range(4):
                for sign in ([1, -1] if name == 'symmetric' else [1]):
                    delta.append([F(sign*t[i][j], 8) for i in range(12)])
        panels.append(dict(name=name, plus=[[str(a+b) for a,b in zip(z0,row)] for row in delta],
                           minus=[[str(v) for v in z0] for _ in delta]))
    save('inputs', dict(transform=t, panels=panels,
                       boundaries=[dict(name='empty', plus=[], minus=[], shape=[0,12]),
                                   dict(name='nonfinite', plus=[['NaN'] + [str(v) for v in z0[1:]]],
                                        minus=[[str(v) for v in z0]])]))
    expected = dict(aligned=dict(rank_z=4, rank_q=4, gradient_at_zero=dict(
        candidate=['-3/32']*4, free=['-1/64','-1/64','1/32']*4)),
        full_rank=dict(rank_z=12, rank_q=4, gradient_at_zero=dict(candidate=['0']*4, free=['-1/96']*12)),
        symmetric=dict(rank_z=4, rank_q=4, gradient_at_zero=dict(candidate=['0']*4, free=['0']*12)))
    save('config', dict(dtype='float64', candidate_regularizer='1/1000', free_regularizer='1/6000',
         solver=dict(max_iterations=200, gradient_l2_tolerance=1e-10, armijo_c=1e-4, maximum_halvings=40),
         scalar=dict(bracket=[0.0,64.0], width_tolerance=1e-13, max_iterations=128),
         comparison_tolerance=1e-9, native_threads=2, maximum_pairs_per_panel=12,
         maximum_feature_rows_per_panel=24, maximum_dimension=12, maximum_array_bytes=1048576,
         expected=expected))
    inputs = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in SOURCE.glob('*.py')}
    for suffix in ['inputs.json','config.json','protocol.md']:
        p = OUT / ('AL27_'+suffix)
        inputs[p.relative_to(ROOT).as_posix()] = sha(p)
    np_path = Path(importlib.util.find_spec('numpy').origin)
    deps = [Path(sys.executable), np_path]
    deps += list((np_path.parent/'_core').glob('_multiarray_umath*.pyd'))
    deps += list((np_path.parent.parent/'numpy.libs').glob('*openblas*.dll'))
    deps += list(np_path.parent.parent.glob('numpy-*.dist-info/METADATA'))
    dependencies = {str(p):sha(p) for p in deps}
    upstream_names = ['research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json',
        'research-plan/AL27_FULL_HEAD_REFERENCE_CPU_20260919.md',
        'research-plan/AL20_OR1_COMPACT_BASELINE_20260919.md',
        'research-plan/AL23_OR1_MATCHING_OBJECTIVE_20260919.md',
        'research-plan/AL24_MATCHING_OBJECTIVE_CPU_20260919.md',
        'research-plan/reviews/AL25_REVIEW_20260919.md']
    upstream = {str(MAIN/p):sha(MAIN/p) for p in upstream_names}
    historical = {}
    for prefix in ['AL01','AL04','AL06','AL09','AL12','AL15','AL18','AL20','AL24','AL25']:
        for p in OUT.glob(prefix+'_*'):
            if p.is_file():
                historical[p.relative_to(ROOT).as_posix()] = sha(p)
    for folder in ['or1_cpu','or1_numerics','or1_baseline_audit','or1_matching_reference','or1_filtered_readout']:
        for p in (SOURCE.parent/folder).glob('*'):
            if p.is_file():
                historical[p.relative_to(ROOT).as_posix()] = sha(p)
    save('freeze', dict(created_at=datetime.now(timezone.utc).isoformat(),
        parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version, numpy_version=importlib.metadata.version('numpy'),
        inputs=inputs, dependencies=dependencies, upstream_at_freeze=upstream, historical=historical,
        numeric_objective_or_optimizer_run=False,
        note='Commit this receipt and all inputs before invoking run.py. No numeric objective evaluated here.'))


if __name__ == '__main__':
    main()
