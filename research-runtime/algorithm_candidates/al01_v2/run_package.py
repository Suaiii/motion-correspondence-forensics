"""Freeze then evaluate new AL01 controls; archived references are read-only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import warnings
import numpy as np
import scipy
from scipy.optimize import OptimizeWarning
from threadpoolctl import threadpool_limits,threadpool_info
import joint_v2 as v2

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'
OLD=ROOT/'research-plan/fallback-runtime/joint_marginal_reference.py'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ah(value):return hashlib.sha256(np.asarray(value,dtype='<f8').tobytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def jsonable(v):
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {k:jsonable(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [jsonable(x) for x in v]
    return v
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(jsonable(value),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def load_old(cfg):
    if sha(OLD)!=cfg['old_reference_sha256']:raise ValueError('Archived reference changed')
    spec=importlib.util.spec_from_file_location('al01_archived',OLD)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    fn=old.linprog
    def capped(*args,**kwargs):
        kwargs['options']=dict(kwargs.get('options',{}),threads=2,parallel=False)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',category=OptimizeWarning,message='Unrecognized options detected.*')
            return fn(*args,**kwargs)
    old.linprog=capped
    return old


def inputs(cfg):
    cases=[]
    groups=dict(cfg['collision_groups'])
    u=float(np.sqrt(2.13)-1)
    groups['same_mean_cycle']=[[u,u,0],[.9,.1,-.02]]
    for group,rs in groups.items():
        for idx,r in enumerate(rs):
            q=np.stack([v2.binary_q(x) for x in r])
            base=dict(id=f'{group}_{idx}',kind='binary_control',family=group,r=r,q=q,
                expected='compatible' if idx==0 else 'incompatible',split='analytic_development')
            cases.append(base)
            for m in cfg['lift_sizes']:
                k=m//2
                lifted=np.repeat(np.repeat(q,k,axis=1),k,axis=2)/k**2
                cases.append(dict(id=f'{group}_{idx}_lift{m}',kind='lifted_control',family=group,q=lifted,
                    groups=[0]*k+[1]*k,source_case=base['id'],split='fixed_analytic_extension',
                    partition_role='declared observable indices, available to every comparator'))
    for split in ('development','independent_check'):
        rng=np.random.default_rng(cfg[split]['seed'])
        for m in cfg[split]['sizes']:
            z=rng.normal(size=(m,4))
            frames=np.stack([z,z+.21*rng.normal(size=z.shape),rng.normal(size=z.shape)])
            cases.append(dict(id=f'{split}_m{m}_features',kind='features',split=split,z=z,frames=frames))
    for eps in cfg['near_facet_epsilons']:
        for side in (-1,1):
            r=-1/3+side*eps
            cases.append(dict(id=f'near_facet_{eps}_{side}',kind='near_facet',split='numerical_boundary',
                q=np.stack([v2.binary_q(r)]*3),analytic_distance=max(0,-side*eps),epsilon=eps,side=side))
    for eps in cfg['input_mass_perturbations']:
        q=np.ones((3,2,2))/4;q[0,0,0]+=eps
        cases.append(dict(id=f'mass_{eps}',kind='mass_boundary',split='numerical_boundary',q=q,
            perturbation=eps,expected_accept=eps<=v2.MASS_TOL))
    return jsonable(cases)


def prepare(cfg):
    # Verify precisely the adopted review blobs, without cherry-picking or
    # importing changing main-workspace code. No model/LP is run in prepare.
    adopted={}
    for name in ('AL03_cross_review.md','AL03_cross_evidence.json'):
        rel='research-runs/algorithm_search_20260918/'+name
        blob=git('show',cfg['review_commit']+':'+rel)
        blob_sha=hashlib.sha256(blob).hexdigest()
        if blob_sha!=sha(MAIN/rel):raise ValueError('Adopted reviewed file differs from committed bytes')
        adopted[rel]=dict(commit=cfg['review_commit'],sha256=blob_sha)
    review=MAIN/'research-plan/reviews/ROUND6_REVIEW_20260919.md'
    adopted[str(review)]=dict(sha256=sha(review),role='planner acceptance read only')
    save(OUT/'AL01_inputs.json',dict(cases=inputs(cfg),malformed_suite=[
        'tau_zero','tau_negative','tau_nan','tau_inf','tau_bool','tau_array','tau_string','tau_complex',
        'feature_nan','feature_inf','feature_1d','feature_empty_channels','feature_m9','feature_zero_row','feature_complex',
        'q_nan','q_inf','q_negative','q_wrong_shape','q_nonuniform','support_missing'],
        valid_edge_suite=['large_features_1e250','small_features_1e-250','tiny_positive_tau_numeric_rejection'],
        prior_knowledge='AL03 math and AL04 protocol known; no blind scientific confirmation'))
    sources=[HERE/'joint_v2.py',HERE/'run_package.py',HERE/'config.json',OUT/'AL01_inputs.json',OUT/'AL01_design.md',OLD]
    preserved={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in OUT.glob('AL04*') if p.is_file()}
    save(OUT/'AL01_freeze.json',dict(frozen_at=now(),adopted_review=adopted,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources},
        preserved_AL04=preserved,pre_solver_freeze=True,old_reference_sha256=sha(OLD)))
    print(json.dumps(dict(cases=len(inputs(cfg)),adopted_review_files=len(adopted),frozen_before_solving=True)))


def malformed_checks(base_z):
    rows=[]
    def check(name,call,expected):
        try:
            result=call();status='returned';detail=None
        except Exception as exc:
            status=type(exc).__name__;detail=str(exc)
        rows.append(dict(case=name,expected=expected,observed=status,error=detail,passed=status==expected))
    for label,tau in [('zero',0),('negative',-.1),('nan',float('nan')),('inf',float('inf')),
                      ('bool',True),('array',[.1]),('string','.1'),('complex',.1+0j)]:
        check('tau_'+label,lambda tau=tau:v2.symmetric_kernel_coupling(base_z,tau),'InputDomainError')
    bad_features={
        'nan':np.array([[float('nan'),1],[1,2]]),'inf':np.array([[float('inf'),1],[1,2]]),
        '1d':np.ones(4),'empty_channels':np.zeros((2,0)),'m9':np.ones((9,2)),
        'zero_row':np.array([[0,0],[1,2]]),'complex':np.ones((2,2),dtype=complex)}
    for label,z in bad_features.items():
        check('feature_'+label,lambda z=z:v2.symmetric_kernel_coupling(z),'InputDomainError')
    q=np.ones((3,2,2))/4
    for label,value in [('nan',float('nan')),('inf',float('inf')),('negative',-.1)]:
        bad=q.copy();bad[0,0,0]=value
        check('q_'+label,lambda bad=bad:v2.joint_distance(bad),'InputDomainError')
    check('q_wrong_shape',lambda:v2.joint_distance(np.ones((2,2,2))),'InputDomainError')
    check('q_nonuniform',lambda:v2.joint_distance(np.stack([np.diag([.7,.3])]*3)),'InputDomainError')
    check('support_missing',lambda:v2.joint_distance(q,(True,False,True)),'InputDomainError')
    check('tiny_positive_tau_numeric_rejection',lambda:v2.symmetric_kernel_coupling(base_z,1e-300),'NumericalDomainError')
    return rows


def run(cfg,output):
    if output.exists():raise FileExistsError(output)
    freeze=json.loads((OUT/'AL01_freeze.json').read_text(encoding='utf-8'))
    def unchanged():
        for rel,expected in dict(freeze['files'],**freeze['preserved_AL04']).items():
            if sha(ROOT/rel)!=expected:raise ValueError('Frozen/preserved source changed: '+rel)
    unchanged();old=load_old(cfg);start=time.perf_counter();rows=[];by_id={};errors=[];max_bytes=0
    cases=json.loads((OUT/'AL01_inputs.json').read_text(encoding='utf-8'))['cases']
    with threadpool_limits(limits=2):
        pools=threadpool_info()
        for case in cases:
            row=dict(id=case['id'],kind=case['kind'],split=case['split'],checks={})
            try:
                if case['kind']=='features':
                    z=np.asarray(case['z']);frames=np.asarray(case['frames']);m=len(z)
                    qnew=v2.symmetric_kernel_coupling(z,cfg['temperature'])
                    qold=old.symmetric_kernel_coupling(z,cfg['temperature'])
                    triple=np.stack([qnew]*3)
                    newfit=v2.joint_distance(triple);oldfit=old.joint_distance(np.stack([qold]*3))
                    max_bytes=max(max_bytes,newfit['max_matrix_bytes'])
                    row.update(static_new=newfit,old_distance=oldfit['distance'],
                        default_kernel_max_gap=float(abs(qnew-qold).max()))
                    row['checks']['default_kernel_regression']=row['default_kernel_max_gap']<1e-10
                    row['checks']['static_old_new_zero']=max(abs(newfit['distance']),abs(oldfit['distance']))<1e-8
                    normalized=[v2.normalization_pair(frames[a],frames[b],cfg['temperature']) for a,b in v2.PAIRS]
                    raw=np.stack([x['row_only_joint'] for x in normalized]);balanced=np.stack([x['balanced_joint'] for x in normalized])
                    try:v2.joint_distance(raw);raw_status='accepted'
                    except v2.InputDomainError:raw_status='unsupported_uniform_masses'
                    fit=v2.joint_distance(balanced);max_bytes=max(max_bytes,fit['max_matrix_bytes'])
                    row['normalization']=dict(raw_Q=raw,balanced_Q=balanced,raw_candidate_status=raw_status,
                        raw_summaries=v2.summaries(raw),balanced_summaries=v2.summaries(balanced),balanced_candidate=fit,
                        total_Q_l1_change=float(abs(raw-balanced).sum()),
                        interpretation='Preprocessing changes inputs; differences cannot be credited to the objective')
                    row['checks']['raw_mass_scope_reported']=raw_status=='unsupported_uniform_masses' if v2.summaries(raw)['mass_error']>v2.MASS_TOL else raw_status=='accepted'
                    row['checks']['large_finite_normalization']=np.max(abs(v2.symmetric_kernel_coupling(z*1e250)-qnew))<1e-10
                    row['checks']['small_finite_normalization']=np.max(abs(v2.symmetric_kernel_coupling(z*1e-250)-qnew))<1e-10
                else:
                    q=np.asarray(case['q']);row['q_sha256']=ah(q)
                    try:fit=v2.joint_distance(q)
                    except v2.InputDomainError as exc:
                        if case['kind']=='mass_boundary' and not case['expected_accept']:
                            row.update(status='rejected',reason=str(exc));row['checks']['correct_mass_rejection']=True
                            rows.append(row);by_id[row['id']]=row;continue
                        raise
                    max_bytes=max(max_bytes,fit['max_matrix_bytes']);row.update(fit=fit,summaries=v2.summaries(q),status='returned')
                    if case['kind']=='binary_control':
                        facet=v2.binary_facet_distance(q);row['classical_facet_distance']=facet
                        row['checks']['classical_formula_matches']=abs(fit['distance']-facet)<1e-8
                        row['checks']['declared_compatibility']=fit['distance']<=1e-8 if case['expected']=='compatible' else fit['distance']>1e-5
                    if case['kind']=='lifted_control':
                        k=q.shape[1]//2
                        coarse=q.reshape(3,2,k,2,k).sum((2,4));facet=v2.binary_facet_distance(coarse)
                        row.update(coarse_pair_Q=coarse,classical_coarse_facet_distance=facet)
                        row['checks']['classical_coarse_formula_matches']=abs(fit['distance']-facet)<1e-8
                        row['checks']['lift_matches_binary']=abs(fit['distance']-by_id[case['source_case']]['fit']['distance'])<1e-8
                    if case['kind']=='near_facet':
                        row['analytic_distance']=case['analytic_distance']
                        row['checks']['absolute_tolerance_only']=abs(fit['distance']-case['analytic_distance'])<1e-8
                        row['interpretation']='Below zero tolerance: no exact compatibility or tiny positive mechanism claim'
                    if case['kind']=='mass_boundary':
                        row['checks']['accepted_only_inside_declared_band']=case['expected_accept']
                        row['interpretation']='Approximately normalized input; raw objective retained, not exact probability evidence'
            except Exception as exc:
                row.update(status='implementation_or_unexpected_failure',error=repr(exc));errors.append(row['id'])
            row['checks']={k:bool(v) for k,v in row['checks'].items()}
            if not all(row['checks'].values()):errors.append(row['id'])
            rows.append(row);by_id[row['id']]=row
        malformed=malformed_checks(np.array([[1.,0.],[0.,1.]]))
        errors.extend(r['case'] for r in malformed if not r['passed'])
        comparisons={}
        for group,field in [('same_forward_js','forward_js'),('same_entropy','pair_entropy'),('same_mean_cycle','mean_cycle_l1')]:
            a,b=by_id[group+'_0'],by_id[group+'_1']
            gap=float(np.max(abs(np.asarray(a['summaries'][field])-np.asarray(b['summaries'][field]))))
            dj=[a['fit']['distance'],b['fit']['distance']]
            comparisons[group]=dict(summary=field,max_gap=gap,distances=dj,
                full_summaries=[a['summaries'],b['summaries']],
                scope='Only this named summary collides; not a collision of all summaries or complete Q')
            if gap>1e-10 or dj[0]>1e-8 or dj[1]<1e-5:errors.append(group)
    unchanged()
    result=dict(task_id='AL01',dispatch_id=cfg['dispatch_id'],version=cfg['version'],observed_at=now(),
        git_revision=git('rev-parse','HEAD').decode().strip(),command=sys.argv,freeze_sha256=sha(OUT/'AL01_freeze.json'),
        source_and_input_hashes=freeze['files'],adopted_review=freeze['adopted_review'],preserved_AL04_unchanged=True,
        status='pass_bounded_software_and_structural_controls' if not errors else 'failure_preserved',failures=errors,
        rows=rows,malformed_checks=malformed,summary_collision_comparisons=comparisons,
        supported_claim='Compatibility distinguishes certain named scalar summaries on declared inputs',
        adverse_result='Classical binary facet formula exactly substitutes for LP on all binary and known uniform block lifts',
        novelty='not_established',real_detection='not_evaluated',scientific_breakthrough=False,
        independent_v2_review='pending',
        resources=dict(elapsed_seconds=time.perf_counter()-start,threads=2,threadpools=pools,highs_threads=2,
            largest_explicit_constraint_bytes=max_bytes,process_peak_RSS='not_measured',
            numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version(),
            server_access=False,media_read=False,gpu_used=False,training_steps=0,
            cumulative_paid_cost_and_gpu_hours='unknown; unchanged'))
    save(output,result)
    print(json.dumps(dict(status=result['status'],failures=errors,comparisons=comparisons,
        elapsed_seconds=result['resources']['elapsed_seconds']),indent=2))
    if errors:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--output',type=Path,default=OUT/'AL01_evidence.json');a=p.parse_args()
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    if cfg['threads']!=2 or cfg['temperature']!=.1:raise ValueError('Frozen resource/temperature contract')
    if a.mode=='prepare':prepare(cfg)
    else:run(cfg,a.output)

if __name__=='__main__':main()
