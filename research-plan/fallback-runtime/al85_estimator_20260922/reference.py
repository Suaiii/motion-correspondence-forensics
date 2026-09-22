"""Independent Fraction pairwise reference; does not import core."""
from fractions import Fraction
def cell(records,scores,weights,generator):
    pos=[r for r in records if r["label"]==1 and r["generator"]==generator]
    neg=[r for r in records if r["label"]==0]
    wp=sum(weights[r["ancestor_id"]] for r in pos); wn=sum(weights[r["ancestor_id"]] for r in neg)
    if wp<=0 or wn<=0:return None
    u=Fraction(0)
    for p in pos:
        for n in neg:
            sp,sn=scores[p["sample_id"]],scores[n["sample_id"]]
            z=1 if sp>sn else Fraction(1,2) if sp==sn else 0
            u += weights[p["ancestor_id"]]*weights[n["ancestor_id"]]*z
    return {"two_U":int(2*u),"denominator":2*wp*wn,"auc":str(u/(wp*wn))}
def macro_ref(records,scores,weights,methods,tags,generators):
    out={}
    for m in methods:
        out[m]={}
        for tag in tags:
            cells={g:cell(records,scores[m][tag],weights,g) for g in generators}
            if any(v is None for v in cells.values()):return {"valid":False,"reason":"zero_class_weight"}
            out[m][tag]={"cells":cells,"macro":str(sum((__import__("fractions").Fraction(v["auc"]) for v in cells.values()),__import__("fractions").Fraction(0))/len(cells))}
    d={tag:str(__import__("fractions").Fraction(out[methods[0]][tag]["macro"])-__import__("fractions").Fraction(out[methods[1]][tag]["macro"])) for tag in tags}
    return {"valid":True,"methods":out,"deltas":d,"mean_delta":str(sum((__import__("fractions").Fraction(x) for x in d.values()),__import__("fractions").Fraction(0))/len(tags))}
