import json
import os
import platform
import random
import shutil
import time
from pathlib import Path
import cv2
import numpy as np
import torch
from sklearn.metrics import roc_auc_score,balanced_accuracy_score,log_loss
from torch.utils.data import Dataset,DataLoader
from .common import read,write,sha,object_hash,code_hashes,now,event,safe_path,exclusive
from .manifest import require_valid
from .controls import MECHANISM_ARMS,METHOD_ARMS,represent
from .model import Bag
from .video import load_condition,flows,QualityExclusion,RECIPES
from . import budget


def environment():
    result={'python':platform.python_version(),'platform':platform.platform(),'torch':torch.__version__,
            'numpy':np.__version__,'opencv':cv2.__version__,'cpu_count':os.cpu_count(),'cuda':torch.cuda.is_available()}
    result['host_cpu_count']=result['cpu_count']
    for path in (Path('/sys/fs/cgroup/cpu.max'),):
        if path.is_file():
            quota,period=path.read_text().split()
            if quota!='max':
                result['cpu_quota_cores']=int(quota)/int(period)
                result['cpu_count']=min(result['cpu_count'],result['cpu_quota_cores'])
    memory_limit=Path('/sys/fs/cgroup/memory.max')
    if memory_limit.is_file() and memory_limit.read_text().strip()!='max':
        result['memory_limit_bytes']=int(memory_limit.read_text())
    if result['cuda']:
        prop=torch.cuda.get_device_properties(0)
        result.update(gpu=prop.name,vram_bytes=prop.total_memory)
    return result


def prepare(run,cfg,records):
    if Path(run).exists():raise FileExistsError('Use a fresh versioned run')
    receipt=require_valid(records)
    if cfg['sampling']['frames']!=round(cfg['sampling']['fps']*cfg['sampling']['window_sec']):raise ValueError('Sampling count mismatch')
    if cfg['stage'] not in ('mechanism','method','smoke'):raise ValueError('Unknown experiment stage')
    if cfg['stage']=='smoke' and any(r['scope']!='synthetic' for r in records):raise ValueError('Smoke is synthetic-only')
    if cfg['stage']!='smoke' and any(r['scope'] in ('synthetic','historical') for r in records):raise ValueError('Cannot promote synthetic/historical data')
    if cfg['stage']!='smoke':
        exclusions_path=Path(__file__).parents[1]/'configs/historical_exclusions.json'
        exclusions=read(exclusions_path)
        if any(r['sha256'] in set(exclusions['sha256']) for r in records):raise ValueError('Historical video bytes cannot enter new research cohorts')
        cfg=dict(cfg,historical_exclusions_sha256=sha(exclusions_path))
    if cfg['stage']=='mechanism' and any(a not in MECHANISM_ARMS for a in cfg['arms']):raise ValueError('Method arms gated until mechanism passes')
    if cfg['stage']=='method':
        gate_path=Path(cfg['mechanism_evidence'])
        gate=read(gate_path)
        if not gate.get('passed') or not gate.get('ood_positive') or gate.get('scope')!='development':raise ValueError('Mechanism acceptance missing')
        evidence_root=gate_path.parent
        if sha(evidence_root/'config.json')!=gate['configuration_sha256']:raise ValueError('Mechanism configuration changed')
        for key,name in [('development','evaluation_dev_audit.json'),('ood','evaluation_ood_dev.json')]:
            if sha(evidence_root/name)!=gate['evidence'][key]:raise ValueError('Mechanism evidence changed')
        cfg=dict(cfg,mechanism_evidence_sha256=sha(gate_path))
    for c in cfg['conditions']:
        if c not in RECIPES:raise ValueError('Unknown condition '+c)
    if 'clean' not in cfg['conditions']:raise ValueError('Clean calibration required')
    if not set(cfg['training'].get('conditions',['clean'])).issubset(cfg['conditions']):raise ValueError('Training condition not extracted')
    Path(run).mkdir(parents=True)
    write(Path(run)/'config.json',cfg);write(Path(run)/'manifest.json',records)
    code=code_hashes();dest=Path(run)/'code';dest.mkdir()
    for filename in code:shutil.copyfile(Path(__file__).parent/filename,dest/filename)
    write(Path(run)/'lock.json',{'created':now(),'config_sha256':sha(Path(run)/'config.json'),
        'manifest_sha256':sha(Path(run)/'manifest.json'),'manifest_content_hash':receipt['manifest_hash'],
        'code_hashes':code,'environment':environment(),'scope':'synthetic_validation' if cfg['stage']=='smoke' else 'development'})
    event(run,'prepared',n=len(records))


