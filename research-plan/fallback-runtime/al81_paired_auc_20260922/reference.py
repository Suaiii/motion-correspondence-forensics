"""Independent pairwise Fraction reference for AL81."""
from fractions import Fraction
def pair_auc(scores, labels, generator, weights, group):
    pos=[i for i in scores if labels[i]==1 and generator[i]==group];neg=[i for i in scores if labels[i]==0 and generator[i]==group]
    if not pos or not neg:return None
    den=sum(weights[i] for i in pos)*sum(weights[i] for i in neg);num=Fraction(0)
    for i in pos:
        for j in neg:
            num += weights[i]*weights[j]*(1 if scores[i]>scores[j] else Fraction(1,2) if scores[i]==scores[j] else 0)
    return num/den if den else None
def macro_ref(scores,labels,generator,weights):
    vals=[pair_auc(scores,labels,generator,weights,g) for g in sorted(set(generator.values()))]
    return None if any(v is None for v in vals) else sum(vals,Fraction(0))/len(vals)
