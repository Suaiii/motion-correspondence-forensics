"""Exact cross-field clock closure and method-specific returned-slot boundaries."""
from fractions import Fraction
from reference_policy import digest
TOL=Fraction(1,1000000)  # inherited v3 display tolerance; never retuned

class ContractUnverified(ValueError):pass

def origin_offset(r,evidence):
 mapping=r.get('timeline_mapping')
 if mapping is None:return Fraction(0), 'direct_native_time_agreement_no_offset_inferred'
 if set(mapping)!={'mode','offset_seconds','evidence_sha256'} or mapping['mode']!='native_plus_observed_offset':raise ValueError('timeline_mapping_contract')
 offset=Fraction(mapping['offset_seconds']);key=mapping['evidence_sha256']
 if not evidence or key not in evidence:raise ContractUnverified('timeline_origin_evidence_missing')
 e=evidence[key]
 if digest(e)!=key:raise ValueError('timeline_origin_evidence_hash_mismatch')
 for k in ['input_sha256','raw_author_trace_sha256','native_time_base']:
  if e[k]!=r[k]:raise ValueError('timeline_origin_evidence_identity_mismatch')
 chain=r['reference_frame_policy']['chain']
 if e['native_frame_indices']!=chain['base_frame_indices'] or e['native_integer_PTS']!=chain['base_selected_pts']:raise ValueError('timeline_origin_evidence_native_mapping_mismatch')
 if Fraction(e['offset_seconds'])!=offset:raise ValueError('timeline_origin_evidence_offset_mismatch')
 if len(e['display_start_seconds'])!=len(e['native_integer_PTS']):raise ValueError('timeline_origin_evidence_length')
 tb=Fraction(r['native_time_base'])
 for p,t in zip(e['native_integer_PTS'],e['display_start_seconds']):
  if abs(Fraction(str(t))-(p*tb+offset))>TOL:raise ValueError('timeline_origin_evidence_observed_pair_mismatch')
 return offset,'explicit_offset_bound_to_external_hash_evidence'

def verify_contract(r,timeline_evidence=None):
 tb=Fraction(r['native_time_base'])
 if tb<=0:raise ValueError('native_time_base_nonpositive')
 policy=r['reference_frame_policy'];chain=policy.get('chain')
 if policy['strategy']!='staged_author_input' or not chain:raise ContractUnverified('scoreless_return_boundary_requires_staged_trace')
 current=list(chain['base_frame_indices']);pts=list(chain['base_selected_pts'])
 if not current or len(current)!=len(pts) or any(type(x) is not int for x in current+pts):raise ValueError('native_index_PTS_integer_binding')
 offset,origin=origin_offset(r,timeline_evidence);states=[];processor_boundary=None;interval_slots=0
 for ordinal,s in enumerate(chain['stages']):
  n=len(current);m=s['output_to_input_slots']
  if s['input_slots']!=n or not m or any(type(x) is not int or x<0 or x>=n for x in m):raise ValueError('policy_stage_slot_mapping')
  if s['operation']=='processor_temporal_tail_padding':
   if processor_boundary is None:processor_boundary=n
  elif processor_boundary is not None:raise ContractUnverified('postprocessor_nonpadding_stage_boundary_unverified')
  out=[current[x] for x in m];p=[pts[x] for x in m]
  if s['operation']=='display_interval_sampling':
   starts=s['interval_start_seconds'];dur=s['interval_duration_seconds'];target=s['target_seconds']
   if not(len(starts)==len(dur)==len(target)==len(p)):raise ValueError('display_interval_slot_length')
   for j,(native,start,duration,t) in enumerate(zip(p,starts,dur,target)):
    start=Fraction(str(start));duration=Fraction(str(duration));t=Fraction(str(t));expected=native*tb+offset
    if abs(start-expected)>TOL:raise ValueError('native_PTS_timebase_display_start_conflict:stage=%d:slot=%d'%(ordinal,j))
    if duration<=0 or t<start-TOL or t>=start+duration+TOL:raise ValueError('display_target_not_within_bound_native_frame')
   interval_slots+=len(p)
  states.append({'stage':ordinal,'operation':s['operation'],'input_slots':n,'output_slots':len(out)})
  current,pts=out,p
 if current!=r['frame_indices'] or pts!=r['selected_native_integer_PTS']:raise ValueError('selected_PTS_final_stage_mapping_conflict')
 method=r['method'];actual=r['actual_input_slots'];loader=r['loader_or_decoder_slots']
 if method in ['d3','restrav']:
  if processor_boundary is not None:raise ContractUnverified('processor_stage_not_in_current_D3_ReStraV_loader_profile')
  expected=len(current);boundary='returned_decoder_reader_tensor_slots_after_decoder_tail'
  shape=r.get('actual_tensor_shape')
  if shape is not None and (len(shape)!=4 or shape[0]!=actual or shape[-2:]!=r['observed_preprocessed_HW']):raise ValueError('decoder_tensor_slots_or_raster_conflict')
 else:
  expected=processor_boundary if processor_boundary is not None else len(current);boundary='loader_slots_before_processor_temporal_tail'
  grid=r.get('processor_grid_thw')
  if not grid or len(grid)!=1 or len(grid[0])!=3:raise ContractUnverified('native_processor_grid_boundary_missing')
  if any(type(x) is not int or x<=0 for x in grid[0]):raise ValueError('native_processor_grid_invalid')
  # Current locked Qwen processor has temporal_patch_size2. Other revisions
  # remain explicitly unverified instead of borrowing this current contract.
  if r.get('processor_config_revision')!='66285546d2b821cf421d4f5eb2576359d3770cd3':raise ContractUnverified('native_processor_config_boundary_unverified')
  if grid[0][0]*2!=actual:raise ValueError('processor_grid_logical_slot_conflict')
  if any(s['operation']=='processor_temporal_tail_padding' and s['temporal_patch_size']!=2 for s in chain['stages']):raise ValueError('processor_temporal_factor_config_conflict')
  if r.get('processor_logical_padding_slots')!=actual-expected:raise ValueError('processor_padding_vs_loader_count_conflict')
  rows=grid[0][0]*grid[0][1]*grid[0][2]
  if r.get('observed_premerge_patch_rows')!=rows:raise ValueError('processor_grid_patch_row_count_conflict')
  if r.get('actual_tensor_shape') is not None and r['actual_tensor_shape']!=r.get('actual_pixel_tensor_shape'):raise ValueError('processor_actual_tensor_shape_conflict')
  if r.get('actual_pixel_tensor_shape',[None])[0]!=rows:raise ValueError('processor_tensor_row_boundary_conflict')
 if loader!=expected:raise ValueError('loader_count_return_boundary_conflict:expected=%d:actual=%d'%(expected,loader))
 return {'status':'cross_field_current_contract_verified','native_time_base':str(tb),'display_slots_bound':interval_slots,'timeline_origin':origin,'loader_boundary':boundary,'expected_loader_slots':expected,'final_logical_slots':actual,'stages':states,'source_authenticity_verified':False}
