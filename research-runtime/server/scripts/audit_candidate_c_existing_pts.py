"""DX04 fixed retrospective metadata analysis. No probes, media or fitting."""
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
from forensics.mechanism_sampling import choose_six,choose_centered_three
from forensics.composability_config import load_candidate_c_config

FREEZE_SHA='7a841af5377f1f457396ae7bdc652809eddffff9c2ac431fca54fc549c9bde93'
QUANTA=(.001,.002,.005)
SOURCES=('ms','vc2')


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def encode(value):return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
def write_new(path,value):
    with path.open('xb') as f:f.write(encode(value))


def preflight(root):
    frozen_path=root/'research-plan/reviews/dx04_input_freeze_20260918.json'
    assert sha(frozen_path)==FREEZE_SHA,'Frozen input contract changed'
    frozen=read(frozen_path)
    bindings={str(frozen_path.relative_to(root)):FREEZE_SHA}
    for key in ('protocol','archived_writer'):
        item=frozen[key];assert sha(root/item['path'])==item['sha256'],key
        bindings[item['path']]=item['sha256']
    extra={
        'research-runtime/server/forensics/mechanism_sampling.py':frozen['sampler_sha256'],
        'research-runtime/server/configs/candidate_c_centered3_v1.json':frozen['config_sha256'],
        'research-plan/CANDIDATE_C_METADATA_AUDIT_20260918.md':frozen['analysis_plan_sha256']}
    for name,digest in extra.items():
        assert sha(root/name)==digest,name
        bindings[name]=digest
    config=load_candidate_c_config(root/'research-runtime/server/configs/candidate_c_centered3_v1.json')
    protocol=read(root/frozen['protocol']['path'])
    assert protocol['script_sha256']==frozen['archived_writer']['sha256']
    inputs=frozen['inputs'];selection=protocol['selection']
    assert len(inputs)==len(selection)==100
    assert len({r['sample_id'] for r in inputs})==100
    assert Counter(r['source'] for r in inputs)=={'ms':50,'vc2':50}
    assert [(r['sample_id'],r['source']) for r in inputs]==[(r['sample_id'],r['source']) for r in selection]
    old_index={}
    loaded=[]
    for item in inputs:
        path=root/item['metadata_path'];digest=sha(path)
        assert digest==item['sha256'],item['sample_id']
        old_index[path.name]=digest;bindings[item['metadata_path']]=digest
        row=read(path)
        assert row['sample_id']==item['sample_id'] and row['source']==item['source'],'Metadata identity mismatch'
        # Access only before; the after object is never used for any statistic.
        loaded.append((item,row.get('status'),row.get('before')))
    assert hashlib.sha256(encode(old_index)).hexdigest()==frozen['round1_input_hash_index_sha256'],'DX01 index differs'
    return frozen,config,bindings,loaded


def continuous(values,target=None):
    x=np.asarray(values,dtype=np.float64)
    if x.size==0:return dict(n=0,minimum=None,maximum=None,mean=None,std=None,maximum_absolute_deviation_from_target=None)
    result=dict(n=len(x),minimum=x.min(0).tolist(),maximum=x.max(0).tolist(),
        mean=x.mean(0).tolist(),std=x.std(0,ddof=0).tolist(),std_ddof=0)
    result['target']=target
    result['maximum_absolute_deviation_from_target']=None if target is None else np.max(np.abs(x-target),axis=0).tolist()
    return result


