"""AL142: content-orthogonalized semantic velocity with causal LIF.

The representation projects each temporal DINO velocity off the per-video
semantic content vector before a causal LIF. It uses no pair ID at inference
and reuses the locked AL140 DINO features, so the only new information is the
nuisance-removal operator and a matched readout comparison.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np
import torch
from torch import nn

SEEDS=[11,23,37,53,71]
FEATURES=Path("/root/autodl-tmp/cvpr27/runs/AL140_dino_snn/output/features.npy")
MANIFEST=Path("/root/autodl-tmp/cvpr27/runs/AL140_dino_snn/output/manifest.jsonl")
EXPECTED_FEATURE_SHA="3c781b55443704d3e022a518601c9b40ce387a9916418bd44717d4e4dda43872"


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()


def split(rows,seed):
    keys=sorted({r["pair_id"] for r in rows})
    rng=np.random.default_rng(seed); rng.shuffle(keys)
    fit=set(keys[:max(1,int(round(.7*len(keys))))])
    return np.asarray([i for i,r in enumerate(rows) if r["pair_id"] in fit]), np.asarray([i for i,r in enumerate(rows) if r["pair_id"] not in fit])


def transform(x,kind,seed):
    if kind=="normal": return x
    if kind=="static": return np.repeat(x[:,:1],x.shape[1],axis=1)
    if kind=="reverse": return x[:,::-1]
    rng=np.random.default_rng(seed); out=x.copy()
    for i in range(len(out)): out[i]=out[i,rng.permutation(out.shape[1])]
    return out


def ortho_velocity(sem):
    v=sem[:,1:]-sem[:,:-1]
    c=sem.mean(axis=1,keepdims=True)
    den=np.maximum((c*c).sum(axis=-1,keepdims=True),1e-8)
    coeff=(v*c).sum(axis=-1,keepdims=True)/den
    return v-coeff*c


class OrthoLIF(nn.Module):
    def __init__(self,dim):
        super().__init__(); self.inp=nn.Linear(dim,64); self.head=nn.Linear(64,1); self.alpha=.82; self.theta=.25
    def forward(self,x):
        u=torch.zeros(x.shape[0],64,device=x.device); states=[]
        for t in range(x.shape[1]):
            z=torch.tanh(self.inp(x[:,t])); v=self.alpha*u+(1-self.alpha)*z
            s=torch.sigmoid(12*(v-self.theta)); u=v-self.theta*s; states.append(s)
        return self.head(torch.stack(states,1).mean(1)).squeeze(-1)


class DenseVelocity(nn.Module):
    def __init__(self,dim):
        super().__init__(); self.net=nn.Sequential(nn.Linear(dim*2,64),nn.GELU(),nn.Linear(64,1))
    def forward(self,x): return self.net(torch.cat([x.mean(1),x.abs().mean(1)],-1)).squeeze(-1)


def auc(y,score):
    y=np.asarray(y,dtype=np.int64); score=np.asarray(score,dtype=np.float64)
    pos=score[y==1]; neg=score[y==0]
    if len(pos)==0 or len(neg)==0:return float("nan")
    order=np.argsort(score,kind="mergesort"); ranks=np.empty(len(score),float); ranks[order]=np.arange(1,len(score)+1)
    vals,first,counts=np.unique(score[order],return_index=True,return_counts=True)
    for f,c in zip(first,counts):
        if c>1:
            idx=order[f:f+c]; ranks[idx]=(2*(f+1)+c-1)/2
    return float((ranks[y==1].sum()-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg)))


def train(model,x,y,idx,seed):
    torch.manual_seed(seed); opt=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4); loss=nn.BCEWithLogitsLoss()
    ids=torch.as_tensor(idx,dtype=torch.long,device=x.device)
    for _ in range(20):
        p=ids[torch.randperm(len(ids),device=x.device)]
        for b in p.split(16):
            opt.zero_grad(set_to_none=True); q=loss(model(x[b]),y[b]); q.backward(); opt.step()


def evaluate(model,sem,mu,sd,test,y,device,kind,ortho,seed):
    s=transform(sem,kind,seed); z=ortho_velocity(s) if ortho else s[:,1:]-s[:,:-1]
    z=(torch.tensor(z,dtype=torch.float32,device=device)-mu)/sd
    with torch.no_grad(): p=torch.sigmoid(model(z)).detach().cpu().numpy()
    return auc(y[test],p[test])


def run(args):
    args.run_dir.mkdir(parents=True,exist_ok=False); start=time.time()
    if sha(FEATURES)!=EXPECTED_FEATURE_SHA: raise RuntimeError("locked AL140 features hash changed")
    rows=[json.loads(x) for x in MANIFEST.read_text(encoding="utf-8").splitlines() if x.strip()]
    features=np.load(FEATURES,allow_pickle=False).astype(np.float32)
    if len(rows)!=len(features) or len(rows)!=122: raise RuntimeError("feature_manifest_shape_contract")
    np.save(args.run_dir/"features.npy",features)
    sem=features/np.maximum(np.linalg.norm(features,axis=-1,keepdims=True),1e-12)
    y_np=np.asarray([int(r["label_fake"]) for r in rows],dtype=np.float32)
    y=torch.tensor(y_np,dtype=torch.float32,device="cuda")
    v=sem[:,1:]-sem[:,:-1]; o=ortho_velocity(sem)
    v_t=torch.tensor(v,dtype=torch.float32,device="cuda"); o_t=torch.tensor(o,dtype=torch.float32,device="cuda")
    recs=[]; paired=[]
    for seed in SEEDS:
        train_idx,test=split(rows,seed)
        mu_v=torch.tensor(v[train_idx].mean((0,1),keepdims=True),device="cuda"); sd_v=torch.tensor(v[train_idx].std((0,1),keepdims=True).clip(min=1e-4),device="cuda")
        mu_o=torch.tensor(o[train_idx].mean((0,1),keepdims=True),device="cuda"); sd_o=torch.tensor(o[train_idx].std((0,1),keepdims=True).clip(min=1e-4),device="cuda")
        vn=(v_t-mu_v)/sd_v; on=(o_t-mu_o)/sd_o
        raw=DenseVelocity(v.shape[-1]).cuda(); train(raw,vn,y,train_idx,seed)
        ort=DenseVelocity(o.shape[-1]).cuda(); train(ort,on,y,train_idx,seed)
        cand=OrthoLIF(o.shape[-1]).cuda(); train(cand,on,y,train_idx,seed)
        br={"seed":seed,"model":"dense_raw_velocity"}
        bo={"seed":seed,"model":"dense_orthogonal_velocity"}
        bc={"seed":seed,"model":"ortho_velocity_lif"}
        for kind in ("normal","static","shuffle","reverse"):
            br["auc_"+kind]=evaluate(raw,sem,mu_v,sd_v,test,y_np,"cuda",kind,False,seed)
            bo["auc_"+kind]=evaluate(ort,sem,mu_o,sd_o,test,y_np,"cuda",kind,True,seed)
            bc["auc_"+kind]=evaluate(cand,sem,mu_o,sd_o,test,y_np,"cuda",kind,True,seed)
        recs.extend([br,bo,bc])
        strongest=max(br["auc_normal"],bo["auc_normal"])
        paired.append({"seed":seed,"candidate_auc":bc["auc_normal"],"strongest_baseline_auc":strongest,"delta":bc["auc_normal"]-strongest})
    (args.run_dir/"results.json").write_text(json.dumps({"rows":recs},indent=2),encoding="utf-8")
    ds=np.asarray([r["delta"] for r in paired],float); mean=float(ds.mean()); se=float(ds.std(ddof=1)/np.sqrt(len(ds))); ci=[mean-2.776*se,mean+2.776*se]
    summary={"paired":paired,"mean_delta":mean,"descriptive_95_ci":ci,"positive_seed_count":int((ds>0).sum()),"n_seeds":len(ds),"pair_count":len({r["pair_id"] for r in rows}),"status":"no_go_ortho_velocity_lif_pilot_gate","formal_gate":False,"input_feature_sha256":EXPECTED_FEATURE_SHA,"source_manifest_sha256":sha(MANIFEST)}
    (args.run_dir/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    meta={"finished_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"elapsed_seconds":time.time()-start,"torch":torch.__version__,"cuda":torch.cuda.is_available(),"device":"cuda:0","seeds":SEEDS,"contract":"DINO semantic velocity projected orthogonal to per-video content mean; no pair ID at inference"}
    (args.run_dir/"launch_metadata.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    hashes={p.name:sha(p) for p in args.run_dir.iterdir() if p.is_file()}; hashes["source_script_sha256"]=sha(Path(__file__)); hashes["input_feature_sha256"]=EXPECTED_FEATURE_SHA; hashes["source_manifest_sha256"]=sha(MANIFEST)
    (args.run_dir/"artifact_hashes.json").write_text(json.dumps(hashes,indent=2),encoding="utf-8"); print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--run-dir",type=Path,required=True); ap.add_argument("--device",default="cuda:0"); args=ap.parse_args(); run(args)
