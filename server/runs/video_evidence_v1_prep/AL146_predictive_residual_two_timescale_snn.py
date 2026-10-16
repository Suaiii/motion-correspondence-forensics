"""AL146: causal predictive-residual two-timescale signed-event SNN.

The only candidate change is a causal residual event encoder followed by two
fixed leaky traces.  All controls recompute the encoder after transforming the
same locked DINO sequence.  No pair ID enters inference.
"""
from __future__ import annotations
import argparse, hashlib, json, os, time, importlib.util
from pathlib import Path
import numpy as np

SEEDS=(11,23,37,53,71); ALPHA_FAST=.65; ALPHA_SLOW=.95; MAD_K=3.0

def sha(p):
    h=hashlib.sha256();
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def auc(y,s):
    y=np.asarray(y); s=np.asarray(s,float); pos=s[y==1]; neg=s[y==0]
    if not len(pos) or not len(neg): return float('nan')
    order=np.argsort(s,kind='mergesort'); ranks=np.empty(len(s)); ranks[order]=np.arange(1,len(s)+1)
    vals,first,counts=np.unique(s[order],return_index=True,return_counts=True)
    for f,c in zip(first,counts):
        if c>1: ranks[order[f:f+c]]=(2*(f+1)+c-1)/2
    return float((ranks[y==1].sum()-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg)))
def transform(x,kind,seed):
    if kind=='normal': return x
    if kind=='static': return np.repeat(x[:,:1],x.shape[1],axis=1)
    if kind=='reverse': return x[:,::-1]
    out=x.copy(); rng=np.random.default_rng(seed)
    for i in range(len(out)): out[i]=out[i,rng.permutation(out.shape[1])]
    return out
def residual_events(z,median,mad):
    r=np.zeros_like(z); r[:,0]=0
    for t in range(1,z.shape[1]):
        pred=z[:,t-1] if t==1 else z[:,t-1]+.5*(z[:,t-1]-z[:,t-2])
        r[:,t]=z[:,t]-pred
    fast=np.zeros_like(r); slow=np.zeros_like(r)
    for t in range(1,z.shape[1]):
        fast[:,t]=ALPHA_FAST*fast[:,t-1]+(1-ALPHA_FAST)*r[:,t]
        slow[:,t]=ALPHA_SLOW*slow[:,t-1]+(1-ALPHA_SLOW)*r[:,t]
    d=fast-slow; scale=np.maximum(mad,1e-6); return np.sign(d)*((np.abs(d)>MAD_K*scale).astype(np.float32))
