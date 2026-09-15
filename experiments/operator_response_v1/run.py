"""P2C: controlled correspondence response, frozen on legacy cache only."""
import hashlib,json,time
from pathlib import Path
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT=Path(__file__).resolve().parents[2]; SRC=ROOT/'research-runs/alignment_gate_v1'; OUT=ROOT/'research-runs/operator_response_v1_20260914'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def features(a,b,c,tau=1e-3):
    # a=correct, b/c=matched controls; preserve signed residual before robust magnitude.
    aa=np.abs(np.asarray(a,dtype=np.float32)); bb=np.abs(np.asarray(b,dtype=np.float32)); cc=np.abs(np.asarray(c,dtype=np.float32))
    ctl=np.stack([bb,cc],axis=0); med=np.median(ctl,axis=0); mad=np.median(np.abs(ctl-med),axis=0)
    r=(med-aa)/(mad+tau); valid=np.isfinite(r)
    if not valid.all(): raise ValueError('nonfinite response')
    # time/channel pooled, plus temporal consistency and positive-response mass
    x=r.reshape(r.shape[0],-1); absx=np.abs(x)
    return np.array([r.mean(),r.std(),np.quantile(r,.05),np.quantile(r,.5),np.quantile(r,.95),
                     (r>0).mean(),x.mean(1).std(),absx.mean(1).std(),
                     np.quantile(absx,.95),np.mean(np.abs(a),dtype=np.float32),
                     np.mean(np.abs(b),dtype=np.float32),np.mean(np.abs(c),dtype=np.float32)],dtype=np.float32)
def main():
    if OUT.exists(): raise FileExistsError('Preserve existing operator run')
    OUT.mkdir(parents=True); started=time.time()
    manifest=json.loads((SRC/'manifest.json').read_text(encoding='utf-8')); n=len(manifest)
    cfg={'id':'operator_response_v1','cache':str(SRC/'cache'),'tau':1e-3,'arms':['correct','wrong_integer','fractional'],
         'legacy_sampling':'4fps/8frames/128px','scope':'legacy development diagnostic; no external selection',
         'selection':'fit-only LR, C chosen on calibration AUROC','source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [SRC/'manifest.json',SRC/'protocol.json']}}
    arr={k:np.load(SRC/f'cache/clean__{k}.npy',mmap_mode='r') for k in cfg['arms']}
    X=np.empty((n,12),np.float32)
    for i in range(n): X[i]=features(arr['correct'][i],arr['wrong_integer'][i],arr['fractional'][i])
    y=np.array([r['label_fake'] for r in manifest]); roles=np.array([r['role'] for r in manifest]); src=np.array([r['source'] for r in manifest])
    fit,cal,aud=[roles==z for z in ['fit','calibration','audit']]
    grid=[.001,.003,.01,.03,.1,.3,1,3,10,30,100]; trials=[]
    for C in grid:
        m=make_pipeline(StandardScaler(),LogisticRegression(C=C,max_iter=3000,random_state=17)).fit(X[fit],y[fit]); trials.append({'C':C,'calibration_auc':roc_auc_score(y[cal],m.predict_proba(X[cal])[:,1])})
    best=max(trials,key=lambda z:z['calibration_auc']); m=make_pipeline(StandardScaler(),LogisticRegression(C=best['C'],max_iter=3000,random_state=17)).fit(X[fit],y[fit]); p=m.predict_proba(X)[:,1]
    results={'overall':{'fit':roc_auc_score(y[fit],p[fit]),'calibration':roc_auc_score(y[cal],p[cal]),'audit':roc_auc_score(y[aud],p[aud])},'by_source':{}}
    for s in sorted(set(src)):
        ix=aud&(src==s)
        if len(set(y[ix]))>1: results['by_source'][s]={'n':int(ix.sum()),'auc':roc_auc_score(y[ix],p[ix])}
    np.save(OUT/'operator_features.npy',X); np.save(OUT/'scores.npy',p)
    (OUT/'protocol.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    (OUT/'results.json').write_text(json.dumps({'protocol':cfg,'selection':{'trials':trials,'selected':best},'results':results,'n':n,'wall_seconds':time.time()-started},indent=2)+'\n',encoding='utf-8')
    (OUT/'manifest_lock.json').write_text(json.dumps({'manifest_sha256':sha(SRC/'manifest.json'),'protocol_sha256':sha(SRC/'protocol.json'),'feature_sha256':sha(OUT/'operator_features.npy'),'score_sha256':sha(OUT/'scores.npy')},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,indent=2))
if __name__=='__main__': main()
