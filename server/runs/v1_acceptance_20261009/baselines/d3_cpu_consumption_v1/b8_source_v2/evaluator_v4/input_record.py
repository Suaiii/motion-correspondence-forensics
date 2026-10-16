"""A7 v4 scoreless record admission; prediction arithmetic remains unchanged."""
import json,argparse,sys
from pathlib import Path
from jsonschema import Draft202012Validator
from reference_policy import verify_row_policy
from record_contract import verify_contract,ContractUnverified
ROOT=Path(__file__).resolve().parent

def validate_input_record(r,timeline_evidence=None):
 schema=json.loads((ROOT/'input_record_schema_v2.json').read_text());Draft202012Validator(schema).validate(r)
 idx=r['frame_indices'];pts=r['selected_native_integer_PTS']
 if len(idx)!=r['actual_input_slots'] or len(pts)!=len(idx):raise ValueError('input_record_slot_PTS_mismatch')
 if len(set(idx))!=r['unique_native_frames']:raise ValueError('input_record_unique_native_count_mismatch')
 if r['added_native_frames']!=0 or r['encoder_head_calls']!=0 or r['GPU_started']:raise ValueError('input_record_scope_or_native_promotion')
 contract=verify_contract(r,timeline_evidence)
 row={'track':'native_reference','frame_indices':idx,'native_time':{'selected_pts':pts,'time_base':r['native_time_base']},'reference_frame_policy':r['reference_frame_policy'],'processing_id':r.get('processing_id','author_reference/'+r['method'])}
 verdict=verify_row_policy(row)
 if r['model_consumed_HW'] is not None or r['historical_reference_certified'] or r['data_or_scientific_gate_passed']:raise ValueError('input_record_unexecuted_model_or_gate_promoted')
 return {'status':'observed_current_input_rules_verified','contract_version':'input_contract/4.0','sample_id':r['sample_id'],'method':r['method'],'actual_slots':len(idx),'unique_native_frames':len(set(idx)),'policy':verdict,'cross_field_contract':contract,'source_raster_HW':r['source_raster_HW'],'observed_preprocessed_HW':r['observed_preprocessed_HW'],'model_consumed_HW':None,'current_backend_only':True,'source_authenticity_verified':False,'scientific_gate_passed':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('record');p.add_argument('--timeline-evidence');a=p.parse_args()
 try:
  evidence=json.loads(Path(a.timeline_evidence).read_text(encoding='utf-8')) if a.timeline_evidence else None
  result=validate_input_record(json.loads(Path(a.record).read_text(encoding='utf-8')),evidence)
  print(json.dumps({'accepted':True,'result':result}));return 0
 except Exception as e:
  print(json.dumps({'accepted':False,'status':'unverified' if isinstance(e,ContractUnverified) else 'rejected','error':type(e).__name__+': '+str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())