def dense_scores(z,y,fit,cal,rows):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    v=np.abs(np.diff(z,axis=1))
    dt=np.asarray([np.diff(np.asarray(r['ffprobe']['pts'],dtype=np.float64)[(len(r['ffprobe']['pts'])-8)//2:(len(r['ffprobe']['pts'])-8)//2+8]) for r in rows],dtype=np.float64)
    if dt.shape != (len(rows),7) or not np.isfinite(dt).all() or np.any(dt <= 0):
        raise ValueError('invalid native PTS intervals for dense baseline')
    x=np.concatenate([z.mean(1),v.mean(1),(v/dt[:,:,None]).mean(1)],1)
    sc=StandardScaler().fit(x[fit]); xx=sc.transform(x); best=None
    for c in (.1,1.,10.):
        m=LogisticRegression(C=c,max_iter=500,class_weight='balanced',solver='lbfgs').fit(xx[fit],y[fit]); loss=float(-(y[cal]*np.log(np.clip(m.predict_proba(xx[cal])[:,1],1e-8,1-1e-8))+(1-y[cal])*np.log(np.clip(1-m.predict_proba(xx[cal])[:,1],1e-8,1-1e-8))).mean())
        if best is None or loss<best[0]: best=(loss,m)
    return best[1].predict_proba(xx)[:,1]
def fit_snn(events,y,fit,seed,torch,nn):
    torch.manual_seed(seed); device='cuda' if torch.cuda.is_available() else 'cpu'; x=torch.tensor(events,dtype=torch.float32,device=device); yt=torch.tensor(y,dtype=torch.float32,device=device)
    net=nn.Linear(events.shape[-1],64).to(device); head=nn.Linear(64,1).to(device); opt=torch.optim.AdamW(list(net.parameters())+list(head.parameters()),lr=2e-3,weight_decay=1e-4); ids=torch.tensor(np.flatnonzero(fit),device=device)
    for _ in range(30):
        order=ids[torch.randperm(len(ids),device=device)]
        for b in order.split(32):
            opt.zero_grad(set_to_none=True); fast=torch.zeros(len(b),64,device=device); slow=torch.zeros_like(fast); out=[]
            for t in range(x.shape[1]):
                q=torch.tanh(net(x[b,t])); fast=ALPHA_FAST*fast+(1-ALPHA_FAST)*q; slow=ALPHA_SLOW*slow+(1-ALPHA_SLOW)*q; out.append(fast-slow)
            loss=torch.nn.functional.binary_cross_entropy_with_logits(head(torch.stack(out,1).mean(1)).squeeze(-1),yt[b]); loss.backward(); opt.step()
    return net, head, device
def predict_snn(events,model,torch):
    net, head, device = model
    x=torch.tensor(events,dtype=torch.float32,device=device)
    with torch.no_grad():
        fast=torch.zeros(len(x),64,device=device); slow=torch.zeros_like(fast); out=[]
        for t in range(x.shape[1]):
            q=torch.tanh(net(x[:,t])); fast=ALPHA_FAST*fast+(1-ALPHA_FAST)*q; slow=ALPHA_SLOW*slow+(1-ALPHA_SLOW)*q; out.append(fast-slow)
        return torch.sigmoid(head(torch.stack(out,1).mean(1)).squeeze(-1)).cpu().numpy()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--selection',type=Path,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--features',type=Path,required=True); ap.add_argument('--run-dir',type=Path,required=True); ap.add_argument('--device',default='cuda'); a=ap.parse_args()
    import torch; from torch import nn
    adapter_path=Path(__file__).with_name('video_evidence_dense_adapter.py')
    spec=importlib.util.spec_from_file_location('video_evidence_dense_adapter',adapter_path); adapter=importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    contract=adapter.verify_contract(a.selection,a.manifest)
    selection_obj=read(a.selection); rows=selection_obj['rows']; role=np.array([r['selection_role'] for r in rows]); y=np.array([r['label_fake'] for r in rows],int); fit=role=='fit'; cal=role=='calibration'
    feature_lock=a.features/'lock.json'
    if not feature_lock.exists(): raise RuntimeError('missing feature lock')
    lock=read(feature_lock)
    if lock.get('selection_sha256') != sha(a.selection): raise RuntimeError('feature lock selection hash mismatch')
    if lock.get('manifest_sha256') != selection_obj.get('manifest_sha256'): raise RuntimeError('feature lock manifest hash mismatch')
    if lock.get('model') != 'dinov2_vitb14': raise RuntimeError('unexpected feature model')
    records=[]
    for r in rows:
        key=hashlib.sha256(r['sample_id'].encode()).hexdigest(); rec=read(a.features/'records'/f'{key}.json');
        if rec.get('status')!='ok': raise RuntimeError('feature record is not ok: '+r['sample_id'])
        if rec.get('selection_role') != r.get('selection_role') or rec.get('sha256') != r.get('sha256'):
            raise RuntimeError('feature record selection/hash mismatch: '+r['sample_id'])
        p=a.features/rec['feature_file'];
        if sha(p)!=rec['feature_sha256']: raise RuntimeError('feature hash changed: '+r['sample_id'])
        z=np.load(p,allow_pickle=False).astype(np.float32); 
        if z.shape!=(8,768): raise RuntimeError('expected [8,768] feature shape')
        records.append(z/np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12))
    sem=np.asarray(records); a.run_dir.mkdir(parents=True,exist_ok=False); results=[]; paired=[]
    for seed in SEEDS:
        rec={'seed':seed,'candidate_auc':{},'dense_auc':{},'delta':{}}
        normal=transform(sem,'normal',seed); flat=normal[fit].reshape(-1,normal.shape[-1]); median=np.median(flat,axis=0); mad=np.median(np.abs(flat-median),axis=0)*1.4826
        normal_events=residual_events(normal,median,mad); snn_model=fit_snn(normal_events,y,fit,seed,torch,nn)
        for kind in ('normal','static','shuffle','reverse'):
            zz=transform(sem,kind,seed); ff=zz[fit].reshape(-1,zz.shape[-1]); med=np.median(ff,axis=0); mm=np.median(np.abs(ff-med),axis=0)*1.4826; ee=residual_events(zz,med,mm); ss=predict_snn(ee,snn_model,torch); dd=dense_scores(zz,y,fit,cal,rows); 
            for cohort in ('in_domain_audit','held_generator_audit','external_holdout'):
                m=role==cohort; rec['candidate_auc'][f'{kind}:{cohort}']=auc(y[m],ss[m]); rec['dense_auc'][f'{kind}:{cohort}']=auc(y[m],dd[m]); rec['delta'][f'{kind}:{cohort}']=rec['candidate_auc'][f'{kind}:{cohort}']-rec['dense_auc'][f'{kind}:{cohort}']
        results.append(rec); paired.append(rec['delta']['normal:external_holdout'])
    d=np.asarray(paired,float); mean=float(d.mean()); se=float(d.std(ddof=1)/np.sqrt(len(d))); ci=[mean-2.776*se,mean+2.776*se]; summary={'candidate':'causal_predictive_residual_two_timescale_snn','seeds':list(SEEDS),'alpha_fast':ALPHA_FAST,'alpha_slow':ALPHA_SLOW,'median_mad_threshold':MAD_K,'paired_external_delta':paired,'mean_delta':mean,'descriptive_95_ci':ci,'positive_seed_count':int((d>0).sum()),'formal_gate_passed':False,'results':results,'scope':'AAGenvid fit/calibration; AEGIS untouched external holdout; controls recomputed'}
    summary['selection_sha256']=sha(a.selection); summary['manifest_sha256']=sha(a.manifest); summary['feature_lock_sha256']=sha(feature_lock); summary['adapter_sha256']=sha(adapter_path)
    (a.run_dir/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    receipt={'selection_sha256':summary['selection_sha256'],'manifest_sha256':summary['manifest_sha256'],'feature_lock_sha256':summary['feature_lock_sha256'],'adapter_sha256':summary['adapter_sha256'],'script_sha256':sha(Path(__file__)),'contract':contract,'formal_gate_passed':False}
    (a.run_dir/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf8'); print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__': main()
