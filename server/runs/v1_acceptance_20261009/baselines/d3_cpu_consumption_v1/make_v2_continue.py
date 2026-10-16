# Continuation of make_v2_remote.py (2026-10-09), which stopped at sha() because of
# iter(...,b) instead of iter(...,b''). b8_source_v2 copy, backend patch and CODE_LOCK
# update had already completed and are verified (not redone) here.
# Also fixes watch_run_v2 cwd/tmp paths so v2 uses b8_source_v2 and run_output_v2.
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path('/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_cpu_consumption_v1');new=R/'b8_source_v2'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
for n in ('V2_PLAN.json','RUN_COMMAND_V2.json','watch_run_v2.py','launch_c10_v2.py','run_output_v2'):assert not (R/n).exists(),n
p=new/'backend.py';text=p.read_text();assert "if cfg.get('model_type')!='xclip':raise ValueError('XCLIP_config_model_type_required_actual_xclip')" in text
lock=json.loads((new/'CODE_LOCK.json').read_text());h=sha(p);assert lock['runtime_files']['backend.py']==h
oldlock=json.loads((R/'b8_source/CODE_LOCK.json').read_text());before=oldlock['runtime_files']['backend.py']
manifest=R/'meta/d3_execution.json';asset=R/'typed/asset_lock.json';dep1=R.parents[1]/'fingerprint_cpu/author_input_parity_v1/dependencies/site';dep2=R.parents[1]/'baselines/input_qualification_v1/cpu_deps';asset_dir=R.parents[1]/'baselines/inference_assets_ready_v1/assets/xclip16';prepared=R.parents[1]/'fingerprint_cpu/author_input_parity_v1/runs/run_002';out=R/'run_output_v2'
assert sha(manifest)=='c13d6b5dc6951d5dfd5976fd396f9687e06f89df5b9ff7a974e85ab513b74b6e' and sha(asset)=='3239e413748e15def993458f8378ede6c7ab6d41dfd3dbcb97d89f98bf486230'
plan=[sys.executable,'-B',str(new/'runner.py'),'plan','--execution-manifest',str(manifest),'--manifest-sha256',sha(manifest),'--asset-lock',str(asset),'--asset-lock-sha256',sha(asset),'--asset-dir',str(asset_dir),'--prepared-root',str(prepared),'--dependency-path',str(dep1),'--dependency-path',str(dep2),'--output',str(out)]
p2=subprocess.run(plan,capture_output=True,text=True,cwd=new);(R/'V2_PLAN.json').write_text(json.dumps({'argv':plan,'exit_code':p2.returncode,'stdout':p2.stdout,'stderr':p2.stderr,'backend_before':before,'backend_after':h,'prepared_by':'make_v2_continue.py 2026-10-16 after sha() bug in make_v2_remote.py'},indent=2)+'\n')
if p2.returncode!=0:print(p2.stdout[-3000:],p2.stderr[-3000:]);sys.exit(1)
run=plan.copy();run[run.index('plan')]='run';run+=['--cpu-affinity','4,5','--checkpoint-every','1','--max-output-mib','32']
(R/'RUN_COMMAND_V2.json').write_text(json.dumps({'argv':run,'source_variant':'b8_source_v2','output':str(out),'backend_change':'exact config model_type xclip acceptance only','old_failure_preserved':'run_output/MODEL_LOAD_FAILURE.json','input_manifest_sha256':sha(manifest),'asset_lock_sha256':sha(asset),'members':12},indent=2)+'\n')
watch=(R/'watch_run.py').read_text()
for a,b in [('RUN_COMMAND.json','RUN_COMMAND_V2.json'),('worker.stdout.log','worker_v2.stdout.log'),('worker.stderr.log','worker_v2.stderr.log'),('WORKER_HANDLE.json','WORKER_HANDLE_V2.json'),('RUN_RECEIPT.json','RUN_RECEIPT_V2.json'),('WATCH_HEARTBEAT.json','WATCH_HEARTBEAT_V2.json'),("cwd=R/'b8_source'","cwd=R/'b8_source_v2'"),("'run_output/","'run_output_v2/")]:
 assert a in watch,a;watch=watch.replace(a,b)
(R/'watch_run_v2.py').write_text(watch)
launch=(R/'launch_c10.py').read_text()
for a,b in [('RUN_ONCE.claim','RUN_ONCE_V2.claim'),('watch_run.py','watch_run_v2.py'),('supervisor.stdout.log','supervisor_v2.stdout.log'),('supervisor.stderr.log','supervisor_v2.stderr.log'),('LAUNCH.json','LAUNCH_V2.json'),('RUN_RECEIPT.json','RUN_RECEIPT_V2.json')]:
 assert a in launch,a;launch=launch.replace(a,b)
(R/'launch_c10_v2.py').write_text(launch)
print(json.dumps({'backend_before':before,'backend_after':h,'plan_exit':p2.returncode,'plan_stdout_tail':p2.stdout[-1500:],'output':str(out),'members':12}))
