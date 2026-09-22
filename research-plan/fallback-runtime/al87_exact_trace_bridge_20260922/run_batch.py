from __future__ import annotations
import copy, hashlib, importlib.util, json, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
AL79=REPO/"research-plan"/"fallback-runtime"/"al79_rgb_reducer_20260922"
def sha_bytes(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sha_arr(a):return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float64).tobytes(order="C")).hexdigest()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bridge=load("al87_bridge",ROOT/"exact_bridge.py"); reference=load("al87_reference",ROOT/"reference.py"); reducer=load("al79_reducer",AL79/"reducer.py")
def mutate(t,name):
 x=copy.deepcopy(t)
 if name=="wrong_sample":x["calls"][0]["sample_id"]="other"
 elif name=="wrong_probe":x["calls"][0]["probe_id"]="probe-B"
 elif name=="wrong_stage":x["stage"]="OTHER"
 elif name=="wrong_layout":x["support"]["layout"]="BCTHW"
 elif name=="wrong_shape":x["calls"][1]["shape"]=[1,2,5,4,3]
 elif name=="wrong_time_slots":x["calls"][2]["time_slots"]=[1,0]
 elif name=="duplicate_role":x["calls"][3]["role"]="Ra_x"
 elif name=="missing_role":x["calls"]=x["calls"][:-1]
 elif name=="ulp_base_input":
  a=np.asarray(x["calls"][1]["input"],dtype=np.float64); a=np.ascontiguousarray(a); a.flat[0]=np.nextafter(a.flat[0],np.inf); x["calls"][1]["input"]=a.tolist(); x["calls"][1]["input_sha256"]=sha_arr(a)
 return x
def main():
 t0=time.perf_counter();cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"));trace=json.loads((ROOT/"input.json").read_text(encoding="utf-8"));lock=json.loads((ROOT/"freeze.json").read_text(encoding="utf-8"))
 for fn,expected in lock["source_sha256"].items():
  p=AL79/"reducer.py" if fn=="al79_reducer.py" else ROOT/fn
  if sha_bytes(p)!=expected:raise RuntimeError("source_changed:"+fn)
 result=bridge.bridge(trace); ref=reference.reference(trace); checks={}
 for key in ("d_a","d_b","v_a","v_b","K"):
  actual=result["fields"].get(key,result.get(key)); checks["reference_"+key]=bool(np.allclose(actual,ref[key],rtol=1e-12,atol=1e-12))
 valid={"passed":all(checks.values()),"checks":checks}
 reduced=reducer.reduce_fields(result["fields"],layout="BTHWC",blocks=cfg["al79_blocks"]);valid["reducer"]={"version":reduced["version"],"samples":len(reduced["samples"]),"filter_calls":reduced["metrics"]["filter_calls"]}
 invalid=[]
 for name in cfg["invalid_cases"]:
  try:bridge.bridge(mutate(trace,name));invalid.append({"id":name,"passed":False,"error":"accepted"})
  except bridge.BridgeInputError as exc:invalid.append({"id":name,"passed":True,"error":exc.code})
 valid["passed"]=valid["passed"] and all(row["passed"] for row in invalid)
 evidence={"task_id":"AL87","version":cfg["version"],"software_pass":bool(valid["passed"]),"input_sha256":sha_bytes(ROOT/"input.json"),"config_sha256":sha_bytes(ROOT/"config.json"),"source_sha256":lock["source_sha256"],"reference_checks":checks,"valid_case":valid,"invalid_cases":invalid,"derived_field_sha256":{k:sha_arr(v) for k,v in result["fields"].items()},"call_count":4,"reducer_scope":"one bounded AL79 call only","resources":{"network":0,"media":0,"server":0,"gpu":0,"models":0,"wall_seconds":time.perf_counter()-t0},"scientific_breakthrough":False,"scope":"exact-byte precomputed identity and RGB reducer bridge; no real probe or efficacy"}
 out=ROOT/"run_v3"/"evidence.json";out.parent.mkdir(exist_ok=True)
 if out.exists():raise FileExistsError(out)
 out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
 print(json.dumps({"software_pass":evidence["software_pass"],"invalid_passes":sum(x["passed"] for x in invalid),"invalid_cases":invalid},ensure_ascii=False))
 if not evidence["software_pass"]:raise SystemExit(1)
if __name__=="__main__":main()
