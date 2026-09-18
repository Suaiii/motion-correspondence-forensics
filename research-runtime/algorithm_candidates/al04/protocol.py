"""AL04 fixed input generator and audit harness; no new candidate implementation.

prepare freezes all inputs before run invokes the read-only H-J reference.
H-T candidate integration is deliberately separate from baseline arithmetic.
"""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '2'
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
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
from threadpoolctl import threadpool_info, threadpool_limits

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'research-runs/algorithm_search_20260918'
REF = ROOT / 'research-plan/fallback-runtime/joint_marginal_reference.py'
PAIRS = ((0, 1), (1, 2), (0, 2))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def load_reference(cfg):
    if sha(REF) != cfg['reference_sha256']:
        raise ValueError('Frozen H-J source mismatch; do not silently update')
    spec = importlib.util.spec_from_file_location('al04_readonly_hj', REF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.linprog
    # Only resource instrumentation: mathematical arrays/objective untouched.
    def capped_linprog(*args, **kwargs):
        options = dict(kwargs.pop('options', {}), threads=2, parallel=False)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=OptimizeWarning, message='Unrecognized options detected.*')
            return original(*args, options=options, **kwargs)
    module.linprog = capped_linprog
    return module


def projections(g):
    return np.stack([g.sum(2), g.sum(0), g.sum(1)])


def domain(q, support, tol):
    q = np.asarray(q, float)
    if q.ndim != 3 or q.shape[0] != 3 or q.shape[1] != q.shape[2]:
        return 'invalid_shape'
    m = q.shape[1]
    if not 2 <= m <= 8 or not np.isfinite(q).all() or np.min(q) < 0:
        return 'invalid_numeric_input'
    if not all(support):
        return 'unsupported_missing_support'
    if max(np.max(abs(q.sum(1)-1/m)), np.max(abs(q.sum(2)-1/m))) > tol:
        return 'unsupported_mass'
    return 'supported'


def baseline_q(q):
    m = len(q[0]); p = m*q
    gaps = [p[0]@p[1]-p[2], p[2]@p[1].T-p[0], p[0].T@p[2]-p[1]]
    first, second = p[2], p[0]@p[1]
    middle = (first+second)/2
    def kl(x):
        nz = x > 0
        return float(np.sum(x[nz]*np.log(x[nz]/middle[nz]))/m)
    return dict(multiplicative_js=.5*(kl(first)+kl(second)),
                all_cycle_l1=[float(abs(x).sum()/m) for x in gaps],
                pair_entropy=[float(-np.sum(x[x>0]*np.log(x[x>0]))) for x in q],
                uniform_mass_error=float(max(abs(q.sum(1)-1/m).max(), abs(q.sum(2)-1/m).max())))


def reindex_q(q, perms):
    return np.stack([q[k][np.ix_(perms[a], perms[b])] for k, (a,b) in enumerate(PAIRS)])


