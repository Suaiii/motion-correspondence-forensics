"""Check an existing feature cache's bytes, shape and selected-frame metadata only."""
import collections
import hashlib
import json
from pathlib import Path
from fractions import Fraction
import time
import numpy as np


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    start=time.monotonic()
    root=Path('/srv/video_evidence_v1').resolve()
    cache=root/'runs/dino_features'
    prep=Path('/root/autodl-tmp/cvpr27/runs/video_evidence_v1_prep')
    original=prep/'selection_dense_holdout_v1_8frame_clean.json'
    quality=prep/'selection_dense_holdout_v1_8frame_quality_excluded_20261005.json'
    lock=json.loads((cache/'lock.json').read_text())
    assert sha(original)==lock['selection_sha256']
    assert sha(root/'v1_manifest.jsonl')==lock['manifest_sha256']
    selections=json.loads(original.read_text())['rows']
    by_path={r['relative_path']:r for r in selections}
    quality_rows=json.loads(quality.read_text())['rows']
    quality_paths={r['relative_path'] for r in quality_rows}
    ok_paths=set()
    failures=[]
    known_exclusions=[]
    roles=collections.Counter()
    index=[]
    for path in sorted((cache/'records').glob('*.json')):
        r=json.loads(path.read_text())
        source=by_path[r['relative_path']]
        assert source['sha256']==r['sha256'] and source['selection_role']==r['selection_role']
        if r['status']!='ok':
            known_exclusions.append({'record':str(path),'relative_path':r['relative_path'],'reason':r.get('reason')})
            continue
        try:
            feature=(cache/r['feature_file']).resolve()
            assert feature.is_relative_to(cache/'features')
            assert sha(feature)==r['feature_sha256']
            array=np.load(feature,allow_pickle=False)
            assert list(array.shape)==r['shape']==[8,768] and np.isfinite(array).all()
            indices=r['sampling']['indices']
            assert len(indices)==len(set(indices))==8 and indices==sorted(indices)
            pts=source['ffprobe']['pts']
            assert all(0<=i<len(pts) for i in indices)
            expected=[float(Fraction(pts[i])*Fraction(source['ffprobe']['time_base'])) for i in indices]
            assert len(r['sampling']['pts'])==8
            assert np.allclose(expected,r['sampling']['pts'],rtol=0,atol=1e-6)
            assert r['sampling']['sampling_mode']=='center_8_native_frames_no_time_resampling'
            ok_paths.add(r['relative_path'])
            roles[r['selection_role']]+=1
            index.append({'relative_path':r['relative_path'],'input_sha256':r['sha256'],
                'feature_path':str(feature),'feature_sha256':r['feature_sha256'],'feature_shape':r['shape'],
                'label':r['label'],'generator':r['generator'],'selection_role':r['selection_role'],
                'record_path':str(path),'record_sha256':sha(path)})
        except Exception as exc:
            failures.append({'record':str(path),'error_type':type(exc).__name__,'error':str(exc)})
    destination=root/'operational_20261008'
    with (destination/'feature_index.jsonl').open('x') as f:
        for row in index:
            f.write(json.dumps(row,separators=(',',':'))+'\n')
    receipt={'scope':'existing cache integrity and metadata replay; no extraction or prediction',
        'lock_sha256':sha(cache/'lock.json'),'original_selection_sha256':sha(original),'quality_selection_sha256':sha(quality),
        'records_seen':len(list((cache/'records').glob('*.json'))),'feature_checks_passed':len(ok_paths),
        'existing_quality_exclusions':known_exclusions,'new_verification_failures':failures,
        'quality_selection_exactly_matches_valid_features':ok_paths==quality_paths,
        'role_counts':dict(roles),'feature_index_sha256':sha(destination/'feature_index.jsonl'),
        'forward_pass_replayed':False,'new_gpu_work':False,'scientific_gate_passed':False,
        'elapsed_seconds':time.monotonic()-start}
    (destination/'feature_verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='existing_quality_exclusions'}))


if __name__=='__main__':
    main()
