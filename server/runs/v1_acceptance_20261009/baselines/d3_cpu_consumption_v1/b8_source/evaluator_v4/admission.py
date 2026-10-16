"""One frozen schema gate for CLI and public library entry points."""
import hashlib,json,math,re
from fractions import Fraction
from pathlib import Path
from jsonschema import Draft202012Validator
from schema_fingerprints import SCHEMA_SHA256
from reference_policy import verify_row_policy
ROOT=Path(__file__).resolve().parent
def frozen_validator(name):
    b=(ROOT/name).read_bytes()
    if hashlib.sha256(b).hexdigest()!=SCHEMA_SHA256[name]:raise ValueError('frozen_schema_hash_changed:'+name)
    schema=json.loads(b);Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_rows(rows):
    if not isinstance(rows,(list,tuple)):raise ValueError('materialized_prediction_rows_required')
    v=frozen_validator('prediction_schema_v2.json');seen=set()
    for index,r in enumerate(rows):
        errors=sorted(v.iter_errors(r),key=lambda e:str(list(e.absolute_path)))
        if errors:
            e=errors[0];raise ValueError('schema_validation_failed:row'+str(index)+':'+str(list(e.absolute_path))+':'+e.message)
        # JSON Schema numeric integer semantics accept8.0; slots/PTS need true integers.
        frames=r['frame_indices'];pts=r['native_time']['selected_pts'];cb=r['compute_budget']
        if type(r['label_fake']) is not int or any(type(x) is not int or x<0 for x in frames) or any(type(x) is not int for x in pts):raise ValueError('integer_frame_or_PTS_contract')
        if type(cb['n_frames']) is not int or cb['n_frames']!=len(frames) or len(pts)!=len(frames):raise ValueError('frame_slots_selected_pts_n_frames_mismatch')
        if any(type(x) is not int or x<1 for x in cb['input_hw']):raise ValueError('invalid_input_hw')
        unique=len(set(frames))
        if 'n_unique_native_frames' in cb and (type(cb['n_unique_native_frames']) is not int or cb['n_unique_native_frames']!=unique):raise ValueError('unique_frame_budget_mismatch')
        tb=Fraction(r['native_time']['time_base'])
        if tb<=0 or tb>1 or tb.numerator>2147483647 or tb.denominator>2147483647:raise ValueError('unsupported_video_rational_time_base')
        if any(x < -9223372036854775808 or x>9223372036854775807 for x in pts):raise ValueError('PTS_outside_int64')
        mapping={}
        for i,p in zip(frames,pts):
            if i in mapping and mapping[i]!=p:raise ValueError('same_native_index_different_PTS')
            mapping[i]=p
        if len(set(mapping.values()))!=len(mapping):raise ValueError('different_native_index_same_PTS')
        repeated=unique!=len(frames)
        policy=r.get('reference_frame_policy',{}).get('strategy','none')
        if r['track']=='matched_processing':
            if repeated or frames!=sorted(frames):raise ValueError('matched_frames_must_be_unique_ordered')
            if any(b<=a for a,b in zip(pts,pts[1:])):raise ValueError('nonincreasing_pts')
            if policy!='none':raise ValueError('matched_processing_cannot_declare_reference_repetition')
        elif repeated and policy not in ('author_repeat_last','author_fps_resampling','staged_author_input'):raise ValueError('reference_repetition_policy_missing')
        verify_row_policy(r)
        if r['label_fake']==0 and r['generator_family']!='real':raise ValueError('real_generator_family')
        if r['label_fake']==1 and r['generator_family']=='real':raise ValueError('fake_generator_family')
        for key in ('score_raw','score_fake'):
            if type(r[key]) not in (float,int) or not math.isfinite(r[key]):raise ValueError('nonfinite_score')
        transform={'identity':lambda x:x,'negate':lambda x:-x,'one_minus':lambda x:1-x}[r['score_transform']]
        if not math.isclose(r['score_fake'],transform(r['score_raw']),rel_tol=1e-12,abs_tol=1e-12):raise ValueError('score_direction')
        for key in ('decode_wall_seconds','encoder_wall_seconds','head_wall_seconds','peak_memory_bytes'):
            if cb[key] is not None and (type(cb[key]) not in (float,int) or not math.isfinite(cb[key]) or cb[key]<0):raise ValueError('bad_compute_budget')
        if cb['peak_memory_bytes'] is not None and type(cb['peak_memory_bytes']) is not int:raise ValueError('integer_memory_bytes_required')
        if r['ancestry_status']=='fixture' and not r['fixture']:raise ValueError('fixture_ancestry_marker_conflict')
        # fixture=true is retained even if ancestry isunknown/verified; it never looksreal.
        key=tuple(r[k] for k in ('method_id','method_revision','checkpoint_sha256','preprocessing_sha256','split_sha256','track','processing_id','seed'))+(r['role'],r.get('cohort_id'),r['sample_id'])
        if key in seen:raise ValueError('duplicate_video_prediction')
        seen.add(key)
    return rows

def admission_metadata(rows):
    return {'contract_version':'admission/3.0','prediction_schema_sha256':SCHEMA_SHA256['prediction_schema_v2.json'],'n_rows':len(rows),'n_input_slots':sum(r['compute_budget']['n_frames'] for r in rows),'sum_unique_native_frames_per_video':sum(len(set(r['frame_indices'])) for r in rows),'reference_policy_records':[verify_row_policy(r) for r in rows],'synthetic_identity':any(r['fixture'] or r['ancestry_status']=='fixture' for r in rows),'scientific_gate_passed':False}
