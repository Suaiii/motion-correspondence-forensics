import csv,json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'research-runs/source_probe_20260914_cvdf'
pat=re.compile(r'([A-Za-z0-9_-]{11})_(\d{6})_(\d{6})\.mp4$')
receipt=json.loads((ROOT/'receipt.json').read_text(encoding='utf8'))
qc=json.loads((ROOT/'qc.json').read_text(encoding='utf8'))
rows=list(csv.DictReader((ROOT/'train_annotations.csv').open(encoding='utf8')))
byid={}
for r in rows: byid.setdefault(r['youtube_id'],[]).append(r)
out=[]
for item in receipt['records']:
    m=pat.search(item['archive_member'].lstrip('./'))
    rec=dict(item); rec['filename_parse']='ok' if m else 'failed'
    if m:
        vid,start,end=m.groups(); matches=[r for r in byid.get(vid,[]) if int(r['time_start'])==int(start) and int(r['time_end'])==int(end)]
        rec.update(youtube_id=vid,time_start=int(start),time_end=int(end),annotation_matches=len(matches),annotations=matches)
    out.append(rec)
summary={'candidate_count':len(out),'filename_parse_ok':sum(x['filename_parse']=='ok' for x in out),'annotation_exact_matches':sum(x.get('annotation_matches',0)==1 for x in out),'annotation_missing':sum(x.get('annotation_matches',0)==0 for x in out),'duplicate_annotation_matches':sum(x.get('annotation_matches',0)>1 for x in out),'is_cc_counts':{},'ancestry_verified':False,'license_accepted':False,'formal_training':False,'limitations':['only first 16 members of one published shard','no full archive checksum','official CSV is metadata/CC flag, not a licence grant','cross-source ancestry audit remains pending']}
for x in out:
    for a in x.get('annotations',[]): summary['is_cc_counts'][a['is_cc']]=summary['is_cc_counts'].get(a['is_cc'],0)+1
(ROOT/'candidate_annotation_audit.json').write_text(json.dumps({'summary':summary,'records':out},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