def verify_lock(run):
    run=Path(run);lock=read(run/'lock.json')
    if sha(run/'config.json')!=lock['config_sha256'] or sha(run/'manifest.json')!=lock['manifest_sha256']:raise ValueError('Immutable inputs changed')
    if code_hashes()!=lock['code_hashes']:raise ValueError('Code changed after run freeze')
    current=environment()
    for name in ('torch','numpy','opencv'):
        if current[name]!=lock['environment'][name]:raise ValueError('Runtime library changed after freeze: '+name)
    return read(run/'config.json'),read(run/'manifest.json')


def final_access(run,records):
    receipt=read(Path(run)/'final_release.json')
    if receipt['manifest_hash']!=object_hash(records):raise ValueError('Final manifest changed')
    if receipt['config_hash']!=sha(Path(run)/'config.json'):raise ValueError('Final configuration changed')
    for name,h in receipt['checkpoints'].items():
        if sha(Path(run)/name)!=h:raise ValueError('Final checkpoint changed')


def freeze_final(run,review_path):
    cfg,records=verify_lock(run)
    if cfg['stage']=='smoke':raise ValueError('Synthetic validation cannot unlock final data')
    review=read(review_path)
    if not review.get('development_gates_passed') or not review.get('reviewer') or not review.get('primary_comparison'):
        raise ValueError('Signed development review and primary comparator required')
    if review.get('run_lock_sha256')!=sha(Path(run)/'lock.json'):raise ValueError('Review not bound to this run')
    files=list((Path(run)/'training').glob('*/summary.json'))
    if len(files)!=len(cfg['arms'])*len(cfg['seeds']):raise ValueError('Not all fits are complete')
    checkpoints={}
    for p in files:
        s=read(p);cp=p.parent/s['checkpoint'];checkpoints[str(cp.relative_to(run))]=sha(cp)
    write(Path(run)/'final_release.json',{'created':now(),'manifest_hash':object_hash(records),
        'config_hash':sha(Path(run)/'config.json'),'checkpoints':checkpoints,'review_sha256':sha(review_path),'review':review})


