"""Audit only downloaded public metadata; never labels missing ancestors verified."""
import collections
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.common import read,rows,write,sha


def main(root):
    root=Path(root);catalog=read(root/'dataset_catalog_20260910.json');result={'scope':'public metadata only; video bytes not acquired','repositories':[]}
    for repo in catalog['repositories']:
        result['repositories'].append({'repo':repo['repo'],'revision':repo['revision'],'files':len(repo['files']),
            'total_bytes':sum(f['size'] for f in repo['files'])})
    counts=collections.Counter();paths=set();duplicate_paths=0
    for p in sorted((root/'metadata/jian-0/GenVidBench/GenVidBench').glob('*labels.txt')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            path,label=line.rsplit(maxsplit=1);parts=path.replace('\\','/').split('/')
            counts['/'.join([p.stem,parts[1],label])]+=1
            if path in paths:duplicate_paths+=1
            paths.add(path)
    result['genvidbench']={'counts':dict(counts),'duplicate_paths':duplicate_paths,
        'ancestry_status':'not established by binary path-label lists; source and prompt mapping still required'}
    splits={};source_splits={};unknown=collections.Counter();prompt_splits={}
    for p in sorted((root/'metadata/AIGVDBench/AIGVDBench/Split').glob('*.jsonl')):
        rr=rows(p);splits[p.stem]=len(rr)
        for r in rr:
            name=r['Video_id'];m=re.match(r'^(.*)_\d+_\d+to\d+\.mp4$',name)
            if m:source_splits.setdefault(m.group(1),set()).add(p.stem)
            else:unknown[p.stem]+=1
            prompt=r.get('Video_Prompts','').strip()
            if prompt:prompt_splits.setdefault(prompt,set()).add(p.stem)
    overlaps={k:sorted(v) for k,v in source_splits.items() if len(v)>1}
    result['aigvdbench']={'split_rows':splits,'inferred_original_ids':len(source_splits),
        'original_id_cross_split_candidates':len(overlaps),'overlap_examples':dict(list(overlaps.items())[:10]),
        'unparsed_ids':dict(unknown),'identical_prompt_cross_split_candidates':sum(len(v)>1 for v in prompt_splits.values()),
        'interpretation':'Filename-prefix and exact-text candidates, not completed semantic deduplication. Split lists contain Video_id/prompts, not verified fake ancestry.'}
    result['input_hashes']={str(p.relative_to(root)):sha(p) for p in (root/'metadata').rglob('*') if p.is_file() and not p.name.endswith('.partial')}
    write(root/'release_metadata_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='input_hashes'},ensure_ascii=False,indent=2))


if __name__=='__main__':main(sys.argv[1])
