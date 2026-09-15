"""Pinned public-repository metadata and explicit-file downloads; no bulk defaults."""
import hashlib
import json
import os
import io
import zipfile
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from .common import write,read,sha,safe_path,now

REPOS=('jian-0/GenVidBench','AIGVDBench/AIGVDBench')


class RangeReader(io.RawIOBase):
    """Seekable pinned HTTP object. A non-range response is refused before reading."""
    def __init__(self,url,size):self.url=url;self.size=size;self.position=0;self.transferred=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        target=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if target<0:raise ValueError('Negative seek')
        self.position=target;return target
    def read(self,n=-1):
        n=self.size-self.position if n<0 else min(n,self.size-self.position)
        if n<=0:return b''
        if n>64*2**20:raise ValueError('Range request exceeds 64 MiB; use chunked member reads')
        end=self.position+n-1
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={self.position}-{end}'})
        with urllib.request.urlopen(req,timeout=120) as response:
            if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {self.position}-{end}/'):
                raise ValueError('Remote endpoint does not honor exact byte ranges')
            value=response.read(n+1)
        if len(value)!=n:raise ValueError('Short or oversized range response')
        self.position+=n;self.transferred+=n;return value


def remote_zip(catalog_path,repo,archive,output=None,members=None,data_root=None,max_gib=1):
    source=next(r for r in read(catalog_path)['repositories'] if r['repo']==repo)
    meta=next(f for f in source['files'] if f['path']==archive)
    if not archive.lower().endswith('.zip'):raise ValueError('Range member selection supports ZIP, not RAR/solid archives')
    url='https://huggingface.co/datasets/'+repo+'/resolve/'+source['revision']+'/'+urllib.parse.quote(archive,safe='/')
    reader=RangeReader(url,meta['size'])
    with zipfile.ZipFile(reader) as z:
        info=z.infolist()
        if members is None:
            result={'repo':repo,'revision':source['revision'],'archive':archive,'archive_lfs_sha256':meta.get('lfs',{}).get('oid'),
                'files':[{'path':f.filename,'size':f.file_size,'compressed_size':f.compress_size,'crc32':f.CRC} for f in info if not f.is_dir()],
                'transferred_bytes':reader.transferred,'full_archive_downloaded':False}
            write(output,result);return result
        selected=[f for f in info if f.filename in set(members)]
        if len(selected)!=len(set(members)):raise ValueError('Missing or duplicate ZIP member')
        if sum(f.file_size for f in selected)>max_gib*2**30:raise ValueError('Selected members exceed quota')
        root=Path(data_root);root.mkdir(parents=True,exist_ok=True)
        if shutil.disk_usage(root).free<sum(f.file_size for f in selected)+2**30:raise ValueError('Insufficient space')
        for f in selected:
            if f.is_dir() or (f.external_attr>>16)&0o170000==0o120000:raise ValueError('Only regular files allowed')
            dest=safe_path(root,f.filename);receipt=dest.with_name(dest.name+'.receipt.json')
            if receipt.exists():
                saved=read(receipt)
                if saved['revision']!=source['revision'] or saved['archive']!=archive or sha(dest)!=saved['sha256']:raise ValueError('Member provenance changed')
                continue
            if dest.exists():raise FileExistsError('Unreceipted member exists')
            dest.parent.mkdir(parents=True,exist_ok=True);partial=dest.with_name(dest.name+'.partial')
            # Interrupted compressed members restart, completed members are reused.
            if partial.exists():partial.rename(partial.with_name(partial.name+'.failed-'+str(__import__('time').time_ns())))
            with z.open(f) as src,partial.open('xb') as target:
                shutil.copyfileobj(src,target,length=1024*1024)
            if partial.stat().st_size!=f.file_size:raise ValueError('ZIP member size differs')
            digest=sha(partial);os.replace(partial,dest)
            write(receipt,{'repo':repo,'revision':source['revision'],'archive':archive,'member':f.filename,'crc32':f.CRC,
                'sha256':digest,'archive_lfs_sha256':meta.get('lfs',{}).get('oid'),'full_archive_hash_verified':False,
                'verification':'pinned repository object via TLS, ZIP CRC and downloaded member SHA256; not a full-archive hash check'})
    return {'downloaded_members':len(selected),'transferred_bytes':reader.transferred}


