"""Frozen real-source feature cache after completed acquisition; no classifier fit."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,r):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf-8');os.replace(tmp,p)


def init_worker(_):
    import cv2
    from forensics import video
    cv2.setNumThreads(1);torch.set_num_threads(1)
    original=video.command
    def command(args,timeout=180):
        if args[0]=='ffprobe':args=[args[0],'-threads','1',*args[1:]]
        return original(args,timeout)
    video.command=command


class Videos(Dataset):
    def __init__(self,rows):self.rows=rows
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        from index16_decode import decode
        r=self.rows[i]
        try:
            if sha(r['path'])!=r['sha256']:raise ValueError('Raw video changed')
            bgr,meta=decode(r['path'],{'frames':16,'size':224})
            if meta['pts']!=r['expected_sampling']['pts'] or meta['indices']!=r['expected_sampling']['indices']:
                raise ValueError('Sampling differs from acquisition QC')
            rgb=torch.from_numpy(bgr[...,::-1].copy()).permute(0,3,1,2)
            return {'row':r,'frames':rgb,'sampling':meta,'error':None}
        except Exception as e:return {'row':r,'frames':None,'error':type(e).__name__+': '+str(e)}


def collate(batch):
    good=[r for r in batch if r['error'] is None]
    return {'good':[{k:v for k,v in r.items() if k!='frames'} for r in good],
            'errors':[r for r in batch if r['error'] is not None],
            'frames':torch.cat([r['frames'] for r in good]) if good else None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--download-dir',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--decode-scripts',type=Path,required=True)
    p.add_argument('--models',type=Path,required=True);p.add_argument('--deadline',required=True);p.add_argument('--device',default='cuda')
    p.add_argument('--workers',type=int,default=12);p.add_argument('--video-batch',type=int,default=16);p.add_argument('--limit',type=int,required=True)
    p.add_argument('--wait-for-download',action='store_true');a=p.parse_args()
    sys.path[:0]=[a.runtime,str(a.decode_scripts)];root=a.run_dir;root.mkdir(parents=True,exist_ok=True)
    deadline=datetime.fromisoformat(a.deadline)
    def cutoff():return datetime.now(timezone.utc)>=deadline or (root.parent/'STOP_NEW_JOBS').exists()
    while not (a.download_dir/'summary.json').exists():
        if cutoff():save(root/'watch_status.json',{'phase':'cutoff_before_acquisition_complete'});return
        if not a.wait_for_download:raise ValueError('Acquisition summary required')
        save(root/'watch_status.json',{'phase':'waiting_for_acquisition','observed_utc':datetime.now(timezone.utc).isoformat()});time.sleep(30)
    if cutoff():return
    ds=read(a.download_dir/'summary.json')
    if not ds['complete']:raise ValueError('Acquisition is incomplete')
    selected=read(a.selection)['rows']
    if not 0<a.limit<=len(selected):raise ValueError('Invalid explicit limit')
    selected=selected[:a.limit];downloads={}
    for path in (a.download_dir/'records').glob('*.json'):
        r=read(path)
        if r['sample_id'] in downloads:raise ValueError('Duplicate download identity')
        downloads[r['sample_id']]=r
    if any(r['sample_id'] not in downloads for r in selected):raise ValueError('Missing selected download records')
    rev='7764ea0f912e53c92e82eb78a2a1631e92725fc8';repo=a.models/('dinov2-'+rev);weights=a.models/'dinov2_vitb14_pretrain.pth'
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=rev:raise ValueError('DINO code revision changed')
    weight_hash=read(a.models/'dinov2_vitb14_pretrain.pth.receipt.json')['sha256_observed']
    lock={'selection_sha256':sha(a.selection),'download_lock_sha256':sha(a.download_dir/'lock.json'),'requested':len(selected),
          'script_sha256':sha(__file__),'decoder_sha256':sha(a.decode_scripts/'index16_decode.py'),'model_revision':rev,
          'weights_sha256':weight_hash,'workers':a.workers,'video_batch':a.video_batch,'ffprobe_threads':1,'device':a.device,
          'sampling':'center 16 native frames; center square crop; area resize 224; match saved QC PTS',
          'precision':'bfloat16 autocast; saved float32','scope':'One real-source frozen features; ancestry pending; no classifier or formal mechanism training'}
    if (root/'lock.json').exists() and read(root/'lock.json')!=lock:raise ValueError('Feature configuration changed')
    save(root/'lock.json',lock)
    for name in ['records','features']:(root/name).mkdir(exist_ok=True)
    pending=[];complete=[]
    for row in selected:
        sid=row['sample_id'];key=hashlib.sha256(sid.encode()).hexdigest();record=root/'records'/(key+'.json');q=downloads[sid]
        if record.exists():
            old=read(record)
            if old['status']=='ok' and sha(root/old['feature_file'])!=old['feature_sha256']:raise ValueError('Saved feature changed')
            complete.append(old);continue
        if q['status']!='ok' or q.get('native16',{}).get('status')!='ok':
            out={**row,'status':'excluded','reason':q.get('reason') or q.get('native16',{}).get('reason','not_eligible')}
            save(record,out);complete.append(out);continue
        pending.append({**row,'source':'vript','key':key,'sha256':q['sha256'],'path':str(a.download_dir/q['raw_file']),
                        'expected_sampling':q['native16']['sampling']})
    from forensics.backbones import dinov2
    torch.set_num_threads(1);torch.manual_seed(20260911)
    model=dinov2(repo,weights,weight_hash,a.device,'dinov2_vitb14')
    loader=DataLoader(Videos(pending),batch_size=a.video_batch,num_workers=a.workers,collate_fn=collate,worker_init_fn=init_worker,
                      multiprocessing_context='spawn',pin_memory=True,prefetch_factor=2)
    mean=torch.tensor([.485,.456,.406],device=a.device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=a.device)[None,:,None,None]
    started=time.perf_counter();gpu_ms=0.;precision_checked=(root/'precision_check.json').exists();torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        for batch in loader:
            if cutoff():break
            for error in batch['errors']:
                out={**error['row'],'status':'error','reason':error['error']};save(root/'records'/(out['key']+'.json'),out);complete.append(out)
            if not batch['good']:continue
            x=batch['frames'].to(a.device,non_blocking=True).float()/255;x=(x-mean)/std
            if not precision_checked:
                fp=model(x[:16]).float()
                with torch.autocast('cuda',dtype=torch.bfloat16):bf=model(x[:16]).float()
                cos=torch.nn.functional.cosine_similarity(fp,bf,dim=1)
                check={'frames':16,'cosine_min':float(cos.min()),'cosine_mean':float(cos.mean()),'passed':bool(cos.min()>.999)}
                save(root/'precision_check.json',check)
                if not check['passed']:raise ValueError('Mixed-precision sanity check failed')
                precision_checked=True
            start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);start.record()
            with torch.autocast('cuda',dtype=torch.bfloat16):features=model(x)
            end.record();values=features.float().cpu().numpy().reshape(len(batch['good']),16,768);gpu_ms+=start.elapsed_time(end)
            if not np.isfinite(values).all():raise ValueError('Nonfinite feature values')
            for j,item in enumerate(batch['good']):
                row=item['row'];rel='features/'+row['key']+'.npy';target=root/rel
                with open(str(target)+'.tmp','wb') as f:np.save(f,values[j])
                os.replace(str(target)+'.tmp',target)
                out={**row,'status':'ok','sampling':item['sampling'],'feature_file':rel,'feature_sha256':sha(target),'shape':[16,768]}
                save(root/'records'/(row['key']+'.json'),out);complete.append(out)
            progress={'completed':len(complete),'requested':len(selected),'wall_seconds':time.perf_counter()-started,'cuda_forward_seconds':gpu_ms/1000,
                      'peak_gpu_allocated_gib':torch.cuda.max_memory_allocated()/2**30}
            save(root/'progress.json',progress);print(json.dumps(progress),flush=True)
    from collections import Counter
    save(root/'summary.json',{'complete':len(complete)==len(selected),'requested':len(selected),'completed':len(complete),
         'statuses':dict(Counter(r['status'] for r in complete)),'wall_seconds':time.perf_counter()-started,'cuda_forward_seconds':gpu_ms/1000,
         'classification_metrics_computed':False})


if __name__=='__main__':main()