def extract(run,data_root,cache_root,role=None):
    if role not in (None,'final_audit'):raise ValueError('Extract the entire development cohort together, or the released final cohort')
    cfg,records=verify_lock(run);cache_root=Path(cache_root);cache_root.mkdir(parents=True,exist_ok=True)
    if role=='final_audit':final_access(run,records)
    selected=[r for r in records if (r['role']==role if role else r['role']!='final_audit')]
    receipt_path=Path(run)/('cache_final.json' if role=='final_audit' else 'cache.json')
    index=read(receipt_path) if receipt_path.exists() else {'items':{},'excluded':{},'config_sha256':sha(Path(run)/'config.json')}
    if index.get('complete'):
        checked_index(run,cache_root,role=='final_audit')
        print('verified completed extraction; no rewrite',flush=True)
        return
    cv2.setNumThreads(1);start=time.monotonic()
    occupied=sum(p.stat().st_size for p in cache_root.rglob('*.npz'))
    with exclusive(Path(run)/'extract.lock'):
        for i,r in enumerate(selected):
            source=safe_path(data_root,r['path'])
            if sha(source)!=r['sha256']:raise ValueError('Source changed: '+r['sample_id'])
            for condition in cfg['conditions']:
                key=object_hash({'sha':r['sha256'],'condition':condition,'sampling':cfg['sampling'],
                    'video_code':code_hashes()['video.py'],'opencv':cv2.__version__,'numpy':np.__version__})
                rel=f'{key[:2]}/{key}.npz';dest=safe_path(cache_root,rel);marker=dest.with_suffix('.json')
                try:
                    if marker.exists():
                        item=read(marker)
                        if sha(dest)!=item['sha256']:raise ValueError('Corrupt cached shard; preserve and investigate')
                    else:
                        if dest.exists():raise ValueError('Orphan cache file requires review: '+str(dest))
                        tick=time.monotonic();bgr,q=load_condition(source,condition,cfg['sampling'],cache_root/'scratch')
                        f=flows(bgr);estimated=bgr.nbytes+f.nbytes
                        if occupied+estimated>cfg['max_cache_gib']*2**30:raise RuntimeError('Cache quota reached; no automatic raw-data deletion')
                        dest.parent.mkdir(parents=True,exist_ok=True)
                        tmp=dest.with_suffix('.partial')
                        with tmp.open('xb') as h:np.savez_compressed(h,frames=bgr,flow=f)
                        os.replace(tmp,dest);occupied+=dest.stat().st_size
                        item={'path':rel,'sha256':sha(dest),'source_sha256':r['sha256'],'condition':condition,
                              'quality':q,'seconds':time.monotonic()-tick,'bytes':dest.stat().st_size}
                        write(marker,item)
                    index['items'][r['sample_id']+'/'+condition]=item
                except QualityExclusion as exc:
                    index['excluded'][r['sample_id']]={'reason':str(exc),'condition':condition}
                    break
            write(receipt_path,index,replace=receipt_path.exists())
            if (i+1)%25==0:print(f'extract {i+1}/{len(selected)}',flush=True)
    index['complete']=True;index['wall_seconds']=time.monotonic()-start
    index['retained']=[r['sample_id'] for r in selected if r['sample_id'] not in index['excluded']]
    write(receipt_path,index,replace=True);event(run,'extracted',n=len(index['retained']),excluded=len(index['excluded']))


class Inputs(Dataset):
    def __init__(self,records,index,cache_root,arm,cfg,condition='clean'):
        self.records=records;self.index=index;self.root=cache_root;self.arm=arm;self.cfg=cfg;self.condition=condition
        self.materialized={}
        if index.get('_run_dir'):
            receipt=Path(index['_run_dir'])/f'materialized_{arm}.json'
            if receipt.exists():
                meta=read(receipt)
                if meta.get('complete') and not meta.get('purged'):
                    if meta['config_hash']!=sha(Path(index['_run_dir'])/'config.json') or meta['base_cache_hash']!=sha(Path(index['_run_dir'])/'cache.json'):raise ValueError('Materialization config/cache differs')
                    self.materialized=meta['items']
    def __len__(self):return len(self.records)*(len(self.condition) if isinstance(self.condition,list) else 1)
    def __getitem__(self,i):
        conditions=self.condition if isinstance(self.condition,list) else [self.condition]
        r=self.records[i//len(conditions)];condition=conditions[i%len(conditions)]
        rendered=self.materialized.get(r['sample_id']+'/'+condition)
        if rendered:
            value=np.load(safe_path(self.root,rendered['path']),allow_pickle=False)
            return torch.from_numpy(np.asarray(value,dtype=np.float32)).contiguous(),torch.tensor(r['label_fake'],dtype=torch.float32)
        item=self.index['items'][r['sample_id']+'/'+condition]
        with np.load(safe_path(self.root,item['path']),allow_pickle=False) as a:
            frames=a['frames'];flow=a['flow']
        iterator=iter(flow)
        values,_=represent(frames,self.cfg['controls'],lambda current,previous:next(iterator))
        return torch.from_numpy(values[self.arm]).contiguous(),torch.tensor(r['label_fake'],dtype=torch.float32)


def checked_index(run,cache_root,final=False):
    cfg,records=verify_lock(run);known={r['sample_id']:r for r in records}
    index=read(Path(run)/('cache_final.json' if final else 'cache.json'))
    if not index.get('complete'):raise ValueError('Input extraction unfinished')
    if index['config_sha256']!=sha(Path(run)/'config.json'):raise ValueError('Cache belongs to a different configuration')
    for key,item in index['items'].items():
        sid,condition=key.rsplit('/',1)
        if sid not in known or condition not in cfg['conditions'] or item['condition']!=condition or item['source_sha256']!=known[sid]['sha256']:
            raise ValueError('Cache identity/condition does not match manifest')
        if sha(safe_path(cache_root,item['path']))!=item['sha256']:raise ValueError('Input cache changed')
    for sid in index['retained']:
        if sid not in known or (known[sid]['role']=='final_audit')!=final:raise ValueError('Cache role leakage')
        if any(sid+'/'+c not in index['items'] for c in cfg['conditions']):raise ValueError('Incomplete paired conditions')
    if not final:
        for receipt in Path(run).glob('materialized_*.json'):
            meta=read(receipt)
            if meta.get('complete') and not meta.get('purged'):
                if meta['config_hash']!=sha(Path(run)/'config.json') or meta['base_cache_hash']!=sha(Path(run)/'cache.json'):raise ValueError('Materialized provenance changed')
                for value in meta['items'].values():
                    if sha(safe_path(cache_root,value['path']))!=value['sha256']:raise ValueError('Materialized input changed')
    index['_run_dir']=str(Path(run).resolve())
    return index


def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True)


