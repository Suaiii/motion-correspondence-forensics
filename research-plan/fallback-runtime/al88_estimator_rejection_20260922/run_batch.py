from __future__ import annotations
import copy, hashlib, importlib.util, json, math, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
core=load("al85_core",ROOT/"core.py"); ref=load("al85_ref",ROOT/"reference.py")
def mutate(cfg,name):
    d=copy.deepcopy(cfg)
    if name=="duplicate_id": d["records"][1]["sample_id"]="p0"
    elif name=="missing_ancestor": d["records"][0].pop("ancestor_id")
    elif name=="label_bool": d["records"][0]["label"]=True
    elif name=="negative_generator": d["records"][2]["generator"]="g1"
    elif name=="missing_method": d["scores"].pop("baseline")
    elif name=="missing_tag": d["scores"]["candidate"].pop("diagnostic_b")
    elif name=="missing_score": d["scores"]["candidate"]["diagnostic_a"].pop("n2")
    elif name=="nan_score": d["scores"]["candidate"]["diagnostic_a"]["n2"]=float("nan")
    elif name=="weight_bool": d["weights"]["all_one"]["A"]=True
    elif name=="weight_fraction": d["weights"]["all_one"]["A"]=0.5
    elif name=="weight_extra": d["weights"]["all_one"]["X"]=1
    return d
def main():
    t0=time.perf_counter(); cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8")); lock=json.loads((ROOT/"freeze.json").read_text(encoding="utf-8"))
    for fn,expected in lock["source_sha256"].items():
        if sha(ROOT/fn)!=expected:raise RuntimeError("source_changed:"+fn)
    records=cfg["records"]; methods=cfg["methods"]; tags=cfg["tags"]; gens=cfg["generators"]; ancestors=cfg["ancestors"]
    rows=[]; failures=[]; checks=[]
    for name,weights in cfg["weights"].items():
        actual=core.macro(records,cfg["scores"],weights,methods,tags,gens,ancestors)
        expected=cfg["expected"][name]
        rr=ref.macro_ref(records,cfg["scores"],weights,methods,tags,gens)
        ref_ok=(actual["valid"]==rr["valid"] and (not actual["valid"] or (actual["deltas"]==rr["deltas"] and actual["mean_delta"]==rr["mean_delta"])))
        checks.append({"name":name+"/reference","passed":ref_ok})
        if not ref_ok:failures.append(name+"/reference")
        if expected=="invalid":
            ok=actual["valid"] is False
        else:
            ok=actual["valid"] and actual["deltas"]["diagnostic_a"]==expected["tag_a"] and actual["deltas"]["diagnostic_b"]==expected["tag_b"] and actual["mean_delta"]==expected["mean"]
        checks.append({"name":name+"/analytic_expected","passed":ok,"observed":actual.get("mean_delta"),"expected":expected})
        if not ok:failures.append(name+"/analytic_expected")
        rows.append({"name":name,"result":actual,"reference":rr})
    perm=list(reversed(records)); ids=[r["sample_id"] for r in perm]; perm_scores={m:{tag:{sid:cfg["scores"][m][tag][sid] for sid in ids} for tag in tags} for m in methods}
    perm_result=core.macro(perm,perm_scores,cfg["weights"]["all_one"],methods,tags,gens,ancestors)
    base=rows[0]["result"]; checks.append({"name":"record_order_invariance","passed":perm_result==base})
    if perm_result!=base:failures.append("record_order_invariance")
    checks.append({"name":"tag_change_is_visible","passed":rows[0]["result"]["deltas"]["diagnostic_a"]!=rows[0]["result"]["deltas"]["diagnostic_b"]})
    invalid=[]
    for name in cfg["reject_cases"]:
        malformed = mutate(cfg,name)
        scheme = malformed["weights"]["all_one"]
        try:
            core.macro(malformed["records"], malformed["scores"], scheme, methods, tags, gens, ancestors)
            invalid.append({"name":name,"passed":False,"error":"accepted"}); failures.append("reject/"+name)
        except core.InputError as exc: invalid.append({"name":name,"passed":True,"error":exc.code})
    checks.extend(invalid)
    evidence={"task_id":"AL88","version":cfg["version"],"software_pass":not failures,"source_sha256":lock["source_sha256"],"config_sha256":sha(ROOT/"config.json"),"weights":cfg["weights"],"rows":rows,"checks":checks,"failures":failures,"scope":"synthetic point estimand only; no CI/bootstrap/model/media/server/GPU","resources":{"network":0,"media":0,"server":0,"gpu":0,"models":0,"threads":1,"wall_seconds":time.perf_counter()-t0},"scientific_breakthrough":False}
    out=ROOT/"run_v2"/"evidence.json"; out.parent.mkdir(exist_ok=True)
    if out.exists():raise FileExistsError(out)
    out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"software_pass":evidence["software_pass"],"checks":len(checks),"failures":failures},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=="__main__":main()
