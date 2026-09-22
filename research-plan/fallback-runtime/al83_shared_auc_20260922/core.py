"""AL83 shared-negative ancestor-weighted point estimands."""
from __future__ import annotations
from fractions import Fraction
from math import isfinite

INVALID = object()

def validate_scores(records, scores, methods, tags):
    ids={r['sample_id'] for r in records}
    if set(scores)!=set(methods): raise ValueError('method_keys')
    for method in methods:
        if set(scores[method])!=set(tags): raise ValueError('tag_keys')
        for tag in tags:
            if set(scores[method][tag])!=ids: raise ValueError('score_keys')
            for value in scores[method][tag].values():
                if isinstance(value,bool) or not isinstance(value,(int,float,Fraction)): raise ValueError('score_value')
                if isinstance(value,float) and not isfinite(value): raise ValueError('score_nonfinite')

def validate_weights(records,weights):
    ids={r['sample_id'] for r in records}
    if set(weights)!=ids: raise ValueError('weight_keys')
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in weights.values()): raise ValueError('weight_value')

def auc_shared_negative(records,scores,weights,generator):
    pos=[r for r in records if r['label']==1 and r['generator']==generator]
    neg=[r for r in records if r['label']==0 and r['generator'] is None]
    wp=sum(weights[r['sample_id']] for r in pos);wn=sum(weights[r['sample_id']] for r in neg)
    if not pos or not neg or wp==0 or wn==0:return INVALID
    ordered=sorted(neg,key=lambda r:scores[r['sample_id']]);blocks=[]
    for r in ordered:
        score=scores[r['sample_id']]
        if blocks and blocks[-1][0]==score:blocks[-1][1]+=weights[r['sample_id']]
        else:blocks.append([score,weights[r['sample_id']]])
    lower={};running=0
    for score,weight in blocks:lower[score]=running;running+=weight
    two_u=0
    for r in pos:
        score=scores[r['sample_id']];equal=next((w for value,w in blocks if value==score),0)
        lower_score=lower.get(score, sum(weight for value,weight in blocks if value<score))
        two_u+=weights[r['sample_id']]*(2*lower_score+equal)
    return Fraction(two_u,2*wp*wn)

def macro_shared_negative(records,scores,weights,generators):
    values={g:auc_shared_negative(records,scores,weights,g) for g in generators}
    if any(v is INVALID for v in values.values()):return INVALID,values
    return sum(values.values(),Fraction(0))/len(generators),values

def paired_summary(records,score_table,weights,methods,tags,generators):
    result={}
    for method in methods:
        result[method]={}
        for tag in tags:
            macro,groups=macro_shared_negative(records,score_table[method][tag],weights,generators)
            result[method][tag]={'macro':macro,'groups':groups}
    deltas=[]
    for tag in tags:
        a=result['candidate'][tag]['macro'];b=result['baseline'][tag]['macro']
        deltas.append(None if a is INVALID or b is INVALID else a-b)
    return result,deltas