@torch.no_grad()
def predict(model,data,device,batch_size,workers=0):
    model.eval();result=[]
    for x,_ in DataLoader(data,batch_size=batch_size,num_workers=workers):
        result.extend(torch.sigmoid(model(x.to(device))).cpu().tolist())
    return np.array(result)


def train(run,cache_root,device,arm,seed,ledger=None,reservation=None,epochs_this_call=None):
    cfg,records=verify_lock(run)
    if arm not in cfg['arms'] or seed not in cfg['seeds']:raise ValueError('Arm/seed not frozen')
    if cfg['stage']!='smoke' and not str(device).startswith('cuda'):raise ValueError('No silent CPU research-training fallback')
    lease=budget.admit(ledger,reservation,run,'method' if cfg['stage']=='method' else 'mechanism') if cfg['stage']!='smoke' else None
    index=checked_index(run,cache_root);retained=set(index['retained'])
    fit=[r for r in records if r['role']=='fit' and r['sample_id'] in retained]
    val=[r for r in records if r['role']=='calibration' and r['sample_id'] in retained]
    for pool in (fit,val):
        if min(sum(r['label_fake']==label for r in pool) for label in (0,1))<cfg['minimum_per_class']:
            raise ValueError('Insufficient retained class support')
    if cfg['stage']!='smoke':
        if len(retained)<cfg['minimum_retained_total']:raise ValueError('Retained sample target not met')
        if len({r['source'] for r in fit if not r['label_fake']})<2 or len({r['generator'] for r in fit if r['label_fake']})<4:
            raise ValueError('Mechanism training needs two real sources and four generators')
    dest=Path(run)/'training'/f'{arm}_{seed}';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'summary.json').exists():raise FileExistsError('Fit already complete')
    tick=time.monotonic();seed_all(seed);torch.set_num_threads(cfg['cpu_threads'])
    net=Bag(15 if arm=='concat' else 3).to(device)
    optimizer=torch.optim.AdamW(net.parameters(),lr=cfg['training']['lr'],weight_decay=cfg['training']['weight_decay'])
    states=sorted(dest.glob('epoch_*.pt'));start_epoch=0;best_loss=float('inf');best_name=None;elapsed_before=0.
    if states:
        for p in states:
            receipt=read(p.with_suffix('.json'))
            if receipt.get('checkpoint_sha256')!=sha(p):raise ValueError('Resume checkpoint not committed or changed')
        state=torch.load(states[-1],map_location='cpu',weights_only=False)
        if state['config_hash']!=sha(Path(run)/'config.json') or state['cache_hash']!=sha(Path(run)/'cache.json'):raise ValueError('Resume config/cache differs')
        net.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer'])
        random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng']);torch.set_rng_state(state['torch_rng'])
        if str(device).startswith('cuda'):torch.cuda.set_rng_state_all(state['cuda_rng'])
        start_epoch=state['epoch'];best_loss=state['best_loss'];best_name=state['best_name'];elapsed_before=state['elapsed_seconds']
    if str(device).startswith('cuda'):torch.cuda.reset_peak_memory_stats()
    data=Inputs(fit,index,cache_root,arm,cfg,cfg['training'].get('conditions',['clean']));validation=Inputs(val,index,cache_root,arm,cfg)
    with exclusive(dest/'train.lock'):
        for epoch in range(start_epoch+1,cfg['training']['epochs']+1):
            net.train();total=0.
            loader=DataLoader(data,batch_size=cfg['training']['batch_size'],shuffle=True,num_workers=cfg['workers'])
            for x,y in loader:
                elapsed=elapsed_before+time.monotonic()-tick
                if elapsed>cfg['max_fit_seconds']:raise TimeoutError('Fit time cap reached; prior epochs preserved')
                if lease:
                    from datetime import datetime,timezone
                    used=(datetime.now(timezone.utc)-datetime.fromisoformat(lease['started_utc'])).total_seconds()
                    if used>lease['reserved_gpu_hours']*3600:raise TimeoutError('Reservation wall-time exhausted; provider shutdown must be checked')
                optimizer.zero_grad(set_to_none=True);loss=torch.nn.functional.binary_cross_entropy_with_logits(net(x.to(device)),y.to(device))
                if not torch.isfinite(loss):raise FloatingPointError('Non-finite training loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);optimizer.step();total+=float(loss.detach())*len(y)
            p=predict(net,validation,device,cfg['training']['batch_size'],cfg['workers'])
            vl=float(log_loss([r['label_fake'] for r in val],p,labels=[0,1]));name=f'epoch_{epoch:03d}.pt'
            if vl<best_loss:best_loss=vl;best_name=name
            row={'epoch':epoch,'train_bce':total/len(data),'calibration_bce':vl}
            state={'epoch':epoch,'model':{k:v.detach().cpu() for k,v in net.state_dict().items()},'optimizer':optimizer.state_dict(),
                'python_rng':random.getstate(),'numpy_rng':np.random.get_state(),'torch_rng':torch.get_rng_state(),
                'cuda_rng':torch.cuda.get_rng_state_all() if str(device).startswith('cuda') else [],
                'best_loss':best_loss,'best_name':best_name,'config_hash':sha(Path(run)/'config.json'),
                'cache_hash':sha(Path(run)/'cache.json'),
                'elapsed_seconds':elapsed_before+time.monotonic()-tick,'history':row}
            temp=dest/(name+'.partial');torch.save(state,temp);os.replace(temp,dest/name)
            write(dest/f'epoch_{epoch:03d}.json',dict(row,checkpoint_sha256=sha(dest/name)))
            print(arm,seed,epoch,round(vl,4),flush=True)
            if epochs_this_call and epoch-start_epoch>=epochs_this_call and epoch<cfg['training']['epochs']:
                event(run,'fit_paused_at_epoch',arm=arm,seed=seed,epoch=epoch)
                return
        checkpoint=dest/best_name;net.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=False)['model'])
        vp=predict(net,validation,device,cfg['training']['batch_size'],cfg['workers']);y=np.array([r['label_fake'] for r in val])
        grid=np.linspace(.01,.99,99);scores=[balanced_accuracy_score(y,vp>=t) for t in grid]
        tau=min((float(t) for t,s in zip(grid,scores) if abs(s-max(scores))<1e-12),key=lambda t:(abs(t-.5),t))
        tau_fpr=float(np.nextafter(np.quantile(vp[y==0],.99,method='higher'),np.inf))
        write(dest/'summary.json',{'arm':arm,'seed':seed,'checkpoint':best_name,'checkpoint_sha256':sha(checkpoint),
            'params':sum(p.numel() for p in net.parameters()),'threshold':tau,'threshold_calibration_fpr01':tau_fpr,
            'calibration':[{'sample_id':r['sample_id'],'prob_fake':float(v)} for r,v in zip(val,vp)],
            'seconds':elapsed_before+time.monotonic()-tick,'peak_allocated_bytes':torch.cuda.max_memory_allocated() if str(device).startswith('cuda') else None})
    event(run,'fit_complete',arm=arm,seed=seed)


