import hashlib,json,shutil,sys,subprocess
from pathlib import Path
R=Path('/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_cpu_consumption_v1');old=R/'b8_source';new=R/'b8_source_v2'
assert not new.exists();shutil.copytree(old,new)
p=new/'backend.py';text=p.read_text();oldline="if cfg.get('model_type')!='x-clip':raise ValueError('XCLIP_config_model_type_required')";newline="if cfg.get('model_type')!='xclip':raise ValueError('XCLIP_config_model_type_required_actual_xclip')";assert oldline in text;p.write_text(text.replace(oldline,newline))
lock=json.loads((new/'CODE_LOCK.json').read_text());before=lock['runtime_files']['backend.py'];h=hashlib.sha256(p.read_bytes()).hexdigest();lock['runtime_files']['backend.py']=h;lock['version']='B8-D3-runner/1.3_v2_config_model_type_exact';(new/'CODE_LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
manifest=R/'meta/d3_execution.json';asset=R/'typed/asset_lock.json';dep1=R.parents[1]/'fingerprint_cpu/author_input_parity_v1/dependencies/site';dep2=R.parents[1]/'baselines/input_qualification_v1/cpu_deps';asset_dir=R.parents[1]/'baselines/inference_assets_ready_v1/assets/xclip16';prepared=R.parents[1]/'fingerprint_cpu/author_input_parity_v1/runs/run_002';out=R/'run_output_v2'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b):h.update(b)
 return h.hexdigest()
plan=[sys.executable,'-B',str(new/'runner.py'),'plan','--execution-manifest',str(manifest),'--manifest-sha256',sha(manifest),'--asset-lock',str(asset),'--asset-lock-sha256',sha(asset),'--asset-dir',str(asset_dir),'--prepared-root',str(prepared),'--dependency-path',str(dep1),'--dependency-path',str(dep2),'--output',str(out)]
p2=subprocess.run(plan,capture_output=True,text=True);(R/'V2_PLAN.json').write_text(json.dumps({'argv':plan,'exit_code':p2.returncode,'stdout':p2.stdout,'stderr':p2.stderr,'backend_before':before,'backend_after':h},indent=2)+'\n');assert p2.returncode==0
run=plan.copy();run[run.index('plan')]='run';run+=['--cpu-affinity','4,5','--checkpoint-every','1','--max-output-mib','32']
(R/'RUN_COMMAND_V2.json').write_text(json.dumps({'argv':run,'source_variant':'b8_source_v2','output':str(out),'backend_change':'exact config model_type xclip acceptance only','old_failure_preserved':'run_output/MODEL_LOAD_FAILURE.json','input_manifest_sha256':sha(manifest),'asset_lock_sha256':sha(asset),'members':12},indent=2)+'\n')
watch=(R/'watch_run.py').read_text()
for a,b in [('RUN_COMMAND.json','RUN_COMMAND_V2.json'),('worker.stdout.log','worker_v2.stdout.log'),('worker.stderr.log','worker_v2.stderr.log'),('WORKER_HANDLE.json','WORKER_HANDLE_V2.json'),('RUN_RECEIPT.json','RUN_RECEIPT_V2.json'),('WATCH_HEARTBEAT.json','WATCH_HEARTBEAT_V2.json')]:watch=watch.replace(a,b)
(R/'watch_run_v2.py').write_text(watch)
launch=(R/'launch_c10.py').read_text()
for a,b in [('RUN_ONCE.claim','RUN_ONCE_V2.claim'),('watch_run.py','watch_run_v2.py'),('supervisor.stdout.log','supervisor_v2.stdout.log'),('supervisor.stderr.log','supervisor_v2.stderr.log'),('LAUNCH.json','LAUNCH_V2.json')]:launch=launch.replace(a,b)
(R/'launch_c10_v2.py').write_text(launch)
print(json.dumps({'backend_before':before,'backend_after':h,'plan_exit':p2.returncode,'output':str(out),'members':12}))
