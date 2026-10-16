"""Replay frozen external predictions and transfer the existing timing controls."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from sklearn.metrics import roc_auc_score
import torch
from torch import nn


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    a=p.parse_args(); dest=a.root/'verification.json'; assert not dest.exists()
    for rel,digest in read(a.root/'artifact_hashes.json').items():
        assert sha(a.root/rel)==digest
    report=read(a.root/'report.json'); rows=read(a.root/'accepted_manifest.json'); protocol=read(a.root/'protocol.json')
    parent=a.base/'runs/sampling_consistency_pilot_v1'; prior=read(parent/'protocol.json')
    assert sha(parent/'protocol.json')==protocol['frozen_parent_protocol_sha256']
    assert sha(parent/'report.json')==protocol['frozen_parent_report_sha256']
    data=np.load(a.root/'predictions.npz',allow_pickle=False)
    y=np.array([r['label_fake'] for r in rows]);assert np.array_equal(y,data['labels'])
    assert np.array_equal([r['sample_id'] for r in rows],data['sample_ids'])
    x={k:[] for k in ('semantic_duplicate','time_std','time_delta')}
    for r in rows:
        path=a.root/r['feature_file']; assert sha(path)==r['feature_sha256']
        assert sha(r['raw_path'])==r['sha256']
        z=np.load(path).astype(np.float64); z/=np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)
        mean=z.mean(0)
        x['semantic_duplicate'].append(np.r_[mean,mean]);x['time_std'].append(np.r_[mean,z.std(0)])
        x['time_delta'].append(np.r_[mean,np.abs(np.diff(z,axis=0)).mean(0)])
    x={k:torch.tensor(np.asarray(v,dtype=np.float32),device='cuda') for k,v in x.items()}
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    replay=[]; expected_heads=read(a.root/'head_hashes.json')
    for held in prior['holdouts']:
        for arm in prior['arms']:
            probs=[]
            for seed in prior['seeds']:
                key=held+'_'+str(seed)+'_'+arm; path=parent/key/'best.pt'
                assert sha(path)==expected_heads[key]
                cp=torch.load(path,weights_only=True)
                head=nn.Sequential(nn.Linear(1536,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,1)).cuda().eval()
                head.load_state_dict(cp['model']); kind=arm if arm in x else 'time_delta'
                with torch.no_grad():
                    logits=head((x[kind]-cp['mean'].cuda())/cp['scale'].cuda()).ravel().cpu().numpy()
                error=float(np.max(np.abs(logits-data[key]))); assert error<1e-5
                probabilities=expit(data[key]).astype(np.float64);probs.append(probabilities)
                old=next(r for r in report['results'] if (r['training_holdout'],r['arm'],r['seed'])==(held,arm,seed))
                assert abs(roc_auc_score(y,probabilities)-old['auc'])<1e-12
                replay.append(dict(model=key,max_logit_error=error))
            agg=next(r for r in report['aggregates'] if (r['training_holdout'],r['arm'])==(held,arm))
            assert abs(roc_auc_score(y,np.mean(probs,axis=0))-agg['ensemble_auc'])<1e-12
    timing_root=a.base/'runs/paired_time_verification_v2'
    index=read(timing_root/'artifact_hashes.json'); path=timing_root/'timing_models_predictions.json'
    assert sha(path)==index[path.name]
    probes=[]; probe_predictions={}
    for model in read(path):
        if model['probe']=='native_interval':
            continue  # Native8 was not extracted for this new development set.
        values=[]
        for r in rows:
            dt=np.diff(r['sampling']['pts'])
            timing={'time_median_dt':float(np.median(dt)),'time_dt_std':float(np.std(dt)),
                    'time_max_timing_error':float(np.max(np.abs(r['sampling']['timing_error'])))}
            values.append([np.log(max(timing[f],1e-9)) for f in model['fields']])
        z=(np.array(values)-model['mean'])/model['scale']
        scores=expit((z@np.array(model['coef']).T).ravel()+model['intercept'][0])
        key=model['held_generator']+'/'+model['probe'];probe_predictions[key]=scores.tolist()
        probes.append(dict(training_holdout=model['held_generator'],probe=model['probe'],auc=roc_auc_score(y,scores),fit_performed=False))
    output=dict(status='pass',script_sha256=sha(__file__),report_sha256=sha(a.root/'report.json'),
        replayed_heads=len(replay),main_models_refitted=False,raw_and_feature_hashes_verified=True,
        checkpoint_and_metric_replay=replay,timing_probe_transfer=probes,
        timing_prediction_scope='frozen old timing heads; new labels used only to measure AUROC',
        formal_claim_released=False,scope='mechanical replay, not independent scientific replication')
    dest.write_text(json.dumps(output,indent=2)+'\n')
    (a.root/'timing_predictions.json').write_text(json.dumps(probe_predictions,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ('status','replayed_heads','timing_probe_transfer')},indent=2),flush=True)


if __name__=='__main__':
    main()
