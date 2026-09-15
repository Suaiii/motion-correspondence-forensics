"""Bounded public CVDF source availability probe; not a training dataset."""
import argparse
import csv
import hashlib
import io
import json
import tarfile
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'research-runs/source_probe_20260914_cvdf'
ROOT.mkdir(parents=True,exist_ok=True)


def save(name,data):
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def get_small(url,name,limit):
    p=ROOT/name
    if p.exists():return p.read_bytes()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'forensics-public-source-probe/1'}),timeout=30)as r:
        data=r.read(limit+1);headers=dict(r.headers)
    if len(data)>limit:raise ValueError('metadata budget exceeded')
    p.write_bytes(data);save(name+'.receipt.json',{'url':url,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'headers':{k:v for k,v in headers.items()if k.lower()in ('etag','last-modified','content-length')},'utc':datetime.now(timezone.utc).isoformat()})
    return data


def discover():
    raw=get_small('https://s3.amazonaws.com/kinetics/400/train/k400_train_path.txt','k400_train_path.txt',2**20)
    lines=[s.strip()for s in raw.decode().splitlines()if s.strip()]
    candidates=[u for u in lines if u.endswith('part_000.tar.gz')]
    url=candidates[0]if candidates else lines[0]
    if not url.startswith(('https://s3.amazonaws.com/kinetics/','http://s3.amazonaws.com/kinetics/')):raise ValueError('Unexpected public source URL')
    url=url.replace('http://','https://',1)
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30)as r:
        info={'archive_url':url,'content_length':int(r.headers.get('Content-Length','0')),'etag':r.headers.get('ETag'),'last_modified':r.headers.get('Last-Modified'),'version_id':r.headers.get('x-amz-version-id')}
    info.update(source='cvdfoundation/kinetics-dataset published K400 train URL list',probe_rule='first published train shard, first up to 16 complete MP4 members in first 32MiB; availability probe only',max_prefix_bytes=32*2**20,max_videos=16,formal_training=False,full_archive_hash_verified=False)
    save('plan.json',info)
    get_small('https://s3.amazonaws.com/kinetics/400/annotations/train.csv','train_annotations.csv',32*2**20)
    print(json.dumps(info,indent=2),flush=True)


def fetch():
    plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'));size=min(plan['content_length'],plan['max_prefix_bytes'])
    if not size:raise ValueError('Missing archive size')
    path=ROOT/'archive_prefix.bin'
    if not path.exists():
        req=urllib.request.Request(plan['archive_url'],headers={'Range':f'bytes=0-{size-1}','If-Match':plan['etag'],'User-Agent':'forensics-public-source-probe/1'})
        with urllib.request.urlopen(req,timeout=45)as r:
            if r.status!=206 or r.headers.get('Content-Range')!=f'bytes 0-{size-1}/{plan["content_length"]}':raise ValueError('Exact prefix range refused')
            data=r.read(size+1)
        if len(data)!=size:raise ValueError('Prefix size mismatch')
        path.write_bytes(data)
        save('prefix_receipt.json',{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'etag':plan['etag'],'source':plan['archive_url'],'full_gzip_crc_verified':False})
    raw=path.read_bytes();out=ROOT/'videos';out.mkdir(exist_ok=True);records=[];error=None
    try:
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r|gz')as tar:
            for m in tar:
                if not m.isfile()or not m.name.lower().endswith('.mp4'):continue
                if m.size>16*2**20:raise ValueError('Member exceeds probe size budget')
                source=tar.extractfile(m)
                if source is None:raise ValueError('Missing member stream')
                data=source.read(m.size+1)
                if len(data)!=m.size:raise ValueError('Incomplete member')
                sha=hashlib.sha256(data).hexdigest();dest=out/(sha+'.mp4')
                if not dest.exists():dest.write_bytes(data)
                records.append({'archive_member':m.name,'bytes':len(data),'sha256':sha,'path':str(dest),'status':'candidate_not_admitted','verification':'complete tar member from ETag-bound HTTPS prefix; no full archive checksum'})
                if len(records)>=plan['max_videos']:break
    except Exception as exc:error=repr(exc)
    save('receipt.json',{'records':records,'count':len(records),'error':error,'full_archive_verified':False,'formal_training':False})
    print('FETCHED',len(records),'error',error,flush=True)


def qc():
    import cv2
    import numpy as np
    receipt=json.loads((ROOT/'receipt.json').read_text(encoding='utf-8'));records=[]
    for item in receipt['records']:
        r=dict(item)
        cap=cv2.VideoCapture(item['path'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1])
        try:
            if not cap.isOpened():raise ValueError('Cannot open clip')
            fps=float(cap.get(cv2.CAP_PROP_FPS));n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));duration=n/fps
            r.update(fps=fps,frame_count=n,duration=duration,width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            if fps<8 or duration<2:raise ValueError('Not eligible for 2sec 8fps')
            indices=np.floor(((duration-2)/2+np.arange(16)/8)*fps+1e-8).astype(int)
            if len(set(indices))!=16:raise ValueError('Repeated indices')
            pts=[]
            for i in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES,int(i));ok,frame=cap.read()
                if not ok:raise ValueError('Decode failed')
                pts.append(float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000)
            if not np.all(np.diff(pts)>0):raise ValueError('Non-increasing PTS')
            r.update(qc_status='sampled_decode_ok',pts=pts)
        except Exception as exc:r.update(qc_status='failed',error=repr(exc))
        finally:cap.release()
        records.append(r)
    save('qc.json',{'records':records,'count':len(records),'sampling_ok':sum(r['qc_status']=='sampled_decode_ok'for r in records),'ancestry_license_and_content_acceptance':False})
    print(json.dumps([{'member':r['archive_member'],'fps':r.get('fps'),'status':r['qc_status']}for r in records],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['discover','fetch','qc']);a=p.parse_args()
    try:{'discover':discover,'fetch':fetch,'qc':qc}[a.stage]()
    except Exception as exc:save(a.stage+'_error.json',{'error':repr(exc),'utc':datetime.now(timezone.utc).isoformat()});raise
