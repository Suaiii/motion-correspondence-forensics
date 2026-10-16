# v3 = v2 source unchanged; only --prepared-root corrected. v2 failed at frozen_prepared_JPEG_reader
# because member prepared_folder already starts with runs/run_002/ (path doubled). v2 evidence kept.
import hashlib,json,subprocess,sys
from pathlib import Path
R=Path('/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_cpu_consumption_v1')
for n in ('V3_PLAN.json','RUN_COMMAND_V3.json','watch_run_v3.py','launch_c10_v3.py','run_output_v3'):assert not (R/n).exists(),n
cmd=json.loads((R/'RUN_COMMAND_V2.json').read_text())
old_root=str(R.parents[1]/'fingerprint_cpu/author_input_parity_v1/runs/run_002');new_root=str(R.parents[1]/'fingerprint_cpu/author_input_parity_v1')
def fix(a):
 a=list(a);i=a.index('--prepared-root');assert a[i+1]==old_root;a[i+1]=new_root
 j=a.index('--output');a[j+1]=str(R/'run_output_v3');return a
run=fix(cmd['argv']);plan=run[:run.index('--cpu-affinity')];plan[plan.index('run')]='plan'
p=subprocess.run(plan,capture_output=True,text=True,cwd=R/'b8_source_v2')
(R/'V3_PLAN.json').write_text(json.dumps({'argv':plan,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'change_from_v2':'prepared_root '+old_root+' -> '+new_root},indent=2)+'\n')
if p.returncode:print(p.stdout[-2000:],p.stderr[-2000:]);sys.exit(1)
cmd.update(argv=run,output=str(R/'run_output_v3'),prepared_root_change={'v2':old_root,'v3':new_root},v2_failure_preserved='run_output_v2/')
(R/'RUN_COMMAND_V3.json').write_text(json.dumps(cmd,indent=2)+'\n')
for src,dst in (('watch_run_v2.py','watch_run_v3.py'),('launch_c10_v2.py','launch_c10_v3.py')):
 t=(R/src).read_text().replace('_V2','_V3').replace('_v2.','_v3.').replace("'run_output_v2/","'run_output_v3/")
 t=t.replace("cwd=R/'b8_source_v3'","cwd=R/'b8_source_v2'");(R/dst).write_text(t)
print('plan ok')
