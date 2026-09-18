"""Exact enumeration of one fixed illustration; no model or statistical fitting."""
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'AL21_FIXED_ILLUSTRATION_20260919.json'
OUTPUT = HERE / 'AL21_COVERAGE_EXACT_20260919.json'

def main():
    assert not OUTPUT.exists(), 'Preserve the existing receipt'
    raw = INPUT.read_bytes()
    spec = json.loads(raw)
    positives = [r for r in spec['rows'] if r['label'] == 1]
    negatives = [r for r in spec['rows'] if r['label'] == 0]
    pairs = []
    for p in positives:
        for n in negatives:
            difference = F(p['score_exact']) - F(n['score_exact'])
            credit = F(1) if difference > 0 else F(0) if difference < 0 else F(spec['pair_tie_credit_exact'])
            pairs.append(dict(positive=p['id'],negative=n['id'],credit_exact=str(credit),
                              both_accepted=p['z']==n['z']==0))
    accepted_pairs = [r for r in pairs if r['both_accepted']]
    full = sum(F(r['credit_exact']) for r in pairs) / len(pairs)
    selected = sum(F(r['credit_exact']) for r in accepted_pairs) / len(accepted_pairs)
    cpos = F(sum(r['z']==0 for r in positives),len(positives))
    cneg = F(sum(r['z']==0 for r in negatives),len(negatives))
    mass = cpos*cneg
    assert full == F(3,4) and selected == 1 and cpos == cneg == F(1,2)
    assert mass == F(1,4)
    threshold = F(spec['decision_threshold_exact'])
    rates = {}
    for name,rows in [('TPR',positives),('FPR',negatives)]:
        accepted = [r for r in rows if r['z']==0]
        count = sum(F(r['score_exact'])>=threshold for r in accepted)
        coverage = F(len(accepted),len(rows))
        conditional = F(count,len(accepted))
        joint = F(count,len(rows))
        actual_full = F(sum(F(r['score_exact'])>=threshold for r in rows),len(rows))
        assert joint == coverage*conditional
        assert joint <= actual_full <= joint+1-coverage
        rates[name] = dict(accepted_rate_exact=str(conditional),accepted_event_per_all_exact=str(joint),
                          rejected_outcome_unresolved_interval=[str(joint),str(joint+1-coverage)],
                          provided_complete_score_rate_exact=str(actual_full))
    result = dict(task_id='AL21',observed_at=datetime.now(timezone.utc).isoformat(),
        input_sha256=hashlib.sha256(raw).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        score_table=spec['rows'],pairs=pairs,complete_AUC_exact=str(full),accepted_AUC_exact=str(selected),
        positive_coverage_exact=str(cpos),negative_coverage_exact=str(cneg),accepted_pair_fraction_exact=str(mass),
        unresolved_full_score_completion_AUC_interval=[str(mass*selected),str(mass*selected+1-mass)],
        rates_at_fixed_threshold=rates,
        scope='Illustrative pair enumeration only; conditional evaluation can change without any change in scores',
        candidate_or_classifier_run=False,training=False,real_media=False,server_access=False,gpu_used=False)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('complete_AUC_exact','accepted_AUC_exact',
          'positive_coverage_exact','negative_coverage_exact','unresolved_full_score_completion_AUC_interval')},indent=2))

if __name__ == '__main__':
    main()