def generated_cases(cfg, ref):
    cases = []
    def add(case_id, split, family, q, expected, **extra):
        cases.append(dict(id=case_id, split=split, family=family, kind='HJ',
            information=['Q_ab', 'Q_bc', 'Q_ac', 'declared_uniform_masses', 'support_metadata'],
            q=q.tolist(), full_support=[True]*3, expected=expected, **extra))
    for split in ('development', 'independent_check'):
        rng = np.random.default_rng(cfg[split]['seed'])
        for m in cfg[split]['sizes']:
            prefix = f'{split}_m{m}'
            g = np.zeros((m,m,m))
            for weight in cfg['mixture_weights']:
                maps = [rng.permutation(m) for _ in range(3)]
                g[maps[0], maps[1], maps[2]] += weight/m
            alpha = cfg['uniform_mixture']
            g = (1-alpha)*g+alpha/m**3
            qs = projections(g)
            add(prefix+'_multimodal', split, 'compatible_multimodal', qs, 'zero', witness=g.tolist())
            # Incompatible: ab and bc equality; ac nonidentity cyclic shift.
            hard = np.stack([np.eye(m)/m, np.eye(m)/m, np.roll(np.eye(m),1,axis=1)/m])
            eps = cfg['incompatible_uniform_noise']
            bad = (1-eps)*hard+eps/m**2
            excess = float(np.trace(bad[0])+np.trace(bad[1])+1-np.trace(bad[2])-2)
            add(prefix+'_incompatible', split, 'incompatible_marginals', bad, 'positive',
                witness_event_excess=excess, distance_lower_bound=2*excess/3)
            for name, base in [('multimodal',qs), ('incompatible',bad)]:
                perms = [rng.permutation(m) for _ in range(3)]
                add(prefix+'_'+name+'_reindex', split, 'consistent_reindex', reindex_q(base,perms),
                    'invariant', compare_to=prefix+'_'+name, permutations=[p.tolist() for p in perms])
            features = rng.normal(size=(m,3))
            # Input generation only: no joint_distance call in prepare.
            static = ref.symmetric_kernel_coupling(features, cfg['temperature'])
            add(prefix+'_static', split, 'positive_temperature_static', np.stack([static]*3), 'zero',
                features=features.tolist(), temperature=cfg['temperature'])
            rotation = np.linalg.qr(rng.normal(size=(3,3)))[0]
            for name, transformed in [('rotation',features@rotation), ('sign',-features)]:
                qnew = ref.symmetric_kernel_coupling(transformed, cfg['temperature'])
                add(prefix+'_'+name, split, 'shared_feature_coordinate_change', np.stack([qnew]*3),
                    'invariant', compare_to=prefix+'_static', features=transformed.tolist())
            shifts = [np.roll(np.arange(m), k) for k in (0,1,2)]
            add(prefix+'_translation', split, 'ideal_cyclic_translation', reindex_q(np.stack([static]*3),shifts),
                'invariant', compare_to=prefix+'_static')
            mass = np.arange(1,m+1,dtype=float);mass/=mass.sum()
            nonuniform = np.stack([np.diag(mass)]*3)
            add(prefix+'_nonuniform', split, 'nonuniform_compatible', nonuniform, 'reject',
                domain_reason='unsupported_mass', known_general_joint='Gamma[i,i,i]=mass[i]', masses=mass.tolist())
            partial = qs*.8
            add(prefix+'_partial', split, 'partial_mass', partial, 'reject', domain_reason='unsupported_mass', retained_mass=.8)
            hidden = dict(id=prefix+'_missing', split=split, family='missing_support', kind='HJ',
                information=['Q_ab','Q_bc','Q_ac','support_metadata'], q=qs.tolist(), full_support=[True,False,True],
                expected='reject', domain_reason='unsupported_missing_support',
                reason='Uniform-looking renormalized Q does not certify observed support')
            cases.append(hidden)
    # Exact distribution example: all coarse pair tables equal, while the law
    # of the jointly observed tuple of sample pairs differs.
    states = np.array(list(itertools.product([-1.,1.], repeat=3)))
    for split, eta in [('development',.6), ('independent_check',.35)]:
        plus = (1+eta*np.prod(states,axis=1))/8
        minus = (1-eta*np.prod(states,axis=1))/8
        cases.append(dict(id=split+'_pair_law', split=split, kind='information_law',
            family='pair_marginals_vs_joint_observation', states=states.tolist(),
            probabilities=[plus.tolist(),minus.tolist()], eta=eta,
            information=['Declared coarse probability tables or full shared-sample pair tuple; never interchangeable']))
        rng = np.random.default_rng(cfg[split]['seed']+11)
        m = 8
        # Ambiguous observed descriptors, independent of payload; no true paths
        # supplied to any candidate. Fresh deterministic inputs, not old AL02 fixture calls.
        base_keys = rng.normal(size=(m,5))
        keys = np.stack([base_keys+.12*rng.normal(size=(m,5)) for _ in range(3)])
        ab = np.repeat(np.array(list(itertools.product([-1.,1.],repeat=2))),2,axis=0)
        payload = np.zeros((3,m,2));payload[:,:,0]=np.c_[ab,ab[:,0]*ab[:,1]].T
        perms = [rng.permutation(m) for _ in range(3)]
        keys = np.stack([keys[t,perms[t]] for t in range(3)])
        payload = np.stack([payload[t,perms[t]] for t in range(3)])
        variants = [('base',keys,payload,'record'),('sign',keys,-payload,'signed_flip'),
                    ('time_reverse',keys[::-1],payload[::-1],'record'),
                    ('erased_keys',np.ones_like(keys),payload,'record')]
        for scale in cfg['payload_scales']:
            variants.append((f'scale_{scale}',keys,payload*scale,'cubic_scaling'))
        rot = np.linalg.qr(rng.normal(size=(2,2)))[0]
        variants.append(('rotation',keys,payload@rot,'payload_rotation'))
        wrong = keys.copy(); wrong[1]=np.roll(wrong[1],1,axis=0)
        variants.append(('wrong_keys',wrong,payload,'record'))
        for name,k,z,expected in variants:
            cases.append(dict(id=split+'_HT_'+name, split=split, kind='HT_input', family=name,
                keys=k.tolist(), payload=z.tolist(), full_support=[True]*3, expected=expected,
                information=['observed_keys','payload','temperature','support_metadata'],
                prohibited_inputs=['label','true_trajectory','oracle_W','generating_probability'],
                compare_to=split+'_HT_base' if name!='base' else None))
    for case in cases:
        case['input_record_sha256']=digest(case)
    return cases


