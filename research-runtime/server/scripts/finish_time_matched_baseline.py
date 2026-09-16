"""Wait for one identified extraction and evaluate only its complete cache."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def stamp(pid):
    try:return (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:return None


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True)
    p.add_argument('--pid',type=int,required=True);p.add_argument('--start-ticks',required=True)
    a=p.parse_args();base=a.base;root=base/'runs/time_matched_followup_v1';root.mkdir(exist_ok=False)
    cache=base/'runs/time_matched_dino_v1';deadline=time.monotonic()+2100
    def status(phase,**details):
        tmp=root/'status.tmp';tmp.write_text(json.dumps({'observed_utc':datetime.now(timezone.utc).isoformat(),
            'phase':phase,'source_pid':a.pid,'source_start_ticks':a.start_ticks,**details},indent=2)+'\n')
        os.replace(tmp,root/'status.json')
    while True:
        summary=cache/'summary.json'
        if summary.exists():
            s=json.loads(summary.read_text())
            if s.get('complete'):break
            if stamp(a.pid)!=a.start_ticks:
                status('stopped_incomplete',summary=s);return
        elif stamp(a.pid)!=a.start_ticks:
            status('source_terminal_without_summary');return
        if time.monotonic()>deadline:
            status('followup_deadline');return
        status('waiting_for_identified_extraction');time.sleep(10)
    status('evaluating_complete_cache')
    cmd=[sys.executable,str(base/'paired_dino_baseline.py'),'--base',str(base),
         '--time-cache',str(cache),'--output',str(base/'runs/paired_dino_time_v1')]
    try:
        with (root/'evaluation.log').open('x') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        status('evaluation_finished' if result.returncode==0 else 'evaluation_failed',returncode=result.returncode)
    except subprocess.TimeoutExpired:
        status('evaluation_timeout')


if __name__=='__main__':main()
