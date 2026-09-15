"""Post-hoc development diagnostic of temporal readout order; no model tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from model import VideoBaseline
from run import digest, dump

parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True);args=parser.parse_args()
run=args.run_dir.resolve();assert run.drive.upper()=='E:'
cfg=json.loads((run/'protocol.json').read_text(encoding='utf-8'))
rows=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
indices=[i for i,r in enumerate(rows)if r['role']=='audit']
y=np.array([rows[i]['label_fake']for i in indices]);result=[];all_predictions=[]
torch.set_num_threads(4)
for kind in ['raw_temporal','aligned_temporal']:
    cache=np.load(run/'cache'/f'clean__{kind}.npy',allow_pickle=False)
    x=torch.tensor(np.array(cache[indices],dtype=np.float32),device='cuda')
    shuffled=x.clone()
    for j,i in enumerate(indices):
        seed=20260908^int(hashlib.sha256(rows[i]['sample_id'].encode()).hexdigest()[:8],16)
        order=np.random.default_rng(seed).permutation(x.shape[1])
        shuffled[j]=x[j,torch.tensor(order,device='cuda')]
    for seed in cfg['seeds']:
        dest=run/'training'/f'{kind}_seed{seed}'
        stats=json.loads((dest/'summary.json').read_text(encoding='utf-8'))
        assert digest(dest/'best.pt')==stats['checkpoint_sha256']
        model=VideoBaseline(kind).cuda().eval()
        model.load_state_dict(torch.load(dest/'best.pt',map_location='cuda',weights_only=True))
        with torch.no_grad():
            original=torch.sigmoid(model(x)).cpu().numpy()
            permuted=torch.sigmoid(model(shuffled)).cpu().numpy()
        result.append({'kind':kind,'seed':seed,'original_auc':float(roc_auc_score(y,original)),
                       'permuted_residual_auc':float(roc_auc_score(y,permuted)),
                       'mean_absolute_score_change':float(np.mean(np.abs(original-permuted))),
                       'checkpoint_sha256':stats['checkpoint_sha256']})
        for j,i in enumerate(indices):
            all_predictions.append({'kind':kind,'seed':seed,'sample_id':rows[i]['sample_id'],'label_fake':int(y[j]),'original_prob_fake':float(original[j]),'permuted_prob_fake':float(permuted[j])})
        del model
    del x,shuffled,cache
    torch.cuda.empty_cache()
dump(run/'order_probe.json',{'results':result,'predictions':all_predictions,
    'scope':'post-hoc development diagnostic after primary evaluation; no checkpoint, threshold, or recipe changes',
    'interpretation':'Only cached residual order is permuted. Frame-pair temporal evidence remains in residuals. This is not a test of all temporal information or raw-video permutation.',
    'code_sha256':digest(__file__)})
print(json.dumps(result,indent=2))
