"""Resource tuning only: historical inputs and synthetic training tensors, no detector claims."""
import argparse
import gc
import json
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def worker(item):
    import cv2
    import numpy as np
    from forensics import video
    from forensics.controls import represent
    from forensics.common import sha,safe_path
    r,root,cfg=item;cv2.setNumThreads(1)
    original=video.command
    def limited_command(args,timeout=180):
        if args[0]=='ffprobe':args=[args[0],'-threads','1',*args[1:]]
        return original(args,timeout)
    video.command=limited_command
    p=safe_path(root,r['path']);tick=time.perf_counter()
    if sha(p)!=r['sha256']:raise ValueError('Input bytes changed')
    frames,q=video.decode(p,cfg['sampling']);decoded=time.perf_counter()
    f=video.flows(frames);it=iter(f)
    views,_=represent(frames,cfg['controls'],lambda *_:next(it))
    return {'sample_id':r['sample_id'],'decode_seconds':decoded-tick,'flow_and_control_seconds':time.perf_counter()-decoded,
        'pts':q['pts'],'indices':q['indices'],'frame_hash':__import__('hashlib').sha256(frames.tobytes()).hexdigest(),
        'output_shape':list(views['correct'].shape),'finite':bool(np.isfinite(views['correct']).all())}


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--data-root',required=True)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    from forensics.common import read,rows,write,sha
    from forensics.manifest import require_valid
    from forensics.pipeline import environment
    cfg=read(a.config);rr=rows(a.manifest);require_valid(rr)
    if any(r['scope'] not in ('historical','synthetic') or r['role']!='profile' for r in rr):raise ValueError('Performance-only inputs required')
    if a.output.exists():raise FileExistsError('Preserve previous benchmark')
    report={'scope':'hardware/performance tuning, not detector training evidence','environment':environment(),'manifest_sha256':sha(a.manifest),
        'script_sha256':sha(__file__),'cpu_trials':[],'gpu_trials':[],'ffprobe_threads_per_worker':1,'opencv_threads_per_worker':1}
    reference=None
    for workers in (4,8,12):
        if workers>report['environment']['cpu_count']:continue
        tick=time.perf_counter()
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            result=list(pool.map(worker,[(r,a.data_root,cfg) for r in rr],chunksize=1))
        elapsed=time.perf_counter()-tick
        identity=[(r['sample_id'],r['frame_hash'],r['indices'],r['pts']) for r in result]
        if reference is None:reference=identity
        elif identity!=reference:raise ValueError('Parallel workers changed decoded inputs')
        if not all(r['finite'] for r in result):raise ValueError('Non-finite features')
        trial={'workers':workers,'videos':len(rr),'seconds':elapsed,'videos_per_second':len(rr)/elapsed,'per_video':result}
        report['cpu_trials'].append(trial);write(a.output,report,replace=a.output.exists())
        print('CPU',workers,round(elapsed,3),'seconds',flush=True)
    import torch
    from forensics.model import Bag
    torch.set_num_threads(2);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():raise RuntimeError('GPU capacity benchmark requires CUDA')
    total=torch.cuda.get_device_properties(0).total_memory
    size=cfg['sampling']['size']-2*cfg['controls']['margin'];frames=cfg['sampling']['frames']-1
    for bs in (8,16,32,64,128,256):
        model=Bag().cuda();opt=torch.optim.AdamW(model.parameters(),lr=.001)
        x=y=loss=None
        try:
            x=torch.randn(bs,frames,3,size,size,device='cuda');y=torch.zeros(bs,device='cuda')
            def step():
                opt.zero_grad(set_to_none=True)
                loss=torch.nn.functional.binary_cross_entropy_with_logits(model(x),y)
                loss.backward();opt.step()
            for _ in range(2):step()
            torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();tick=time.perf_counter()
            for _ in range(5):step()
            torch.cuda.synchronize();elapsed=time.perf_counter()-tick
            peak=torch.cuda.max_memory_allocated()
            report['gpu_trials'].append({'batch_size':bs,'steps':5,'seconds':elapsed,'clips_per_second':bs*5/elapsed,
                'peak_allocated_bytes':peak,'within_85_percent_vram':peak<=.85*total,'status':'ok'})
            print('GPU',bs,round(bs*5/elapsed,2),'clips/s',round(peak/2**30,2),'GiB',flush=True)
        except torch.cuda.OutOfMemoryError:
            report['gpu_trials'].append({'batch_size':bs,'status':'out_of_memory'})
            print('GPU',bs,'OOM recorded',flush=True)
        finally:
            del model,opt,x,y,loss;gc.collect();torch.cuda.empty_cache()
        write(a.output,report,replace=True)
    report['recommended_workers']=max(report['cpu_trials'],key=lambda x:x['videos_per_second'])['workers']
    eligible=[r for r in report['gpu_trials'] if r['status']=='ok' and r['within_85_percent_vram']]
    report['recommended_batch_size']=max(eligible,key=lambda x:x['clips_per_second'])['batch_size']
    report['note']='Batch is a throughput candidate, not a validated optimization recipe. Freeze a fresh common training protocol before using it.'
    report['complete']=True;write(a.output,report,replace=True)
    print('CAPACITY BENCHMARK COMPLETE',report['recommended_workers'],report['recommended_batch_size'],flush=True)


if __name__=='__main__':main()
