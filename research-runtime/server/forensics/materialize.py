"""Bounded parallel residual rendering; reusable inputs instead of per-epoch warps."""
import multiprocessing
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import cv2
import numpy as np
from .common import read,write,sha,object_hash,safe_path,exclusive,event
from .controls import represent


def render_item(task):
    item,root,controls,arm,dtype,relative=task
    cv2.setNumThreads(1)
    with np.load(safe_path(root,item['path']),allow_pickle=False) as arrays:
        it=iter(arrays['flow']);views,_=represent(arrays['frames'],controls,lambda *_:next(it))
    out=views[arm].astype(dtype);dest=safe_path(root,relative);dest.parent.mkdir(parents=True,exist_ok=True)
    marker=dest.with_suffix('.json')
    if marker.exists():
        committed=read(marker)
        if sha(dest)!=committed['sha256']:raise ValueError('Changed materialized shard')
        return committed
    if dest.exists():raise FileExistsError('Unreceipted materialized file: '+str(dest))
    temp=dest.with_suffix('.partial')
    if temp.exists():temp.rename(temp.with_name(temp.name+'.failed-'+str(__import__('time').time_ns())))
    with temp.open('xb') as f:np.save(f,out,allow_pickle=False)
    os.replace(temp,dest)
    committed={'path':relative,'sha256':sha(dest),'bytes':dest.stat().st_size,'shape':list(out.shape),'dtype':str(out.dtype)}
    write(marker,committed)
    return committed


def materialize(run,cache_root,arm,workers=None):
    from .pipeline import verify_lock,checked_index,environment
    cfg,records=verify_lock(run);run=Path(run);root=Path(cache_root)
    if arm not in cfg['arms']:raise ValueError('Arm was not frozen')
    index=checked_index(run,root);dtype=cfg.get('materialized_dtype','float32')
    if dtype not in ('float32','float16'):raise ValueError('Unsupported materialized precision')
    workers=workers or cfg.get('materialize_workers',1)
    if workers<1 or workers>environment()['cpu_count']:raise ValueError('Workers exceed assigned CPU quota')
    receipt=run/f'materialized_{arm}.json'
    previous=read(receipt) if receipt.exists() else None
    config_hash=sha(run/'config.json');base_hash=sha(run/'cache.json')
    if previous and (previous['config_hash']!=config_hash or previous['base_cache_hash']!=base_hash):raise ValueError('Materialization provenance differs')
    output={'config_hash':config_hash,'base_cache_hash':base_hash,'arm':arm,'dtype':dtype,'items':{},'purged':False}
    if previous and not previous.get('purged'):output['items']=previous['items']
    for value in output['items'].values():
        if sha(safe_path(root,value['path']))!=value['sha256']:raise ValueError('Materialized cache changed')
    side=cfg['sampling']['size']-(2*cfg['controls']['margin'] if cfg['controls']['support']=='interior' else 0)
    size=(cfg['sampling']['frames']-1)*(15 if arm=='concat' else 3)*side*side*np.dtype(dtype).itemsize+256
    tasks=[];prefix=object_hash([config_hash,base_hash,arm,dtype,sha(__file__)])
    for sid in index['retained']:
        for c in cfg['conditions']:
            key=sid+'/'+c
            if key in output['items']:continue
            relative=f'materialized/{prefix}/{object_hash(key)}.npy'
            tasks.append((key,(index['items'][key],str(root),cfg['controls'],arm,dtype,relative)))
    occupied=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    missing=sum(not safe_path(root,task[-1]).exists() for _,task in tasks)
    if occupied+size*missing>cfg['max_cache_gib']*2**30:raise ValueError('Cache quota insufficient; verify and purge a completed materialized arm first')
    with exclusive(run/f'materialize_{arm}.lock'):
        if workers==1:
            for key,task in tasks:
                output['items'][key]=render_item(task);write(receipt,output,replace=receipt.exists())
        else:
            with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
                for (key,_),value in zip(tasks,pool.map(render_item,[t for _,t in tasks],chunksize=1)):
                    output['items'][key]=value;write(receipt,output,replace=receipt.exists())
        output['complete']=True;write(receipt,output,replace=receipt.exists())
    event(run,'materialized',arm=arm,items=len(output['items']),workers=workers,dtype=dtype)
    return output


def purge(run,cache_root,arm):
    from .pipeline import verify_lock
    cfg,_=verify_lock(run)
    if arm not in cfg['arms']:raise ValueError('Arm was not frozen')
    run=Path(run);receipt=run/f'materialized_{arm}.json';meta=read(receipt)
    if any((run/'training').glob(f'{arm}_*/train.lock')):raise ValueError('Cannot purge inputs used by active training')
    if not meta.get('complete'):raise ValueError('Cannot purge unfinished materialization')
    root=Path(cache_root).resolve();materialized_root=(root/'materialized').resolve()
    targets=[safe_path(root,r['path']) for r in meta['items'].values()]
    if any(not p.is_relative_to(materialized_root) for p in targets):raise ValueError('Deletion must stay in the derived materialized subtree')
    for row,p in zip(meta['items'].values(),targets):
        if p.exists() and sha(p)!=row['sha256']:raise ValueError('Changed file: refuse deletion')
    for p in targets:
        if p.exists():p.unlink()
        marker=p.with_suffix('.json')
        if marker.exists():marker.unlink()
    meta['purged']=True;write(receipt,meta,replace=True)
    event(run,'purged_derived_arm_only',arm=arm,files=len(targets))