def ordinary_controls(keys,z,tau):
    # Baselines only. No candidate conditional/max-entropy statistic implemented.
    normalized=keys/np.maximum(np.linalg.norm(keys,axis=2,keepdims=True),1e-12)
    transitions=[]
    for a,b in PAIRS:
        x=normalized[a]@normalized[b].T/tau;x-=x.max(1,keepdims=True)
        p=np.exp(x);transitions.append(p/p.sum(1,keepdims=True))
    m=z.shape[1]
    w=transitions[0][:,:,None]*transitions[1][None,:,:]/m
    def tensor(weight):
        masses=[weight.sum((1,2)),weight.sum((0,2)),weight.sum((0,1))]
        centered=[z[t]-masses[t]@z[t] for t in range(3)]
        return np.einsum('ijk,ip,jq,kr->pqr',weight,*centered,optimize=True)
    t=tensor(w)
    diagonal=np.zeros_like(w);diagonal[np.arange(m),np.arange(m),np.arange(m)]=1/m
    pooled=np.concatenate([keys,z],axis=2).reshape(3*m,-1)
    full=np.concatenate([keys,z],axis=2)
    unit=full/np.maximum(np.linalg.norm(full,axis=2,keepdims=True),1e-12)
    full_q=[]
    for a,b in PAIRS:
        x=unit[a]@unit[b].T/tau;x-=x.max(1,keepdims=True)
        p=np.exp(x);full_q.append(p/p.sum(1,keepdims=True))
    return dict(w=w.tolist(), ordinary_tensor=t.tolist(), ordinary_norm=float(np.linalg.norm(t)),
        unaligned_norm=float(np.linalg.norm(tensor(diagonal))),
        full_static_second=(pooled.T@pooled/len(pooled)).tolist(),
        full_indexed_Q=np.stack(full_q).tolist(),
        key_entropy=float(-sum(np.sum(p*np.log(np.maximum(p,1e-300))) for p in transitions)/(3*m)),
        temporal_coordinate_third=((z-z.mean(0))**3).mean((0,1)).tolist(),
        candidate_status='pending', candidate_score=None,
        full_C_status='not_run; these are indexed Q observations, not a complete C detector')


def ht_adapter(candidate, case, cfg):
    """Future integration hook, not invoked in this frozen run.

    Caller must bind the candidate+transitive-source hashes in a NEW receipt.
    No override_w/label/truth arguments are passed; independent same-W arithmetic
    uses the returned W with the original inputs. This is not an AL02 rewrite.
    """
    k=np.asarray(case['keys']); z=np.asarray(case['payload'])
    if not all(case['full_support']):
        return dict(status='unsupported_missing_support', score=None)
    result=candidate.infer(k.copy(),z.copy(),cfg['temperature'])
    if not all(name in result for name in cfg['ht_candidate']['required_output']):
        raise ValueError('Incomplete candidate audit fields')
    w=np.asarray(result['w'])
    if w.shape!=(z.shape[1],)*3 or not np.isfinite(w).all() or w.min()<0 or abs(w.sum()-1)>1e-10:
        raise ValueError('Invalid returned W')
    masses=[w.sum((1,2)),w.sum((0,2)),w.sum((0,1))]
    c=[z[t]-masses[t]@z[t] for t in range(3)]
    ordinary=np.einsum('ijk,ip,jq,kr->pqr',w,*c,optimize=True)
    return dict(status='observed', candidate_score=float(result['score']),
                ordinary_same_W_norm=float(np.linalg.norm(ordinary)),
                candidate_tensor_error=float(abs(ordinary-result['tensor']).max()))


def prepare(cfg):
    ref=load_reference(cfg)
    with threadpool_limits(limits=2):
        cases=generated_cases(cfg,ref)
    save(OUT/'AL04_cases.json',dict(protocol_version=cfg['protocol_version'],cases=cases))
    sources=[HERE/'config.json',Path(__file__),OUT/'AL04_protocol.md',OUT/'AL04_cases.json',REF]
    save(OUT/'AL04_freeze.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        freeze_stage='all inputs and rules saved before any H-J LP or H-T candidate call',
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources},
        generator_calls_hj_distance=False,ht_candidate_status='pending',
        development_seed=cfg['development']['seed'],independent_check_seed=cfg['independent_check']['seed'],
        prior_knowledge='Known AL01 and AL02/AL03 qualitative outcomes were read; these are new protocol-check instances, not blind scientific confirmation'))
    print(json.dumps(dict(prepared_cases=len(cases),case_file_sha256=sha(OUT/'AL04_cases.json'))))


