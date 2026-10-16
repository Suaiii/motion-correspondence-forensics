"""Lossless-remux timing diagnostic; changes playback speed, not decoded frame content."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def worker(task):
    import cv2
    import numpy as np
    from forensics import video
    row,path,target=task;cv2.setNumThreads(1);factor=.8 if row['source']=='ms' else 1.25
    def frames_and_pts(p):
        info=json.loads(video.command(['ffprobe','-threads','1','-v','error','-select_streams','v:0','-show_frames',
            '-show_entries','frame=best_effort_timestamp_time','-of','json',str(p)]))
        pts=np.array([float(r['best_effort_timestamp_time']) for r in info['frames']])
        cap=cv2.VideoCapture(str(p),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);hashes=[]
        try:
            while True:
                ok,f=cap.read()
                if not ok:break
                hashes.append(hashlib.sha256(f.tobytes()).hexdigest())
        finally:cap.release()
        if len(pts)!=len(hashes) or len(pts)<2 or not (np.diff(pts)>0).all():raise ValueError('Frame/PTS mismatch')
        duration=float(pts[-1]-pts[0]+np.median(np.diff(pts)))
        targets=pts[0]+(duration-2)/2+np.arange(16)/8
        indices=np.searchsorted(pts,targets,side='right')-1
        eligible=duration+1e-6>=2 and indices.min()>=0 and len(set(indices))==16
        return {'frame_hashes':hashes,'pts':pts.tolist(),'duration_from_pts':duration,'strict_8fps_2s_eligible':bool(eligible)}
    result={'sample_id':row['sample_id'],'source':row['source'],'timestamp_scale':factor,'status':'error'}
    try:
        before=frames_and_pts(path)
        command=['ffmpeg','-v','error','-nostdin','-itsscale',str(factor),'-i',path,'-map','0:v:0','-an','-c:v','copy',target]
        video.command(command,timeout=120)
        after=frames_and_pts(target)
        result.update(status='ok',before=before,after=after,decoded_frames_identical=before['frame_hashes']==after['frame_hashes'],
            eligibility_changed=before['strict_8fps_2s_eligible']!=after['strict_8fps_2s_eligible'])
    except Exception as exc:result['reason']=type(exc).__name__+': '+str(exc)
    return result


def main():
    from forensics.common import read,write,object_hash,sha
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--parent-run',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--workers',type=int,default=12);p.add_argument('--deadline',required=True)
    a=p.parse_args();root=a.run_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    if datetime.now(timezone.utc)>=datetime.fromisoformat(a.deadline) or (a.parent_run/'STOP_NEW_JOBS').exists():raise RuntimeError('No new job after cutoff')
    selection=read(a.selection)['rows'];selected=[];tasks=[]
    for source in ('ms','vc2'):
        group=sorted([r for r in selection if r['source']==source],key=lambda r:object_hash(['retime-20260911',r['sample_id']]))[:50]
        files={r['basename']:r for r in read(a.parent_run/f'extraction_{source}.json')['files']}
        for row in group:
            entry=files[row['basename']]
            if sha(entry['path'])!=entry['sha256']:raise ValueError('Source changed')
            tasks.append((row,entry['path'],str(root/(object_hash(row['sample_id'])+'.mp4'))))
        selected+=group
    write(root/'protocol.json',{'scope':'posthoc playback-speed/eligibility diagnostic, no detection accuracy','selection':selected,
        'source_sampling':'same frozen 1000-video cohort; deterministic 50 per source','timestamp_scales':{'ms':.8,'vc2':1.25},
        'expected_invariant':'same ordered decoded pixels; elapsed playback time intentionally changes','script_sha256':sha(__file__)})
    results=[];started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        for f in as_completed([pool.submit(worker,t) for t in tasks]):
            row=f.result();results.append(row);write(root/(object_hash(row['sample_id'])+'.json'),row)
    summary={'requested':100,'completed':len(results),'ok':sum(r['status']=='ok' for r in results),
        'identical_decoded_frames':sum(r.get('decoded_frames_identical',False) for r in results),
        'eligibility_flipped_with_identical_frames':sum(r.get('eligibility_changed',False) and r.get('decoded_frames_identical',False) for r in results),
        'wall_seconds':time.perf_counter()-started,'classification_metrics_computed':False,
        'meaning':'Selection can depend on playback timing despite identical frames. This does not prove time is irrelevant or that source bias is removed.'}
    write(root/'summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
