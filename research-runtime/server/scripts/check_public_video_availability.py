"""Bounded metadata-only availability probe; no media, credentials or browser cookies."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);a=p.parse_args()
    root=a.run_dir;root.mkdir(parents=True,exist_ok=False);tools=root/'tools'
    selection=json.loads(a.selection.read_text(encoding='utf-8-sig'));rows=selection['rows']
    if len(rows)!=3:raise ValueError('Only the frozen three-video metadata probe is allowed')
    env=dict(os.environ,PIP_CONFIG_FILE=os.devnull)
    for key in ('PIP_INDEX_URL','PIP_EXTRA_INDEX_URL'):env.pop(key,None)
    subprocess.run([sys.executable,'-m','pip','install','--index-url','https://pypi.org/simple','--target',str(tools),
                    '--report',str(root/'install_report.json'),'yt-dlp==2026.8.19'],check=True,timeout=180,env=env)
    env['PYTHONPATH']=str(tools)
    lock={'selection_sha256':hashlib.sha256(a.selection.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'version':'2026.8.19','media_download':False,'cookies_used':False,'no_alternative_id_replacement':True}
    (root/'lock.json').write_text(json.dumps(lock,indent=2));results=[]
    for r in rows:
        if r['url']!='https://www.youtube.com/watch?v='+r['video_id'] or not re.fullmatch(r'[A-Za-z0-9_-]{11}',r['video_id']):raise ValueError('Unexpected author URL')
        cmd=[sys.executable,'-m','yt_dlp','--ignore-config','--no-cache-dir','--skip-download','--dump-single-json',
             '--no-playlist','--socket-timeout','10','--retries','0','--extractor-retries','0','--no-progress',r['url']]
        result={'video_id':r['video_id'],'observed_utc':datetime.now(timezone.utc).isoformat(),'downloaded_video':False}
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=45,env=env)
            result['returncode']=proc.returncode
            # Do not persist resolved CDN URLs or proxy credentials.
            result['message']=re.sub(r'(https?://)[^/\s@]+@',r'\1[REDACTED]@',proc.stderr[-2500:])
            if proc.returncode==0:
                info=json.loads(proc.stdout);assert info['id']==r['video_id']
                result.update(status='metadata_available',duration=info.get('duration'),availability=info.get('availability'),
                              video_formats=sum(f.get('vcodec','none')!='none' for f in info.get('formats',[])))
            else:result['status']='unavailable_or_tool_error'
        except subprocess.TimeoutExpired:result.update(status='timeout',timeout_seconds=45)
        results.append(result);(root/'results.json').write_text(json.dumps(results,indent=2))
        print(json.dumps({'video_id':result['video_id'],'status':result['status']}),flush=True)
    (root/'summary.json').write_text(json.dumps({'completed':len(results),'metadata_available':sum(r['status']=='metadata_available' for r in results),
        'videos_downloaded':0,'scope':'three lexicographic prefix IDs; availability probe, not dataset acceptance'},indent=2))


if __name__=='__main__':main()
