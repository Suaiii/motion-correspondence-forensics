"""Full available-cache exploratory baseline with group-disjoint generator holdout.

Not the formal mechanism pipeline: preserves native16 timing, pending licences
and ancestry. Never opens a final set or releases a downstream training gate.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.preprocessing import StandardScaler
import sklearn


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def save(p, v):
    tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(v, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(tmp,p)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args(); start=time.monotonic()
    root=a.output; root.mkdir(parents=True,exist_ok=False)
    dirs=[a.base/'runs/overnight_20260911'/s for s in ['gpu_dino_v1','vript_dino_group1746_v1']]
    locks=[read(d/'lock.json') for d in dirs]
    assert locks[0]['weights_sha256']==locks[1]['weights_sha256']
    assert locks[0]['decode_sha256']==locks[1]['decoder_sha256']
    assert locks[0]['repo_commit']==locks[1]['model_revision']
    exclusion_path=a.base/'releases/v0.1.3/cvpr27-server/configs/historical_exclusions.json'
    exclusions=set(read(exclusion_path)['sha256'])
    protocol={'scope':'exposed native16 cache exploratory baseline; not confirmatory',
              'C_grid':[0.1,1.0,10.0], 'selection':'calibration BCE only; smallest C wins ties',
              'holdouts':['ms','vc2'],'split_seed':'dino-cached-baseline-v1',
              'arms':['semantic','semantic_delta','semantic_velocity'],
              'split':'sha256(group) 60/20/20; shared fake UUID and real original prefix grouped',
              'weights':'balanced class and, within class, inverse ancestor multiplicity',
              'limits':{'seconds':900,'cpu_threads':4},'final_access':False,
              'input_lock_hashes':{str(d):sha(d/'lock.json') for d in dirs},
              'historical_exclusion_sha256':sha(exclusion_path),'script_sha256':sha(__file__),
              'limitations':['one real source only','native16 physical time varies by source',
                             'ancestor IDs inferred from filenames, not fully verified',
                             'earlier exposed assets; no new final confirmation',
                             'no claim that derivative scaling proves invariance or novelty'],
              'sklearn':sklearn.__version__,'numpy':np.__version__}
    save(root/'protocol.json',protocol)
    def deadline():
        if time.monotonic()-start>900: raise TimeoutError('Bounded baseline time exhausted')
    rows=[]; vectors=[]; rejected=[]; hashes={}
    for d in dirs:
        for p in sorted((d/'records').glob('*.json')):
            deadline(); r=read(p)
            if r['status']!='ok':
                rejected.append({'record':str(p),'reason':r.get('reason',r['status'])});continue
            if r['sha256'] in exclusions:
                rejected.append({'record':str(p),'reason':'historical_exact_hash'});continue
            source=r['source']; label=0 if source=='vript' else 1
            assert source in ('vript','ms','vc2')
            feature=d/r['feature_file']
            if sha(feature)!=r['feature_sha256']:raise ValueError('Feature changed: '+str(feature))
            z=np.load(feature,allow_pickle=False).astype(np.float64)
            pts=np.asarray(r['sampling']['pts']); dt=np.diff(pts)
            assert z.shape==(16,768) and pts.shape==(16,)
            assert np.isfinite(z).all() and np.isfinite(dt).all() and (dt>0).all()
            sid=r['sample_id']; name=Path(sid).stem
            if source=='vript':
                group='real:'+re.sub(r'-Scene-\d+$','',name)
            else:
                matched=re.search(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',name)
                if not matched:raise ValueError('Missing fake ancestor proxy: '+sid)
                group='fake:'+matched[0]
            # Per-frame unit normalization shared across all arms.
            z=z/np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)
            semantic=z.mean(0); delta=np.abs(np.diff(z,axis=0))
            value=int(hashlib.sha256((protocol['split_seed']+group).encode()).hexdigest()[:8],16)/2**32
            role='fit' if value<.6 else 'calibration' if value<.8 else 'audit'
            rows.append({'sample_id':sid,'source':source,'label_fake':label,'group':group,'role':role,
                         'sha256':r['sha256'],'feature_sha256':r['feature_sha256'],'record_sha256':sha(p),
                         'feature_file':str(feature),'median_dt':float(np.median(dt))})
            vectors.append(np.r_[semantic,delta.mean(0),(delta/dt[:,None]).mean(0)])
            hashes[r['sha256']]=hashes.get(r['sha256'],0)+1
            if len(rows)%2000==0:print('validated features',len(rows),flush=True)
    keep=[i for i,r in enumerate(rows) if hashes[r['sha256']]==1]
    duplicate_removed=len(rows)-len(keep)
    x=np.asarray(vectors,dtype=np.float32)[keep]; rows=[rows[i] for i in keep]; del vectors
    save(root/'manifest.json',rows); save(root/'exclusions.json',rejected)
    save(root/'cache_audit.json',{'rows':len(rows),'duplicate_rows_removed':duplicate_removed,
                                'source_counts':dict(Counter(r['source'] for r in rows))})
    y=np.array([r['label_fake'] for r in rows]); source=np.array([r['source'] for r in rows]); role=np.array([r['role'] for r in rows])
    cols={'semantic':np.arange(768),'semantic_delta':np.arange(1536),
          'semantic_velocity':np.r_[np.arange(768),np.arange(1536,2304)]}
    results=[]; predictions=[]; models={}
    for held in protocol['holdouts']:
        train_source='vc2' if held=='ms' else 'ms'
        masks={'fit':(role=='fit')&(source!=held),'calibration':(role=='calibration')&(source!=held),
               'in_domain_audit':(role=='audit')&(source!=held),
               'held_generator_audit':(role=='audit')&((source==held)|(source=='vript'))}
        groups={k:{rows[i]['group'] for i in np.flatnonzero(v)} for k,v in masks.items()}
        assert not groups['fit'] & (groups['calibration']|groups['in_domain_audit']|groups['held_generator_audit'])
        assert not groups['calibration'] & (groups['in_domain_audit']|groups['held_generator_audit'])
        weights=np.zeros(len(rows)); fit=masks['fit']; cal=masks['calibration']
        multiplicity=Counter(rows[i]['group'] for i in np.flatnonzero(fit))
        for i in np.flatnonzero(fit):weights[i]=1/multiplicity[rows[i]['group']]
        for label in (0,1):
            m=fit&(y==label);weights[m]*=fit.sum()/2/weights[m].sum()
        for arm,columns in cols.items():
            deadline(); data=x[:,columns]; scaler=StandardScaler().fit(data[fit]); data=scaler.transform(data)
            best=None; trials=[]
            for c in protocol['C_grid']:
                deadline(); model=LogisticRegression(C=c,max_iter=300,solver='lbfgs').fit(data[fit],y[fit],sample_weight=weights[fit])
                score=float(log_loss(y[cal],model.predict_proba(data[cal])[:,1]))
                converged=bool(model.n_iter_.max()<300)
                trials.append({'C':c,'calibration_bce':score,'converged':converged})
                if best is None or score<best[0]:best=(score,c,model,converged)
            loss,c,model,converged=best
            record={'held_generator':held,'fit_generator':train_source,'arm':arm,'selected_C':c,
                    'selected_converged':converged,'trials':trials,'metrics':{}}
            for cohort,mask in masks.items():
                prob=model.predict_proba(data[mask])[:,1]
                record['metrics'][cohort]={'n':int(mask.sum()),'auc':float(roc_auc_score(y[mask],prob)),
                                         'bce':float(log_loss(y[mask],prob))}
                if 'audit' in cohort:
                    for i,v in zip(np.flatnonzero(mask),prob):
                        predictions.append({**rows[i],'held_generator':held,'arm':arm,'cohort':cohort,'prob_fake':float(v)})
            results.append(record)
            models[held+'/'+arm]={'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
                                 'coef':model.coef_.tolist(),'intercept':model.intercept_.tolist()}
            save(root/'progress.json',{'completed_arms':len(results),'total_arms':6,'seconds':time.monotonic()-start})
            save(root/'results_partial.json',results)
            print(held,arm,record['metrics']['held_generator_audit'],flush=True)
    save(root/'predictions.json',predictions);save(root/'models.json',models)
    save(root/'results.json',{'complete':True,'scope':protocol['scope'],'formal_gate_passed':False,
                            'results':results,'wall_seconds':time.monotonic()-start})
    save(root/'artifact_hashes.json',{p.name:sha(p) for p in root.iterdir() if p.is_file()})
    print('COMPLETE',time.monotonic()-start,flush=True)


if __name__=='__main__':
    main()
