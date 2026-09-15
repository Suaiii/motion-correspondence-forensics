"""Cross-check completed real-source acquisition and frozen feature artifacts."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def records(root):
    result={};digests={}
    for p in sorted((root/'records').glob('*.json')):
        r=read(p)
        if r['sample_id'] in result:raise ValueError('Duplicate record identity')
        result[r['sample_id']]=r;digests[p.name]=sha(p)
    return result,digests


def main():
    p=argparse.ArgumentParser();p.add_argument('--download-dir',type=Path,required=True);p.add_argument('--feature-dir',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    if a.output_dir.exists():raise FileExistsError('Preserve completed or failed audits')
    ds=read(a.download_dir/'summary.json');fs=read(a.feature_dir/'summary.json')
    if not ds['complete'] or not fs['complete']:raise ValueError('Acquisition and feature extraction must finish first')
    selected=read(a.selection)['rows'];wanted={r['sample_id'] for r in selected}
    if len(wanted)!=len(selected):raise ValueError('Duplicate selection identities')
    groups=[r['source_group_candidate'] for r in selected]
    if len(groups)!=len(set(groups)):raise ValueError('More than one chosen clip per candidate origin group')
    d,dh=records(a.download_dir);f,fh=records(a.feature_dir)
    if set(d)!=wanted or set(f)!=wanted:raise ValueError('Different cohort coverage')
    if read(a.feature_dir/'lock.json')['download_lock_sha256']!=sha(a.download_dir/'lock.json'):raise ValueError('Different acquisition lock')
    if read(a.feature_dir/'lock.json')['selection_sha256']!=sha(a.selection):raise ValueError('Selection digest differs')
    ids=[];vectors=[];feature_hashes={};failures=[];duplicates=defaultdict(list)
    for sid in sorted(wanted):
        dr=d[sid];fr=f[sid]
        if dr['status']=='ok':
            if not dr['original_header_matches_quickopen']:raise ValueError('Member header was not verified')
            raw=a.download_dir/dr['raw_file']
            if not raw.is_file() or raw.stat().st_size!=dr['raw_bytes']:raise ValueError('Raw file absent or resized')
            duplicates[dr['sha256']].append(sid)
        expected=dr['status']=='ok' and dr.get('native16',{}).get('status')=='ok'
        if expected != (fr['status']=='ok'):raise ValueError('Native eligibility and feature success differ')
        if fr['status']!='ok':failures.append({'sample_id':sid,'reason':fr.get('reason')});continue
        if fr['sha256']!=dr['sha256'] or fr['sampling']['pts']!=dr['native16']['sampling']['pts']:raise ValueError('Source or sampling identity differs')
        path=a.feature_dir/fr['feature_file'];digest=sha(path)
        if digest!=fr['feature_sha256']:raise ValueError('Feature SHA differs')
        values=np.load(path,allow_pickle=False)
        if values.shape!=(16,768) or not np.isfinite(values).all():raise ValueError('Malformed feature tensor')
        feature_hashes[fr['feature_file']]=digest
        ids.append({'sample_id':sid,'source':'vript','source_group_candidate':dr['source_group_candidate'],
                    'ancestry_status':dr['ancestry_status'],'raw_sha256':dr['sha256']});vectors.append(values.mean(0))
    if dict(Counter(r['status'] for r in d.values()))!=ds['download_statuses'] or dict(Counter(r['status'] for r in f.values()))!=fs['statuses']:
        raise ValueError('Saved summary counts differ from records')
    result={'requested':len(wanted),'candidate_origin_groups':len(groups),
            'download_statuses':ds['download_statuses'],'strict_2s_statuses':ds['strict_2s_statuses'],'native16_statuses':ds['native16_statuses'],
            'strict_failure_reasons':dict(Counter(r.get('strict_2s',{}).get('reason','not_run') for r in d.values() if r.get('strict_2s',{}).get('status')!='ok')),
            'feature_statuses':fs['statuses'],'verified_feature_files':len(ids),'feature_exclusions':failures,
            'raw_duplicate_groups_from_verified_receipts':[v for v in duplicates.values() if len(v)>1],
            'raw_bytes':sum(r.get('raw_bytes',0) for r in d.values()),'packed_member_bytes':sum(r.get('packed_bytes',0) for r in d.values()),
            'feature_wall_seconds':fs['wall_seconds'],'cuda_forward_seconds':fs['cuda_forward_seconds'],
            'timing_scope':'Feature wall starts after model construction; includes data-worker startup, decoding, precision check and artifact writes. CUDA events cover ordinary model forward only, excluding copies, normalization and precision-check forwards.',
            'classification_metrics_computed':False,'formal_training_started':False,
            'verification_scope':'All feature bytes rehashed; source SHA and PTS matched to acquisition records. Raw sizes checked here; raw SHA was recomputed by the feature worker, not repeated in this final audit. No full archive hash or ancestry verification.',
            'input_sha256':{'selection':sha(a.selection),'download_lock':sha(a.download_dir/'lock.json'),'feature_lock':sha(a.feature_dir/'lock.json')},
            'record_sha256':{'download':dh,'features':fh},'feature_sha256':feature_hashes,'script_sha256':sha(__file__)}
    a.output_dir.mkdir(parents=True)
    np.save(a.output_dir/'pooled_features.npy',np.stack(vectors).astype(np.float32))
    (a.output_dir/'ids.json').write_text(json.dumps(ids),encoding='utf-8')
    (a.output_dir/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['requested','download_statuses','strict_2s_statuses','feature_statuses','verified_feature_files']}))


if __name__=='__main__':main()
