import json,os,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
claim=R/'RUN_ONCE_V2.claim'
fd=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,str(time.time()).encode());os.close(fd)
if (R/'RUN_RECEIPT_V2.json').exists():raise RuntimeError('already completed')
out=(R/'supervisor_v2.stdout.log').open('xb');err=(R/'supervisor_v2.stderr.log').open('xb')
p=subprocess.Popen([sys.executable,'-I','-B',str(R/'watch_run_v2.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
stat=(Path('/proc')/str(p.pid)/'stat').read_text();tail=stat[stat.rfind(')')+2:].split()
rec={'PID':p.pid,'start_ticks':tail[19],'server_unix':time.time(),'argv':[sys.executable,'-I','-B',str(R/'watch_run_v2.py')],'SSH_lifecycle_independent':True,'automatic_restart':False}
(R/'LAUNCH_V2.json').open('x').write(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));out.close();err.close()
