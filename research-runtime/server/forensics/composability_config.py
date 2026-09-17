"""Explicit software candidates; identities are not scientific acceptance."""
from copy import deepcopy
import hashlib
import json
import math
import re
from pathlib import Path

A = 'reference_a_six_v1'
C = 'candidate_c_centered3_v1'
A_TRIPLETS = ((0,1,2),(1,2,3),(2,3,4),(3,4,5),(0,2,4),(1,3,5))


def frame_count(candidate_id=A):
    if candidate_id == A: return 6
    if candidate_id == C: return 3
    raise ValueError('Unknown candidate; B is not implemented')


def triplets(candidate_id=A, branch_mode='temporal'):
    n = frame_count(candidate_id)
    if branch_mode == 'temporal': return A_TRIPLETS if candidate_id == A else ((0,1,2),)
    if branch_mode == 'static': return tuple((i,i,i) for i in range(n))
    if branch_mode == 'anchor_static' and candidate_id == C: return ((0,0,0),)
    raise ValueError('Unsupported branch for this candidate')


def descriptor(candidate_id=A, branch_mode='temporal', interior_control=False):
    groups = triplets(candidate_id,branch_mode)
    return dict(candidate_id=candidate_id,frame_count=frame_count(candidate_id),
        triplets=[list(t) for t in groups],branch_mode=branch_mode,aggregation='uniform_group_mean',
        control_scope=('anchor_only_local_diagnostic' if branch_mode == 'anchor_static' else
            'all_observed_frames_static_baseline' if branch_mode == 'static' else 'temporal_candidate'),
        middle_support='fixed_interior' if interior_control else 'full',
        sampler_sha256=hashlib.sha256((Path(__file__).parent/'mechanism_sampling.py').read_bytes()).hexdigest(),
        temperature=.1,scales=[1,2,4],grid=[16,16],target_span_seconds=1.25 if candidate_id==A else 1.,
        semantic_frames=list(range(frame_count(candidate_id))))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def cache_identity(candidate_id,branch_mode,provenance,interior_control=False):
    """For response maps only. No inference of compatibility from shape or name."""
    required={'original_sha256','processed_video_sha256','selected_indices','selected_pts',
              'backbone_sha256','preprocessing','precision','augmentation_identity'}
    if not required.issubset(provenance): raise ValueError('Missing frame/backbone provenance')
    n=frame_count(candidate_id)
    for key in ('original_sha256','processed_video_sha256','backbone_sha256'):
        if not isinstance(provenance[key],str) or not re.fullmatch('[a-f0-9]{64}',provenance[key]):
            raise ValueError('Invalid source/backbone SHA256')
    if any(type(i) is not int or i<0 for i in provenance['selected_indices']):
        raise ValueError('Invalid original indices')
    if len(provenance['selected_indices'])!=n or len(set(provenance['selected_indices']))!=n or len(provenance['selected_pts'])!=n:
        raise ValueError('Cache frame identity mismatch or repeated indices')
    if any(b<=a for a,b in zip(provenance['selected_indices'],provenance['selected_indices'][1:])):
        raise ValueError('Original frame indices must preserve presentation order')
    pts=provenance['selected_pts']
    if not all(isinstance(t,(int,float)) and not isinstance(t,bool) and math.isfinite(t) for t in pts) or any(b<=a for a,b in zip(pts,pts[1:])):
        raise ValueError('Invalid selected PTS')
    if any(not provenance[k] for k in ('preprocessing','precision','augmentation_identity')):
        raise ValueError('Empty processing provenance')
    record=dict(schema='composability_response_cache_v2',
        protocol=descriptor(candidate_id,branch_mode,interior_control),provenance=deepcopy(provenance))
    return dict(record=record,sha256=fingerprint(record))


def load_candidate_c_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    expected=dict(candidate_id=C,frame_count=3,eligibility_window_seconds=1.5,
        duration_estimator='last_minus_first_pts_plus_median_native_gap',
        target_offsets_from_center_seconds=[-.5,0.,.5],target_span_seconds=1.,
        maximum_selection_error_seconds=.125,numerical_tolerance_seconds=1e-6,
        tie_tolerance_seconds=1e-9,tie_break='earlier_original_frame',
        duplicate_or_interpolated_frames_allowed=False,grid=[16,16],temperature=.1,scales=[1,2,4],
        temporal_triplets=[[0,1,2]],static_triplets=[[0,0,0],[1,1,1],[2,2,2]],
        anchor_static_triplets=[[0,0,0]],aggregation='uniform_group_mean',
        semantic_frames_all_branches=[0,1,2],static_scope='all_observed_frames_static_baseline',
        anchor_scope='anchor_only_local_diagnostic',formal_training_authorized=False,
        real_source_joint_support_established=False,scope='offline_software_only',
        plan_version='cvpr27-20260918-v1.2')
    if config!=expected: raise ValueError('Configuration is not the reviewed candidate C software definition')
    return config


def candidate_training_specs(common_recipe,candidate_id=C,include_anchor=False):
    required={'data_manifest_sha256','split_sha256','seeds','augmentations','optimizer','checkpoint_selection','head'}
    if not required.issubset(common_recipe) or 'protocol' in common_recipe or 'branch_mode' in common_recipe:
        raise ValueError('Incomplete or conflicting training recipe')
    modes=['temporal','static']+(['anchor_static'] if include_anchor else [])
    specs=[dict(deepcopy(common_recipe),protocol=descriptor(candidate_id,mode)) for mode in modes]
    validate_candidate_training_specs(*specs)
    return tuple(specs)


def validate_candidate_training_specs(*specs):
    if len(specs) not in (2,3): raise ValueError('Expected temporal/static and optional anchor')
    modes=['temporal','static']+(['anchor_static'] if len(specs)==3 else [])
    first=specs[0]; candidate=first['protocol']['candidate_id']
    common={k:v for k,v in first.items() if k!='protocol'}
    required={'data_manifest_sha256','split_sha256','seeds','augmentations','optimizer','checkpoint_selection','head'}
    if not required.issubset(common) or not {'feature_dim','width','hidden'}.issubset(common['head']):
        raise ValueError('Missing reproducible training/head configuration')
    for spec,mode in zip(specs,modes):
        if spec['protocol']!=descriptor(candidate,mode): raise ValueError('Incorrect candidate/control identity')
        if {k:v for k,v in spec.items() if k!='protocol'}!=common:
            raise ValueError('Unmatched data, seeds, capacity or training/selection recipe')
