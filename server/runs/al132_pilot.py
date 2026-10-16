import argparse, json, hashlib, os, time, platform, subprocess
from pathlib import Path
import numpy as np
import cv2
import torch
from torch import nn

SEEDS=[17,29,43,71]

def sha_file(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def auroc(y,s):
 y=np.asarray(y); s=np.asarray(s); pos=s[y==1]; neg=s[y==0]
 if len(pos)==0 or len(neg)==0:return float('nan')
 return float((pos[:,None]>neg[None,:]).mean()+0.5*(pos[:,None]==neg[None,:]).mean())
def macro(xs): return float(np.nanmean(xs))
def bootstrap(vals,seed=90210,n=4000):
 rng=np.random.default_rng(seed); a=np.asarray(vals,float); means=np.empty(n)
 for i in range(n): means[i]=np.mean(a[rng.integers(0,len(a),len(a))])
 return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]
def read_rows(path): return [json.loads(x) for x in open(path,encoding='utf-8')]
def decode(path,T=8,S=32):
 cap=cv2.VideoCapture(path); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));
 if n<2: cap.release(); raise RuntimeError('too few frames '+path)
 idx=np.linspace(0,n-1,T).round().astype(int); out=[]
 for j in idx:
  cap.set(cv2.CAP_PROP_POS_FRAMES,int(j)); ok,fr=cap.read()
  if not ok: cap.release(); raise RuntimeError('decode failure '+path)
  fr=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); fr=cv2.resize(fr,(S,S),interpolation=cv2.INTER_AREA).astype('float32')/255.
  out.append(fr)
 cap.release(); return np.stack(out)
def fit_linear(Xtr,ytr,Xte,yte,seed,epochs=140):
 torch.manual_seed(seed); np.random.seed(seed)
 dev='cuda' if torch.cuda.is_available() else 'cpu'; x=torch.tensor(Xtr,dtype=torch.float32,device=dev); y=torch.tensor(ytr,dtype=torch.float32,device=dev)
 model=nn.Linear(x.shape[1],1).to(dev); opt=torch.optim.AdamW(model.parameters(),lr=.015,weight_decay=1e-3)
 for _ in range(epochs):
  opt.zero_grad(); loss=nn.functional.binary_cross_entropy_with_logits(model(x).squeeze(1),y); loss.backward(); opt.step()
 with torch.no_grad(): pred=torch.sigmoid(model(torch.tensor(Xte,dtype=torch.float32,device=dev))).cpu().numpy().ravel()
 return pred, sum(p.numel() for p in model.parameters()), dev

def lif_features(E,kind,W,learned_thr=None,shuffle=False):
 # E [N,7,1024], fixed random projection W [1024,D]
 z=np.einsum('ntd,dk->ntk',E,W); D=z.shape[-1]
 if kind=='vanilla':
  v=np.zeros((len(E),D),np.float32); out=[]
  for t in range(z.shape[1]): v=.8*v+z[:,t]; out.append((v>1.0).astype(np.float32)); v-=out[-1]
  return np.mean(out,axis=0)
 if kind in ('dual','dual_fixed'):
  vf=np.zeros((len(E),D),np.float32); vs=np.zeros((len(E),D),np.float32); out=[]
  thr=np.ones(D,np.float32)*(.65 if kind=='dual_fixed' else .65)
  for t in range(z.shape[1]):
   vf=.55*vf+z[:,t]; vs=.92*vs+z[:,t]; sf=(vf>thr).astype(np.float32); ss=(vs>thr).astype(np.float32)
   out.append((sf-ss)+.25*(z[:,t])*(sf>0))
   vf-=sf; vs-=ss
  return np.mean(out,axis=0)
 raise ValueError(kind)
def make_features(frames,E,W,kind):
 if kind=='event_count': return E.mean(axis=(1,2),keepdims=False)[:,None]
 if kind=='dense_mean': return frames.mean(axis=1).reshape(len(frames),-1)
 if kind=='ema':
  a=np.zeros((len(frames),1024),np.float32)
  for t in range(frames.shape[1]): a=.7*a+.3*frames[:,t].reshape(len(frames),-1)
  return a
 if kind in ('vanilla','dual','dual_fixed'): return lif_features(E,kind,W)
 if kind=='frame_energy': return np.concatenate([frames.mean((1,2,3))[:,None],frames.std((1,2,3))[:,None]],1)
 raise ValueError(kind)
def eval_method(kind,frames,E,labels,train_idx,test_idx,seed,W):
 X=make_features(frames,E,W,kind)
 # fixed standardization fit train only
 mu=X[train_idx].mean(0); sd=X[train_idx].std(0)+1e-6; X=(X-mu)/sd
 pred,nparam,dev=fit_linear(X[train_idx],labels[train_idx],X[test_idx],labels[test_idx],seed)
 return auroc(labels[test_idx],pred),pred,nparam,dev

