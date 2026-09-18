"""Materialize the AL18 work-order cases, exact expectations and dependencies.
Does not import the candidate numerical-contract module or execute probes.
"""
from datetime import datetime,timezone
from fractions import Fraction as F
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(value),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def bound(value,basis='analytic_mock'):
    return dict(value=value,basis=basis)
def endpoints(ab,ba,da,db):
    return dict(hat_ab=ab,hat_ba=ba,bounds=dict(delta_ab=bound(da),delta_ba=bound(db),rho_K=bound(F(0),'exact_rational_arithmetic')))
def quotient(hn,hd,bn,bd):
    return dict(hat_n=hn,hat_d=hd,bounds=dict(B_N=bound(bn),B_D=bound(bd),
        rho_q=bound(F(0),'exact_rational_arithmetic'),rho_s=bound(F(0),'exact_rational_arithmetic')))


def identity_trace(h,epsilon,signs):
    """Frozen closed-form observations, independent of runtime probe callbacks."""
    a,b,ab,ba=signs;x=(F(1,2),F(1,4))
    return dict(x=x,ra0=(x[0]+a*epsilon,x[1]),rb0=(x[0]+b*epsilon,x[1]),
        pa=(x[0]+h*a*epsilon,x[1]),pb=(x[0]+h*b*epsilon,x[1]),
        rab=(x[0]+h*b*epsilon+ab*epsilon,x[1]),rba=(x[0]+h*a*epsilon+ba*epsilon,x[1]),
        uab=(x[0]+h*(b+ab)*epsilon,x[1]),uba=(x[0]+h*(a+ba)*epsilon,x[1]))


def n2payload(h,epsilon,signs):
    bounds={name:bound(epsilon) for name in ('eps_a0','eps_b0','eps_ab','eps_ba')}
    bounds.update({name:bound(F(1)) for name in ('L_a','L_b')})
    bounds.update({name:bound(F(0),'exact_rational_arithmetic') for name in ('rho_a','rho_b','rho_ab','rho_ba','rho_K')})
    return dict(observations=identity_trace(h,epsilon,signs),bounds=bounds)