def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'cvpr27-forensics/0.1'})
    with urllib.request.urlopen(req,timeout=45) as response:
        return json.load(response),response.headers.get('Link','')


def catalog(output):
    result={'created':now(),'repositories':[],'contains_downloaded_videos':False}
    for repo in REPOS:
        info,_=get_json('https://huggingface.co/api/datasets/'+repo)
        revision=info['sha'];entries=[];url=f'https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true&limit=1000'
        while url:
            page,link=get_json(url);entries.extend(p for p in page if p['type']=='file')
            url=None
            for part in link.split(','):
                if 'rel="next"' in part:
                    next_url=part[part.find('<')+1:part.find('>')]
                    if not next_url.startswith('https://huggingface.co/api/datasets/'+repo+'/'):raise ValueError('Unexpected pagination host')
                    url=next_url
        result['repositories'].append({'repo':repo,'revision':revision,'card_data':info.get('cardData',{}),'files':entries})
    write(output,result);return result


def download_plan(catalog_path,repo,include,output):
    source=next(r for r in read(catalog_path)['repositories'] if r['repo']==repo)
    chosen=[r for r in source['files'] if r['path'] in include]
    if {r['path'] for r in chosen}!=set(include) or not chosen:raise ValueError('Select exact existing file paths')
    write(output,{'repo':repo,'revision':source['revision'],'files':chosen,'total_bytes':sum(f['size'] for f in chosen),
        'catalog_sha256':sha(catalog_path),'warning':'Archive-level downloads only; member selection and provenance audit still required'})


def fetch(plan_path,data_root,max_gib):
    plan=read(plan_path);root=Path(data_root);root.mkdir(parents=True,exist_ok=True)
    if plan['repo'] not in REPOS or not plan['files']:raise ValueError('Unapproved public dataset source')
    if len(plan['revision'])!=40:raise ValueError('Use an immutable commit')
    if plan['total_bytes']!=sum(f['size'] for f in plan['files']):raise ValueError('Download plan size mismatch')
    if plan['total_bytes']>max_gib*2**30:raise ValueError('Download exceeds specified quota')
    if shutil.disk_usage(root).free<plan['total_bytes']+2**30:raise ValueError('Insufficient free space')
    for f in plan['files']:
        dest=safe_path(root,plan['repo']+'/'+f['path']);receipt=dest.with_name(dest.name+'.receipt.json')
        if receipt.exists():
            if sha(dest)!=read(receipt)['sha256']:raise ValueError('Downloaded source changed')
            continue
        if dest.exists():raise FileExistsError('Unreceipted source requires review')
        dest.parent.mkdir(parents=True,exist_ok=True);partial=dest.with_name(dest.name+'.partial')
        offset=partial.stat().st_size if partial.exists() else 0
        if offset>f['size']:raise ValueError('Oversized partial')
        if offset<f['size']:
            url='https://huggingface.co/datasets/'+plan['repo']+'/resolve/'+plan['revision']+'/'+urllib.parse.quote(f['path'],safe='/')
            headers={'Range':f'bytes={offset}-'} if offset else {}
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:
                if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):
                    raise ValueError('Server did not honor byte-range resume; preserve partial')
                with partial.open('ab' if offset else 'xb') as target:
                    count=offset
                    for chunk in iter(lambda:response.read(1024*1024),b''):
                        count+=len(chunk)
                        if count>f['size']:raise ValueError('Source exceeded declared size')
                        target.write(chunk)
        if partial.stat().st_size!=f['size']:raise ValueError('Incomplete download; rerun to resume')
        digest=sha(partial)
        if f.get('lfs'):
            if digest!=f['lfs']['oid']:raise ValueError('LFS SHA256 mismatch')
        else:
            h=hashlib.sha1(f"blob {f['size']}\0".encode())
            with partial.open('rb') as handle:
                for b in iter(lambda:handle.read(1024*1024),b''):h.update(b)
            if h.hexdigest()!=f['oid']:raise ValueError('Git object mismatch')
        os.replace(partial,dest)
        write(receipt,{'sha256':digest,'revision':plan['revision'],'repo':plan['repo'],'path':f['path'],'bytes':f['size']})
        print('verified',f['path'],flush=True)
