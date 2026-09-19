"""Exact enumeration of one predeclared illustrative distribution; no bootstrap run."""
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDER = ROOT/'research-plan/AL42_CLUSTER_MISSING_MASS_AUDIT_20260919.md'
OUT = ROOT/'research-plan/reviews/AL42_CLUSTER_MISSING_MASS_EXACT_20260919.json'


def quantile(atoms, alpha):
    assert 0 < alpha <= 1
    assert sum(mass for _,mass in atoms)==1
    cumulative=F(0)
    for point,mass in sorted(atoms):
        cumulative+=mass
        if cumulative>=alpha:
            return point
    raise AssertionError('unreachable')


def main():
    assert not OUT.exists(), 'Output already exists; do not overwrite or repeat'
    start=datetime.now(timezone.utc).isoformat()
    order_sha=hashlib.sha256(ORDER.read_bytes()).hexdigest()
    source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    # The only example is exactly the distribution in the already-written work order.
    rho, alpha, value=F(1,25),F(1,40),F(1,10)
    valid=[(value,F(1))]
    completed_left=[(F(-1),rho),(value,1-rho)]
    completed_right=[(value,1-rho),(F(1),rho)]
    checks=[]

    def check(name, condition):
        checks.append({'name':name,'passed':bool(condition)})
        assert condition,name

    qvalid=quantile(valid,alpha)
    qleft=quantile(completed_left,alpha)
    qright=quantile(completed_right,alpha)
    formula_left=F(-1) if alpha<=rho else quantile(valid,(alpha-rho)/(1-rho))
    formula_right=F(1) if alpha>1-rho else quantile(valid,alpha/(1-rho))
    check('valid_only_lower_equals_one_tenth',qvalid==value)
    check('left_completed_lower_equals_minus_one',qleft==F(-1))
    check('right_completed_lower_equals_one_tenth',qright==value)
    check('lower_quantile_formula_matches_enumeration',formula_left==qleft)
    check('upper_quantile_formula_matches_enumeration',formula_right==qright)
    check('positive_conditional_lower_does_not_force_positive_completion',qvalid>0 and qleft<0)
    check('same_declared_work_order_bytes_after_calculation',hashlib.sha256(ORDER.read_bytes()).hexdigest()==order_sha)
    result={'task_id':'AL42','started_at':start,'completed_at':datetime.now(timezone.utc).isoformat(),
            'scope':'one_exact_missing_mass_distribution_not_actual_bootstrap',
            'work_order_sha256':order_sha,'source_sha256':source_sha,'checks':checks,
            'invalid_probability':str(rho),'alpha':str(alpha),'valid_atom':str(value),
            'conditional_quantile':str(qvalid),'extreme_completion_quantile_interval':[str(qleft),str(qright)],
            'left_atoms':[[str(x),str(p)] for x,p in completed_left],
            'right_atoms':[[str(x),str(p)] for x,p in completed_right],
            'random_draws_performed':0,'empirical_AUROC_evaluations':0,
            'model_calls':0,'server_calls':0,'gpu_calls':0,'real_samples_accessed':False,
            'confidence_interval_measured':False,'frequentist_coverage_certified':False,
            'independent_scientific_review':False,'scientific_breakthrough':False}
    with OUT.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
    print(json.dumps({'checks_executed':len(checks),'conditional_lower':str(qvalid),
                      'completion_lower_envelope':str(qleft),'bootstrap_or_model_run':False}))


if __name__=='__main__':
    main()