def run(cfg, output):
    if output.exists():
        raise FileExistsError(output)
    freeze=json.loads((OUT/'AL04_freeze.json').read_text(encoding='utf-8'))
    for path,expected in freeze['files'].items():
        if sha(ROOT/path)!=expected:
            raise ValueError('Frozen file changed: '+path)
    frozen_cases=json.loads((OUT/'AL04_cases.json').read_text(encoding='utf-8'))['cases']
    ref=load_reference(cfg)
    rows=[];by_id={};start=time.perf_counter();matrix_bytes=0
    with threadpool_limits(limits=2):
        pools=threadpool_info()
        for case in frozen_cases:
            inputs=dict(case);hashed=inputs.pop('input_record_sha256')
            if digest(inputs)!=hashed:
                raise ValueError('Case digest mismatch')
            row=dict(id=case['id'],split=case['split'],family=case['family'],input_sha256=hashed,checks={})
            check=row['checks']
            if case['kind']=='HJ':
                q=np.asarray(case['q']);m=q.shape[1]
                status=domain(q,case['full_support'],cfg['tolerances']['input_mass'])
                row['domain']=status
                if case['expected']=='reject':
                    check['expected_coverage_rejection']=status==case['domain_reason']
                    row.update(distance=None,classification='coverage_only_not_robustness',reference_called=False)
                else:
                    if status!='supported':
                        raise ValueError('Unexpected domain failure: '+case['id'])
                    fit=ref.joint_distance(q);g=fit.pop('gamma')
                    matrix_bytes=max(matrix_bytes,fit['largest_matrix_bytes'])
                    row.update(fit,baselines=baseline_q(q),fitted_gamma=g.tolist(),reference_called=True)
                    check['objective_recomputed']=abs(fit['distance']-np.abs(projections(g)-q).sum()/3)<cfg['tolerances']['lp_objective']
                    check['primal_nonnegative']=bool(g.min()>=-1e-9)
                    check['single_masses']=max(abs(g.sum(axes)-1/m).max() for axes in [(1,2),(0,2),(0,1)])<1e-8
                    if case['expected']=='zero':
                        check['joint_zero']=abs(fit['distance'])<cfg['tolerances']['lp_zero']
                    if 'witness' in case:
                        witness=np.asarray(case['witness'])
                        check['stored_joint_witness']=bool(witness.min()>=0 and np.abs(projections(witness)-q).max()<1e-10)
                        row['multiplication_disagrees']=row['baselines']['multiplicative_js']>1e-8
                    if case['expected']=='positive':
                        check['violated_compatibility_bound']=case['witness_event_excess']>1e-3
                        check['distance_respects_certificate']=fit['distance']>=case['distance_lower_bound']-1e-8
                    if case['expected']=='invariant':
                        other=by_id[case['compare_to']]
                        check['distance_invariant']=abs(fit['distance']-other['distance'])<cfg['tolerances']['invariance']
                        for field in ('multiplicative_js','all_cycle_l1','pair_entropy'):
                            check[field+'_invariant']=np.max(abs(np.asarray(row['baselines'][field])-np.asarray(other['baselines'][field])))<cfg['tolerances']['invariance']
                        # Feature transforms also preserve full Q. Row relabels
                        # are compared at the invariant scalar level, not bytes.
                        if case['family']=='shared_feature_coordinate_change':
                            original=next(c for c in frozen_cases if c['id']==case['compare_to'])
                            check['complete_Q_tuple_unchanged']=np.max(abs(q-np.asarray(original['q'])))<1e-10
                    row['classification']='restricted_structural_check'
            elif case['kind']=='information_law':
                states=np.asarray(case['states']);a,b=[np.asarray(x) for x in case['probabilities']]
                pair_a=projections(a.reshape(2,2,2));pair_b=projections(b.reshape(2,2,2))
                # Exact finite joint law of ((X,Y),(Y,Z),(X,Z)), not separate histograms.
                observed=np.array([[*s[[0,1]],*s[[1,2]],*s[[0,2]]] for s in states])
                distinct=len(np.unique(observed,axis=0))==len(states)
                row.update(coarse_pair_tuple_max_gap=float(abs(pair_a-pair_b).max()),
                    joint_observation_tuple_total_variation=float(.5*abs(a-b).sum()),
                    third_moments=[float(a@np.prod(states,axis=1)),float(b@np.prod(states,axis=1))],
                    observation_tuple_atoms=observed.tolist(),classification='information_contract_example',candidate_score=None)
                check['all_coarse_pair_tables_equal']=np.max(abs(pair_a-pair_b))<1e-10
                check['joint_tuple_preserves_triple']=distinct
                check['joint_tuple_laws_differ']=row['joint_observation_tuple_total_variation']>1e-3
            else:
                result=ordinary_controls(np.asarray(case['keys']),np.asarray(case['payload']),cfg['temperature'])
                row.update(result,classification='baseline_arithmetic_only')
                w=np.asarray(result['w'])
                check['W_probability']=bool(w.min()>=0 and abs(w.sum()-1)<1e-10)
                if case['compare_to']:
                    other=by_id[case['compare_to']]
                    t=np.asarray(result['ordinary_tensor']);old=np.asarray(other['ordinary_tensor'])
                    if case['expected']=='signed_flip':
                        check['ordinary_tensor_sign_flip']=abs(t+old).max()<1e-10
                        check['complete_indexed_Q_equal']=np.max(abs(np.asarray(result['full_indexed_Q'])-other['full_indexed_Q']))<1e-10
                        check['ordinary_norm_same']=abs(result['ordinary_norm']-other['ordinary_norm'])<1e-10
                        row['full_static_second_gap']=float(np.max(abs(np.asarray(result['full_static_second'])-other['full_static_second'])))
                    if case['expected']=='payload_rotation':
                        check['ordinary_norm_rotation_invariant']=abs(result['ordinary_norm']-other['ordinary_norm'])<1e-10
                    if case['expected']=='cubic_scaling':
                        scale=float(case['family'].split('_')[1])
                        check['ordinary_tensor_cubic_scaling']=abs(t-scale**3*old).max()<1e-10
            row['checks']={k:bool(v) for k,v in check.items()}
            row['protocol_checks_pass']=all(row['checks'].values())
            rows.append(row);by_id[row['id']]=row
    for path,expected in freeze['files'].items():
        if sha(ROOT/path)!=expected:
            raise ValueError('Input or source changed during evaluation: '+path)
    failures=[r['id'] for r in rows if not r['protocol_checks_pass']]
    output_record=dict(task_id='AL04',dispatch_id=cfg['dispatch_id'],plan_version=cfg['plan_version'],
        plan_sha256=cfg['plan_sha256'],observed_at_utc=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command=sys.argv,freeze_sha256=sha(OUT/'AL04_freeze.json'),frozen_files=freeze['files'],
        inputs_and_sources_unchanged=True,execution_status='completed',
        protocol_software_status='pass' if not failures else 'fail',failed_cases=failures,
        hypothesis_result='inconclusive_for_detector_mechanism_and_novelty',
        ht_candidate=cfg['ht_candidate'],known_reference_defect='symmetric_kernel_coupling does not validate finite tau>0; original left unchanged; positive tau frozen here',
        rows=rows,resources=dict(elapsed_seconds=time.perf_counter()-start,threads=2,threadpools=pools,
            highs_options=dict(threads=2,parallel=False),max_reference_matrix_bytes=matrix_bytes,
            process_peak_RSS='not_measured',python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
            server_access=False,media_read=False,gpu_used=False,training_steps=0,package_gpu_hours=0,
            cumulative_paid_cost_and_gpu_hours='unknown; not reset by this CPU-only package'),
        independent_scientific_review='pending; same author wrote and ran this protocol',
        scientific_breakthrough=False)
    save(output,output_record)
    print(json.dumps(dict(output=str(output),rows=len(rows),failures=failures,
        protocol_software_status=output_record['protocol_software_status'],
        elapsed_seconds=output_record['resources']['elapsed_seconds'])))
    if failures:
        raise SystemExit(1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['prepare','run'])
    parser.add_argument('--output',type=Path,default=OUT/'AL04_validation.json')
    args=parser.parse_args()
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    if cfg['threads']!=2 or not np.isfinite(cfg['temperature']) or cfg['temperature']<=0:
        raise ValueError('Frozen CPU/positive temperature contract violated')
    if args.mode=='prepare':prepare(cfg)
    else:run(cfg,args.output)


if __name__=='__main__':
    main()
