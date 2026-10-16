# Creates adapter_v2 (metric-only fix) and runs AL145 retry2 with a receipt; v1 adapter and failed outputs untouched.
import hashlib,json,subprocess,time
from pathlib import Path
P=Path('/root/autodl-tmp/cvpr27/runs/video_evidence_v1_prep');old=P/'video_evidence_dense_adapter.py';new=P/'video_evidence_dense_adapter_v2.py'
out=P/'AL145_dense_baseline_quality_excluded_retry2_20261016'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old)=='80ea991be93062911c0d67ed7163fd50e12cb15e80f6455f580f2822407e9a54' and not new.exists() and not out.exists()
t=old.read_text()
a='''            metric[cohort] = {"n": int(mask.sum()), "auc": float(roc_auc_score(y[mask], prob[mask])) if mask.sum() else None,
                              "bce": float(log_loss(y[mask], prob[mask])) if mask.sum() else None}'''
b='''            n_fake = int(y[mask].sum()); two_class = 0 < n_fake < int(mask.sum())
            metric[cohort] = {"n": int(mask.sum()), "n_fake": n_fake,
                              "auc": float(roc_auc_score(y[mask], prob[mask])) if two_class else None,
                              "auc_undefined_single_class": bool(mask.sum()) and not two_class,
                              "bce": float(log_loss(y[mask], prob[mask], labels=[0, 1])) if mask.sum() else None,
                              "mean_prob_fake": float(prob[mask].mean()) if mask.sum() else None}'''
assert t.count(a)==1;new.write_text(t.replace(a,b))
out.mkdir()
cmd=['/root/autodl-tmp/cvpr27/environment/venv/bin/python',str(new),'train','--selection',str(P/'selection_dense_holdout_v1_8frame_quality_excluded_20261005.json'),'--manifest','/srv/video_evidence_v1/v1_manifest.jsonl','--features','/srv/video_evidence_v1/runs/dino_features','--output',str(out)]
s=time.time()
with (out/'adapter.stdout.txt').open('w') as o,(out/'adapter.stderr.txt').open('w') as e:r=subprocess.run(cmd,stdout=o,stderr=e,env={'PATH':'/usr/bin:/bin','OMP_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':''})
rec={'status':'ok' if r.returncode==0 else 'failed','returncode':r.returncode,'command':cmd,'wall_seconds':time.time()-s,
 'selection_sha256':sha(P/'selection_dense_holdout_v1_8frame_quality_excluded_20261005.json'),'manifest_sha256':sha(Path('/srv/video_evidence_v1/v1_manifest.jsonl')),
 'adapter_sha256':sha(new),'adapter_v1_sha256':sha(old),'features_lock_sha256':sha(Path('/srv/video_evidence_v1/runs/dino_features/lock.json')),
 'change_from_retry1':'metric harness only: single-class cohort AUC=null, log_loss labels=[0,1], add n_fake/mean_prob_fake; fitting, C grid, features, selection unchanged',
 'previous_failures_preserved':['AL145_dense_baseline_quality_excluded_20261005','AL145_dense_baseline_quality_excluded_retry1_20261005'],
 'formal_gate_passed':False,'scope':'strong dense baseline gate; no mechanism acceptance'}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec)[:400])
