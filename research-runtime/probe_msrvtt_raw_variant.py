"""Public metadata check for a candidate higher-rate MSR-VTT mirror."""
import json
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'research-runs/source_probe_20260912/raw_variant'
root.mkdir(parents=True,exist_ok=True)
repo='VLM2Vec/MSR-VTT'


def get(url,name):
    path=root/name
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'research-source-probe/1'}),timeout=30)as r:
        data=r.read(32*2**20+1)
    if len(data)>32*2**20:raise ValueError('metadata bound exceeded')
    obj=json.loads(data);path.write_bytes(data);return obj


info=get('https://huggingface.co/api/datasets/'+repo,'repo.json')
tree=get(f"https://huggingface.co/api/datasets/{repo}/tree/{info['sha']}/raw_videos?limit=1000",'raw_tree_first_page.json')
print(json.dumps({'repo':repo,'revision':info['sha'],'card':info.get('cardData',{}),'count_first_page':len(tree),'examples':tree[:5]},ensure_ascii=False,indent=2))
