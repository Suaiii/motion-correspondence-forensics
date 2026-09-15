"""Recompute results and paired development uncertainty; no refitting or tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score, balanced_accuracy_score


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True);args=parser.parse_args()
root=args.run_dir.resolve();assert root.drive.upper()=='E:'
evaluation=json.loads((root/'evaluation.json').read_text(encoding='utf-8'))
pred=json.loads((root/'predictions.json').read_text(encoding='utf-8'))
assert sha(root/'predictions.json')==evaluation['predictions_sha256']
checks=[]
for item in evaluation['results']:
    group=[r for r in pred if all(r[k]==item[k] for k in ('kind','seed','condition'))]
    assert len({r['sample_id']for r in group})==len(group)==item['n']
    y=np.array([r['label_fake']for r in group]);p=np.array([r['prob_fake']for r in group])
    auc=float(roc_auc_score(y,p));ba=float(balanced_accuracy_score(y,p>=item['threshold']))
    assert abs(auc-item['auc'])<1e-12 and abs(ba-item['balanced_accuracy'])<1e-12
    checks.append({k:item[k] for k in ('kind','seed','condition')})
paired=[]
for condition in sorted({r['condition']for r in pred}):
    ids=sorted({r['sample_id']for r in pred if r['condition']==condition})
    y=np.array([next(r['label_fake']for r in pred if r['sample_id']==sid)for sid in ids])
    probs={kind:np.array([np.mean([r['prob_fake']for r in pred if r['sample_id']==sid and r['condition']==condition and r['kind']==kind])for sid in ids])for kind in ('raw_temporal','aligned_temporal')}
    rng=np.random.default_rng(20260908);a=np.where(y==0)[0];b=np.where(y==1)[0];diff=[]
    for _ in range(1000):
        idx=np.r_[rng.choice(a,len(a),replace=True),rng.choice(b,len(b),replace=True)]
        diff.append(roc_auc_score(y[idx],probs['aligned_temporal'][idx])-roc_auc_score(y[idx],probs['raw_temporal'][idx]))
    paired.append({'condition':condition,'statistic':'AUC(seed-mean aligned probabilities) minus AUC(seed-mean raw probabilities)',
        'difference':float(roc_auc_score(y,probs['aligned_temporal'])-roc_auc_score(y,probs['raw_temporal'])),
        'paired_stratified_percentile95':np.quantile(diff,[.025,.975]).tolist(),
        'limitation':'small historical development sample; not correction for model/condition selection or source uncertainty'})
result={'recomputed_groups':len(checks),'all_passed':True,'paired_diagnostics':paired,'review_type':'same-implementer numerical verification; not independent scientific reproduction'}
(root/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
hashes={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file() and p.name!='artifact_hashes.json'}
(root/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
