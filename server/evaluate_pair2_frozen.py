"""QC, DINO extraction and frozen-head transfer to an author-mapped Pair2 prefix.

No heads are trained or selected here. Prefix selection and exposed provenance
make this external development, never final confirmation.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.special import expit
from sklearn.metrics import roc_auc_score
import torch
from torch import nn

import time_matched_dino as decoder


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); os.replace(tmp,p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-cache', type=Path, help='Reuse successful records from a verified earlier transfer; retry errors')
    parser.add_argument('--probe-timeout', type=int, default=60, help='ffprobe timeout in seconds; 0 disables it for slow valid clips')
    a = parser.parse_args(); started = time.monotonic()
    root = a.output; root.mkdir(parents=True, exist_ok=True)
    for name in ('records', 'features'):
        (root/name).mkdir(exist_ok=True)
    parent = a.base/'runs/sampling_consistency_pilot_v1'
    prior = read(parent/'protocol.json')
    old_cache = a.base/'runs/time_matched_dino_v1'
    old_lock = read(old_cache/'lock.json')
    assert sha(decoder.__file__) == old_lock['script_sha256'], 'Sampling decoder differs from frozen cache'
    rows = read(a.audit/'manifest.json')
    eligible = [r for r in rows if r['development_eligible_before_qc']]
    weights = a.base/'models/dinov2_vitb14_pretrain.pth'
    assert sha(weights) == old_lock['weights_sha256']
    repo = a.base/'models'/('dinov2-'+old_lock['model_revision'])
    import subprocess
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip() == old_lock['model_revision']
    assert not subprocess.check_output(['git','-C',str(repo),'diff','--name-only'],text=True).strip()
    protocol = dict(scope='external-development prefix transfer; no final confirmation', script_sha256=sha(__file__),
        audit_manifest_sha256=sha(a.audit/'manifest.json'), frozen_parent_protocol_sha256=sha(parent/'protocol.json'),
        frozen_parent_report_sha256=sha(parent/'report.json'), decoder_sha256=sha(decoder.__file__),
        weights_sha256=old_lock['weights_sha256'], model_revision=old_lock['model_revision'],
        sampling=old_lock['sampling'], precision=old_lock['precision'], workers=12, video_batch=32,
        reuse_cache=str(a.reuse_cache.resolve()) if a.reuse_cache else None,
        probe_timeout_seconds=a.probe_timeout or None,
        fit_performed=False, requested=len(eligible), final_access=False, walltime_cap=None,
        selection='all eligible prefix candidates after author metadata, ancestry-ID and exact-hash exclusions',
        bootstrap='resample complete YouTube-origin groups jointly across real/generated labels; 2000 draws',
        limits=['Archive prefix, not random sampling; author provenance, not independent content proof.',
                'No recalibration, threshold tuning or best-seed selection on this new cohort.',
                'Intervals condition on frozen heads and candidate source groups.',
                'Nearest-frame timing cues and only 100 requested clips per new source remain limitations.'])
    if (root/'protocol.json').exists():
        assert read(root/'protocol.json') == protocol
    else:
        save(root/'protocol.json', protocol)
    torch.set_num_threads(4); decoder.cv2.setNumThreads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    complete = []; pending = []
    if a.reuse_cache:
        reused_protocol=read(a.reuse_cache/'protocol.json')
        for field in ('audit_manifest_sha256','decoder_sha256','weights_sha256','model_revision'):
            assert reused_protocol[field]==protocol[field]
    for r in eligible:
        key = hashlib.sha256(r['sample_id'].encode()).hexdigest()
        p = root/'records'/(key+'.json')
        if not p.exists() and a.reuse_cache:
            old_record=a.reuse_cache/'records'/(key+'.json')
            if old_record.exists():
                q=read(old_record)
                if q['status']=='ok':
                    assert q['sha256']==r['sha256'] and sha(a.reuse_cache/q['feature_file'])==q['feature_sha256']
                    dest=root/'features'/(key+'.npy');shutil.copyfile(a.reuse_cache/q['feature_file'],dest)
                    q.update(feature_file=str(dest.relative_to(root)),reused_record_sha256=sha(old_record),reused_from=str(old_record.resolve()))
                    save(p,q)
        if p.exists():
            q=read(p)
            if q['status']=='ok':
                assert sha(root/q['feature_file']) == q['feature_sha256']
            complete.append(q)
        else:
            pending.append(dict(r,key=key))
    gpu_seconds = 0
    if pending:
        assert a.probe_timeout >= 0
        # Change only the operational timeout, preserving probe arguments,
        # timestamp selection, decoded pixels and checkpoint preprocessing.
        original_run=decoder.subprocess.run
        def run_with_probe_timeout(*args, **kwargs):
            if args and args[0][0]=='ffprobe':
                kwargs['timeout']=a.probe_timeout or None
            return original_run(*args, **kwargs)
        decoder.subprocess.run=run_with_probe_timeout
        # Bounded source pool decodes while GPU inference consumes prior batches.
        with ThreadPoolExecutor(max_workers=12) as pool:
            decoded = iter(pool.map(decoder.decode, pending))
            model=torch.hub.load(str(repo),'dinov2_vitb14',source='local',pretrained=False).cuda().eval()
            model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
            mean=torch.tensor([.485,.456,.406],device='cuda')[None,:,None,None]
            std=torch.tensor([.229,.224,.225],device='cuda')[None,:,None,None]
            with torch.inference_mode():
                while True:
                    batch=list(itertools.islice(decoded,32))
                    if not batch:
                        break
                    good=[]
                    for r,frames,meta,error in batch:
                        if error:
                            q=dict(r,status='qc_excluded_or_error',reason=error)
                            save(root/'records'/(r['key']+'.json'),q); complete.append(q)
                        else:
                            good.append((r,frames,meta))
                    if good:
                        x=torch.from_numpy(np.concatenate([item[1] for item in good])[...,::-1].copy()).permute(0,3,1,2).cuda().float()/255
                        begin=torch.cuda.Event(enable_timing=True); end=torch.cuda.Event(enable_timing=True); begin.record()
                        with torch.autocast('cuda',dtype=torch.bfloat16):
                            z=model((x-mean)/std)
                        end.record(); z=z.float().cpu().numpy().reshape(len(good),8,768)
                        gpu_seconds += begin.elapsed_time(end)/1000
                        assert np.isfinite(z).all()
                        for j,(r,_,meta) in enumerate(good):
                            path=root/'features'/(r['key']+'.npy'); np.save(path,z[j])
                            q=dict(r,status='ok',sampling=meta,feature_file=str(path.relative_to(root)),feature_sha256=sha(path))
                            save(root/'records'/(r['key']+'.json'),q); complete.append(q)
                    save(root/'progress.json',dict(phase='extracting',completed=len(complete),requested=len(eligible),seconds=time.monotonic()-started))
                    print('Processed',len(complete),'/',len(eligible),flush=True)
            del model, x, z
    accepted=sorted([r for r in complete if r['status']=='ok'],key=lambda r:r['sample_id'])
    assert len(accepted)>0
    y=np.array([r['label_fake'] for r in accepted]); assert len(set(y))==2
    features={k:[] for k in ('semantic_duplicate','time_std','time_delta')}
    for r in accepted:
        z=np.load(root/r['feature_file']).astype(np.float64)
        z/=np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)
        mean=z.mean(0)
        features['semantic_duplicate'].append(np.r_[mean,mean])
        features['time_std'].append(np.r_[mean,z.std(0)])
        features['time_delta'].append(np.r_[mean,np.abs(np.diff(z,axis=0)).mean(0)])
    features={k:torch.tensor(np.asarray(v,dtype=np.float32),device='cuda') for k,v in features.items()}
    metrics=[]; predictions={}; head_hashes={}; ensembles={}
    for held in prior['holdouts']:
        for arm in prior['arms']:
            probs=[]
            for seed in prior['seeds']:
                folder=parent/(held+'_'+str(seed)+'_'+arm)
                expected=read(folder/'hashes.json')['best.pt']; assert sha(folder/'best.pt')==expected
                head_hashes[folder.name]=expected
                saved=torch.load(folder/'best.pt',weights_only=True)
                model=nn.Sequential(nn.Linear(1536,256),nn.GELU(),nn.Dropout(.1),nn.Linear(256,1)).cuda().eval()
                model.load_state_dict(saved['model'])
                key=arm if arm in features else 'time_delta'
                with torch.no_grad():
                    logits=model((features[key]-saved['mean'].cuda())/saved['scale'].cuda()).ravel().cpu().numpy()
                p=expit(logits).astype(np.float64); probs.append(p)
                predictions[folder.name]=logits
                metrics.append(dict(training_holdout=held,arm=arm,seed=seed,auc=float(roc_auc_score(y,p))))
            ensembles[held+'/'+arm]=np.mean(probs,axis=0)
    groups={}
    for i,r in enumerate(accepted):
        groups.setdefault(r['group'],[]).append(i)
    group_arrays=list(groups.values()); rng=np.random.default_rng(20260917)
    samples={key:[] for key in ensembles}; differences={key:[] for key in ensembles if not key.endswith('/semantic_duplicate')}
    for _ in range(2000):
        ix=np.concatenate([group_arrays[j] for j in rng.integers(len(group_arrays),size=len(group_arrays))])
        if len(set(y[ix]))<2:
            continue
        scores={key:roc_auc_score(y[ix],p[ix]) for key,p in ensembles.items()}
        for key,value in scores.items():
            samples[key].append(value)
            if key in differences:
                differences[key].append(value-scores[key.split('/')[0]+'/semantic_duplicate'])
    aggregated=[]
    for key,p in ensembles.items():
        held,arm=key.split('/')
        item=dict(training_holdout=held,arm=arm,ensemble_auc=float(roc_auc_score(y,p)),ci95=np.quantile(samples[key],[.025,.975]).tolist(),
            seed_auc_mean=float(np.mean([r['auc'] for r in metrics if r['training_holdout']==held and r['arm']==arm])))
        if key in differences:
            item.update(gain_over_semantic=float(roc_auc_score(y,p)-roc_auc_score(y,ensembles[held+'/semantic_duplicate'])),
                gain_ci95=np.quantile(differences[key],[.025,.975]).tolist())
        aggregated.append(item)
    np.savez_compressed(root/'predictions.npz',labels=y,sample_ids=np.array([r['sample_id'] for r in accepted]),**predictions)
    save(root/'accepted_manifest.json',accepted)
    save(root/'head_hashes.json',head_hashes)
    report=dict(complete=True,fit_performed=False,counts=dict(Counter(r['source'] for r in accepted)),
        qc_statuses=dict(Counter(r['status'] for r in complete)),qc_reasons=dict(Counter(r.get('reason') for r in complete if r['status']!='ok')),
        metadata_excluded=len(rows)-len(eligible),ancestor_groups=len(groups),multilabel_groups=sum(len({int(y[i]) for i in values})>1 for values in groups.values()),
        results=metrics,aggregates=aggregated,seconds=time.monotonic()-started,
        cuda_forward_seconds=gpu_seconds,peak_gpu_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
        formal_claim_released=False,scope=protocol['scope'])
    save(root/'report.json',report)
    save(root/'artifact_hashes.json',{p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name!='artifact_hashes.json'})
    print(json.dumps({k:report[k] for k in ('counts','qc_statuses','seconds','aggregates')},indent=2),flush=True)


if __name__=='__main__':
    main()
