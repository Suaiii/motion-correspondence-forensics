"""Idempotent server launch: deadline guard first, then one registered QC job."""
import argparse
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def process_matches(pid,needle):
    try:return str(needle).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes()
    except OSError:return False


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--python',required=True);p.add_argument('--deadline',required=True);a=p.parse_args()
    deadline=datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:raise ValueError('Explicit timezone required')
    root=a.base.resolve()/'runs/overnight_20260911';root.mkdir(parents=True,exist_ok=True)
    assets=a.assets.resolve();guard=assets/'deadline_guard.py'
    if not guard.is_file():raise FileNotFoundError('Deadline guard must be uploaded first')
    lock=root/'guard.lock'
    active=False
    if lock.exists():
        pid=int(lock.read_text());active=process_matches(pid,guard)
        if not active:lock.rename(root/f'guard.stale-{time.time_ns()}.lock')
    if not active:
        log=(root/'guard.log').open('a')
        subprocess.Popen([sys.executable,str(guard),'--run-dir',str(root),'--deadline',a.deadline],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(30):
        status=root/'guard_status.json'
        if status.exists():
            s=json.loads(status.read_text())
            if s['deadline']==deadline.isoformat() and process_matches(s['guard_pid'],guard):break
        time.sleep(.2)
    else:raise RuntimeError('No live verified deadline guard; refuse workloads')
    if s['phase']!='running' or datetime.now(timezone.utc)>=deadline-timedelta(minutes=20):
        print(json.dumps({'guard_verified':True,'work_started':False,'reason':'cutoff_reached'}));return
    if (root/'qc_summary.json').exists():
        print(json.dumps({'guard_verified':True,'work_started':False,'reason':'QC_already_completed'}));return
    record=root/'job_qc.json'
    if record.exists():
        job=json.loads(record.read_text())
        if process_matches(job['pid'],root):
            print(json.dumps({'guard_verified':True,'work_started':False,'reason':'QC_already_running','pid':job['pid']}));return
    if not shutil.which('unrar'):
        print(json.dumps({'guard_verified':True,'work_started':False,'reason':'unrar_installation_required'}));return
    env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTHONUTF8='1')
    temp=a.base/'cache/tmp';temp.mkdir(parents=True,exist_ok=True);env['TMPDIR']=str(temp)
    selection=assets/'night_qc_selection_20260911.json'
    cmd=[a.python,str(assets/'night_qc.py'),'--run-dir',str(root),'--selection',str(selection),
        '--archive-root',str(a.base/'data/releases/jian-0/GenVidBench/GenVidBench/Pair1'),
        '--deadline',a.deadline,'--workers','12']
    log=(root/'qc.log').open('a');job=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    stat=(Path('/proc')/str(job.pid)/'stat').read_text().rsplit(')',1)[1].split()
    record.write_text(json.dumps({'pid':job.pid,'start_ticks':stat[19],'command':cmd,'started_utc':datetime.now(timezone.utc).isoformat()},indent=2))
    print(json.dumps({'guard_verified':True,'work_started':True,'pid':job.pid,'run_dir':str(root)}))


if __name__=='__main__':main()
