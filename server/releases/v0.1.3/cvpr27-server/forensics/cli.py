import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from .common import read,write,rows,sha,event,object_hash,safe_path


def doctor(args):
    from .pipeline import environment
    info=environment();info['ffmpeg']=shutil.which('ffmpeg');info['ffprobe']=shutil.which('ffprobe')
    info['data_root_exists']=Path(args.data_root).is_dir();info['cache_root_exists']=Path(args.cache_root).is_dir()
    if Path(args.cache_root).exists():info['cache_free_gib']=shutil.disk_usage(args.cache_root).free/2**30
    try:
        if sys.platform=='linux':
            fields=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
            info['host_ram_gib']=int(fields['MemTotal'].split()[0])/2**20
            info['ram_gib']=min(info['host_ram_gib'],info.get('memory_limit_bytes',float('inf'))/2**30)
    except (ValueError,KeyError):pass
    info['meets_gpu_memory_target']=info.get('vram_bytes',0)>=23*2**30
    info['meets_cpu_target']=info['cpu_count']>=8
    info['meets_ram_target']=info.get('ram_gib',0)>=30
    info['server_verified']=False
    info['note']='Local process inventory only. Billing, persistent-disk retention and remote host identity require provider verification.'
    if args.output:write(args.output,info)
    print(json.dumps(info,indent=2));return info


def profile(args):
    import numpy as np
    import torch
    from .pipeline import environment
    from .model import Bag
    from .controls import represent
    from .video import load_condition,flows
    from .manifest import require_valid
    from . import budget
    records=rows(args.manifest);require_valid(records)
    if any(r['role']=='final_audit' for r in records):raise ValueError('No final samples in profiling')
    if args.synthetic and any(r['scope']!='synthetic' for r in records):raise ValueError('Synthetic profile requires synthetic inputs')
    if not args.synthetic:budget.admit(args.ledger,args.reservation,args.run_dir,'profile')
    cfg=read(args.config);groups={}
    for r in sorted(records,key=lambda r:object_hash(r['sample_id'])):groups.setdefault(r['source'],[]).append(r)
    selected=[]
    while groups and len(selected)<args.limit:
        for key in list(groups):
            if len(selected)<args.limit:selected.append(groups[key].pop())
            if not groups[key]:del groups[key]
    net=Bag().to(args.device).eval();result=[];started=time.monotonic();Path(args.cache_root).mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(cfg['cpu_threads'])
    if str(args.device).startswith('cuda'):torch.cuda.reset_peak_memory_stats()
    for r in selected:
        tick=time.monotonic();source=safe_path(args.data_root,r['path'])
        if sha(source)!=r['sha256']:raise ValueError('Source changed')
        bgr,q=load_condition(source,'clean',cfg['sampling'],Path(args.cache_root)/'scratch');decoded=time.monotonic()
        f=flows(bgr);it=iter(f);views,_=represent(bgr,cfg['controls'],lambda *_:next(it));extracted=time.monotonic()
        with torch.no_grad():net(torch.from_numpy(views['correct'][None]).to(args.device))
        if str(args.device).startswith('cuda'):torch.cuda.synchronize()
        result.append({'sample_id':r['sample_id'],'decode_seconds':decoded-tick,'flow_and_controls_seconds':extracted-decoded,
            'inference_seconds':time.monotonic()-extracted,'cache_uncompressed_bytes':bgr.nbytes+f.nbytes})
    total=time.monotonic()-started
    write(Path(args.run_dir)/'profile.json',{'scope':'synthetic_validation' if args.synthetic else 'server_profile',
        'environment':environment(),'attempted':len(selected),'completed':len(result),'wall_seconds':total,
        'peak_allocated_bytes':torch.cuda.max_memory_allocated() if str(args.device).startswith('cuda') else None,
        'records':result,'actual_provider_cost_cny':None,'note':'Inference profile includes decode, flow and all controls. Not a training throughput or cloud billing receipt.'})