def metrics(records,p,threshold,tau_fpr):
    y=np.array([r['label_fake'] for r in records]);p=np.asarray(p)
    if len(p)!=len(records) or not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('Invalid probabilities')
    if len(np.unique(y))!=2:raise ValueError('Both classes required')
    groups={}
    for gen in sorted({r['generator'] for r in records if r['label_fake']}):
        ix=np.array([not r['label_fake'] or r['generator']==gen for r in records])
        groups[gen]=float(roc_auc_score(y[ix],p[ix]))
    source_fpr={src:float(np.mean(p[[i for i,r in enumerate(records) if not r['label_fake'] and r['source']==src]]>=threshold)) for src in sorted({r['source'] for r in records if not r['label_fake']})}
    ece=0.
    for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
        ix=(p>=lo)&((p<hi) if hi<1 else (p<=hi))
        if ix.any():ece+=float(ix.mean()*abs(p[ix].mean()-y[ix].mean()))
    return {'n':len(y),'auc':float(roc_auc_score(y,p)),'macro_auc':float(np.mean(list(groups.values()))),
        'worst_generator_auc':min(groups.values()),'generator_auc':groups,'bacc':float(balanced_accuracy_score(y,p>=threshold)),
        'source_fpr':source_fpr,'ece_10_equal_width':ece,'tpr_at_calibrated_fpr01':float(np.mean(p[y==1]>=tau_fpr)),
        'actual_fpr_at_calibrated_fpr01':float(np.mean(p[y==0]>=tau_fpr))}


