"""Small order-invariant residual-statistics diagnostic with complete provenance."""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from run import digest, dump

p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();root=a.run_dir.resolve()
assert root.drive.upper()=='E:'
cfg=json.loads((root/'protocol.json').read_text(encoding='utf-8'))
rows=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
if (root/'statistics_probe.json').exists():raise FileExistsError('No overwriting diagnostic outcomes')
protocol=Path(__file__).with_name('diagnostic_protocol.json')
dump(root/'statistics_probe_lock.json',{'protocol_sha256':digest(protocol),'code_sha256':digest(__file__),'manifest_sha256':digest(root/'manifest.json'),'fixed_before_feature_extraction_and_fitting':True})
y=np.array([r['label_fake']for r in rows]);roles={r:np.array([i for i,x in enumerate(rows)if x['role']==r])for r in ('fit','calibration','audit')}
feature_sets={}
for condition in cfg['conditions']:
    columns=[]
    for rep in ('raw_temporal','aligned_temporal'):
        data=np.load(root/'cache'/f'{condition}__{rep}.npy',mmap_mode='r',allow_pickle=False)
        values=[]
        for x in data:
            x=np.array(x,dtype=np.float32);abs_x=np.abs(x)
            values.append([float(abs_x.mean()),float(abs_x.mean(axis=(1,2,3)).std()),float(np.sqrt((x*x).mean())),float(np.quantile(abs_x,.95))])
        columns.append(np.array(values))
    feature_sets[condition]=np.log1p(np.concatenate(columns,axis=1))
scaler=StandardScaler().fit(feature_sets['clean'][roles['fit']])
clf=LogisticRegression(C=1,max_iter=1000,random_state=20260911).fit(scaler.transform(feature_sets['clean'][roles['fit']]),y[roles['fit']])
vp=clf.predict_proba(scaler.transform(feature_sets['clean'][roles['calibration']]))[:,1]
grid=np.linspace(.01,.99,99);scores=[balanced_accuracy_score(y[roles['calibration']],vp>=t)for t in grid]
threshold=min((float(t)for t,s in zip(grid,scores)if abs(s-max(scores))<1e-12),key=lambda x:(abs(x-.5),x))
records=[];metrics=[]
for condition,X in feature_sets.items():
    probs=clf.predict_proba(scaler.transform(X))[:,1]
    for role,indices in roles.items():
        metrics.append({'condition':condition,'role':role,'n':len(indices),'auc':float(roc_auc_score(y[indices],probs[indices])),'bacc':float(balanced_accuracy_score(y[indices],probs[indices]>=threshold))})
        for i in indices:records.append({'condition':condition,'role':role,'sample_id':rows[i]['sample_id'],'label_fake':int(y[i]),'prob_fake':float(probs[i]),'features_log1p':X[i].tolist()})
dump(root/'statistics_probe.json',{'metrics':metrics,'predictions':records,'threshold':threshold,'coef':clf.coef_.tolist(),'intercept':clf.intercept_.tolist(),'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist(),'protocol_sha256':digest(protocol),'scope':'fixed eight order-invariant residual statistics; developer diagnostic, not a video detector innovation'})
print(json.dumps(metrics,indent=2))
