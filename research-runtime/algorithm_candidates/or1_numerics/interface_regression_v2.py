"""Only the two reviewed API modes and corresponding controls; no v1 suite replay."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime,timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'
V1_SHA='3ac18e29774aaa9f2eeecb593f2a8e8233d864b0a69cdd6156520fee640d5984'
EVIDENCE_SHA='b56917ec8688c534cddaf82ba3f2a503cd48f5388b9faf1cb26d42053e250c9f'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def decode(v):
    if isinstance(v,dict):
        if set(v)=={'nonfinite'}:return float(v['nonfinite'])
        return {k:decode(x) for k,x in v.items()}
    if isinstance(v,list):return [decode(x) for x in v]
    return v
def save(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(data),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def bound(v):return dict(value=v,basis='analytic_mock')


def prepare():
    if sha(HERE/'bounds.py')!=V1_SHA or sha(OUT/'AL18_evidence.json')!=EVIDENCE_SHA:
        raise ValueError('Original frozen source/result changed')
    rows=[]
    def add(name,kind,payload,status,h,**expected):
        rows.append(dict(id=name+'__h'+h,kind=kind,payload=payload,h=h,eta='1/1000000000000',
            expected=dict(status=status,**expected)))
    for h in ('1/4','1/8','1/16'):
        n5=dict(hat_n='1/4',hat_d='1/2',hat_q={'nonfinite':'nan'},
            bounds=dict(B_N=bound('0'),B_D=None,rho_q=bound('0'),rho_s=bound('0')))
        add('N5_nan_observation_unknown_bound','N5',copy.deepcopy(n5),'invalid_input',h)
        n5['hat_q']='1/2'
        add('N5_finite_observation_unknown_bound','N5',copy.deepcopy(n5),'uncertified_bound',h)
        n5['bounds']['B_D']=bound('0')
        add('N5_finite_observation_known_bound','N5',copy.deepcopy(n5),'conditional_interval',h,q_hat='1/2',B_q='0')
        obs={k:['0'] for k in ('x','ra0','rb0','pa','pb','rab','rba','uab','uba')}
        b={k:bound('0') for k in ('eps_a0','eps_b0','eps_ab','eps_ba','rho_a','rho_b','rho_ab','rho_ba','rho_K')}
        b.update(L_a=bound('1'),L_b=bound('1'))
        n2=dict(observations=obs,bounds=b,hat_k=[{'nonfinite':'nan'}])
        add('N2_nan_final_observation','N2',copy.deepcopy(n2),'invalid_input',h)
        n2['hat_k']=['0']
        add('N2_finite_final_observation','N2',copy.deepcopy(n2),'residual_energy_not_certified_positive',h,K_hat=['0'],B_K='0')
        n2['bounds']['L_a']=None
        add('N2_finite_final_unknown_L','N2',copy.deepcopy(n2),'uncertified_bound',h)
        n2['bounds']['L_a']=bound('1');n2['hat_k']=['1/64'];n2['bounds']['rho_K']=bound('1/64')
        add('N2_nonzero_final_observation_used','N2',copy.deepcopy(n2),'residual_energy_not_certified_positive',h,
            K_hat=['1/64'],B_K='1/64',first_interval=['0','1/32'])
        del n2['hat_k'];n2['undeclared_final_K']=['0']
        add('N2_unsupported_output_field','N2',copy.deepcopy(n2),'invalid_input',h)
    save(OUT/'AL18_v2_interface_inputs.json',dict(records=rows,
        scope='Two reviewed modes with valid/unknown/consumption/schema controls; no new scientific examples',
        public_queries_expected=24,probe_calls_expected=0,endpoint_readouts_expected=0,v1_queries_in_this_run=0))
    paths=[HERE/'bounds.py',HERE/'bounds_v2.py',Path(__file__),OUT/'AL18_v2_interface_inputs.json',
        OUT/'AL18_v2_interface_note.md',OUT/'AL18_interface_findings_source.json',
        OUT/'AL18_evidence.json',OUT/'AL18_inputs.json',OUT/'AL18_freeze.json']
    save(OUT/'AL18_v2_interface_freeze.json',dict(frozen_at=datetime.now(timezone.utc).isoformat(),
        v1_source_sha256=V1_SHA,v1_evidence_sha256=EVIDENCE_SHA,original_result_commit='0546f63',
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths},
        candidate_queries_before_freeze=0,reviewer_v1_queries=2,v1_queries_by_this_executor=0))
    print('Frozen 24 targeted v2 interface records; no contract calls yet')


def run(output):
    if output.exists():raise FileExistsError(output)
    path=OUT/'AL18_v2_interface_freeze.json';lock=json.loads(path.read_text(encoding='utf-8'))
    def unchanged():
        for rel,want in lock['files'].items():
            if sha(ROOT/rel)!=want:raise ValueError('Interface freeze changed: '+rel)
        old=json.loads((OUT/'AL18_freeze.json').read_text(encoding='utf-8'))
        for rel,want in dict(old['files'],**old['preserved']).items():
            if sha(ROOT/rel)!=want:raise ValueError('Original AL18/history changed: '+rel)
        for dep,want in old['dependencies'].items():
            if sha(dep)!=want:raise ValueError('Original runtime dependency changed')
    unchanged()
    import bounds_v2
    records=json.loads((OUT/'AL18_v2_interface_inputs.json').read_text(encoding='utf-8'))['records']
    start=time.perf_counter()
    def evaluate(row):
        result=bounds_v2.evaluate(row['kind'],decode(row['payload']),row['h'],row['eta'])
        checks=dict(expected_state=result['status']==row['expected']['status'],no_origin_label=result['origin_decision'] is None)
        for key in ('q_hat','B_q','B_K'):
            if key in row['expected']:checks[key+'_honored']=result[key]==F(row['expected'][key])
        if 'K_hat' in row['expected']:
            checks['supplied_K_is_returned']=result['K_hat']==tuple(F(x) for x in row['expected']['K_hat'])
            checks['supplied_K_is_marked_checked']=result['final_K_observation']=='supplied_and_checked'
        if 'first_interval' in row['expected']:
            checks['nonzero_observation_changes_interval']=result['coordinate_intervals'][0]==tuple(F(x) for x in row['expected']['first_interval'])
        if row['expected']['status'] in ('invalid_input','uncertified_bound'):
            checks['not_certified']=not result['interval_valid']
        return dict(id=row['id'],worker=threading.current_thread().name,result=result,checks=checks,passed=all(checks.values()))
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='AL18v2') as pool:
        rows=list(pool.map(evaluate,records))
    unchanged();failures=[r['id'] for r in rows if not r['passed']]
    receipt=dict(task_id='AL18',dispatch_id='cc-al18-numerical-contract-20260919',scope='bounded_interface_v2_regression_only',
        observed_at=datetime.now(timezone.utc).isoformat(),git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        status='pass_targeted_interface_repair' if not failures else 'failure_preserved',failures=failures,records=rows,
        source_hash_before=V1_SHA,source_hash_v2=sha(HERE/'bounds_v2.py'),v1_evidence_sha256=EVIDENCE_SHA,
        v2_freeze_sha256=sha(path),files=lock['files'],v1_and_old_artifacts_unchanged=True,
        calls=dict(v2_public_contract_queries=len(rows),v1_public_queries_by_this_executor=0,
            reviewer_preliminary_v1_queries=2,mock_probe_calls=0,endpoint_readouts=0,original_147_replayed=False,AL15_replayed=False),
        worker_cap=2,observed_workers=sorted({r['worker'] for r in rows}),wall_seconds=time.perf_counter()-start,
        arithmetic='stdlib Fraction',scientific_breakthrough=False,real_AE_precision_certified=False)
    save(output,receipt)
    print(json.dumps(dict(status=receipt['status'],records=len(rows),failures=failures,calls=receipt['calls'],wall_seconds=receipt['wall_seconds']),indent=2))
    if failures:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);parser.add_argument('--output',type=Path,default=OUT/'AL18_v2_interface_evidence.json');args=parser.parse_args()
    if args.mode=='freeze':prepare()
    else:run(args.output)