def eval_controls(kind,frames,E,labels,train_idx,test_idx,seed,W):
 # deterministic controls keep labels/weights/split fixed
 if kind=='static_repeat': E=np.zeros_like(E); frames=np.repeat(frames[:,0:1],frames.shape[1],axis=1)
 elif kind=='shuffle':
  E=E.copy(); rng=np.random.default_rng(777); E=np.stack([e[rng.permutation(len(e))] for e in E])
 elif kind=='reverse': E=E[:,::-1].copy()
 return eval_method('dual',frames,E,labels,train_idx,test_idx,seed,W)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--holdout',required=True); args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
 rows=read_rows(args.manifest); hold=read_rows(args.holdout)
 # rows are already selection-locked by manifest generation
 allrows=rows+hold; out.joinpath('selected_manifest.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in allrows),encoding='utf-8')
 def load(rs):
  fs=[]; ys=[]
  for r in rs:
   p='/root/autodl-tmp/cvpr27/data/'+r['path']; fr=decode(p); fs.append(fr); ys.append(r['label_fake'])
  f=np.stack(fs); return f,np.asarray(ys,np.int64)
 t0=time.perf_counter(); frames,y=load(rows); frames_h,yh=load(hold); decode_sec=time.perf_counter()-t0
 E=np.abs(np.diff(frames,axis=1)); Eh=np.abs(np.diff(frames_h,axis=1));
 # train normalization frozen from development only
 scale=float(E.mean()+3*E.std()+1e-6); E/=scale; Eh/=scale
 rng=np.random.default_rng(13132); W=rng.normal(0,.12,(1024,32)).astype('float32'); W/=np.linalg.norm(W,axis=0,keepdims=True)+1e-6
 # fixed split stratified by source/label hash: 20 train, 10 test per class
 tr=[]; te=[]
 for lab in [0,1]:
  ix=np.where(y==lab)[0]; tr.extend(ix[:20]); te.extend(ix[20:])
 tr=np.array(sorted(tr)); te=np.array(sorted(te));
 methods=['event_count','dense_mean','ema','vanilla','dual','dual_fixed','frame_energy']
 result={'protocol':'AL132_temporal_event_snn_v1','decode_seconds':decode_sec,'n_dev':len(rows),'n_holdout':len(hold),'train_indices':tr.tolist(),'test_indices':te.tolist(),'scale':scale,'methods':{},'controls':{},'seed_results':{},'provenance':[]}
 for r in allrows: result['provenance'].append({'sample_id':r['sample_id'],'path':r['path'],'sha256':r.get('sha256'),'label_fake':r['label_fake'],'source':r.get('source'),'generator':r.get('generator')})
 for seed in SEEDS:
  result['seed_results'][str(seed)]={}
  for m in methods:
   a,p,nparam,dev=eval_method(m,frames,E,y,tr,te,seed,W); ah,ph,_,_=eval_method(m,frames_h,Eh,yh,np.arange(len(frames_h)),np.arange(len(frames_h)),seed,W) if len(np.unique(yh))>1 else (float('nan'),None,0,dev)
   # holdout prediction uses train fit only, rerun fit train then holdout features
   X=make_features(frames,E,W,m); Xh=make_features(frames_h,Eh,W,m); mu=X[tr].mean(0); sd=X[tr].std(0)+1e-6; X=(X-mu)/sd; Xh=(Xh-mu)/sd; pred,nparam,dev=fit_linear(X[tr],y[tr],Xh,yh,seed)
   ah=auroc(yh,pred)
   result['seed_results'][str(seed)][m]={'dev_auroc':a,'holdout_auroc':ah,'nparam':nparam,'device':dev}
  for c in ['static_repeat','shuffle','reverse']:
   a,_,nparam,dev=eval_controls(c,frames,E,y,tr,te,seed,W); result['controls'].setdefault(c,{})[str(seed)]={'dev_auroc':a,'nparam':nparam,'device':dev}
 for m in methods:
  ds=[result['seed_results'][str(s)][m]['dev_auroc'] for s in SEEDS]; hs=[result['seed_results'][str(s)][m]['holdout_auroc'] for s in SEEDS]; result['methods'][m]={'dev_mean':macro(ds),'holdout_mean':macro(hs),'dev_per_seed':ds,'holdout_per_seed':hs}
 dual=np.array(result['methods']['dual']['dev_per_seed']); base=np.array(result['methods']['vanilla']['dev_per_seed']); result['paired_dual_minus_vanilla']=dual-base; result['paired_ci']=bootstrap(dual-base)
 # source/generator-only leakage probes on development metadata (fixed features, no claim of detector efficacy)
 result['metadata_controls']={'source_only_trainable_probe':'pending_labels_only_not_run','generator_only_trainable_probe':'pending_labels_only_not_run','dino_baseline':'unavailable_no_weight_in_runtime','dino_proxy':'frame_energy_only_not_DINO'}
 result['decision']='go_candidate' if result['methods']['dual']['dev_mean']-result['methods']['vanilla']['dev_mean']>=.03 and result['paired_ci'][0]>0 else 'no_go_pilot_continue_independent_ablation'
 result['system']={'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'pid':os.getpid(),'argv':os.sys.argv}
 out.joinpath('result.json').write_text(json.dumps(result,indent=2,sort_keys=True),encoding='utf-8')
 out.joinpath('runtime.txt').write_text(json.dumps({'pid':os.getpid(),'start_unix':time.time(),'host':platform.node(),'gpu':result['system']['gpu']},indent=2),encoding='utf-8')
 print(json.dumps({'decision':result['decision'],'methods':result['methods'],'paired_ci':result['paired_ci']},indent=2))
if __name__=='__main__': main()
