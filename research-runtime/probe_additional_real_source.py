"""Bounded public MSR-VTT candidate-source discovery, not dataset acceptance."""
import hashlib
import json
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'research-runs'/'source_probe_20260912'
root.mkdir(parents=True,exist_ok=True)
repo='friedrichor/MSR-VTT'


def fetch(url,name,limit=20*2**20):
    target=root/name
    if target.exists():return json.loads(target.read_text(encoding='utf-8'))
    req=urllib.request.Request(url,headers={'User-Agent':'video-forensics-research/0.1'})
    with urllib.request.urlopen(req,timeout=30)as r:
        raw=r.read(limit+1)
    if len(raw)>limit:raise ValueError('Public metadata exceeds bound')
    obj=json.loads(raw)
    target.write_bytes(raw)
    (root/(name+'.receipt.json')).write_text(json.dumps({'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'time_utc':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
    return obj


try:
    info=fetch('https://huggingface.co/api/datasets/'+repo,'repo.json')
    rev=info['sha']
    files=fetch(f'https://huggingface.co/api/datasets/{repo}/tree/{rev}?recursive=true&limit=1000','tree.json')
    print(json.dumps({'repo':repo,'revision':rev,'card_data':info.get('cardData',{}),'files':[{'path':x['path'],'size':x.get('size'),'lfs':x.get('lfs')}for x in files if x['type']=='file'],'scope':'candidate source discovery; no video bytes or acceptance yet'},ensure_ascii=False,indent=2))
except Exception as exc:
    (root/'error.json').write_text(json.dumps({'error':repr(exc),'time_utc':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
    raise
