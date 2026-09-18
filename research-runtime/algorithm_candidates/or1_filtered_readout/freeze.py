"""AL25 inputs and independent analytic/Fraction references; no candidate/NumPy import."""
from datetime import datetime,timezone
from fractions import Fraction as F
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'research-runs/algorithm_search_20260918'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')
FILTERS=('identity','laplacian','sobel_x','sobel_y')
COEFFICIENTS=(1,2,-1)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def save(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(data),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def exact_float(value):
    value=F(value);result=float(value)
    if F.from_float(result)!=value:raise ValueError('A frozen response input is not exactly representable')
    return result
def field(pattern,x,y):
    return {'zero':F(0),'constant':F(1),'x':x,'bowl':x*x+y*y,'u':x+y}[pattern]
def analytic(pattern,name,x,y):
    if name=='identity':return field(pattern,x,y)
    if pattern in ('zero','constant'):return F(0)
    if name=='laplacian':return F(1,16) if pattern=='bowl' else F(0)
    if name=='sobel_x':return x/2 if pattern=='bowl' else F(1,4)
    if name=='sobel_y':return y/2 if pattern=='bowl' else F(1,4) if pattern=='u' else F(0)
    raise ValueError(name)
def raw_array(pattern,scale,t=2,h=5,w=5):
    return [[[[exact_float(scale*c*field(pattern,F(col-2,4),F(row-2,4))) for c in COEFFICIENTS]
        for col in range(w)] for row in range(h)] for _ in range(t)]
def filtered_array(pattern,scale,name):
    return [[[[scale*c*analytic(pattern,name,F(col-2,4),F(row-2,4)) for c in COEFFICIENTS]
        for col in range(1,4)] for row in range(1,4)] for _ in range(2)]
def flat(array):return [value for t in array for row in t for pixel in row for value in pixel]


def main():
    spec_path=OUT/'AL25_readout_spec.json';spec=json.loads(spec_path.read_text(encoding='utf-8'))
    work=MAIN/'research-plan/AL25_OR1_FILTERED_READOUT_CPU_20260919.md'
    if sha(work)!=spec['work_order_sha256']:raise ValueError('Canonical AL25 work-order hash changed')
    eta=F(spec['eta_mathematical']);eta_binary=F.from_float(spec['eta_float_literal'])
    declarations=[('zero','zero',[0,0,0,0]),('constant','constant',[1,0,1,0]),
        ('ramp_x','x',[1,0,1,0]),('quadratic','bowl',[1,0,1,0]),
        ('positive_inner','u',[2,1,1,0]),('negative_inner','u',[-1,1,1,0]),
        ('near_cancellation','constant',[1+F(1,2**28),1,1,0])]
    records=[]
    for name,pattern,scale in declarations:
        scales=dict(zip(('d_a','d_b','v_a','v_b'),map(F,scale)))
        actual={key:raw_array(pattern,value) for key,value in scales.items()}
        reference=[]
        for filt in FILTERS:
            fields={key:filtered_array(pattern,value,filt) for key,value in (scales|{'K':scales['d_a']-scales['d_b']}).items()}
            values={key:flat(value) for key,value in fields.items()};count=len(values['K'])
            energy=lambda key:sum((x*x for x in values[key]),F(0))/count
            n,a,b,ea,eb=[energy(key) for key in ('K','d_a','d_b','v_a','v_b')]
            c=sum((x*y for x,y in zip(values['d_a'],values['d_b'])),F(0))/count
            if n!=a+b-2*c:raise AssertionError('Analytic reference energy identity failed')
            d=ea+eb+eta;db=ea+eb+eta_binary
            reference.append(dict(filter=filt,filtered_fields=fields,support_elements=count,
                N=n,E_a=ea,E_b=eb,A=a,B=b,C=c,D=d,z=(a/d,b/d,c/d),q=n/d,
                D_binary_eta=db,q_binary_eta=n/db,compact_numerator=n,
                eta_only=ea+eb==0))
        records.append(dict(id=name,pattern=pattern,scales=scales,fields=actual,reference=reference,
            mode='cancellation_diagnostic' if name=='near_cancellation' else 'normal',
            reference_basis='Independent analytic stencil responses and Fraction sums, not candidate filtering'))
    bad_shape=copy.deepcopy(records[1]['fields']);bad_shape['d_b']=bad_shape['d_b'][:1]
    bad_nan=copy.deepcopy(records[0]['fields']);bad_nan['d_a'][0][2][2][0]={'nonfinite':'nan'}
    short={key:raw_array('zero',F(0),h=2) for key in ('d_a','d_b','v_a','v_b')}
    invalid=[dict(id='different_shape',fields=bad_shape,expected_code='shape_mismatch'),
        dict(id='NaN_input',fields=bad_nan,expected_code='nonfinite_input'),
        dict(id='spatial_edge_under_3',fields=short,expected_code='empty_valid_support')]
    save(OUT/'AL25_inputs.json',dict(records=records,invalid_inputs=invalid,eta_exact=eta,eta_binary=eta_binary,
        expected_common_support_shape=[2,3,3,3],expected_support_elements=54,expected_filter_applications=140,
        repeated_time_slots_are_not_independent_samples=True,candidate_calls_before_freeze=0))
    paths=[HERE/'readout.py',HERE/'freeze.py',HERE/'run.py',spec_path,OUT/'AL25_protocol.md',OUT/'AL25_inputs.json']
    preserved={}
    prefixes=('AL01','AL04','AL06','AL09','AL12','AL15','AL18','AL20','AL24')
    for path in OUT.rglob('*'):
        if path.is_file() and path.relative_to(OUT).parts[0].startswith(prefixes):
            preserved[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    for folder in ('or1_cpu','or1_numerics','or1_baseline_audit','or1_matching_reference'):
        for path in (ROOT/'research-runtime/algorithm_candidates'/folder).glob('*'):
            if path.is_file():preserved[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    np_spec=importlib.util.find_spec('numpy');npdir=Path(np_spec.origin).parent
    dependencies=[Path(sys.executable),Path(np_spec.origin)]+list((npdir/'_core').glob('_multiarray_umath*.pyd'))
    dependencies+=list((npdir.parent/'numpy.libs').glob('*openblas*.dll'))+list(npdir.parent.glob('numpy-*.dist-info/METADATA'))
    context=['research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json','research-plan/AL25_OR1_FILTERED_READOUT_CPU_20260919.md',
        'research-plan/reviews/AL20_AL24_REVIEW_20260919.md','research-plan/reviews/AL16_OR1_NUMERICAL_REVIEW_20260919.md',
        'research-plan/reviews/AL19_CLAMP_COORDINATES_REVIEW_20260919.md']
    save(OUT/'AL25_freeze.json',dict(frozen_at=datetime.now(timezone.utc).isoformat(),candidate_calls_before_freeze=0,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths},preserved=preserved,
        dependency_files={str(p):sha(p) for p in dependencies},numpy_version=importlib.metadata.version('numpy'),
        canonical_context={p:sha(MAIN/p) for p in context},
        reference_scope='Analytic polynomial/constant fields, signed responses, exact rational energies; no AE bound'))
    print(json.dumps(dict(cases=len(records),invalid_cases=len(invalid),raw_elements_per_field=150,support_elements=54,candidate_calls_before_freeze=0)))

if __name__=='__main__':main()
