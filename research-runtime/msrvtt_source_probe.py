"""Pinned, bounded public candidate acquisition; no formal dataset acceptance."""
import argparse
import hashlib
import io
import json
import random
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'research-runs'/'source_probe_20260912'


def save(name,data):
    p=RUN/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def metadata():
    info=json.loads((RUN/'repo.json').read_text(encoding='utf-8'));tree=json.loads((RUN/'tree.json').read_text(encoding='utf-8'))
    rev=info['sha'];repo='friedrichor/MSR-VTT'
    for name in ['raw_data/MSRVTT_data.json','raw_data/MSRVTT_train.7k.csv','README.md','raw_data/category.txt']:
        entry=next(x for x in tree if x['path']==name)
        if entry['size']>32*2**20:raise ValueError('Metadata size budget exceeded')
        dest=RUN/'metadata'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'+urllib.parse.quote(name,safe='/')
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'research-source-probe/1'}),timeout=45)as response:
                raw=response.read(entry['size']+1)
            if len(raw)!=entry['size']:raise ValueError('Metadata size mismatch')
            sha=hashlib.sha256(raw).hexdigest()
            if entry.get('lfs'):
                if sha!=entry['lfs']['oid']:raise ValueError('Metadata LFS hash mismatch')
            elif hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()!=entry['oid']:raise ValueError('Metadata Git blob mismatch')
            dest.write_bytes(raw)
            save('metadata/'+name+'.receipt.json',{'repo':repo,'revision':rev,'path':name,'bytes':len(raw),'sha256':sha,'upstream_object_verified':True})
        print('METADATA',name,flush=True)
    data=json.loads((RUN/'metadata/raw_data/MSRVTT_data.json').read_text(encoding='utf-8'))
    print('schema',list(data)if isinstance(data,dict)else 'list')
    if isinstance(data,dict):
        for k,v in data.items():
            if isinstance(v,list):print(k,len(v),'example',json.dumps(v[:1],ensure_ascii=False)[:1800])


class RangeFile(io.RawIOBase):
    def __init__(self,url,size):self.url=url;self.size=size;self.pos=0;self.transferred=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,o,w=0):
        self.pos=o if w==0 else self.pos+o if w==1 else self.size+o
        if self.pos<0:raise ValueError('negative offset')
        return self.pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        if n<=0:return b''
        if n>32*2**20 or self.transferred+n>512*2**20:raise ValueError('HTTP byte budget exceeded')
        start=self.pos;end=start+n-1
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}','User-Agent':'research-source-probe/1'})
        with urllib.request.urlopen(req,timeout=45)as response:
            expected=f'bytes {start}-{end}/{self.size}'
            if response.status!=206 or response.headers.get('Content-Range')!=expected:
                raise ValueError(f'Exact range not honored: {response.status} {response.headers.get("Content-Range")} expected {expected}')
            data=response.read(n+1)
        if len(data)!=n:raise ValueError('range length mismatch')
        self.pos+=n;self.transferred+=n;return data


def index():
    repo='friedrichor/MSR-VTT';rev=json.loads((RUN/'repo.json').read_text(encoding='utf-8'))['sha']
    tree=json.loads((RUN/'tree.json').read_text(encoding='utf-8'));entry=next(r for r in tree if r['path']=='MSRVTT_Videos.zip')
    reader=RangeFile(f'https://huggingface.co/datasets/{repo}/resolve/{rev}/MSRVTT_Videos.zip',entry['size'])
    with zipfile.ZipFile(reader)as z:
        rows=[{'path':i.filename,'size':i.file_size,'compressed_size':i.compress_size,'crc32':i.CRC}for i in z.infolist()if not i.is_dir()]
    save('video_zip_index.json',{'repo':repo,'revision':rev,'archive':entry['path'],'archive_bytes':entry['size'],'archive_lfs_sha256':entry['lfs']['oid'],'transferred_bytes':reader.transferred,'entries':rows,'full_archive_verified':False})
    print('INDEX',len(rows),'files',reader.transferred,'bytes',json.dumps(rows[:3]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['metadata','index']);a=p.parse_args()
    try:{'metadata':metadata,'index':index}[a.stage]()
    except Exception as exc:
        save(a.stage+'_error.json',{'error':repr(exc),'time_utc':datetime.now(timezone.utc).isoformat()});raise
