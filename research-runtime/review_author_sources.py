"""Read-only, pinned public-source inspection; never imports downloaded code.

Only tiny source/text files are cached locally. No repository checkout, model,
dataset, server connection, dependency install or third-party execution.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import subprocess
import urllib.request


def fetch(url,limit):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7897','http':'http://127.0.0.1:7897'}))
    req=urllib.request.Request(url,headers={'User-Agent':'research-source-review','Accept':'application/vnd.github+json'})
    with opener.open(req,timeout=30) as response:data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Text/metadata size limit exceeded')
    return data


def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--selection',type=Path)
    p.add_argument('--repository',action='append',default=[]);a=p.parse_args()
    a.cache.mkdir(parents=True,exist_ok=True);a.inventory.parent.mkdir(parents=True,exist_ok=True)
    if a.selection:
        record=json.loads(a.inventory.read_text());chosen=json.loads(a.selection.read_text())
        for repo,paths in chosen.items():
            metadata=record['repositories'][repo];commit=metadata['commit'];allowed={v['path']:v for v in metadata['tree'] if v['type']=='blob'}
            metadata.setdefault('inspected_files',[])
            existing={v['path'] for v in metadata['inspected_files']}
            for name in paths:
                rel=PurePosixPath(name)
                if rel.is_absolute() or '..' in rel.parts or name not in allowed:raise ValueError('Invalid source path')
                if allowed[name].get('mode')=='120000':raise ValueError('Refuse symlink')
                if rel.suffix.lower() not in ('.py','.md','.yaml','.yml','.txt','.json','.sh'):raise ValueError('Source/text files only')
                if name in existing:continue
                url=f'https://raw.githubusercontent.com/{repo}/{commit}/{name}'
                data=fetch(url,200_000);data.decode('utf-8')
                blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                if blob!=allowed[name]['sha']:raise ValueError('Git blob digest mismatch')
                path=a.cache/repo.replace('/','__')/commit/Path(name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                metadata['inspected_files'].append(dict(path=name,bytes=len(data),git_blob_sha1=blob,
                    sha256=hashlib.sha256(data).hexdigest(),raw_url=url,local_cache=str(path)))
        record['last_fetch_utc']=datetime.now(timezone.utc).isoformat()
    else:
        if a.inventory.exists():raise FileExistsError(a.inventory)
        def inventory(repo):
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('Invalid public repo identifier')
            result=subprocess.run(['git','-c','http.proxy=http://127.0.0.1:7897','ls-remote',f'https://github.com/{repo}.git','HEAD'],capture_output=True,text=True,check=True,timeout=40)
            commit=result.stdout.split()[0]
            data=fetch(f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1',2_000_000)
            tree=json.loads(data)
            if tree.get('truncated'):raise ValueError('Truncated tree')
            return repo,dict(commit=commit,tree=tree['tree'],inspected_files=[])
        with ThreadPoolExecutor(max_workers=3) as pool:repos=dict(pool.map(inventory,a.repository))
        record=dict(observed_utc=datetime.now(timezone.utc).isoformat(),repositories=repos,
            purpose='Pinned source inspection only; no third-party code executed or reproduced',
            models_downloaded=False,datasets_downloaded=False,server_accessed=False)
    a.inventory.write_text(json.dumps(record,indent=2)+'\n')
    for repo,v in record['repositories'].items():
        relevant=[r['path'] for r in v['tree'] if r['type']=='blob' and r['path'].endswith(('.py','.yaml','.yml','.sh','.md'))]
        print(json.dumps(dict(repo=repo,commit=v['commit'],source_paths=relevant[:100],fetched=len(v['inspected_files']))))


if __name__=='__main__':main()