def main():
    p=argparse.ArgumentParser(description='Versioned server video-forensics research')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('doctor','audit','split','prepare','extract','train','evaluate','probes','decide','verify','freeze-final','profile','catalog','download-plan','fetch','zip-index','zip-fetch','materialize','purge-materialized','budget-init','budget-reserve','budget-settle'):
        s=sub.add_parser(name)
        for arg in ('data-root','cache-root','run-dir'):s.add_argument('--'+arg,type=Path,default=Path('.'))
        s.add_argument('--device',default='cuda:0');s.add_argument('--output',type=Path)
        if name in ('audit','split','prepare','profile'):s.add_argument('--manifest',type=Path,required=True)
        if name in ('prepare','profile'):s.add_argument('--config',type=Path,required=True)
        if name=='audit':s.add_argument('--check-files',action='store_true')
        if name in ('extract','evaluate'):s.add_argument('--role',choices=['dev_audit','ood_dev','final_audit'])
        if name=='train':
            s.add_argument('--arm',required=True);s.add_argument('--seed',type=int,required=True)
            s.add_argument('--epochs-this-call',type=int)
        if name in ('materialize','purge-materialized'):s.add_argument('--arm',required=True)
        if name=='materialize':s.add_argument('--workers',type=int)
        if name=='freeze-final':s.add_argument('--review',type=Path,required=True)
        if name=='profile':s.add_argument('--limit',type=int,default=100);s.add_argument('--synthetic',action='store_true')
        if name in ('train','profile') or name.startswith('budget-'):
            s.add_argument('--ledger',type=Path);s.add_argument('--reservation')
        if name=='budget-reserve':
            s.add_argument('--category',required=True);s.add_argument('--hours',type=float,default=0);s.add_argument('--hourly-rate',type=float,default=0)
            s.add_argument('--fixed-cny',type=float,default=0);s.add_argument('--quote',required=True)
        if name=='budget-settle':s.add_argument('--actual-cny',type=float,required=True);s.add_argument('--hours',type=float,required=True);s.add_argument('--receipt',required=True)
        if name=='download-plan':s.add_argument('--catalog',type=Path,required=True);s.add_argument('--repo',required=True);s.add_argument('--include',nargs='+',required=True)
        if name=='fetch':s.add_argument('--plan',type=Path,required=True);s.add_argument('--max-gib',type=float,required=True)
        if name in ('zip-index','zip-fetch'):
            s.add_argument('--catalog',type=Path,required=True);s.add_argument('--repo',required=True);s.add_argument('--archive',required=True)
        if name=='zip-fetch':s.add_argument('--members',type=Path,required=True);s.add_argument('--max-gib',type=float,required=True)
    a=p.parse_args()
    try:
        if a.command=='doctor':doctor(a)
        elif a.command in ('audit','split'):
            from .manifest import audit,split_groups
            data=rows(a.manifest)
            if a.command=='split':
                if not a.output:raise ValueError('--output required')
                data=split_groups(data)
                report=audit(data)
                if not report['valid']:raise ValueError(report['errors'])
                with a.output.open('x',encoding='utf-8') as f:
                    for r in data:f.write(json.dumps(r,ensure_ascii=False)+'\n')
            else:
                report=audit(data,a.data_root,a.check_files)
                if a.output:write(a.output,report)
                print(json.dumps(report,ensure_ascii=False,indent=2))
                if not report['valid']:return 2
        elif a.command in ('catalog','download-plan','fetch','zip-index','zip-fetch'):
            from . import data
            if a.command=='catalog':data.catalog(a.output)
            elif a.command=='download-plan':data.download_plan(a.catalog,a.repo,a.include,a.output)
            elif a.command=='fetch':data.fetch(a.plan,a.data_root,a.max_gib)
            elif a.command=='zip-index':data.remote_zip(a.catalog,a.repo,a.archive,output=a.output)
            else:print(data.remote_zip(a.catalog,a.repo,a.archive,members=read(a.members),data_root=a.data_root,max_gib=a.max_gib))
        elif a.command.startswith('budget-'):
            from . import budget
            if not a.ledger:raise ValueError('--ledger required')
            if a.command=='budget-init':budget.init(a.ledger)
            elif a.command=='budget-reserve':budget.reserve(a.ledger,a.reservation,a.category,a.hours,a.hourly_rate,a.fixed_cny,a.quote)
            else:budget.settle(a.ledger,a.reservation,a.actual_cny,a.hours,a.receipt)
        elif a.command=='profile':profile(a)
        else:
            from . import pipeline,statistics
            run=a.run_dir
            if a.command=='prepare':pipeline.prepare(run,read(a.config),rows(a.manifest))
            elif a.command=='extract':pipeline.extract(run,a.data_root,a.cache_root,a.role)
            elif a.command=='train':pipeline.train(run,a.cache_root,a.device,a.arm,a.seed,a.ledger,a.reservation,a.epochs_this_call)
            elif a.command=='evaluate':pipeline.evaluate(run,a.cache_root,a.device,a.role or 'dev_audit')
            elif a.command=='freeze-final':pipeline.freeze_final(run,a.review)
            elif a.command=='probes':statistics.probes(run,a.cache_root)
            elif a.command=='decide':statistics.decide(run)
            elif a.command=='verify':print(json.dumps(statistics.verify_predictions(run),indent=2))
            elif a.command in ('materialize','purge-materialized'):
                from . import materialize
                if a.command=='materialize':materialize.materialize(run,a.cache_root,a.arm,a.workers)
                else:materialize.purge(run,a.cache_root,a.arm)
        return 0
    except Exception as exc:
        if a.run_dir!=Path('.') and a.run_dir.exists():event(a.run_dir,a.command,status='failed',error=repr(exc))
        raise


if __name__=='__main__':sys.exit(main())