def evaluate(run,cache_root,device,role='dev_audit'):
    cfg,records=verify_lock(run)
    if role not in ('dev_audit','ood_dev','final_audit'):raise ValueError('Evaluation role')
    if role=='final_audit':final_access(run,records)
    dest=Path(run)/f'evaluation_{role}.json'
    if dest.exists():raise FileExistsError('Scores already opened; no overwrite')
    index=checked_index(run,cache_root,role=='final_audit')
    selected=[r for r in records if r['role']==role and r['sample_id'] in set(index['retained'])]
    if not selected:raise ValueError('No eligible evaluation samples')
    outputs=[];predictions=[];torch.set_num_threads(cfg['cpu_threads'])
    for arm in cfg['arms']:
        for seed in cfg['seeds']:
            folder=Path(run)/'training'/f'{arm}_{seed}';s=read(folder/'summary.json');checkpoint=folder/s['checkpoint']
            if sha(checkpoint)!=s['checkpoint_sha256']:raise ValueError('Checkpoint changed')
            net=Bag(15 if arm=='concat' else 3).to(device);net.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=False)['model'])
            for c in cfg['conditions']:
                tick=time.monotonic();p=predict(net,Inputs(selected,index,cache_root,arm,cfg,c),device,cfg['training']['batch_size'],cfg['workers'])
                outputs.append({'arm':arm,'seed':seed,'condition':c,'seconds_cached_input_inference':time.monotonic()-tick,
                    **metrics(selected,p,s['threshold'],s['threshold_calibration_fpr01'])})
                for r,v in zip(selected,p):predictions.append({**{k:r[k] for k in ('sample_id','source_group','source','generator','label_fake')},'arm':arm,'seed':seed,'condition':c,'prob_fake':float(v)})
    write(dest,{'role':role,'scope':'synthetic_validation' if cfg['stage']=='smoke' else ('final' if role=='final_audit' else 'development'),
        'config_hash':sha(Path(run)/'config.json'),'manifest_hash':sha(Path(run)/'manifest.json'),'metrics':outputs,'predictions':predictions})
    event(run,'evaluated',role=role,groups=len(outputs))
