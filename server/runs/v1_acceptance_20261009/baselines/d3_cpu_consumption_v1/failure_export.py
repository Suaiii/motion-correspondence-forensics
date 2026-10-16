import hashlib,json,os
from pathlib import Path
R=Path('/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_cpu_consumption_v1')
names=['PROCESS_START.json','RUN_RECEIPT.json','run_output/RUN_IDENTITY.json','run_output/MODEL_LOAD_FAILURE.json','run_output/PROCESS_EXIT.json','run_output/RUN_SUMMARY.json','run_output/RESULT_LEDGER.jsonl','run_output/events.jsonl','run_output/EXECUTION_MANIFEST.json','run_output/ASSET_LOCK.json','run_output/PLANNED_IDENTITY.json','worker.stdout.log','worker.stderr.log','meta/d3_execution.json','meta/d3_environment.json','typed/asset_lock.json']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
out={}
for n in names:
 p=R/n
 if p.exists():
  text=p.read_text(errors='replace') if p.suffix in ('.json','.jsonl','.log') else None
  out[n]={'bytes':p.stat().st_size,'SHA256':sha(p),'text_tail':text[-8000:] if text is not None else None}
procs={}
for pid in ('106022','106023','106024'):
 p=Path('/proc')/pid/'stat';procs[pid]={'exists':p.exists()}
 if p.exists():
  text=p.read_text();v=text[text.rfind(')')+2:].split();procs[pid].update({'state':v[0],'start_ticks':v[19]})
out['processes']=procs;out['cloud_writes_by_export']=0;print(json.dumps(out,ensure_ascii=False))
