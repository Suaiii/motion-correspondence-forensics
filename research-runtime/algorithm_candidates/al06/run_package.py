"""AL06 bounded pre-frozen study: 24 inputs including controls, no adaptive search."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import warnings
import numpy as np
import scipy
from scipy.optimize import OptimizeWarning
from threadpoolctl import threadpool_limits,threadpool_info
import certificates as c

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'
REF=ROOT/'research-plan/fallback-runtime/joint_marginal_reference.py'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def pack(v):
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(value),f,indent=2,allow_nan=False,ensure_ascii=False);f.write('\n')
def now():return datetime.now(timezone.utc).isoformat()
def project(g):return np.stack([g.sum(2),g.sum(0),g.sum(1)])


def generate(cfg):
    records=[]
    for split in ('development','independent_check'):
        m=cfg[split]['m'];rng=np.random.default_rng(cfg[split]['seed']);local=[]
        for shape in cfg['compatible_dense_shapes']:
            g=rng.gamma(shape,1,size=(m,m,m));g/=g.sum()
            for iteration in range(10000):
                g*=((1/m)/g.sum((1,2)))[:,None,None]
                g*=((1/m)/g.sum((0,2)))[None,:,None]
                g*=((1/m)/g.sum((0,1)))[None,None,:]
                if max(abs(g.sum(axes)-1/m).max() for axes in ((1,2),(0,2),(0,1)))<1e-13:break
            else:raise RuntimeError('Fixed input balancing failed before experiment')
            local.append(dict(family='dense_joint_witness',Q=project(g),Gamma=g,shape=shape))
        for n in cfg['compatible_sparse_components']:
            g=np.zeros((m,m,m));weights=rng.dirichlet(np.ones(n));perms=[]
            for weight in weights:
                maps=[rng.permutation(m) for _ in range(3)];perms.append(maps)
                g[maps[0],maps[1],maps[2]]+=weight/m
            alpha=cfg['compatible_sparse_uniform_noise'];g=(1-alpha)*g+alpha/m**3
            local.append(dict(family='sparse_joint_witness',Q=project(g),Gamma=g,weights=weights,
                generation_permutations=perms,uniform_noise=alpha))
        for mixture in cfg['pair_mixtures']:
            q=np.zeros((3,m,m));perms=[]
            for edge in range(3):
                ep=[]
                for weight in mixture['weights']:
                    mapping=rng.permutation(m);ep.append(mapping)
                    q[edge,np.arange(m),mapping]+=weight/m
                perms.append(ep)
            alpha=mixture['uniform_noise'];q=(1-alpha)*q+alpha/m**2
            local.append(dict(family='independent_pair_mixtures',Q=q,generation=mixture,
                generation_permutations=perms,compatibility_label='unassigned_until_reference'))
        for pos in cfg['derived_reindex_parent_positions']:
            parent=local[pos];perms=[rng.permutation(m) for _ in range(3)]
            q=np.stack([parent['Q'][edge][np.ix_(perms[a],perms[b])] for edge,(a,b) in enumerate(c.PAIRS)])
            row=dict(family='consistent_reindex',Q=q,parent_position=pos,permutations=perms)
            if 'Gamma' in parent:row['Gamma']=parent['Gamma'][np.ix_(*perms)]
            local.append(row)
        pi=np.arange(1,m+1,dtype=float);pi/=pi.sum()
        nonuniform=np.einsum('i,j,k->ijk',pi,pi,pi)
        local.append(dict(family='nonuniform_domain_control',Q=project(nonuniform),Gamma=nonuniform,
            expected='reject_uniform_interface',masses=pi))
        if len(local)!=cfg['instances_per_split_including_reindex']:raise AssertionError('Input cap')
        for idx,row in enumerate(local):
            row.update(id=f'{split}_m{m}_{idx:02}',split=split,m=m,
                candidate_inputs=['Q_ab','Q_bc','Q_ac','declared_masses'],
                audit_only=['Gamma','generating_permutations','family'])
            if 'parent_position' in row:row['parent_id']=f'{split}_m{m}_{row["parent_position"]:02}'
            record=pack(row);record['record_sha256']=digest(record);records.append(record)
    if len(records)>cfg['max_total_Q_instances']:raise AssertionError('Input cap')
    return records


def reference(cfg):
    if sha(REF)!=cfg['reference_sha256']:raise ValueError('Frozen H-J reference changed')
    spec=importlib.util.spec_from_file_location('al06_original_hj',REF)
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref);lp=ref.linprog
    def capped(*args,**kwargs):
        kwargs['options']=dict(kwargs.get('options',{}),threads=2,parallel=False)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',category=OptimizeWarning,message='Unrecognized options detected.*')
            return lp(*args,**kwargs)
    ref.linprog=capped;return ref


def prepare(cfg):
    with threadpool_limits(limits=2):records=generate(cfg)
    save(OUT/'AL06_inputs.json',dict(records=records,maximum_total_including_controls=24,
        no_method_evaluated_during_generation=True,no_known_binary_block_lift=True))
    sources=[HERE/'certificates.py',HERE/'run_package.py',HERE/'config.json',OUT/'AL06_inputs.json',OUT/'AL06_design.md',REF]
    preserve={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in OUT.glob('*') if p.is_file() and p.name.startswith(('AL01','AL04'))}
    for path in (ROOT/'research-runtime/algorithm_candidates/al01_v2').glob('*'):
        if path.is_file():preserve[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    adopted=['research-plan/AL06_PROJECTED_CERTIFICATES_20260919.md','research-plan/reviews/AL01_REVIEW_20260919.md',
        'research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json']
    save(OUT/'AL06_freeze.json',dict(frozen_at=now(),pre_evaluation=True,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources},preserved=preserve,
        canonical_inputs_at_freeze={name:sha(MAIN/name) for name in adopted},
        source_reading=dict(url=cfg['source_url'],sections='3-4',equations='4-7',
            claim='balanced single-projection triangles are a restricted classical special case'),
        unmodified_known_issue='AL01-NUMPY-BOOL; no scalar-temperature helper used in AL06'))
    print(json.dumps(dict(frozen_records=len(records),files=len(sources))))


def run(cfg,output):
    if output.exists():raise FileExistsError(output)
    freeze=json.loads((OUT/'AL06_freeze.json').read_text(encoding='utf-8'))
    def unchanged():
        for rel,want in dict(freeze['files'],**freeze['preserved']).items():
            if sha(ROOT/rel)!=want:raise ValueError('Frozen/preserved file changed: '+rel)
    unchanged();ref=reference(cfg);start=time.perf_counter();rows=[];byid={};failures=[]
    records=json.loads((OUT/'AL06_inputs.json').read_text(encoding='utf-8'))['records']
    tol=cfg['comparison_tolerance'];largest_array=0
    with threadpool_limits(limits=2):
        pools=threadpool_info()
        for record in records:
            raw=dict(record);expected=raw.pop('record_sha256')
            if digest(raw)!=expected:raise ValueError('Record hash mismatch')
            q=np.asarray(record['Q']);row=dict(id=record['id'],family=record['family'],split=record['split'],
                input_sha256=expected,checks={})
            try:
                if record['family']=='nonuniform_domain_control':
                    try:c.certificate(q);rejected=False
                    except ValueError:rejected=True
                    row.update(status='coverage_rejection',L_bin=None,DJ=None,reference_called=False)
                    row['checks']['nonuniform_not_sent_to_uniform_formula']=rejected
                else:
                    begin=time.perf_counter();cert=c.certificate(q);lb_seconds=time.perf_counter()-begin
                    begin=time.perf_counter();fit=ref.joint_distance(q);lp_seconds=time.perf_counter()-begin
                    controls=c.simple_controls(q);checks=c.direct_pair_checks(q,cert)
                    lb=cert['lower_bound'];dj=fit['distance'];gap=dj-lb
                    largest_array=max(largest_array,cert['max_facet_array_bytes'],fit['largest_matrix_bytes'])
                    row.update(status='observed',certificate=cert,reference=fit,simple_controls=controls,
                        projection_checks=checks,L_bin=lb,DJ=dj,gap=gap,
                        missed_incompatibility=dj>tol and lb<=tol,strict_underestimate=gap>tol,
                        timings=dict(projection_seconds=lb_seconds,reference_seconds=lp_seconds,
                            interpretation='single small-array call including allocation; not a deployment speed benchmark'))
                    row['checks']['valid_lower_bound']=lb<=dj+tol
                    row['checks']['projected_pair_axis_order']=max(checks['coarse_loop_max_error'],checks['correlation_max_error'])<1e-10
                    row['checks']['all_eight_sign_choices_same_bound']=max(abs(x['bound']-lb) for x in checks['sign_representative_checks'])<1e-10
                    qcoarse=np.asarray(cert['witness_coarse_Q'])
                    row['checks']['coarse_uniform_marginals']=max(abs(qcoarse.sum(1)-.5).max(),abs(qcoarse.sum(2)-.5).max())<1e-10
                    if record['m']==4:
                        full=c.search_tables(c.tables(q,c.partitions(4,False)))
                        row['full_sign_family_bound']=full['lower_bound']
                        row['checks']['full_m4_family_same_as_representatives']=abs(full['lower_bound']-lb)<1e-10
                    if 'Gamma' in record:
                        witness=np.asarray(record['Gamma'])
                        row['checks']['generating_joint_witness']=witness.min()>=0 and abs(project(witness)-q).max()<1e-10
                        row['checks']['compatible_no_positive_certificate']=max(lb,abs(dj))<=tol
                    if 'parent_id' in record:
                        parent=byid[record['parent_id']]
                        row['checks']['reindex_Lbin_invariant']=abs(lb-parent['L_bin'])<tol
                        row['checks']['reindex_DJ_invariant']=abs(dj-parent['DJ'])<tol
                        row['checks']['reindex_all_simple_controls_invariant']=all(
                            np.max(abs(np.asarray(value)-np.asarray(parent['simple_controls'][name])))<tol for name,value in controls.items())
                    fitted=fit['gamma']
                    row['checks']['reference_objective_recomputed']=abs(np.abs(project(fitted)-q).sum()/3-dj)<1e-7
            except Exception as exc:
                row.update(status='failure',error=repr(exc));failures.append(row['id'])
            row['checks']={k:bool(v) for k,v in row['checks'].items()}
            if not all(row['checks'].values()):failures.append(row['id'])
            rows.append(row);byid[row['id']]=row
    unchanged()
    misses=[r['id'] for r in rows if r.get('missed_incompatibility')]
    under=[r['id'] for r in rows if r.get('strict_underestimate')]
    result=dict(task_id='AL06',dispatch_id=cfg['dispatch_id'],observed_at=now(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),command=sys.argv,
        freeze_sha256=sha(OUT/'AL06_freeze.json'),files=freeze['files'],preserved_files_unchanged=True,
        status='pass_bounded_classical_control' if not failures else 'failure_preserved',failures=failures,
        records=rows,missed_incompatibility_ids=misses,strict_underestimate_ids=under,
        omission_conclusion='misses_observed_on_fixed_inputs' if misses else 'no_miss_in_finite_inputs_not_completeness',
        method_classification='classical balanced projected triangle constraints; not a new algorithm',
        independent_scientific_review='pending',novelty=False,real_detection='not_evaluated',scientific_breakthrough=False,
        source_relation=freeze['source_reading'],known_unmodified_issue=freeze['unmodified_known_issue'],
        resources=dict(elapsed_seconds=time.perf_counter()-start,threads=2,threadpools=pools,highs_threads=2,
            max_explicit_array_bytes=largest_array,process_peak_RSS='not_measured',numpy=np.__version__,scipy=scipy.__version__,
            server_access=False,media_read=False,gpu_used=False,training_steps=0,cumulative_usage='unknown; unchanged'))
    if largest_array>cfg['max_explicit_array_bytes']:raise RuntimeError('Array resource cap exceeded')
    save(output,result)
    print(json.dumps(dict(status=result['status'],failures=failures,misses=misses,underestimates=under,
        rows=[dict(id=r['id'],DJ=r.get('DJ'),L_bin=r.get('L_bin'),gap=r.get('gap')) for r in rows],
        elapsed_seconds=result['resources']['elapsed_seconds']),indent=2))
    if failures:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--output',type=Path,default=OUT/'AL06_evidence.json');a=p.parse_args()
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    if cfg['threads']!=2 or cfg['max_total_Q_instances']!=24:raise ValueError('Frozen task caps')
    if a.mode=='prepare':prepare(cfg)
    else:run(cfg,a.output)

if __name__=='__main__':main()
