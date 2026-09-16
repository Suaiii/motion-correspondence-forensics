"""Re-extract DINO on a common time grid; server-only, resumable, no final data.

Eight nearest native frames in a centered one-second window at 8 Hz. This
window admits the 1.6-second VC2 clips without retiming them. Actual PTS error
is preserved: equal target spacing does NOT guarantee equal native lag.
Native8 controls are sliced from prior native16 features on the same IDs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np
import torch


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text())


def save(p,v):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)


def choose(pts):
    pts=np.asarray(pts,dtype=np.float64)
    if len(pts)<8 or not np.isfinite(pts).all() or not (np.diff(pts)>0).all():
        raise ValueError('invalid_or_insufficient_native_pts')
    duration=pts[-1]-pts[0]+np.median(np.diff(pts))
    if duration<1-1e-6:raise ValueError('shorter_than_one_second')
    target=pts[0]+(duration-1)/2+np.arange(8)/8
    hi=np.clip(np.searchsorted(pts,target),0,len(pts)-1);lo=np.maximum(0,hi-1)
    ix=np.where(np.abs(pts[lo]-target)<=np.abs(pts[hi]-target),lo,hi)
    if len(set(ix))!=8:raise ValueError('repeated_sample_indices')
    if np.max(np.abs(pts[ix]-target))>.062501:raise ValueError('native_timing_error_exceeds_half_step')
    return ix,{'indices':ix.tolist(),'pts':pts[ix].tolist(),'targets':target.tolist(),
               'duration':float(duration),'timing_error':(pts[ix]-target).tolist(),
               'median_dt':float(np.median(np.diff(pts[ix])))}


def decode(row):
    try:
        path=row['raw_path']
        if sha(path)!=row['sha256']:raise ValueError('source_hash_changed')
        probe=subprocess.run(['ffprobe','-threads','1','-v','error','-select_streams','v:0','-show_frames',
            '-show_entries','frame=best_effort_timestamp_time','-of','json',path],capture_output=True,timeout=60,check=True)
        pts=[float(f['best_effort_timestamp_time']) for f in json.loads(probe.stdout)['frames']]
        ix,meta=choose(pts); wanted=set(ix); frames=[]
        cap=cv2.VideoCapture(path,cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1])
        try:
            for j in range(int(ix[-1])+1):
                ok,bgr=cap.read()
                if not ok:raise ValueError('frame_decode_failed')
                if j in wanted:
                    h,w=bgr.shape[:2];s=min(h,w)
                    frames.append(cv2.resize(bgr[(h-s)//2:(h-s)//2+s,(w-s)//2:(w-s)//2+s],(224,224),interpolation=cv2.INTER_AREA))
        finally:cap.release()
        assert len(frames)==8
        frames=np.stack(frames); gray=np.stack([cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in frames])
        if np.mean((gray.mean((1,2))<5)&(gray.std((1,2))<5))>=.5:raise ValueError('black_frames')
        return row,frames,meta,None
    except Exception as e:return row,None,None,repr(e)


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-seconds',type=int,default=1800);a=p.parse_args();start=time.monotonic();root=a.output
    b=a.base; parent=b/'runs/cached_dino_baseline_v1';old=read(parent/'manifest.json')
    dirs=[b/'runs/overnight_20260911'/n for n in ('gpu_dino_v1','vript_dino_group1746_v1')]
    mapping={}
    for d in dirs:
        for file in (d/'records').glob('*.json'):
            r=read(file)
            if r['status']=='ok':mapping[r['sample_id']]=r
    rows=[]
    for r in old:
        q=mapping[r['sample_id']];assert q['sha256']==r['sha256']
        rows.append(dict(r,raw_path=q['path']))
    weights=b/'models/dinov2_vitb14_pretrain.pth';rev='7764ea0f912e53c92e82eb78a2a1631e92725fc8'
    repo=b/'models'/('dinov2-'+rev);assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==rev
    assert not subprocess.check_output(['git','-C',str(repo),'diff','--name-only'],text=True).strip()
    weight_hash=sha(weights);assert weight_hash=='0b8b82f85de91b424aded121c7e1dcc2b7bc6d0adeea651bf73a13307fad8c73'
    lock={'scope':'matched-time exploratory re-extraction; not final','parent_manifest_sha256':sha(parent/'manifest.json'),
          'script_sha256':sha(__file__),'model_revision':rev,'weights_sha256':weight_hash,
          'sampling':'center 1 second, 8 nearest unique native frames at 8Hz, tie earlier, no pixel interpolation',
          'spatial':'center square, area resize 224; RGB ImageNet normalization',
          'native_control':'middle 8 of the same frozen native16 cache',
          'precision':'float32 features from bfloat16 autocast; same as original cache',
          'budget_seconds_per_attempt':a.max_seconds,'workers':8,'video_batch':16,'torch':torch.__version__,
          'requested':len(rows),'final_access':False,'training_released':False}
    root.mkdir(parents=True,exist_ok=True)
    if (root/'lock.json').exists():assert read(root/'lock.json')==lock
    else:save(root/'lock.json',lock)
    for name in ('features','records'):(root/name).mkdir(exist_ok=True)
    pending=[];complete=[]
    for r in rows:
        key=hashlib.sha256(r['sample_id'].encode()).hexdigest();record=root/'records'/(key+'.json')
        if record.exists():
            old_record=read(record)
            if old_record['status']=='ok':assert sha(root/old_record['time_feature_file'])==old_record['time_feature_sha256']
            complete.append(old_record)
        else:pending.append(dict(r,key=key))
    cv2.setNumThreads(1);torch.set_num_threads(4);torch.manual_seed(20260916)
    model=torch.hub.load(str(repo),'dinov2_vitb14',source='local',pretrained=False).cuda().eval()
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
    mean=torch.tensor([.485,.456,.406],device='cuda')[None,:,None,None];std=torch.tensor([.229,.224,.225],device='cuda')[None,:,None,None]
    gpu_seconds=0;torch.cuda.reset_peak_memory_stats()
    progress={'requested':len(rows),'completed':len(complete),'this_attempt_seconds':0,
              'cuda_forward_seconds':0,'peak_gpu_allocated_gib':0}
    with ThreadPoolExecutor(max_workers=8) as pool, torch.inference_mode():
        for start_i in range(0,len(pending),16):
            if time.monotonic()-start>a.max_seconds:break
            if __import__('shutil').disk_usage(root).free<2*2**30:raise RuntimeError('2GiB reserve reached')
            batch=list(pool.map(decode,pending[start_i:start_i+16])); good=[]
            for row,frames,meta,error in batch:
                if error:
                    item=dict(row,status='excluded_or_error',reason=error);save(root/'records'/(row['key']+'.json'),item);complete.append(item)
                else:good.append((row,frames,meta))
            if good:
                arr=np.concatenate([v[1] for v in good]);x=torch.from_numpy(arr[...,::-1].copy()).permute(0,3,1,2).cuda().float()/255
                begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);begin.record()
                with torch.autocast('cuda',dtype=torch.bfloat16):z=model((x-mean)/std)
                end.record();z=z.float().cpu().numpy().reshape(len(good),8,768);gpu_seconds+=begin.elapsed_time(end)/1000
                assert np.isfinite(z).all()
                for i,(r,_,meta) in enumerate(good):
                    dest=root/'features'/(r['key']+'.npy');tmp=dest.with_suffix('.partial')
                    with tmp.open('xb') as f:np.save(f,z[i])
                    os.replace(tmp,dest)
                    item=dict(r,status='ok',sampling=meta,time_feature_file=str(dest.relative_to(root)),time_feature_sha256=sha(dest))
                    save(root/'records'/(r['key']+'.json'),item);complete.append(item)
            progress={'requested':len(rows),'completed':len(complete),'this_attempt_seconds':time.monotonic()-start,
                      'cuda_forward_seconds':gpu_seconds,'peak_gpu_allocated_gib':torch.cuda.max_memory_allocated()/2**30}
            save(root/'progress.json',progress)
            if len(complete)%160<16:print(json.dumps(progress),flush=True)
    from collections import Counter
    save(root/'summary.json',dict(progress,complete=len(complete)==len(rows),statuses=dict(Counter(r['status'] for r in complete))))


if __name__=='__main__':main()
