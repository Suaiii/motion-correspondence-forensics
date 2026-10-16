"""Unchanged v1 arithmetic kernels. Not an admission API; use evaluation.py."""
import hashlib,json,math
from collections import defaultdict
from admission import validate_rows
IDENTITY = ("method_id", "method_revision", "checkpoint_sha256", "preprocessing_sha256", "split_sha256", "track", "processing_id", "seed")
def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",",":"), allow_nan=False).encode()).hexdigest()

def undefined(reason): return {"value": None, "status": "undefined", "reason": reason}

def value(x): return {"value": x, "status": "defined"}

def split_violations(rows):
    role_by_ancestor, role_by_bytes = defaultdict(set), defaultdict(set)
    for r in rows:
        role_by_ancestor[r["ancestor_id"]].add(r["role"])
        role_by_bytes[r["input_sha256"]].add(r["role"])
    violations = [{"kind":"ancestor_cross_role","identity":k,"roles":sorted(v)} for k,v in role_by_ancestor.items() if len(v)>1]
    violations += [{"kind":"same_bytes_cross_role","identity":k,"roles":sorted(v)} for k,v in role_by_bytes.items() if len(v)>1]
    return violations

def auroc(rows):
    n1 = sum(r["label_fake"] for r in rows); n0 = len(rows)-n1
    if not n1 or not n0: return undefined("single_class_cell")
    groups = defaultdict(lambda:[0,0])
    for r in rows: groups[r["score_fake"]][r["label_fake"]] += 1
    lower_real = 0; wins = 0.0
    for _,(real,fake) in sorted(groups.items()):
        wins += fake*(lower_real+0.5*real); lower_real += real
    return value(wins/(n1*n0))

def average_precision(rows):
    nf = sum(r["label_fake"] for r in rows)
    if not nf or nf==len(rows): return undefined("single_class_cell")
    groups = defaultdict(lambda:[0,0])
    for r in rows: groups[r["score_fake"]][r["label_fake"]] += 1
    seen=tp=0; ap=0.0
    for _,(real,fake) in sorted(groups.items(),reverse=True):
        seen+=real+fake; tp+=fake; ap += (fake/nf)*(tp/seen)
    return value(ap)

def operating_point(rows, lock):
    real = [r for r in rows if r["label_fake"]==0]; fake = [r for r in rows if r["label_fake"]==1]
    if lock is None: return {"tpr":undefined("threshold_not_locked"),"fpr":undefined("threshold_not_locked")}
    t = lock["threshold"]
    return {"tpr":value(sum(r["score_fake"]>t for r in fake)/len(fake)) if fake else undefined("no_fake"),
            "fpr":value(sum(r["score_fake"]>t for r in real)/len(real)) if real else undefined("no_real"),
            "threshold":t,"target_fpr":lock["target_fpr"],"rule":"score_fake > threshold"}

def calibrate(rows, target_fpr=0.01):
    validate_rows(rows)
    if not rows or any(r["role"]!="calibration" for r in rows): raise ValueError("calibration_only")
    if not 0<target_fpr<1: raise ValueError("target_fpr")
    ids = {tuple(r[k] for k in IDENTITY) for r in rows}
    if len(ids)!=1: raise ValueError("mixed_calibration_contracts")
    real = [r for r in rows if r["label_fake"]==0]
    if not real: raise ValueError("no_calibration_real")
    if len({r["input_sha256"] for r in real})!=len(real): raise ValueError("duplicate_calibration_bytes")
    k = math.floor(target_fpr*len(real))
    threshold = sorted((r["score_fake"] for r in real), reverse=True)[k]
    lock = {"version":"threshold_lock/1.0","identity":dict(zip(IDENTITY,next(iter(ids)))), "threshold":threshold,"target_fpr":target_fpr,"positive_class":"fake","rule":"score_fake > threshold", "n_calibration_real":len(real),"empirical_fpr":sum(r["score_fake"]>threshold for r in real)/len(real),"fpr_resolution":1/len(real),"low_fpr_resolution_supported":len(real)>=math.ceil(1/target_fpr),"calibration_rows_sha256":digest(rows),"calibration_ancestors":sorted({r["ancestor_id"] for r in rows}),"calibration_bytes":sorted({r["input_sha256"] for r in rows}),"population_fpr_guarantee":False}
    lock["sha256"] = digest(lock)
    return lock

def check_threshold_lock(rows, lock):
    copy = dict(lock); declared=copy.pop("sha256",None)
    if digest(copy)!=declared: raise ValueError("threshold_lock_hash_changed")
    for r in rows:
        if any(r[k]!=lock["identity"][k] for k in IDENTITY): raise ValueError("threshold_contract_mismatch")
        if r["ancestor_id"] in lock["calibration_ancestors"] or r["input_sha256"] in lock["calibration_bytes"]: raise ValueError("calibration_audit_overlap")

def generator_macro(rows):
    generators=sorted({r["generator_family"] for r in rows if r["label_fake"]==1})
    real_by_source=defaultdict(list)
    for r in rows:
        if r["label_fake"]==0: real_by_source[r["source_family"]].append(r)
    gs=[]
    for g in generators:
        sources=sorted({r["source_family"] for r in rows if r["generator_family"]==g})
        cells=[]
        for s in sources:
            f=[r for r in rows if r["label_fake"]==1 and r["generator_family"]==g and r["source_family"]==s]
            rr=real_by_source[s]
            cells.append({"source_family":s,"n_fake":len(f),"n_real":len(rr),"auroc":auroc(f+rr) if rr else undefined("no_predeclared_real_control_same_source")})
        vals=[c["auroc"]["value"] for c in cells]
        a = value(sum(vals)/len(vals)) if vals and all(v is not None for v in vals) else undefined("incomplete_source_cells")
        gs.append({"generator_family":g,"source_cells":cells,"auroc":a})
    vals=[x["auroc"]["value"] for x in gs]
    return {"generators":gs,"auroc":value(sum(vals)/len(vals)) if vals and all(v is not None for v in vals) else undefined("incomplete_generator_support"),"definition":"equal mean over generator families of equal source-cell AUROCs against shared, same-source real controls"}
