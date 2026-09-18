"""Stdlib-only materialization of declared inputs/analytic expectations; no core import."""
from datetime import datetime,timezone
from fractions import Fraction as F
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')
DRAFT=OUT/'AL12_cpu_preregistration.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def f(x):return F(str(x))
def support(n):
    return dict(slot_ids=[f'mock_coordinate_{i}' for i in range(n)],window=[0,1],clock_policy='mock_declared_grid',
        condition_id='mock_none',intermediate_lossy_codec=False,cache_policy='fresh_empty_per_call')


def embed_vector(values,n,perm):
    padded=[f(x) for x in values]+[F(0)]*(n-len(values))
    return [padded[i] for i in perm]


def operators(family,case,n,perm,base):
    slots=[perm.index(i) for i in range(base)]
    if 'A' in case:
        specs=[]
        for name,matrix in [('a',case['A']),('b',case['B'])]:
            full=[[F(int(i==j)) for j in range(n)] for i in range(n)]
            for i in range(base):
                for j in range(base):full[i][j]=f(matrix[i][j])
            full=[[float(full[i][j]) for j in perm] for i in perm]
            specs.append(dict(name=name,kind='linear',matrix=full,deterministic=True))
    elif family=='constant_translation':
        specs=[dict(name=name,kind='translation',offset=[float(x) for x in embed_vector(case[key],n,perm)],deterministic=True)
               for name,key in [('a','v_a'),('b','v_b')]]
    elif family=='nonlinear_remainder':
        specs=[dict(name=name,kind='nonlinear_'+name,active_slots=slots,deterministic=True) for name in ('a','b')]
    else:raise ValueError('Undeclared family')
    if family=='probe_order_swap':specs=specs[::-1]
    return specs


def expected(family,base_x,h,n,perm,eta):
    x=[f(v) for v in base_x];zero=[F(0)]*len(x)
    if family in ('linear_exact','noncommuting_but_redundant'):
        k=[x[0],-x[1]];va=[x[1],F(0)];vb=[F(0),x[0]]
    elif family=='constant_translation':k=zero;va=[F(1,4),F(0)];vb=[F(0),F(1,8)]
    elif family=='commuting_projection':k=zero;va=[F(0),F(0),-x[2]];vb=[F(0),-x[1],-x[2]]
    elif family in ('matched_scalar_errors','probe_order_swap','equal_output_distribution'):
        k=[-x[1]/4,F(0),F(0)];va=[-x[0]/2,F(0),F(0)];vb=[x[1]/2-x[0],x[2]/2-x[1],-x[2]]
        if family=='probe_order_swap':k=[-v for v in k];va,vb=vb,va
    elif family=='nonlinear_remainder':
        k=[-x[0]**2,2*x[0]*x[1]+h*x[1]**2];va=[F(0),x[0]**2];vb=[x[1],F(0)]
    else:raise ValueError(family)
    energy=lambda v:sum(t*t for t in v)
    ek,ea,eb=energy(k),energy(va),energy(vb);den=ea+eb
    result=dict(K=[float(v) for v in embed_vector(k,n,perm)],
        K_exact=[str(v) for v in embed_vector(k,n,perm)],
        v_a=[float(v) for v in embed_vector(va,n,perm)],v_b=[float(v) for v in embed_vector(vb,n,perm)],
        energy_sum={key:float(value) for key,value in dict(K=ek,a=ea,b=eb,input=energy(x)).items()},
        energy_sum_exact={key:str(value) for key,value in dict(K=ek,a=ea,b=eb,input=energy(x)).items()},
        q_mean_fixed_eta=float(ek/(den+n*eta)),q_sum_fixed_eta=float(ek/(den+eta)),
        q_mean_scaled_eta=float(ek/(den+len(x)*eta)),
        q_mean_fixed_eta_exact=str(ek/(den+n*eta)),q_mean_scaled_eta_exact=str(ek/(den+len(x)*eta)))
    if family=='nonlinear_remainder':
        result['bracket']=[float(v) for v in embed_vector([-x[0]**2,2*x[0]*x[1]],n,perm)]
        result['remainder_norm_exact']=str(h*x[1]**2)
        result['remainder_norm']=float(h*x[1]**2)
    return result


