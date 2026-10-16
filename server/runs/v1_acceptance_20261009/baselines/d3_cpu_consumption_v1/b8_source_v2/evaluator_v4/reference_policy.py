"""Known reference policies, staged slot maps, and explicit temporal controls."""
from fractions import Fraction
import hashlib,json

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def ordered(indices,pts):return all(a<=b for a,b in zip(indices,indices[1:])) and all(a<=b for a,b in zip(pts,pts[1:]))
def repeat_suffix(indices,pts):
    if not ordered(indices,pts):raise ValueError('repeat_last_order_rewind')
    first_repeat=next((i for i in range(1,len(indices)) if indices[i]==indices[i-1]),None)
    if first_repeat is not None:
        if any(x!=indices[first_repeat-1] for x in indices[first_repeat:]):raise ValueError('repeat_last_internal_repeat_not_suffix')
        if any(x!=pts[first_repeat-1] for x in pts[first_repeat:]):raise ValueError('repeat_last_PTS_not_suffix')
    return True

def validate_chain(chain,final_indices,final_pts):
    # source positions, not tensor/JPEG similarity, are the temporal identity.
    current=list(chain['base_frame_indices']);p=list(chain['base_selected_pts'])
    if len(current)!=len(p) or not current or len(set(current))!=len(current) or not ordered(current,p):raise ValueError('policy_chain_base_native_identity')
    native={i:t for i,t in zip(current,p)};states=[]
    for ordinal,stage in enumerate(chain['stages']):
        op=stage['operation'];mapping=stage['output_to_input_slots'];n=len(current)
        if stage['input_slots']!=n or not mapping or any(type(x) is not int or not 0<=x<n for x in mapping):raise ValueError('policy_stage_slot_mapping')
        out=[current[i] for i in mapping];outp=[p[i] for i in mapping]
        if op=='native_selection':
            if len(set(mapping))!=len(mapping) or mapping!=sorted(mapping):raise ValueError('native_selection_not_unique_ordered')
        elif op in ('author_fps_resampling','display_interval_sampling'):
            if mapping!=sorted(mapping) or not ordered(out,outp):raise ValueError('resampling_stage_native_rewind')
            if op=='display_interval_sampling':
                starts=stage['interval_start_seconds'];durations=stage['interval_duration_seconds'];targets=stage['target_seconds']
                if len(starts)!=len(mapping) or len(durations)!=len(mapping) or len(targets)!=len(mapping):raise ValueError('display_interval_slot_length')
                for target,start,duration in zip(targets,starts,durations):
                    target,start,duration=Fraction(str(target)),Fraction(str(start)),Fraction(str(duration))
                    if duration<=0 or target<start-Fraction(1,1000000) or target>=start+duration+Fraction(1,1000000):raise ValueError('display_interval_target_not_played_frame')
        elif op in ('repeat_last_padding','processor_temporal_tail_padding'):
            if len(mapping)<n or mapping[:n]!=list(range(n)) or any(i!=n-1 for i in mapping[n:]):raise ValueError('repeat_last_stage_not_prefix_plus_last_suffix')
            if op=='processor_temporal_tail_padding':
                factor=stage['temporal_patch_size'];expected=(-n)%factor
                if factor<1 or len(mapping)!=n+expected:raise ValueError('processor_temporal_padding_count')
        elif op=='explicit_temporal_order_control':
            if sorted(mapping)!=list(range(n)):raise ValueError('temporal_control_requires_explicit_permutation')
        else:raise ValueError('unknown_reference_stage_operation')
        if stage['evidence_status']!='observed':raise ValueError('known_reference_stage_evidence_not_observed')
        states.append({'stage':ordinal,'operation':op,'input_slots':n,'output_slots':len(mapping),'unique_native_frames':len(set(out)),'added_native_frames':0,'rules_verified':True});current,p=out,outp
    if current!=list(final_indices) or p!=list(final_pts):raise ValueError('policy_chain_final_mapping_mismatch')
    return {'status':'known_stage_rules_verified','stages':states,'slots':len(current),'unique_native_frames':len(set(current)),'source_authenticity_or_historical_reference_certified':False}

def verify_row_policy(r):
    indices=r['frame_indices'];pts=r['native_time']['selected_pts'];policy=r.get('reference_frame_policy',{'strategy':'none'});strategy=policy['strategy']
    if r['track']=='matched_processing':
        if strategy!='none':raise ValueError('matched_reference_policy_not_allowed')
        return {'status':'matched_unique_ordered','strategy':'none'}
    if strategy=='none':
        if len(set(indices))!=len(indices) or not ordered(indices,pts):raise ValueError('native_reference_unexplained_repeat_or_order')
        return {'status':'ordered_no_repetition','strategy':strategy}
    if strategy=='author_repeat_last':repeat_suffix(indices,pts);return {'status':'known_repeat_last_suffix_verified','strategy':strategy}
    if strategy=='author_fps_resampling':
        if not ordered(indices,pts):raise ValueError('fps_resampling_order_rewind')
        return {'status':'known_monotonic_FPS_resampling_pattern','strategy':strategy,'publisher_or_decoder_equivalence_certified':False}
    if strategy=='explicit_time_control':
        if policy.get('control_processing_id')!=r['processing_id'] or r['processing_id']=='identity':raise ValueError('temporal_control_processing_identity_missing')
        if len(set(indices))!=len(indices):raise ValueError('simple_temporal_control_repetition_requires_stages')
        return {'status':'explicit_order_control_not_author_reference','strategy':strategy}
    if strategy=='staged_author_input':
        chain=policy['chain']
        if digest(chain)!=policy['policy_sha256']:raise ValueError('reference_stage_chain_hash_changed')
        controls=any(s['operation']=='explicit_temporal_order_control' for s in chain['stages'])
        if controls and (policy.get('control_processing_id')!=r['processing_id'] or r['processing_id']=='identity'):raise ValueError('stage_control_processing_identity_missing')
        return validate_chain(chain,indices,pts)|{'strategy':strategy}
    raise ValueError('unknown_reference_policy')
