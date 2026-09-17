"""DX01: derive joint lags only from previously saved complete BEFORE PTS.

Reads the archived retiming diagnostic's originals, never its transformed
timestamps. No ffprobe, decoder, media access, feature extraction or fitting.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.mechanism_sampling import choose_six


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def object_hash(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def summarize(rows,indices,quantum):
    sources=sorted({r['source'] for r in rows});bins={};continuous={}
    for source in sources:
        x=np.array([r['joint'][indices].ravel() for r in rows if r['source']==source])
        signatures=[tuple(np.floor(v/quantum+.5).astype(int)) for v in x]
        bins[source]=Counter(signatures)
        continuous[source]=dict(n=len(x),minimum=x.min(0).tolist(),maximum=x.max(0).tolist(),
            mean=x.mean(0).tolist(),std=x.std(0).tolist(),
            maximum_deviation_from_target=float(np.max(np.abs(x-(.5 if indices==[4,5] else .25)))))
    common=set.intersection(*(set(v) for v in bins.values())) if bins else set()
    return dict(quantum_seconds=quantum,continuous_by_source=continuous,common_bins=len(common),
        supported_counts={s:sum(bins[s][k] for k in common) for s in sources},
        scope='Intersection only among available sources; missing real sources cannot be inferred.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();started=time.monotonic();a.output.mkdir(parents=True,exist_ok=False)
    prior=a.base/'runs/overnight_20260911/retiming_diagnostic';protocol=read(prior/'protocol.json')
    writer=a.base/'incoming/night20260911/retime_qc.py'
    assert sha(writer)==protocol['script_sha256'],'Archived writer does not match protocol'
    selection=protocol['selection'];assert len({r['sample_id'] for r in selection})==len(selection)
    rows=[];excluded=[];input_hashes={};counts=Counter(r['source'] for r in selection)
    for selected in selection:
        path=prior/(object_hash(selected['sample_id'])+'.json')
        r=read(path);input_hashes[path.name]=sha(path)
        assert r['sample_id']==selected['sample_id'] and r['source']==selected['source']
        try:
            if r['status']!='ok':raise ValueError('historical_record_not_ok')
            before=r['before'];pts=np.asarray(before['pts'],dtype=np.float64)
            if len(pts)!=len(before['frame_hashes']):raise ValueError('full_pts_vs_decoded_frame_count_mismatch')
            if not before['frame_hashes']:raise ValueError('no_full_decoded_frame_evidence')
            index,sampling=choose_six(pts)
            row=dict(sample_id=r['sample_id'],source=r['source'],full_native_pts=pts.tolist(),
                metadata_origin='before',source_record_sha256=sha(path),sampling=sampling,
                joint=np.asarray(sampling['joint_triplet_intervals']))
            rows.append(row)
        except (KeyError,ValueError) as error:
            excluded.append(dict(sample_id=r['sample_id'],source=r['source'],reason=str(error)))
    assert rows,'No complete original PTS passed metadata qualification'
    source_counts=Counter(r['source'] for r in rows)
    joint={name:[summarize(rows,indices,q) for q in (.001,.002,.005)] for name,indices in
        [('four_short_triplets',[0,1,2,3]),('two_long_triplets',[4,5]),('all_six_triplets',[0,1,2,3,4,5])]}
    # The combined view has a mixed target vector; retain raw vectors and avoid
    # reporting the short-target deviation scalar for that view.
    for result in joint['all_six_triplets']:
        for source,value in result['continuous_by_source'].items():
            observed=np.array([r['joint'].ravel() for r in rows if r['source']==source])
            value['maximum_deviation_from_target']=float(np.max(np.abs(observed-np.array([.25]*8+[.5]*4))))
    serialized=[dict(r,joint=r['joint'].tolist()) for r in rows]
    (a.output/'selected_joint_records.json').write_text(json.dumps(serialized,indent=2)+'\n')
    (a.output/'input_record_hashes.json').write_text(json.dumps(input_hashes,indent=2)+'\n')
    missing={source:dict(available_complete_native_pts=0,joint_support_evaluated=False,exclusion_rate=None,
        reason='Inspected caches/writers save only selected-frame PTS or no timestamps, not a verified complete native sequence.')
        for source in ('vript','hd_vg_130m','cogvideo')}
    report=dict(work_package='cc-round-1-20260917',plan_version='cvpr27-20260917-v1.1',
        status='partial_missing_real_source_full_pts',observed_utc=datetime.now(timezone.utc).isoformat(),
        existing_metadata_scope=str(prior),original_only=True,retimed_after_pts_used=False,
        considered_counts=dict(counts),eligible_counts=dict(source_counts),
        exclusion_rates={s:1-source_counts[s]/n for s,n in counts.items()},exclusions=excluded,
        complete_pts_metadata_missing=missing,raw_media_read=False,new_probe_run=False,new_feature_extraction=False,
        new_gpu_job=False,classifier_fitted=False,real_fake_joint_support_established=False,formal_gate_passed=False,
        sampling=dict(window=1.5,fps_target=4,frames=6,short_triplets=[[0,1,2],[1,2,3],[2,3,4],[3,4,5]],
            long_triplets=[[0,2,4],[1,3,5]],long_edge_target_seconds=.5),joint_support=joint,
        protocol_sha256=sha(prior/'protocol.json'),archived_writer_sha256=sha(writer),
        input_hash_index_sha256=sha(a.output/'input_record_hashes.json'),joint_records_sha256=sha(a.output/'selected_joint_records.json'),
        script_sha256=sha(__file__),sampler_sha256=sha(Path(__file__).resolve().parents[1]/'forensics/mechanism_sampling.py'),
        wall_seconds=time.monotonic()-started,
        limitations=['Only the archived 50 MS/50 VC2 diagnostic cohort has verified complete native PTS here.',
                    'No inference from nominal FPS, duration or selected 8/16 timestamps to a complete frame sequence.',
                    'Missing timestamps are not video-quality exclusions, and no real/fake overlap can be claimed.',
                    'No current raw-media rehash/decoding was performed; provenance is the archived metadata and writer receipt.',
                    'Existing paid instance was used for CPU/read-only work; this is not a zero-cost claim.'])
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','eligible_counts','exclusion_rates','wall_seconds')},indent=2),flush=True)


if __name__=='__main__':main()
