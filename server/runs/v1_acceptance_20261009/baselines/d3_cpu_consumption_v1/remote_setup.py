import hashlib,json,os,shutil,subprocess,sys,time,tarfile
from pathlib import Path
R=Path('/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_cpu_consumption_v1');BASE=R.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def accounting():
 led=R/'meta_RESOURCE_LEDGER_033.json';assert sha(led)=='001da0f261461df9dc4b52096aa105be3a0d8124ec1b9d0f45db6240558d7894'
 d=json.loads(led.read_text());required=d['floor_bytes'];rows={};over=[]
 for name,item in d['reservations'].items():
  p=BASE/item['namespace'];logical=allocated=0
  if p.exists():
   for x in p.rglob('*'):
    try:s=x.stat()
    except FileNotFoundError:continue
    if not x.is_file():continue
    logical+=s.st_size;allocated+=s.st_blocks*512
  charged=max(logical,allocated);remaining=max(0,item['cap']-charged);required+=remaining;rows[name]={'logical':logical,'allocated':allocated,'charged':charged,'remaining':remaining,'cap':item['cap']}
  if logical>item['cap'] or charged>item['cap']:over.append(name)
 free=shutil.disk_usage(R).free;state={'server_unix':time.time(),'free':free,'required':required,'margin':free-required,'rows':rows,'over_cap':over,'CPU_affinity':sorted(os.sched_getaffinity(0)),'RSS_self':__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss*1024}
 save('FRESH_PREFLIGHT.json',state);assert not over and free>=required and {4,5}.issubset(set(os.sched_getaffinity(0))),state;return state
def run(cmd,out=None):
 p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=120);obj={'argv':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'wall_seconds':None};
 if out:save(out,obj)
 if p.returncode:raise RuntimeError(json.dumps(obj))
 return obj
def main():
 if not (R/'b8_source').exists():
  with tarfile.open(R/'stage.tar') as tf:
   members=tf.getmembers();assert all(m.isfile() and (R/m.name).resolve().is_relative_to(R.resolve()) for m in members);tf.extractall(R,filter='data')
 pre=accounting();b8=R/'b8_source';typed=R/'typed';dep1=BASE/'fingerprint_cpu/author_input_parity_v1/dependencies/site';dep2=BASE/'baselines/input_qualification_v1/cpu_deps'
 env=R/'meta'/'d3_environment.json';env.parent.mkdir(exist_ok=True)
 cmd=[sys.executable,'-B',str(b8/'environment_lock.py'),'--cv2-distribution','opencv-python-headless','--dependency-path',str(dep1),'--dependency-path',str(dep2)]
 result=run(cmd);env.write_text(result['stdout']);env_sha=sha(env);save('meta/environment_command.json',result)
 identity=typed/'identity.json';selection=typed/'selection.jsonl';prepared=typed/'prepared_index.jsonl';records=typed/'input_records.jsonl';manifest=R/'meta'/'d3_execution.json'
 cmd=[sys.executable,'-B',str(b8/'assemble_manifest.py'),'--selection',str(selection),'--selection-sha256',sha(selection),'--prepared-index',str(prepared),'--prepared-index-sha256',sha(prepared),'--input-records',str(records),'--input-records-sha256',sha(records),'--environment',str(env),'--environment-sha256',env_sha,'--identity',str(identity),'--identity-sha256',sha(identity),'--output',str(manifest)]
 result=run(cmd);save('meta/assembly_command.json',result)
 asset=R/'typed'/'asset_lock.json';asset_lock_sha=sha(asset)
 asset_dir=BASE/'baselines/inference_assets_ready_v1/assets/xclip16';prepared_root=BASE/'fingerprint_cpu/author_input_parity_v1/runs/run_002';out=R/'run_output'
 plan_cmd=[sys.executable,'-B',str(b8/'runner.py'),'plan','--execution-manifest',str(manifest),'--manifest-sha256',sha(manifest),'--asset-lock',str(asset),'--asset-lock-sha256',asset_lock_sha,'--asset-dir',str(asset_dir),'--prepared-root',str(prepared_root),'--dependency-path',str(dep1),'--dependency-path',str(dep2),'--output',str(out)]
 result=run(plan_cmd);save('meta/plan_command.json',result)
 run_cmd=plan_cmd.copy();run_cmd[run_cmd.index('plan')]='run';run_cmd+=['--cpu-affinity','4,5','--checkpoint-every','1','--max-output-mib','32']
 save('RUN_COMMAND.json',{'argv':run_cmd,'execution_manifest':str(manifest),'manifest_sha256':sha(manifest),'asset_lock':str(asset),'asset_lock_sha256':asset_lock_sha,'asset_dir':str(asset_dir),'prepared_root':str(prepared_root),'dependency_paths':[str(dep1),str(dep2)],'fixed_members':12,'seed':0,'batch_size':1,'dtype':'float32','GPU':False,'media_decode':False})
 print(json.dumps({'preflight_margin':pre['margin'],'environment_SHA256':env_sha,'execution_manifest_SHA256':sha(manifest),'plan_status':json.loads(result['stdout'])['status'],'run_command':'saved','members':12}))
if __name__=='__main__':main()
