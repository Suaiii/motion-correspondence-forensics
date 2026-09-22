"""Independent pairwise Fraction oracle for AL83; no core import."""
from fractions import Fraction

def pair_auc(records,scores,weights,generator):
    pos=[r for r in records if r['label']==1 and r['generator']==generator];neg=[r for r in records if r['label']==0 and r['generator'] is None]
    wp=sum(weights[r['sample_id']] for r in pos);wn=sum(weights[r['sample_id']] for r in neg)
    if not pos or not neg or wp==0 or wn==0:return None
    numerator=Fraction(0)
    for p in pos:
        for n in neg:
            tie=1 if scores[p['sample_id']]>scores[n['sample_id']] else Fraction(1,2) if scores[p['sample_id']]==scores[n['sample_id']] else 0
            numerator+=weights[p['sample_id']]*weights[n['sample_id']]*tie
    return numerator/(wp*wn)

def summary(records,score_table,weights,methods,tags,generators):
    result={}
    for method in methods:
        result[method]={}
        for tag in tags:
            groups={g:pair_auc(records,score_table[method][tag],weights,g) for g in generators}
            result[method][tag]={'groups':groups,'macro':None if any(v is None for v in groups.values()) else sum(groups.values(),Fraction(0))/len(groups)}
    deltas=[]
    for tag in tags:
        a=result['candidate'][tag]['macro'];b=result['baseline'][tag]['macro'];deltas.append(None if a is None or b is None else a-b)
    return result,deltas
