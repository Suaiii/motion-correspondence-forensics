"""AL20: exact read-only audit of three predeclared archive traces, no core calls."""
from fractions import Fraction as F
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918';MAIN=Path('E:/aNB/TECH/脉冲神经网络')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def save(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(data),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def frac(v):return F.from_float(v) if isinstance(v,float) else F(v)
def vec(v):return tuple(frac(x) for x in v)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','run']);p.add_argument('--output',type=Path,default=OUT/'AL20_trace_audit.json');args=p.parse_args()
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    archive=ROOT/cfg['archive_path'];work=MAIN/'research-plan/AL20_OR1_COMPACT_BASELINE_20260919.md'
    if sha(archive)!=cfg['archive_sha256'] or sha(work)!=cfg['work_order_sha256']:
        raise ValueError('Input/work-order hash mismatch')
    lock_path=OUT/'AL20_freeze.json'
    if args.mode=='freeze':
        files=[Path(__file__),HERE/'config.json',OUT/'AL20_protocol.md',archive]
        save(lock_path,dict(frozen_at=datetime.now(timezone.utc).isoformat(),trace_ids=cfg['trace_ids'],
            files={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in files},
            mathematical_trace_reads_before_freeze=0,work_order_sha256=sha(work),
            AL23_review_sha256=sha(MAIN/'research-plan/reviews/AL23_MATCHING_OBJECTIVE_REVIEW_20260919.md')))
        print('AL20 trace IDs/formulas/source hashes frozen; no numeric trace audit yet');return
    if args.output.exists():raise FileExistsError(args.output)
    lock=json.loads(lock_path.read_text(encoding='utf-8'))
    for path,want in lock['files'].items():
        if sha(ROOT/path)!=want:raise ValueError('Frozen input changed: '+path)
    start=time.perf_counter();data=json.loads(archive.read_text(encoding='utf-8'))
    selected={r['id']:r for r in data['evaluations'] if r['id'] in cfg['trace_ids']}
    if set(selected)!=set(cfg['trace_ids']):raise ValueError('Exact declared trace IDs missing; no fallback selection')
    rows=[];failures=[]
    for trace_id in cfg['trace_ids']:
        archived=selected[trace_id];r=archived['result'];h=frac(r['h']);eta=frac(r['eta_mean'])
        x,ra,rb,pa,pb,rab,rba=[vec(r[key]) for key in ('x','ra','rb','pa','pb','ra_pb','rb_pa')]
        n=len(x)
        da=tuple(v/h for v in sub(sub(rab,pb),sub(ra,x)))
        db=tuple(v/h for v in sub(sub(rba,pa),sub(rb,x)))
        k=sub(da,db);va=sub(ra,x);vb=sub(rb,x)
        a,b,c=dot(da,da)/n,dot(db,db)/n,dot(da,db)/n
        denominator=(dot(va,va)+dot(vb,vb))/n+eta
        z=(a/denominator,b/denominator,c/denominator)
        q_from_triple=z[0]+z[1]-2*z[2];q_from_k=dot(k,k)/n/denominator
        # Read-only scalar rounding replay, no R/core invocation.
        ek,ea,eb=[r['energy_sum'][key] for key in ('K','a','b')]
        scalar_float_replay=(ek/n)/((ea+eb)/n+r['eta_mean'])
        checks=dict(primary_h=h==F(1,8),K_reconstructed_exactly=k==vec(r['K']),
            endpoint_relation_exact=k==tuple(v/(h*h) for v in sub(vec(r['endpoint_ab']),vec(r['endpoint_ba']))),
            energy_expansion_exact=dot(k,k)/n==a+b-2*c,ratio_reconstruction_exact=q_from_k==q_from_triple,
            archived_scalar_rounding_replayed=scalar_float_replay==r['q_mean_fixed_eta'])
        row=dict(trace_id=trace_id,h=h,dimension=n,x=x,d_a=da,d_b=db,K=k,
            mean_cross_energy=(a,b,c),common_denominator=denominator,eta_as_archived_binary_rational=eta,
            normalized_compact_triplet=z,q_exact=q_from_k,
            archived_q_float=r['q_mean_fixed_eta'],archive_float_minus_exact=frac(r['q_mean_fixed_eta'])-q_from_k,
            float_difference_display=float(frac(r['q_mean_fixed_eta'])-q_from_k),
            checks=checks,passed=all(checks.values()))
        rows.append(row)
        if not row['passed']:failures.append(trace_id)
    t=[[F(0)]*4 for _ in range(12)]
    for col in range(4):
        for offset,value in enumerate((1,1,-2)):t[3*col+offset][col]=F(value)
    gram=[[sum((t[row][i]*t[row][j] for row in range(12)),F(0)) for j in range(4)] for i in range(4)]
    gram_ok=all(gram[i][j]==(6 if i==j else 0) for i in range(4) for j in range(4))
    if not gram_ok:failures.append('T_gram')
    for path,want in lock['files'].items():
        if sha(ROOT/path)!=want:raise ValueError('Input changed during audit: '+path)
    output=dict(task_id='AL20',dispatch_id=cfg['dispatch_id'],observed_at=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        status='pass_finite_response_baseline_contract' if not failures else 'failure_preserved',failures=failures,
        freeze_sha256=sha(lock_path),files=lock['files'],traces=rows,T=t,T_transpose_T=gram,
        regularization=dict(candidate_lambda='1/1000',canonical_embedding_penalty_factor='6',
            proposed_free_baseline_lambda='1/6000',old_candidate_lambda_changed=False,
            training_objective_inclusion_requires='Same features, pairs, weights, support, denominator and the lambda/6 baseline penalty',
            test_generalization_order='not_proven'),
        coverage=dict(archive_entries_mathematically_checked=3,selected_inner_products_all_zero=all(r['mean_cross_energy'][2]==0 for r in rows),
            note='The first and third prescribed traces share their numeric setup; no additional trace was selected to create novelty'),
        calls=dict(AL15_core=0,probe=0,classifier_fitting=0),elapsed_seconds=time.perf_counter()-start,
        resources=dict(stdlib_only=True,worker_count=1,worker_cap=2,trace_vector_dimension=2,coefficient_matrix_shape=[12,4],
            server=False,GPU=False,media=False,models=False),scientific_breakthrough=False)
    save(args.output,output)
    print(json.dumps(dict(status=output['status'],trace_count=3,failures=failures,elapsed_seconds=output['elapsed_seconds'])))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
