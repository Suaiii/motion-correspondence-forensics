"""Freeze AL30 actual inputs and precision policy before any numeric objective."""
import copy
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'research-runs/algorithm_search_20260918'
SOURCE = Path(__file__).resolve().parent
MAIN = Path('E:/aNB/TECH/脉冲神经网络')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def save(name, data):
    with (OUT/('AL30_'+name+'.json')).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n')


def main():
    order = MAIN/'research-plan/AL30_ACCURACY_BUDGETED_STOPPING_CPU_20260919.md'
    assert sha(order)=='7b529dd8a39637e0d67d111b6815d3b529d597c43b1c493dd73ee3cb05e3ee51'
    original_freeze = read('AL27_freeze.json')
    original_config = read('AL27_config.json')
    original_inputs = read('AL27_inputs.json')
    original_evidence = read('AL27_evidence.json')
    assert original_evidence['gate_result']=='fail'
    assert sha(OUT/'AL27_evidence.json')=='6fe894345287a0dda2cbe4cac029c5538da2161f371b191cd84a74dac3b3c11b'
    assert sha(SOURCE/'objective.py')==sha(SOURCE.parent/'or1_head_reference/objective.py')
    for category in ['inputs','dependencies','historical']:
        for p,digest in original_freeze[category].items():
            assert sha(ROOT/p)==digest,(category,p)
    panels = copy.deepcopy(original_inputs['panels'])
    for panel in panels:
        panel['case_role']='known_regression'
    z0 = [F(v) for v in (1,1,0)*4]
    panels.append(dict(name='full_rank_scale',case_role='new_prespecified_scale_control',
        plus=[[str(v+F(int(i==j),8)) for i,v in enumerate(z0)] for j in range(12)],
        minus=[[str(v) for v in z0] for _ in range(12)]))
    save('inputs',dict(transform=original_inputs['transform'],panels=panels,
        boundaries=original_inputs['boundaries'],
        regression_reference=dict(path=(OUT/'AL27_inputs.json').relative_to(ROOT).as_posix(),
            sha256=sha(OUT/'AL27_inputs.json'), original_gate_result='fail',
            original_evidence_sha256=sha(OUT/'AL27_evidence.json'))))
    config = copy.deepcopy(original_config)
    del config['solver']['gradient_l2_tolerance']
    config['stopping']={}
    for head in ['candidate','free']:
        regularizer = F(config[head+'_regularizer'])
        mu = 2*regularizer
        epsilon = F(1,10**9)
        tau = min(F(1,10**10),mu*epsilon/2)
        reg_float = float(regularizer)
        config['stopping'][head]=dict(formula='min(1e-10, mu*epsilon_x/2)',
            regularizer_exact=str(regularizer),regularizer_float=reg_float,
            mu_exact=str(mu),mu_float=2*reg_float,
            epsilon_x_exact=str(epsilon),epsilon_x_float=float(epsilon),
            tau_exact=str(tau),tau_float=min(1e-10,(2*reg_float)*float(epsilon)/2),
            gradient_rounding_error_bound=None,parameter_error_certified=False)
    assert config['stopping']['candidate']['tau_exact']=='1/1000000000000'
    assert config['stopping']['free']['tau_exact']=='1/6000000000000'
    config['expected']['full_rank_scale']=dict(rank_z=12,rank_q=4,
        gradient_at_zero=dict(candidate=['0']*4,free=['-1/192']*12))
    config['old_AL27_gate_result']='fail'
    config['case_roles']={p['name']:p['case_role'] for p in panels}
    save('config',config)
    frozen_inputs = {p.relative_to(ROOT).as_posix():sha(p) for p in SOURCE.glob('*.py')}
    for suffix in ['inputs.json','config.json','protocol.md']:
        p=OUT/('AL30_'+suffix)
        frozen_inputs[p.relative_to(ROOT).as_posix()]=sha(p)
    historical = dict(original_freeze['historical'])
    for p in list(OUT.glob('AL27_*'))+list((SOURCE.parent/'or1_head_reference').glob('*.py')):
        if p.is_file():
            historical[p.relative_to(ROOT).as_posix()]=sha(p)
    upstream_paths = ['research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json',
        'research-plan/AL30_ACCURACY_BUDGETED_STOPPING_CPU_20260919.md',
        'research-plan/AL23_OR1_MATCHING_OBJECTIVE_20260919.md',
        'research-plan/reviews/AL23_MATCHING_OBJECTIVE_REVIEW_20260919.md',
        'research-plan/reviews/AL27_REVIEW_20260919.md']
    save('freeze',dict(created_at=datetime.now(timezone.utc).isoformat(),
        parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        python=sys.version,numpy_version=original_freeze['numpy_version'],
        inputs=frozen_inputs,dependencies=original_freeze['dependencies'],historical=historical,
        upstream_at_freeze={str(MAIN/p):sha(MAIN/p) for p in upstream_paths},
        objective_source_byte_identical_to_AL27=True,
        numeric_objective_or_optimizer_run=False,
        note='Commit receipt, all implementation files and actual inputs before the single AL30 batch.'))


if __name__=='__main__':
    main()
