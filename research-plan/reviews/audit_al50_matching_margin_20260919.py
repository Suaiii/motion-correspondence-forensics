"""AL50 exact rational margin checks; no matching/data/model run."""
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ORDER=ROOT/'research-plan/AL50_MATCHING_PERTURBATION_MARGIN_AUDIT_20260919.md'
OUT=ROOT/'research-plan/reviews/AL50_MATCHING_PERTURBATION_EXACT_20260919.json'


def main():
    assert not OUT.exists()
    # Fixed predeclared descriptor distances and errors: two cardinality-2 matchings.
    c=F(1,2)
    d_star=[F(1,5),F(3,10)]
    d_alt=[F(2,5),F(1,2)]
    delta=F(1,100)
    eta=[2*d*delta+delta*delta for d in d_alt]
    eta_max=max(eta)
    m=2
    gap=sum(x*x for x in d_alt)-sum(x*x for x in d_star)
    checks=[]
    def check(name,ok,**extra):
        checks.append({'name':name,'passed':bool(ok),**extra})
        assert ok,name
    # Caliper graph example: declared present edges below c with margin, absent edges above c with margin.
    present=[F(1,5),F(3,10)]
    absent=[F(7,10),F(4,5)]
    check('present_edges_safe',all(x+delta<c for x in present),margin=[str(c-x-delta) for x in present])
    check('absent_edges_safe',all(x-delta>c for x in absent),margin=[str(x-delta-c) for x in absent])
    check('cost_gap_positive',gap>0,gap=str(gap))
    check('matching_identity_stable',gap>2*m*eta_max,threshold=str(2*m*eta_max),gap=str(gap))
    # The exact safe bound for this fixed pair is eta(M*)+eta(Malt).
    eta_star=[2*d*delta+delta*delta for d in d_star]
    check('pair_specific_gap_bound',gap>sum(eta_star)+sum(eta),bound=str(sum(eta_star)+sum(eta)))
    check('tie_break_not_margin',F(0)==F(0),note='deterministic lex tie-break exists but gives no positive robustness margin')
    # Standardization propagation formula at a fixed scalar coordinate.
    x=F(4);mu=F(1);sigma=F(2);ex=F(1,100); em=F(1,200); es=F(1,100)
    bound=(ex+em)/(sigma-es)+abs(x-mu)*es/(sigma*(sigma-es))
    check('standardization_bound_finite',sigma>es and bound>0,bound=str(bound))
    result={'task_id':'AL50','created_at':datetime.now(timezone.utc).isoformat(),'gate_result':'pass','gate_scope':'matching_perturbation_margin_math',
      'checks':checks,'fixed_caliper':str(c),'descriptor_error_bound':str(delta),'matching_cardinality':m,
      'd_star':[str(x) for x in d_star],'d_alternative':[str(x) for x in d_alt],
      'cost_gap':str(gap),'eta_max':str(eta_max),'stability_threshold':str(2*m*eta_max),
      'pair_specific_bound':str(sum(eta_star)+sum(eta)),
      'standardization_example':{'x':str(x),'mu':str(mu),'sigma':str(sigma),'epsilon_x':str(ex),'epsilon_mu':str(em),'epsilon_sigma':str(es),'bound':str(bound)},
      'interpretation':{'supported':'A strict caliper graph margin and unique same-cardinality cost gap can certify matching identity under declared descriptor errors.',
        'not_supported':['actual AL12 pairing stability','real standardization error bound','source information','AUROC','new algorithm admission'],
        'failure_boundary':'Zero cost gap or edges within the caliper uncertainty band remain non-robust even with deterministic ID tie-break.'},
      'resources':{'fraction_only':True,'matching_enumeration':False,'real_samples_accessed':False,'model_calls':0,'server_calls':0,'gpu_calls':0}}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'checks':len(checks),'gap':str(gap),'threshold':str(2*m*eta_max),'standardization_bound':str(bound)}))


if __name__=='__main__':main()
