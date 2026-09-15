"""Recompute filename-derived origin-ID overlap; no content/ancestry verification."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def parse(path, prefix, pattern):
    rows=[];unmatched=[];groups={}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.startswith(prefix):continue
        m=re.fullmatch(pattern,line)
        if not m:unmatched.append(line);continue
        rows.append(line);groups.setdefault(m.group(1),[]).append(line.rsplit(' ',1)[0])
    return groups,rows,unmatched


def main():
    p=argparse.ArgumentParser();p.add_argument('--pair1',type=Path,required=True);p.add_argument('--pair2',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    vp=r'Pair1/vript/([A-Za-z0-9_-]{11})-Scene-\d+\.mp4 0'
    hp=r'Pair2/hd_vg_130m/\d+___([A-Za-z0-9_-]{11})\.[^ ]+ 0'
    v,vr,vu=parse(a.pair1,'Pair1/vript/',vp);h,hr,hu=parse(a.pair2,'Pair2/hd_vg_130m/',hp)
    overlap=sorted(set(v)&set(h))
    result={'vript_candidate_source_ids':len(v),'hdvg_candidate_source_ids':len(h),
            'vript_matched_rows':len(vr),'hdvg_matched_rows':len(hr),
            'unmatched':{'vript':vu,'hdvg':hu},'overlap_count':len(overlap),'overlap_ids':overlap,
            'overlap_members':{k:{'vript':v[k],'hdvg':h[k]} for k in overlap},
            'verified_ancestry':False,'scope':'Author-filename YouTube-ID candidates only; not decoded-content verification',
            'recommended_split_rule':'Unify candidate IDs across collections before grouped splits; exclude shared IDs from an independently held-out real-source cohort',
            'input_sha256':{'pair1':hashlib.sha256(a.pair1.read_bytes()).hexdigest(),'pair2':hashlib.sha256(a.pair2.read_bytes()).hexdigest()},
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['vript_candidate_source_ids','hdvg_candidate_source_ids','overlap_count']}))


if __name__=='__main__':main()
