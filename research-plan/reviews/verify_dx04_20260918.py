"""Verify saved DX04 records using original JSON and arithmetic, without sampling jobs."""
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'research-runs/shared_plan_20260917'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(value):
    # Historical Windows receipts may contain backslashes; preserve receipts.
    return ROOT / value.replace('\\', '/')


def main():
    start = time.perf_counter()
    audit_path = RUN / 'candidate_c_existing_pts_audit.json'
    records_path = RUN / 'candidate_c_existing_pts_records.json'
    assert sha(audit_path) == 'e623f9f389634e422101ade22a99dfb1ec1a502d20e6178eef92017f1b82971c'
    assert sha(records_path) == '6e738435aa8c2053cf553be3923e657f1c64380b5dbeaa5d724add9f2a6623d8'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    rows = json.loads(records_path.read_text(encoding='utf-8'))['records']
    frozen = json.loads((ROOT / 'research-plan/reviews/dx04_input_freeze_20260918.json').read_text(encoding='utf-8'))
    assert audit['records_sha256'] == sha(records_path)
    assert audit['script_sha256'] == sha(ROOT / 'research-runtime/server/scripts/audit_candidate_c_existing_pts.py')
    for rel, digest in audit['input_sha256'].items():
        assert sha(repo_path(rel)) == digest, rel
    assert [(r['sample_id'],r['source']) for r in rows] == [(r['sample_id'],r['source']) for r in frozen['inputs']]
    assert len(rows) == len({r['sample_id'] for r in rows}) == 100
    assert audit['timestamp_provenance']['native_integer_pts_verified'] is False
    writer = (ROOT / frozen['archived_writer']['path']).read_text(encoding='utf-8')
    assert "frame=best_effort_timestamp_time" in writer
    assert "float(r['best_effort_timestamp_time'])" in writer
    assert 'time_base' not in writer

    for row in rows:
        raw = json.loads((ROOT / row['input_metadata_path']).read_text(encoding='utf-8'))
        assert raw['sample_id'] == row['sample_id'] and raw['source'] == row['source']
        assert raw['status'] == 'ok' and row['status'] == 'eligible'
        before = raw['before']
        pts = np.asarray(before['pts'], dtype=np.float64)
        assert len(pts) == len(before['frame_hashes']) == row['complete_original_timestamp_count']
        assert np.isfinite(pts).all() and (np.diff(pts) > 0).all()
        s = row['sampling']; indices = np.asarray(s['indices'])
        duration = float(pts[-1] - pts[0] + np.median(np.diff(pts)))
        center = pts[0] + duration / 2
        targets = center + np.array([-.5, 0., .5])
        selected = pts[indices]
        assert len(set(indices)) == 3 and duration >= 1.5-1e-6
        np.testing.assert_array_equal(selected, s['pts'])
        np.testing.assert_array_equal(targets, s['targets'])
        np.testing.assert_array_equal(selected-targets, s['timing_error'])
        np.testing.assert_array_equal(np.diff(selected), s['joint_triplet_intervals'][0])
        assert s['native_duration'] == duration
        assert s['actual_span_seconds'] == float(selected[-1]-selected[0])
        assert s['center_error_seconds'] == float(selected[1]-center)
        for idx, target in zip(indices, targets):
            distances = np.abs(pts-target)
            earliest_tied = int(np.flatnonzero(distances <= distances.min()+1e-9)[0])
            assert idx == earliest_tied and distances[idx] <= .125+1e-6
        assert row['timestamp_field_origin'] == 'best_effort_timestamp_time'
        assert row['native_integer_pts_verified'] is False
        assert row['ancestry_status'] == 'unverified'
        assert row['A_check']['status'] == 'A_eligible'
        assert s['indices'] == row['A_check']['A_selected_indices'][1::2]
        np.testing.assert_array_equal(s['targets'], row['A_check']['A_targets'][1::2])

    fields = {'joint_lags':('joint_triplet_intervals',[.5,.5]), 'span':('actual_span_seconds',1.),
        'signed_sampling_errors':('timing_error',[0.,0.,0.]), 'signed_center_error':('center_error_seconds',0.),
        'native_duration_estimate':('native_duration',None)}
    for source in ('ms','vc2'):
        cohort = [r for r in rows if r['source']==source]
        assert audit['counts'][source] == dict(total=50,eligible=50,excluded=0,exclusion_rate=0.)
        for name,(key,target) in fields.items():
            x=np.asarray([r['sampling'][key][0] if key=='joint_triplet_intervals' else r['sampling'][key] for r in cohort])
            got=audit['continuous_by_source'][source][name]
            for stat,expected in [('minimum',x.min(0)),('maximum',x.max(0)),('mean',x.mean(0)),('std',x.std(0))]:
                np.testing.assert_allclose(got[stat],expected,rtol=0,atol=1e-15)
            if target is None: assert got['maximum_absolute_deviation_from_target'] is None
            else: np.testing.assert_allclose(got['maximum_absolute_deviation_from_target'],np.max(np.abs(x-target),axis=0),rtol=0,atol=1e-15)

    view_count=0
    for name,with_center in [('joint_lags',False),('joint_lags_and_center_error',True)]:
        for view,q in zip(audit['joint_support'][name],(.001,.002,.005)):
            assert view['quantum_seconds']==q
            hist={}
            for source in ('ms','vc2'):
                vectors=[r['sampling']['joint_triplet_intervals'][0]+([r['sampling']['center_error_seconds']] if with_center else []) for r in rows if r['source']==source]
                counts=Counter(tuple(np.floor(np.asarray(v)/q+.5).astype(int)) for v in vectors)
                saved={tuple(v['bin_indices']):v['count'] for v in view['histograms'][source]}
                assert counts==saved
                hist[source]=counts
            common=set(hist['ms']) & set(hist['vc2'])
            assert sorted(common)==[tuple(v) for v in view['common_bins']]
            assert view['common_bin_count']==1
            assert view['common_support_counts']=={s:sum(h[k] for k in common) for s,h in hist.items()}
            view_count+=1
    assert view_count==6
    for rel,digest in audit['input_sha256'].items(): assert sha(repo_path(rel))==digest
    result=dict(status='pass',scope='saved_metadata_hash_and_arithmetic_review_only',
        observed_at=datetime.datetime.now().astimezone().isoformat(),records_verified=100,
        input_bindings_verified=len(audit['input_sha256']),joint_views_verified=view_count,
        audit_sha256=sha(audit_path),records_sha256=sha(records_path),
        timestamp_source='ffprobe best_effort_timestamp_time',native_integer_pts_verified=False,
        raw_media_reverified=False,C_sampler_invocations=0,server_accessed=False,
        scientific_gate_passed=False,elapsed_local_seconds=time.perf_counter()-start)
    with Path(__file__).with_name('dx04_planner_verification_20260918.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
