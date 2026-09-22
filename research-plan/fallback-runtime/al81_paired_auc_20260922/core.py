"""AL81 point estimands; standard library only, no training or CI."""
from fractions import Fraction

INVALID = object()

def auc_rank(pos, neg, weights):
    if not pos or not neg: return INVALID
    total=Fraction(0); denom=sum(weights[x] for x in pos)*sum(weights[x] for x in neg)
    if denom <= 0:return INVALID
    for i in pos:
        for j in neg:
            total += weights[i]*weights[j]*(1 if pos[i]>neg[j] else Fraction(1,2) if pos[i]==neg[j] else 0)
    return total/denom

def macro(scores, labels, generator, weights):
    groups=[]
    for g in sorted(set(generator.values())):
        pos={i:scores[i] for i in scores if generator[i]==g and labels[i]==1}
        neg={i:scores[i] for i in scores if generator[i]==g and labels[i]==0}
        value=auc_rank(pos,neg,weights)
        if value is INVALID:return INVALID
        groups.append(value)
    return sum(groups,Fraction(0))/len(groups) if groups else INVALID

def paired_macro(candidate,baseline,labels,generator,weights):
    a=macro(candidate,labels,generator,weights);b=macro(baseline,labels,generator,weights)
    return INVALID if a is INVALID or b is INVALID else a-b
