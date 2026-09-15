"""Verify complete feature cache and rank content-similarity candidates on GPU."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--qc-dir',type=Path,required=True);p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    if a.output_dir.exists():raise FileExistsError('Preserve prior audit')
    summary=read(a.run_dir/'summary.json');lock=read(a.run_dir/'lock.json')
    if not summary['complete'] or sha(a.selection)!=lock['selection_sha256']:raise ValueError('Incomplete or different selection')
    wanted={r['sample_id'] for r in read(a.selection)['rows']};records={}
    for file in (a.run_dir/'records').glob('*.json'):
        r=read(file)
        if r['sample_id'] in records:raise ValueError('Duplicate cache identity')
        records[r['sample_id']]=r
    if set(records)!=wanted:raise ValueError('Cache identity coverage differs')
    if dict(Counter(r['status'] for r in records.values()))!=summary['statuses']:raise ValueError('Status counts differ')
    qc={}
    for file in (a.qc_dir/'records').glob('*.json'):
        r=read(file)
        if r['sample_id'] in qc:raise ValueError('Duplicate QC identity')
        qc[r['sample_id']]=r
    if set(qc)!=wanted:raise ValueError('QC identity coverage differs')
    a.output_dir.mkdir(parents=True)
    protocol={'scope':'Development content-similarity triage only; no verified ancestry or classifier fitting',
              'neighbor_count':5,'candidate_cosine_min':.98,'pooling':'mean of 16 frozen CLS features; L2 normalize',
              'device':'cuda','block_rows':1024,'model_lock_sha256':sha(a.run_dir/'lock.json'),
              'script_sha256':sha(__file__),'selection_sha256':sha(a.selection)}
    (a.output_dir/'protocol.json').write_text(json.dumps(protocol,indent=2))
    ids=[];vectors=[];errors=[];checked=0;started=time.perf_counter()
    for sid in sorted(records):
        r=records[sid];q=qc[sid]
        if r['status']!='ok':
            if q['status']=='ok':raise ValueError('DINO failed a QC-eligible video')
            errors.append({'sample_id':sid,'dino_reason':r.get('reason'),'qc_reason':q.get('reason')});continue
        f=a.run_dir/r['feature_file']
        if sha(f)!=r['feature_sha256'] or r['sha256']!=q['file_sha256']:raise ValueError('Source/feature hash mismatch')
        x=np.load(f,allow_pickle=False)
        if x.shape!=(16,768) or not np.isfinite(x).all():raise ValueError('Invalid feature tensor')
        if r['sampling']['pts']!=q['sampling']['pts']:raise ValueError('Sampling timestamps differ from QC')
        ids.append({'sample_id':sid,'source':r['source'],'file_sha256':r['sha256'],'feature_sha256':r['feature_sha256']})
        vectors.append(x.mean(0));checked+=1
    features=np.stack(vectors).astype(np.float32);norm=np.linalg.norm(features,axis=1)
    if (norm<=0).any():raise ValueError('Zero pooled feature')
    np.save(a.output_dir/'pooled_features.npy',features)
    (a.output_dir/'ids.json').write_text(json.dumps(ids),encoding='utf-8')
    torch.set_num_threads(1);torch.backends.cuda.matmul.allow_tf32=False
    x=torch.from_numpy(features/norm[:,None]).cuda();count=len(ids);candidate_map={}
    with torch.inference_mode(),(a.output_dir/'neighbors.jsonl').open('w') as output:
        for start in range(0,count,1024):
            stop=min(count,start+1024);scores=x[start:stop]@x.T
            scores[torch.arange(stop-start,device='cuda'),torch.arange(start,stop,device='cuda')]=-float('inf')
            values,indices=scores.topk(5,dim=1);values=values.cpu().numpy();indices=indices.cpu().numpy()
            for j in range(stop-start):
                row={'sample_id':ids[start+j]['sample_id'],'neighbors':[{'sample_id':ids[int(k)]['sample_id'],'cosine':float(v)} for k,v in zip(indices[j],values[j])]}
                output.write(json.dumps(row)+'\n')
                for k,v in zip(indices[j],values[j]):
                    if v>=.98:
                        left,right=sorted((start+j,int(k)))
                        candidate_map[(left,right)]={'left':ids[left]['sample_id'],'right':ids[right]['sample_id'],'cosine':float(v)}
    candidates=[candidate_map[k] for k in sorted(candidate_map)]
    (a.output_dir/'candidates.json').write_text(json.dumps(candidates,indent=2))
    result={'verified_feature_files':checked,'non_ok_records':errors,'retrieval_top_k':5,
            'candidate_pairs_at_or_above_098':len(candidates),'candidate_set_is_complete_threshold_graph':False,
            'limitations':'Only top-five neighbors per item; threshold pairs may be omitted. Similarity is not verified duplication or ancestry.',
            'wall_seconds':time.perf_counter()-started,'classification_metrics_computed':False,
            'artifact_sha256':{f.name:sha(f) for f in a.output_dir.iterdir() if f.is_file()}}
    (a.output_dir/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