def joint_support(records,with_center,q):
    hist={}
    for source in SOURCES:
        vectors=[r['sampling']['joint_triplet_intervals'][0]+([r['sampling']['center_error_seconds']] if with_center else [])
            for r in records if r['source']==source and r['status']=='eligible']
        bins=Counter(tuple(np.floor(np.asarray(x)/q+.5).astype(np.int64).tolist()) for x in vectors)
        hist[source]=bins
    common=set.intersection(*(set(v) for v in hist.values()))
    return dict(quantum_seconds=q,rounding='floor(x/q+0.5), including signed center errors; ties toward positive infinity',
        vector=['lag_ab','lag_bc']+(['signed_center_error'] if with_center else []),
        histograms={s:[dict(bin_indices=list(k),count=v) for k,v in sorted(h.items())] for s,h in hist.items()},
        common_bins=[list(k) for k in sorted(common)],common_bin_count=len(common),
        common_support_counts={s:sum(h[k] for k in common) for s,h in hist.items()},
        means_exact_continuous_equality=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    root=a.repo_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    record_path=out/'candidate_c_existing_pts_records.json';audit_path=out/'candidate_c_existing_pts_audit.json'
    if record_path.exists() or audit_path.exists():raise FileExistsError('Preserve prior one-pass audit outputs')
    start=time.perf_counter();frozen,config,bindings,loaded=preflight(root)
    rows=[];calls=0
    for item,status,before in loaded:
        r=dict(sample_id=item['sample_id'],source=item['source'],ancestry_status=item['ancestry_status'],
            input_metadata_path=item['metadata_path'],input_sha256=item['sha256'],
            metadata_origin='before',timestamp_field_origin='best_effort_timestamp_time',
            native_integer_pts_verified=False,status='excluded',exclusion_reason=None,
            sampling=None,A_check=dict(status='not_evaluated'))
        try:
            if status!='ok':raise ValueError('Historical record status is not ok')
            if not isinstance(before,dict) or 'pts' not in before or 'frame_hashes' not in before:
                raise ValueError('Missing original timestamp or decoded-frame hash arrays')
            pts=before['pts'];hashes=before['frame_hashes']
            r['complete_original_timestamp_count']=len(pts);r['archived_decoded_frame_hash_count']=len(hashes)
            if not hashes or len(pts)!=len(hashes):raise ValueError('Complete original timestamps/frame hashes count mismatch')
            calls+=1
            indices,sampling=choose_centered_three(pts)
            r.update(status='eligible',sampling=sampling)
            try:
                ai,am=choose_six(pts)
                r['A_check']=dict(status='A_eligible',indices_equal=bool(np.array_equal(indices,ai[[1,3,5]])),
                    target_max_abs_difference=float(np.max(np.abs(np.array(sampling['targets'])-np.array(am['targets'])[[1,3,5]]))),
                    A_selected_indices=ai.tolist(),A_targets=am['targets'])
            except ValueError as exc:
                r['A_check']=dict(status='A_excluded_C_retained',reason=str(exc))
        except (ValueError,TypeError,KeyError) as exc:
            r['exclusion_reason']=str(exc)
            r['exclusion_scope']='metadata_or_sampling_eligibility_not_video_quality'
        rows.append(r)
    assert len(rows)==100 and len({r['sample_id'] for r in rows})==100
    counts={};stats={}
    fields={'joint_lags':('joint_triplet_intervals',[.5,.5]),'span':('actual_span_seconds',1.),
        'signed_sampling_errors':('timing_error',[0.,0.,0.]),'signed_center_error':('center_error_seconds',0.),
        'native_duration_estimate':('native_duration',None)}
    for source in SOURCES:
        cohort=[r for r in rows if r['source']==source];eligible=[r for r in cohort if r['status']=='eligible']
        counts[source]=dict(total=len(cohort),eligible=len(eligible),excluded=len(cohort)-len(eligible),
            exclusion_rate=1-len(eligible)/len(cohort))
        stats[source]={}
        for name,(key,target) in fields.items():
            values=[r['sampling'][key][0] if key=='joint_triplet_intervals' else r['sampling'][key] for r in eligible]
            stats[source][name]=continuous(values,target)
    support={name:[joint_support(rows,with_center,q) for q in QUANTA] for name,with_center in
        [('joint_lags',False),('joint_lags_and_center_error',True)]}
    # Recheck immutable inputs after computation, before publishing results.
    for name,digest in bindings.items():assert sha(root/name)==digest,'Input changed during audit: '+name
    write_new(record_path,dict(dispatch_id=frozen['dispatch_id'],plan_version=frozen['plan_version'],
        metadata_scope=frozen['metadata_scope'],records=rows))
    audit=dict(dispatch_id=frozen['dispatch_id'],task_id='DX04',plan_version=frozen['plan_version'],
        observed_utc=datetime.now(timezone.utc).isoformat(),status='descriptive_audit_completed',
        gate_scope='existing_metadata_diagnostic_only',scientific_gate_result='not_evaluated',
        counts=counts,continuous_by_source=stats,joint_support=support,
        C_sampler_calls=calls,A_comparisons=dict(C_eligible=sum(r['status']=='eligible' for r in rows),
            A_eligible=sum(r['A_check']['status']=='A_eligible' for r in rows),
            indices_match=sum(r['A_check'].get('indices_equal',False) for r in rows),
            target_max_abs_difference=max((r['A_check'].get('target_max_abs_difference',0.) for r in rows),default=None)),
        timestamp_provenance=dict(archived_field='before.pts',writer_source='ffprobe best_effort_timestamp_time',
            completeness_basis='archived timestamp count equals ordered decoded-frame hash count',
            native_integer_pts_verified=False,raw_media_or_pixels_reverified=False,after_pts_used=False),
        missing_complete_original_pts=['vript','hd_vg_130m','cogvideo'],
        native_duration_target=None,native_duration_target_note='No equality target; 1.5 s is eligibility minimum, not target duration',
        configuration=config,input_sha256=bindings,freeze_sha256=FREEZE_SHA,
        round1_input_hash_index_sha256=frozen['round1_input_hash_index_sha256'],
        records_sha256=sha(record_path),script_sha256=sha(Path(__file__)),
        work_plan_sha256=sha(root/'research-plan/WORK_PLAN.md'),
        elapsed_local_seconds=time.perf_counter()-start,numpy_version=np.__version__,python_version=sys.version.split()[0],
        server_accessed=False,ffprobe_executed=False,media_read=False,backbone_executed=False,gpu_used=False,
        classifier_fitted=False,optimizer_steps=0,detection_metrics_computed=False,
        real_fake_joint_support_established=False,formal_gate_passed=False,
        limitations=['Retrospective already exposed two-fake-source metadata only; ancestry unverified',
            'Equal bins are not continuous equality or scientific exchangeability',
            'Historical best-effort presentation estimates are not newly verified integer native PTS',
            'No real-source support, classification evidence or C parameter selection'])
    write_new(audit_path,audit)
    print(json.dumps({k:audit[k] for k in ('status','counts','C_sampler_calls','A_comparisons','continuous_by_source','joint_support','elapsed_local_seconds')},indent=2))


if __name__=='__main__':main()