def main():
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    work=MAIN/'research-plan/AL18_OR1_NUMERICAL_CPU_20260919.md'
    if sha(work)!=cfg['work_order_sha256'] or sha(MAIN/'research-plan/WORK_PLAN.md')!=cfg['plan_sha256']:
        raise ValueError('Canonical work order/plan changed')
    eta=F(cfg['eta']);delta=F(cfg['delta']);epsilon=F(cfg['epsilon']);rows=[]
    def add(family,h,label,kind,payload,expect,**extra):
        rows.append(dict(id=f'F{family}__h{h}__{label}',family=family,nominal_h=h,h=h,eta=eta,
            kind=kind,payload=payload,expected=expect,**extra))
    for h_text in cfg['steps']:
        h=F(h_text)
        for family,true_a in ((1,F(1,8)),(2,F(0))):
            for sa,sb in itertools.product((-1,1),repeat=2):
                oa=(true_a+sa*delta,F(0));ob=(sb*delta,F(0));khat=(true_a+(sa-sb)*delta)/(h*h)
                bk=2*delta/(h*h);truth=true_a/(h*h)
                add(family,h,f'{sa}_{sb}','N1',endpoints(oa,ob,delta,delta),
                    dict(status='conditional_interval' if family==1 else 'residual_energy_not_certified_positive',
                        B_K=bk,K_hat=(khat,F(0)),truth_K=(truth,F(0)),actual_error=abs(khat-truth),tight=abs(sa-sb)==2),
                    signs=(sa,sb),true_endpoints=((true_a,F(0)),(F(0),F(0))))
        for signs in itertools.product((-1,1),repeat=4):
            a,b,ab,ba=signs;coefficient=b+ab-a-ba;khat=coefficient*epsilon/h
            add(3,h,'_'.join(map(str,signs)),'N2',n2payload(h,epsilon,signs),
                dict(status='residual_energy_not_certified_positive',B_K=4*epsilon/h,K_hat=(khat,F(0)),
                    truth_K=(F(0),F(0)),actual_error=abs(khat),tight=abs(coefficient)==4,
                    delta_ab=2*h*epsilon,delta_ba=2*h*epsilon),
                signs=signs,epsilon=epsilon,mock_probe_calls=4)
        for sign in (-1,1):
            z=sign*F(1,64);hn=F(1,4096);bn=F(3,4096);hd=F(1,4)+eta
            payload=dict(hat_z=(z,),bounds=dict(B_z=bound(F(1,64)),rho_N=bound(F(0),'exact_rational_arithmetic')))
            add(4,h,str(sign),'N4_then_N5',payload,
                dict(status='residual_energy_not_certified_positive',B_N=bn,numerator_interval=(F(0),F(1,1024)),
                    truth_n=F(0),truth_q=F(0),B_q=bn/hd,ratio_interval=(F(0),F(1,1024)/hd)),
                ratio_denominator=hd)
        hn,bn=F(1,4),F(1,16);hd,bd=F(1,2)+eta,F(1,8)
        bq=bn/(hd-bd)+hn*bd/(hd*(hd-bd));qhat=hn/hd
        for sn,sd in itertools.product((-1,1),repeat=2):
            truth_n=hn+sn*bn;truth_d=hd+sd*bd;truth_q=truth_n/truth_d
            add(5,h,f'{sn}_{sd}','N5',quotient(hn,hd,bn,bd),
                dict(status='conditional_interval',B_q=bq,q_hat=qhat,truth_n=truth_n,truth_d=truth_d,
                    truth_q=truth_q,ratio_interval=(qhat-bq,qhat+bq),sign_stability='strict_positive'),corner=(sn,sd))
        add(6,h,'denominator_lower','N5',quotient(F(0),eta,F(0),2*eta),
            dict(status='denominator_lower_not_positive',denominator_lower=-eta))
        add(6,h,'eta_only','N5',quotient(F(0),eta,F(0),F(0)),
            dict(status='residual_energy_not_certified_positive',ratio_interval=(F(0),F(0)),
                response_energy_lower=F(0),denominator_residual_energy_lower=F(0),sign_stability='boundary_or_uncertain'))
        for name in cfg['family7_cases']:
            payload=endpoints((F(1,8),F(0)),(F(0),F(0)),delta,delta);kind='N1';actual_h=h;actual_eta=eta
            expected='invalid_input'
            if name=='unknown_endpoint':payload['bounds']['delta_ab']=bound(None,'unknown');expected='uncertified_bound'
            elif name=='unknown_L':payload=n2payload(h,epsilon,(1,1,1,1));payload['bounds']['L_a']=bound(None,'unknown');kind='N2';expected='uncertified_bound'
            elif name=='empirical_zero_bound':payload['bounds']['delta_ab']=bound(F(0),'empirical_repeat_agreement');expected='uncertified_bound'
            elif name=='negative_bound':payload['bounds']['delta_ab']=bound(-delta)
            elif name=='endpoint_nan':payload['hat_ab']=({'nonfinite':'nan'},F(0))
            elif name=='endpoint_inf':payload['hat_ab']=({'nonfinite':'inf'},F(0))
            elif name=='mix_inf':payload=n2payload(h,epsilon,(1,1,1,1));payload['observations']['pa']=({'nonfinite':'inf'},F(1,4));kind='N2'
            elif name=='energy_nan':payload=dict(hat_z=(F(1,64),),hat_n={'nonfinite':'nan'},bounds=dict(B_z=bound(F(1,64)),rho_N=bound(F(0),'exact_rational_arithmetic')));kind='N4'
            elif name=='denominator_inf':payload=quotient(F(1,4),{'nonfinite':'inf'},F(1,16),F(1,8));kind='N5'
            elif name=='h_zero':actual_h=F(0)
            elif name=='h_above_one':actual_h=F(5,4)
            elif name=='eta_zero':actual_eta=F(0)
            elif name=='eta_negative':actual_eta=-eta
            elif name=='bound_inf':payload['bounds']['delta_ab']=bound({'nonfinite':'inf'})
            elif name=='h_nan':actual_h={'nonfinite':'nan'}
            elif name=='eta_inf':actual_eta={'nonfinite':'inf'}
            else:raise ValueError(name)
            add(7,h,name,kind,payload,dict(status=expected),invalid_case=name)
            rows[-1]['h']=actual_h;rows[-1]['eta']=actual_eta
        payload=endpoints((delta,F(0)),(F(0),F(0)),None,F(0))
        payload['bounds']['delta_ab']['basis']='unknown'
        add(8,h,'repeat_biased','repeat_then_N1',payload,
            dict(status='uncertified_bound',repeat_gap=F(0),known_status='residual_energy_not_certified_positive',
                known_B_K=delta/(h*h),truth_K=(F(0),F(0))),
            repeat_readouts=(delta,delta),exact_endpoint=F(0),analytic_bias_bound=delta,endpoint_readout_calls=2)
    if len(rows)!=147:raise AssertionError('Unexpected fixed record count')
    save(OUT/'AL18_inputs.json',dict(records=rows,expected_mock_probe_calls=192,expected_repeat_endpoint_readouts=6,
        expected_public_contract_queries=156,expected_family_counts={str(i):sum(r['family']==i for r in rows) for i in range(1,9)},
        preparation='Analytical Fraction fixtures only; candidate module not imported or run',
        nonfinite_encoding='Tagged values decode to actual NaN/Inf only in invalid-input tests'))
    source=[HERE/'bounds.py',HERE/'config.json',HERE/'freeze.py',HERE/'run.py',OUT/'AL18_inputs.json',OUT/'AL18_protocol.md']
    preserved={}
    for p in OUT.rglob('*'):
        if p.is_file() and p.relative_to(OUT).parts[0].startswith(('AL01','AL04','AL06','AL09','AL12','AL15')):
            preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    for p in (ROOT/'research-runtime/algorithm_candidates/or1_cpu').glob('*'):
        if p.is_file():preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    import fractions
    deps=[Path(sys.executable),Path(fractions.__file__)]
    context=['research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json','research-plan/AL18_OR1_NUMERICAL_CPU_20260919.md',
        'research-plan/reviews/AL15_REVIEW_20260919.md','research-plan/reviews/AL16_OR1_NUMERICAL_REVIEW_20260919.md']
    save(OUT/'AL18_freeze.json',dict(frozen_at=datetime.now(timezone.utc).isoformat(),candidate_calls_before_freeze=0,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source},preserved=preserved,
        dependencies={str(p):sha(p) for p in deps},canonical_context={p:sha(MAIN/p) for p in context},
        mathematical_truth='Exact rational fixed mock definitions; no actual AE accuracy claim'))
    print(json.dumps(dict(records=len(rows),mock_probe_calls=192,repeat_readout_calls=6,public_contract_queries=156,candidate_calls_before_freeze=0)))

if __name__=='__main__':main()
