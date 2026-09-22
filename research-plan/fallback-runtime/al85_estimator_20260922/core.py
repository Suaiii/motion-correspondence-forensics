"""AL85 strict shared-negative ancestor-weighted AUROC point estimator."""
from __future__ import annotations
from fractions import Fraction
from numbers import Real
import math

class InputError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def _integer(value, code):
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputError(code)
    return value

def validate_records(records, methods, tags, generators):
    if not isinstance(records, list) or not records:
        raise InputError("records")
    ids=[]; by={}
    for row in records:
        if not isinstance(row,dict) or set(row)!={"sample_id","ancestor_id","label","generator"}:
            raise InputError("record_schema")
        sid=row["sample_id"]
        if not isinstance(sid,str) or not sid or sid in by: raise InputError("sample_id")
        anc=row["ancestor_id"]
        if not isinstance(anc,str) or not anc: raise InputError("ancestor_id")
        lab=_integer(row["label"],"label")
        if lab not in (0,1): raise InputError("label")
        gen=row["generator"]
        if lab==0 and gen is not None: raise InputError("negative_generator")
        if lab==1 and (not isinstance(gen,str) or gen not in generators): raise InputError("positive_generator")
        ids.append(sid); by[sid]=row
    return ids,by

def validate_weights(weights, ancestors):
    if not isinstance(weights,dict) or set(weights)!=set(ancestors):
        raise InputError("weight_keys")
    for anc,w in weights.items():
        _integer(w,"weight_integer")
        if w<0: raise InputError("weight_nonnegative")
    return weights

def validate_scores(scores, ids, methods, tags):
    if not isinstance(scores,dict) or set(scores)!=set(methods):
        raise InputError("method_keys")
    for m in methods:
        if not isinstance(scores[m],dict) or set(scores[m])!=set(tags):
            raise InputError("tag_keys")
        for tag in tags:
            table=scores[m][tag]
            if not isinstance(table,dict) or set(table)!=set(ids):
                raise InputError("score_keys")
            for value in table.values():
                if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(float(value)):
                    raise InputError("score_value")
    return scores

def auc_rank(records, score_table, weights, generator, *, return_cell=False):
    pos=[r for r in records if r["label"]==1 and r["generator"]==generator]
    neg=[r for r in records if r["label"]==0]
    wp=sum(weights[r["ancestor_id"]] for r in pos)
    wn=sum(weights[r["ancestor_id"]] for r in neg)
    if wp<=0 or wn<=0:
        return None if not return_cell else {"valid":False,"reason":"zero_class_weight","two_U":None,"denominator":None,"auc":None}
    # One sorted pass over score blocks; no pairwise loop in the primary estimator.
    blocks={}
    for r in pos+neg:
        blocks.setdefault(float(score_table[r["sample_id"]]),[0,0])
        if r["label"]==1: blocks[float(score_table[r["sample_id"]])][0]+=weights[r["ancestor_id"]]
        else: blocks[float(score_table[r["sample_id"]])][1]+=weights[r["ancestor_id"]]
    negative_below=0; two_u=0
    for score in sorted(blocks):
        pos_w,neg_w=blocks[score]
        two_u += pos_w*(2*negative_below + neg_w)
        negative_below += neg_w
    denominator=2*wp*wn
    result=Fraction(two_u,denominator)
    if not return_cell: return result
    return {"valid":True,"generator":generator,"positive_weight":wp,"negative_weight":wn,
            "two_U":two_u,"denominator":denominator,"auc":str(result)}
def macro(records,scores,weights,methods,tags,generators,ancestors):
    ids,by=validate_records(records,methods,tags,generators)
    validate_weights(weights,ancestors); validate_scores(scores,ids,methods,tags)
    cells={}
    deltas={}
    for m in methods:
        cells[m]={}
        for tag in tags:
            cells[m][tag]={}
            vals=[]
            for g in generators:
                cell=auc_rank(records,scores[m][tag],weights,g,return_cell=True)
                cells[m][tag][g]=cell
                if not cell["valid"]: return {"valid":False,"reason":cell["reason"],"cells":cells}
                vals.append(Fraction(cell["two_U"],cell["denominator"]))
            cells[m][tag]["macro"]=str(sum(vals,Fraction(0))/len(vals))
    for tag in tags:
        deltas[tag]=str(Fraction(cells[methods[0]][tag]["macro"])-Fraction(cells[methods[1]][tag]["macro"]))
    mean=sum((Fraction(v) for v in deltas.values()),Fraction(0))/len(tags)
    return {"valid":True,"cells":cells,"deltas":deltas,"mean_delta":str(mean)}
