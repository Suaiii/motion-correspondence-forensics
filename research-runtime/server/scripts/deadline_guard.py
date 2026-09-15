"""Instance-local deadline enforcement; independent of SSH and the desktop scheduler."""
import argparse
import errno
import json
import os
import signal
import subprocess
import time
from datetime import datetime,timezone,timedelta
from pathlib import Path


def phase(now,deadline,early=False):
    if early or now>=deadline-timedelta(minutes=1):return 'shutdown'
    if now>=deadline-timedelta(minutes=10):return 'drain'
    if now>=deadline-timedelta(minutes=20):return 'no_new_jobs'
    return 'running'


def save(path,value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8') as f:
        json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)


def best_effort_save(path,value):
    try:save(path,value);return True
    except OSError:return False


def stop_marker(root):
    try:(root/'STOP_NEW_JOBS').touch(exist_ok=True)
    except OSError:pass


def invoke_shutdown(command):
    """AutoDL may install executable shell text without a shebang."""
    argv=[command]
    try:
        result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    except OSError as exc:
        if exc.errno!=errno.ENOEXEC:raise
        argv=['/bin/bash',command]
        result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    return {'returncode':result.returncode,'stdout':result.stdout[-1000:],
            'stderr':result.stderr[-1000:],'invocation':argv}


def stop_registered(root):
    stopped=[]
    for file in sorted(root.glob('job_*.json')):
        try:
            job=json.loads(file.read_text());pid=int(job['pid'])
            proc=Path('/proc')/str(pid)
            if not proc.exists():continue
            stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
            if stat[19]!=str(job['start_ticks']):continue
            cmd=(proc/'cmdline').read_bytes()
            if str(root).encode() not in cmd:continue
            if os.getpgid(pid)!=pid:raise RuntimeError('Job must have its own process group')
            os.killpg(pid,signal.SIGTERM);stopped.append(pid)
        except (OSError,ValueError,KeyError,IndexError,RuntimeError):continue
    return stopped


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--deadline',required=True)
    p.add_argument('--shutdown-command',default='/usr/bin/shutdown');p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();root=a.run_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    deadline=datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:raise ValueError('Explicit timezone required')
    fd=os.open(root/'guard.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd,str(os.getpid()).encode());os.close(fd)
    previous=None;stopped=[]
    try:
        while True:
            now=datetime.now(timezone.utc);state=phase(now,deadline,(root/'stop_early.request').exists())
            if state in ('drain','shutdown'):
                stopped+=stop_registered(root)
                stop_marker(root)
            elif state=='no_new_jobs':stop_marker(root)
            receipt={'guard_pid':os.getpid(),'observed_utc':now.isoformat(),'deadline':deadline.isoformat(),'phase':state,
                'stopped_registered_jobs':sorted(set(stopped)),'shutdown_command':a.shutdown_command,'dry_run':a.dry_run}
            best_effort_save(root/'guard_status.json',receipt)
            if state!=previous:
                try:print(json.dumps(receipt),flush=True)
                except OSError:pass
                previous=state
            if state=='shutdown':
                if a.dry_run:return
                try:os.sync()
                except OSError:pass
                try:
                    response=invoke_shutdown(a.shutdown_command)
                except (OSError,subprocess.TimeoutExpired) as exc:
                    response={'returncode':124,'error':type(exc).__name__,
                              'errno':getattr(exc,'errno',None),'strerror':getattr(exc,'strerror',None)}
                best_effort_save(root/'shutdown_command_result.json',{'time_utc':datetime.now(timezone.utc).isoformat(),**response})
                # If the process survives a failed provider call, retry; never restart compute.
                time.sleep(3)
            else:time.sleep(min(5,max(.1,(deadline-timedelta(minutes=1)-now).total_seconds())))
    finally:
        (root/'guard.lock').unlink(missing_ok=True)


if __name__=='__main__':main()
