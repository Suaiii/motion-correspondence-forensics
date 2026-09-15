"""Recompute timing/identifier constraints from saved evidence, no model fitting."""
import hashlib
import json
import re
import zipfile
from collections import Counter,defaultdict
from pathlib import Path
from filename_tokens import generator_token

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research-runs/overnight_20260911'
OUT=ROOT/'research-runs/protocol_audit_20260912';OUT.mkdir(parents=True,exist_ok=True)
stats=defaultdict(list);identifiers=defaultdict(set);examples={};inputs={};verification={}
for filename,prefix in [('dino_checkpoint_v1.zip','gpu_dino_v1/records/'),('real_and_closeout_checkpoint_v1.zip','vript_dino_group1746_v1/records/')]:
    path=BASE/filename;h=hashlib.sha256()
    with path.open('rb')as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    inputs[filename]=h.hexdigest()
    with zipfile.ZipFile(path)as z:
        if 'ARCHIVE_INDEX.json'in z.namelist():
            index=json.loads(z.read('ARCHIVE_INDEX.json'));receipt={r['name']:r for r in index['entries']}
            verification[filename]='Record SHA256 checked against embedded transfer index; whole bundle SHA recorded'
        else:
            receipt=None
            verification[filename]='Legacy ZIP has no embedded SHA index; record ZIP CRC checked by zipfile; whole bundle SHA recorded, not independently authenticated'
        for name in z.namelist():
            if not(name.startswith(prefix)and name.endswith('.json')):continue
            raw=z.read(name)
            if receipt is not None and hashlib.sha256(raw).hexdigest()!=receipt[name]['sha256']:raise ValueError('Record differs from bundle manifest')
            r=json.loads(raw)
            if r.get('status')!='ok':continue
            s=r['source'];sample=r['sampling'];pts=sample['pts']
            span=pts[-1]-pts[0];dt=(pts[-1]-pts[0])/(len(pts)-1)
            stats[s].append((span,dt,sample['duration']))
            base=r.get('basename',r['sample_id'].split('/')[-1])
            examples.setdefault(s,base)
            token=generator_token(base)
            identifiers[s].add(token)
summary={}
for source,rows in stats.items():
    spans=sorted(r[0]for r in rows);rates=sorted(1/r[1]for r in rows if r[1]>0)
    summary[source]={'count':len(rows),'sampled_native_span_seconds':{'min':min(spans),'median':spans[len(spans)//2],'max':max(spans)},
                     'effective_sampled_fps':{'min':min(rates),'median':rates[len(rates)//2],'max':max(rates)},
                     'duration_at_least_2':sum(r[2]>=2-1e-6 for r in rows),'duration_at_least_1_5':sum(r[2]>=1.5-1e-6 for r in rows),
                     'filename_example':examples[source]}
fake_sources=[s for s in identifiers if s!='vript'];cross=[]
for i,a in enumerate(fake_sources):
    for b in fake_sources[i+1:]:
        overlap=identifiers[a]&identifiers[b]
        cross.append({'a':a,'b':b,'normalized_filename_token_overlap_count':len(overlap),'examples':sorted(overlap)[:10],
                      'interpretation':'filename token overlap is only an ancestry candidate, not verified prompt/reference equivalence'})
result={'summary':summary,'cross_generator_identifier_candidates':cross,'input_bundle_sha256':inputs,'bundle_verification':verification,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'finding_scope':'Native frame count equality does not match physical observation time. Eligibility counts here use recorded duration only, not fresh decoded PTS checks.',
        'candidate_protocol':'Evaluate fixed 1.5sec x 8fps (12 samples) coverage prospectively; not silently replace the locked 2sec primary protocol.',
        'formal_training_runs':0}
(OUT/'report_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
