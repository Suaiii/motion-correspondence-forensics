"""Review AL49 using expanded rational polynomials; preserve prior receipt/errors."""
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'research-plan/reviews'
OLD=R/'AL49_SOFT_COMPOSITION_NULL_EXACT_20260919.json'
OUT=R/'AL49_POLYNOMIAL_REVIEW_20260919.json'


def main():
    assert not OUT.exists(), 'Do not overwrite a completed audit'
    started=datetime.now(timezone.utc).isoformat()
    old_bytes=OLD.read_bytes();old=json.loads(old_bytes)
    h,x=F(1,8),F(1,2);a=1-h
    # Expanded endpoints, independently of the previous nested pa/pb functions.
    ab=a*a*x+a*h*x**4+h*a*a*x**2+2*a*h*h*x**5+h**3*x**8
    ba=a*a*x+a*h*x**2+h*a**4*x**4+4*a**3*h**2*x**5+6*a*a*h**3*x**6+4*a*h**4*x**7+h**5*x**8
    combined=-a*h*h*x*x+h*a*(1-a**3)*x**4+2*a*h*h*(1-2*a*a)*x**5-6*a*a*h**3*x**6-4*a*h**4*x**7+(h**3-h**5)*x**8
    ra=a*x+h*x*x;rb=a*x+h*x**4
    checks=[]
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)});assert value,name
    check('first_soft_a_equals_15_over32',ra==F(15,32))
    check('first_soft_b_equals_57_over128',rb==F(57,128))
    check('expanded_ab_matches_recorded_value',ab==F(old['identity_check']['soft_ab']))
    check('expanded_ba_matches_recorded_value',ba==F(old['identity_check']['soft_ba']))
    check('collected_polynomial_equals_endpoint_difference',combined==ab-ba)
    check('nonzero_K_matches_recorded_value',combined/h**2==F(-14721,131072)==F(old['identity_check']['K_h']))
    check('old_receipt_unchanged',OLD.read_bytes()==old_bytes)
    receipt={
      'task_id':'AL49','review_started_at':started,'review_completed_at':datetime.now(timezone.utc).isoformat(),
      'evidence_kind':'expanded_polynomial_cross_check_and_execution_history_correction',
      'old_receipt_sha256':hashlib.sha256(old_bytes).hexdigest(),
      'work_order_sha256':hashlib.sha256((ROOT/'research-plan/AL49_SOFT_COMPOSITION_NULL_AUDIT_20260919.md').read_bytes()).hexdigest(),
      'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'checks_executed':checks,'h':str(h),'u':str(x),'P_a_u':str(ra),'P_b_u':str(rb),
      'expanded_PaPb':str(ab),'expanded_PbPa':str(ba),'difference':str(combined),'K_h':str(combined/h**2),
      'arithmetic_result':'verified_on_fixed_input',
      'execution_contract_result':'fail_single_attempt_requirement_not_met',
      'prior_execution_history':[
         'Inline nested rational calculation already obtained both endpoints before the saved script.',
         'First saved script failed at a wrong intermediate expected-value assertion after computing endpoints.',
         'A separate inline call printed correct intermediate15/32 and57/128.',
         'Only expected constants were changed, and the saved script was rerun; it wrote the old receipt.',
         'Temporary saved script was then deleted; its exact historical bytes are not retained.'],
      'failed_assertion_from_observed_tool_output':'assert ra==9*F(1,16)+F(1,32) and rb==15*F(1,16)+F(1,128)',
      'failed_command_exit_code':1,'failure_kind':'wrong_expected_constants_in_reviewer_script_not_an_input_or_model_change',
      'same_input_used_throughout':True,'new_input_or_h_search':False,
      'old_search_count1_not_run_count':True,
      'old_started_at_note':'Old receipt assigned start/end timestamps during receipt construction after arithmetic; not timing evidence for the full batch.',
      'independent_scientific_review':False,'model_calls':0,'training_calls':0,'media_accessed':False,'server_calls':0,'gpu_calls':0,
      'interpretation':'One mathematical counterexample remains valid, but do not certify the original single-attempt protocol or call it a breakthrough.'}
    with OUT.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'actual_checks':len(checks),'K_h':str(combined/h**2),
                     'arithmetic':'verified','single_attempt_contract':'failed','old_receipt_preserved':True}))


if __name__=='__main__':main()