def main():
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    if sha(MAIN/'research-plan/WORK_PLAN.md')!=cfg['plan_sha256']:
        raise ValueError('Canonical plan version changed before freeze')
    draft=json.loads(DRAFT.read_text(encoding='utf-8'))
    blob=subprocess.check_output(['git','show',cfg['draft_commit']+':'+str(DRAFT.relative_to(ROOT)).replace('\\','/')],cwd=ROOT)
    if sha(DRAFT)!=cfg['draft_sha256'] or hashlib.sha256(blob).hexdigest()!=cfg['draft_sha256']:
        raise ValueError('Final committed AL12 draft binding failed')
    families={row['id']:row for row in draft['cases']};records=[]
    for family,original in families.items():
        case=copy.deepcopy(families[original.get('reuse',original.get('probe_case',family))])
        if family=='equal_output_distribution':
            samples=[dict(x=x,audit_set=s,i=i) for s in ('Y0','Y1') for i,x in enumerate(original['output_multiset_'+s])]
        else:
            samples=[dict(x=x,i=i) for i,x in enumerate(case.get('x_pair',[case.get('x')]))]
        for variant in cfg['variants']:
            for sample in samples:
                x=sample['x'];base=len(x);n=base if variant['dimension']=='base' else variant['dimension']
                perm=list(range(n)) if variant['permutation']=='identity' else variant['permutation']
                for step in cfg['steps']:
                    h=f(step);ops=operators(family,case,n,perm,base)
                    record=dict(id=f"{family}__{variant['id']}__{sample.get('audit_set','sample')}_{sample['i']}__h{step}",
                        family=family,variant=variant['id'],base_dimension=base,dimension=n,
                        permutation=perm,base_x=x,x=[float(v) for v in embed_vector(x,n,perm)],
                        h=step,eta_mean=cfg['eta_mean'],operators=ops,support=support(n),
                        expected=expected(family,x,h,n,perm,f(cfg['eta_mean'])))
                    if 'audit_set' in sample:record['audit_only_set']=sample['audit_set']
                    records.append(record)
    if len(records)!=210:raise AssertionError('Expected exactly 210 four-call evaluations')
    base=next(r for r in records if r['family']=='linear_exact' and r['variant']=='development_base' and r['h']==.125)
    negatives=[]
    specs=[('input_nan',0),('unknown_clock',0),('declared_stochastic',0),('output_slots',1),('output_window',1),
           ('output_nan',1),('output_shape',1),('shared_cache_policy',0),('intermediate_lossy',0),('forbidden_producer_field',0)]
    for name,calls in specs:
        row={key:copy.deepcopy(base[key]) for key in ('x','operators','h','eta_mean','support')}
        row.update(id=name,expected_exception='ContractError',expected_probe_calls=calls)
        if name=='input_nan':row['x'][0]={'float64_special':'NaN'}
        if name=='unknown_clock':row['support']['clock_policy']='unknown'
        if name=='declared_stochastic':row['operators'][0]['deterministic']=False
        if name.startswith('output_'):
            row['operators'][0]['behavior']={'output_slots':'slot_mismatch','output_window':'window_mismatch','output_nan':'nan_output','output_shape':'shape_mismatch'}[name]
        if name=='shared_cache_policy':row['support']['cache_policy']='shared_across_branches'
        if name=='intermediate_lossy':row['support']['intermediate_lossy_codec']=True
        if name=='forbidden_producer_field':row['support']['production_decoder_id']='forbidden_mock_id'
        negatives.append(row)
    arms=[]
    for name,label,depth,parent,origin in [('C',0,0,None,'camera'),('R',0,1,'C','camera'),('R2',0,2,'R','camera'),
                                          ('G',1,1,None,'generated'),('G2',1,2,'G','generated')]:
        chain=(['native_export']+['R_i']*depth) if label==0 else ['D_i_generate']+['R_i']*(depth-1)
        arms.append(dict(arm=name,origin=origin,origin_label=label,known_D_count=depth,parent=parent,
            root_origin_id='mock_'+origin,transform_chain=chain+['A_kappa'],historical_other_processing='unknown'))
    bad_arms=[]
    for name in ('relabel_R_fake','codec_before_base','different_final_codec','unknown_D_count'):
        data=copy.deepcopy(arms)
        if name=='relabel_R_fake':data[1]['origin_label']=1
        if name=='codec_before_base':data[2]['transform_chain']=['native_export','A_kappa','R_i','R_i']
        if name=='different_final_codec':data[4]['transform_chain'][-1]='different_A'
        if name=='unknown_D_count':data[1]['known_D_count']=None
        bad_arms.append(dict(id=name,arms=data,expected='reject_main_mock_comparison'))
    repeats=[dict(id='normal_a',operator=base['operators'][0],expected_equal=True),
             dict(id='normal_b',operator=base['operators'][1],expected_equal=True),
             dict(id='declared_deterministic_alternating',operator=dict(base['operators'][0],behavior='alternating'),expected_equal=False)]
    save(OUT/'AL15_inputs.json',dict(records=records,negative_contracts=negatives,
        repeat_diagnostics=dict(x=base['x'],support=base['support'],cases=repeats),
        valid_mock_arms=arms,invalid_mock_arm_sets=bad_arms,
        expected_core_calls=840,expected_negative_contract_calls=4,expected_repeat_diagnostic_calls=6,
        scientific_labels_assigned=False,nan_encoding='Tagged NaN denotes actual invalid float64 input; not missing data'))
    source_paths=[HERE/'core.py',HERE/'config.json',HERE/'freeze.py',HERE/'run.py',OUT/'AL15_protocol.md',OUT/'AL15_inputs.json',DRAFT]
    preserved={}
    for p in OUT.rglob('*'):
        if p.is_file() and p.relative_to(OUT).parts[0].startswith(('AL01','AL04','AL06','AL09','AL12')):
            preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    for folder in ('al01_v2','al04','al06'):
        for p in (ROOT/'research-runtime/algorithm_candidates'/folder).glob('*'):
            if p.is_file():preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    spec=importlib.util.find_spec('numpy');npdir=Path(spec.origin).parent
    dependency_paths=[Path(sys.executable),Path(spec.origin)]
    dependency_paths+=list((npdir/'_core').glob('_multiarray_umath*.pyd'))
    dependency_paths+=list((npdir.parent/'numpy.libs').glob('*openblas*.dll'))
    dependency_paths+=list(npdir.parent.glob('numpy-*.dist-info/METADATA'))
    adopted=['research-plan/WORK_PLAN.md','research-plan/AL15_OR1_CPU_WORK_ORDER_20260919.md',
             'research-plan/reviews/AL12_REVIEW_20260919.md','research-plan/task-hermes/project.json']
    save(OUT/'AL15_freeze.json',dict(frozen_at=datetime.now(timezone.utc).isoformat(),
        current_dispatch_authorizes_this_new_package=True,archived_draft_not_modified=True,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source_paths},preserved=preserved,
        canonical_context={p:sha(MAIN/p) for p in adopted},
        dependency_files={str(p):sha(p) for p in dependency_paths},numpy_distribution=importlib.metadata.version('numpy'),
        preparation='Stdlib Fraction expectations and materialized inputs only; core/NumPy never imported by this script',
        candidate_evaluations_before_freeze=0))
    print(json.dumps(dict(records=len(records),core_calls_expected=840,contract_calls_expected=4,extra_diagnostic_calls_expected=6,
        dependency_hashes=len(dependency_paths),candidate_evaluations_before_freeze=0)))

if __name__=='__main__':main()
