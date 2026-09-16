"""Mechanical replay, ancestor-cluster bootstrap and timing-shortcut probe."""
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def read(p): return json.loads(p.read_text())
def auc(y,s):
    n=int(y.sum());return float((rankdata(s)[y==1].sum()-n*(n+1)/2)/(n*(len(y)-n)))


def main():
    root=Path(sys.argv[1]); dest=root/'verification.json'
    if dest.exists():raise FileExistsError(dest)
    for rel,digest in read(root/'artifact_hashes.json').items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,rel
    protocol=read(root/'protocol.json'); results=read(root/'results.json')['results']
    preds=read(root/'predictions.json'); manifest=read(root/'manifest.json')
    comparisons=[]; metadata_results=[]
    for held in protocol['holdouts']:
        arm_rows={}
        for arm in protocol['arms']:
            items=sorted([r for r in preds if r['held_generator']==held and r['arm']==arm and r['cohort']=='held_generator_audit'],key=lambda r:r['sample_id'])
            y=np.array([r['label_fake'] for r in items]);s=np.array([r['prob_fake'] for r in items])
            found=next(r for r in results if r['held_generator']==held and r['arm']==arm)
            assert abs(roc_auc_score(y,s)-found['metrics']['held_generator_audit']['auc'])<1e-12
            arm_rows[arm]=items
        ids=[r['sample_id'] for r in arm_rows['semantic']]
        assert all([r['sample_id'] for r in v]==ids for v in arm_rows.values())
        scores={k:np.array([r['prob_fake'] for r in v]) for k,v in arm_rows.items()}
        ref=arm_rows['semantic'];y=np.array([r['label_fake'] for r in ref])
        groups=defaultdict(lambda:defaultdict(list))
        for i,r in enumerate(ref):groups[(r['source'],r['label_fake'])][r['group']].append(i)
        strata=[list(v.values()) for v in groups.values()]
        rng=np.random.default_rng(20260916);deltas={a:[] for a in ['semantic_delta','semantic_velocity']}
        for _ in range(2000):
            draw=np.concatenate([np.concatenate([values[j] for j in rng.integers(0,len(values),len(values))]) for values in strata])
            base=auc(y[draw],scores['semantic'][draw])
            for arm in deltas:deltas[arm].append(auc(y[draw],scores[arm][draw])-base)
        for arm,values in deltas.items():
            comparisons.append({'held_generator':held,'comparison':arm+' - semantic',
                'delta':auc(y,scores[arm])-auc(y,scores['semantic']),
                'paired_source_stratified_ancestor_bootstrap_ci95':np.quantile(values,[.025,.975]).tolist(),
                'replicates':2000,'counts':dict(Counter(r['source'] for r in ref))})
        # Same predeclared grouping and train-only scaler, timing is a diagnostic
        # rather than a fourth proposed detector. Select C on calibration only.
        train=[r for r in manifest if r['source']!=held and r['role']=='fit']
        cal=[r for r in manifest if r['source']!=held and r['role']=='calibration']
        train_groups={r['group'] for r in train};cal_groups={r['group'] for r in cal}
        assert not train_groups & cal_groups
        assert not (train_groups|cal_groups) & {r['group'] for r in ref}
        xf=np.array([[np.log(r['median_dt'])] for r in train]);yf=np.array([r['label_fake'] for r in train])
        xc=np.array([[np.log(r['median_dt'])] for r in cal]);yc=np.array([r['label_fake'] for r in cal])
        xa=np.array([[np.log(r['median_dt'])] for r in ref])
        scaler=StandardScaler().fit(xf);best=None
        mult=Counter(r['group'] for r in train);w=np.array([1/mult[r['group']] for r in train])
        for label in (0,1):w[yf==label]*=len(yf)/2/w[yf==label].sum()
        for c in protocol['C_grid']:
            model=LogisticRegression(C=c,max_iter=300).fit(scaler.transform(xf),yf,sample_weight=w)
            loss=log_loss(yc,model.predict_proba(scaler.transform(xc))[:,1])
            if best is None or loss<best[0]:best=(loss,c,model)
        p=best[2].predict_proba(scaler.transform(xa))[:,1]
        metadata_results.append({'held_generator':held,'timing_only_auc':roc_auc_score(y,p),'selected_C':best[1],
            'timing_median_by_source':{src:float(np.median([r['median_dt'] for r in manifest if r['source']==src])) for src in ['vript','ms','vc2']},
            'interpretation':'High timing-probe AUROC establishes available nuisance information, not that the feature head necessarily uses it.'})
    report={'status':'pass','scope':'mechanical metric replay; not independent scientific verification',
        'source_counts':dict(Counter(r['source'] for r in manifest)),
        'all_selected_fits_converged':all(r['selected_converged'] for r in results),
        'comparisons':comparisons,'timing_probe':metadata_results,
        'formal_claim_released':False,
        'limits':['Bootstrap conditions on fixed heads and observed source/ancestor proxies.',
                  'Temporal arms add features; parameter/representation controls still required.',
                  'One real source; timing and content/source confounding unresolved.']}
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
