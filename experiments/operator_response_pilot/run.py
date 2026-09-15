import json, random, sys
from pathlib import Path
import numpy as np, torch
from sklearn.metrics import roc_auc_score

ROOT=Path(__file__).resolve().parents[2]; CACHE=ROOT/'research-runs/alignment_gate_v1/cache'; RUN=ROOT/'research-runs/operator_response_pilot_20260916'
sys.path.insert(0,str(ROOT/'research-runtime/server'))
from forensics.model import Bag, ResponseBag

def main():
 if RUN.exists(): raise FileExistsError(RUN)
 RUN.mkdir(parents=True)
 rows=json.loads((ROOT/'research-runs/alignment_gate_v1/manifest.json').read_text())
 roles=np.array([r['role'] for r in rows]); y=np.array([r['label_fake'] for r in rows],dtype=np.float32)
 fit=np.where(roles=='fit')[0]; cal=np.where(roles=='calibration')[0]; aud=np.where(roles=='audit')[0]
 arrays={k:np.load(CACHE/f'clean__{k}.npy',mmap_mode='r') for k in ['correct','wrong_integer','fractional']}
 device='cuda' if torch.cuda.is_available() else 'cpu'; results=[]
 for seed in [17,29,43]:
  item={'seed':seed}
  for arm in ['correct_only','response_bag']:
   random.seed(seed);np.random.seed(seed);torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
   model=(Bag() if arm=='correct_only' else ResponseBag()).to(device)
   opt=torch.optim.AdamW(model.parameters(),lr=1e-3,weight_decay=1e-4); loss_fn=torch.nn.BCEWithLogitsLoss()
   order=np.random.default_rng(seed).permutation(fit)
   for epoch in range(10):
    model.train()
    for start in range(0,len(order),16):
     ix=order[start:start+16]; x=torch.from_numpy(np.asarray(arrays['correct'][ix],dtype=np.float32)).to(device); c=torch.from_numpy(np.stack([arrays['wrong_integer'][ix],arrays['fractional'][ix]],axis=1).astype(np.float32)).to(device)
     opt.zero_grad(); z=(model(x) if arm=='correct_only' else model(x,c)); loss=loss_fn(z,torch.from_numpy(y[ix]).to(device)); loss.backward();opt.step()
   model.eval(); out={}
   with torch.no_grad():
    for name,ix in [('fit',fit),('calibration',cal),('audit',aud)]:
     vals=[]
     for start in range(0,len(ix),32):
      j=ix[start:start+32]; x=torch.from_numpy(np.asarray(arrays['correct'][j],dtype=np.float32)).to(device); c=torch.from_numpy(np.stack([arrays['wrong_integer'][j],arrays['fractional'][j]],axis=1).astype(np.float32)).to(device); vals.extend(torch.sigmoid(model(x) if arm=='correct_only' else model(x,c)).cpu().numpy())
     out[name]=float(roc_auc_score(y[ix],vals))
   item[arm]=out
  item['audit_delta']=item['response_bag']['audit']-item['correct_only']['audit']
  results.append(item)
 (RUN/'results.json').write_text(json.dumps({'protocol':json.loads((Path(__file__).with_name('protocol.json')).read_text()),'device':device,'results':results},indent=2)+'\n')
 print(json.dumps(results,indent=2))
if __name__=='__main__': main()
