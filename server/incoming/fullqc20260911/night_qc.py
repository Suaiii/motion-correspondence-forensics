"""Fixed, source-only QC: no detector fitting or classification metrics."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SAMPLING={'frames':16,'fps':8,'window_sec':2,'size':224}
ARCHIVE_SHA={'ms':'27359fa0ff7aa94802bcbed73701fcfedeb0b49a4e8767e0480d67f639d1e70d',
             'vc2':'e9d68507e10c882e834146451e2d0ede5befaebfa8e7d36a977d3fe672531589'}


def worker(task):
    import cv2
    import numpy as np
    from forensics import video
    from forensics.controls import represent,fields,MECHANISM_ARMS
    from forensics.common import sha
    row,path=task;cv2.setNumThreads(1);started=time.perf_counter()
    result={**row,'file_sha256':sha(path),'status':'error','scope':'source-only quality/representation inspection'}
    original=video.command
    def command(args,timeout=180):
        if args[0]=='ffprobe':args=[args[0],'-threads','1',*args[1:]]
        return original(args,timeout)
    video.command=command
    try:
        meta=json.loads(command(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,duration','-of','json',path]))
        result['stream']=meta['streams'][0]
        frames,q=video.decode(path,SAMPLING);result['sampling']=q
        result['sampled_frame_sha256']=[hashlib.sha256(f.tobytes()).hexdigest() for f in frames]
        phashes=[]
        for idx in (0,len(frames)//2,len(frames)-1):
            gray=cv2.cvtColor(frames[idx],cv2.COLOR_BGR2GRAY)
            small=cv2.resize(gray,(32,32),interpolation=cv2.INTER_AREA).astype(np.float32)
            coeff=cv2.dct(small)[:8,:8].reshape(-1);bits=coeff>np.median(coeff[1:])
            phashes.append(np.packbits(bits).tobytes().hex())
        result['phash_three_frames']=phashes
        result['duplicate_sampled_content']=len(frames)-len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})
        f=video.flows(frames);result['representations']={}
        for support in ('interior','common'):
            cfg={'support':support,'margin':16,'flow_bound':12,'kernel':'linear'}
            it=iter(f);views,quality=represent(frames,cfg,lambda *_:next(it))
            if not all(np.isfinite(views[k]).all() for k in MECHANISM_ARMS):raise ValueError('nonfinite_control_input')
            actual,frac,nulls,_=fields(f[0],12 if support=='interior' else None)
            yy,xx=np.mgrid[:frames.shape[1],:frames.shape[2]].astype(np.float32)
            tables=[cv2.convertMaps(xx+v[...,0],yy+v[...,1],cv2.CV_16SC2)[1] for v in [actual,frac]+nulls]
            if not all(np.array_equal(tables[0],t) for t in tables[1:]):raise ValueError('interpolation_weight_mismatch')
            stats={}
            for arm in MECHANISM_ARMS:
                x=views[arm];ax=np.abs(x)
                stats[arm]={'mean_abs':float(ax.mean()),'rms':float(np.sqrt(np.mean(x*x))),
                    'abs_p95':float(np.quantile(ax,.95)),'temporal_abs_mean_std':float(ax.mean((1,2,3)).std())}
            result['representations'][support]={'stats':stats,'quality_mean':{k:float(np.mean([v[k] for v in quality])) for k in quality[0]},
                'first_pair_interpolation_weights_equal':True,'shape':list(views['correct'].shape)}
        result['status']='ok'
    except video.QualityExclusion as exc:
        result.update(status='excluded',reason=str(exc))
        if str(exc)=='black_frames':result['black_fraction_lower_bound']=.5
    except Exception as exc:result.update(status='error',reason=type(exc).__name__+': '+str(exc))
    finally:
        video.command=original
        result['seconds']=time.perf_counter()-started
    return result


def extract_source(archive,selected,out,allow_missing=False):
    from forensics.common import read,write,sha
    source=selected[0]['source'];receipt=out/f'extraction_{source}.json'
    if receipt.exists():
        result=read(receipt)
        if result['archive_sha256']!=ARCHIVE_SHA[source]:raise ValueError('Archive identity changed')
        for entry in result['files']:
            if sha(entry['path'])!=entry['sha256']:raise ValueError('Extracted input changed')
        return {r['basename']:r['path'] for r in result['files']}
    if sha(archive)!=ARCHIVE_SHA[source]:raise ValueError('Full archive SHA256 mismatch')
    tool=shutil.which('unrar')
    if not tool:raise RuntimeError('Install the server unrar package before starting QC')
    listing=subprocess.run([tool,'lb','-c-','-p-',str(archive)],capture_output=True,text=True,encoding='utf-8',timeout=180)
    if listing.returncode:raise RuntimeError('Cannot list RAR archive: '+listing.stderr[-500:])
    wanted={r['basename'] for r in selected};members={}
    for line in listing.stdout.splitlines():
        name=line.strip().replace('\\','/');base=Path(name).name
        if base in wanted:
            if '..' in Path(name).parts or name.startswith('/') or base in members:raise ValueError('Ambiguous or unsafe archive member')
            members[base]=name
    missing=sorted(wanted-set(members))
    if missing and not allow_missing:raise ValueError('Pinned selection has missing archive members; no replacements')
    target=out/'extracted'/f'{source}-{time.time_ns()}';target.mkdir(parents=True)
    include=target/'members.txt';include.write_text('\n'.join(members.values())+'\n',encoding='utf-8')
    extraction=subprocess.run([tool,'e','-inul','-o-','-p-',str(archive),'@'+str(include),str(target)+os.sep],capture_output=True,text=True,timeout=900)
    if extraction.returncode:raise RuntimeError('RAR extraction failed: '+extraction.stderr[-500:])
    files=[]
    for base in sorted(members):
        p=target/base
        if not p.is_file():raise ValueError('Selected file not extracted')
        files.append({'basename':base,'path':str(p),'sha256':sha(p)})
    write(receipt,{'archive_sha256':ARCHIVE_SHA[source],'files':files,'missing_members':missing})
    return {r['basename']:r['path'] for r in files}


def main():
    from forensics.common import read,write,sha,object_hash
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--archive-root',type=Path,required=True);p.add_argument('--deadline',required=True);p.add_argument('--workers',type=int,default=12)
    p.add_argument('--expected-per-source',type=int,default=500);p.add_argument('--allow-missing',action='store_true')
    a=p.parse_args();root=a.run_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    deadline=datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:raise ValueError('Timezone required')
    if datetime.now(timezone.utc)>=deadline or (root/'STOP_NEW_JOBS').exists():raise RuntimeError('No new work after cutoff')
    selection=read(a.selection);rows=selection['rows']
    total=2*a.expected_per_source
    if a.expected_per_source<1 or Counter(r['source'] for r in rows)!={'ms':a.expected_per_source,'vc2':a.expected_per_source}:raise ValueError('Selection count differs from frozen per-source target')
    if len({r['sample_id'] for r in rows})!=total:raise ValueError('Duplicate sample identity')
    lock={'selection_sha256':sha(a.selection),'script_sha256':sha(__file__),'sampling':SAMPLING,'workers':a.workers,
          'deadline':a.deadline,'requested':total,'allow_missing_archive_members':a.allow_missing,'classification_metrics_computed':False,'scope':'two generated sources; no real/fake accuracy or generalization conclusion'}
    lock_path=root/'qc_lock.json'
    if lock_path.exists():
        if read(lock_path)!=lock:raise ValueError('QC protocol changed; use a new run')
    else:write(lock_path,lock)
    tasks=[];records_dir=root/'records';records_dir.mkdir(exist_ok=True)
    for source in ('ms','vc2'):
        if datetime.now(timezone.utc)>=deadline or (root/'STOP_NEW_JOBS').exists():raise RuntimeError('Extraction cutoff reached')
        selected=[r for r in rows if r['source']==source]
        files=extract_source(a.archive_root/(source+'.rar'),selected,root,a.allow_missing)
        for r in selected:
            if r['basename'] in files:tasks.append((r,files[r['basename']]))
            else:
                record=records_dir/(object_hash(r['sample_id'])+'.json')
                if not record.exists():write(record,{**r,'status':'excluded','reason':'missing_archive_member','scope':'quality inspection; no replacement'})
    completed={}
    for file in records_dir.glob('*.json'):
        r=read(file);completed[r['sample_id']]=r
    pending=[t for t in tasks if t[0]['sample_id'] not in completed]
    started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(worker,t):t[0]['sample_id'] for t in pending}
        for future in as_completed(futures):
            r=future.result();write(records_dir/(object_hash(r['sample_id'])+'.json'),r);completed[r['sample_id']]=r
            if len(completed)%50==0:print('QC',len(completed),'/',total,flush=True)
    counts={s:dict(Counter(r['status'] for r in completed.values() if r['source']==s)) for s in ('ms','vc2')}
    reasons=dict(Counter(r.get('reason','') for r in completed.values() if r['status']!='ok'))
    report={'complete':len(completed)==total,'requested':total,'completed':len(completed),'counts':counts,'failure_reasons':reasons,
        'wall_seconds_this_attempt':time.perf_counter()-started,'classification_metrics_computed':False,'scope':lock['scope']}
    write(root/'qc_summary.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
