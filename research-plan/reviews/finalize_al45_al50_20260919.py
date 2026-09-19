from pathlib import Path
from datetime import datetime
import json,hashlib,os,sys,copy,subprocess
root=Path.cwd()
sys.path.insert(0,str(root/'research-plan/task-hermes'))
import board
project=root/'research-plan/task-hermes/project.json'
before=project.read_bytes(); data=json.loads(before); cc=data['continuous_collaboration']; by=board.index(data)
now=datetime.now().astimezone().isoformat(timespec='seconds')
assert len(by)==79 and by['AL50']['status']=='ready' and 'AL51' not in by
assert cc['current_dispatch']['id']=='cc-al50-planner-matching-margin-20260919'
reviews=root/'research-plan/reviews'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for tid in ['AL46','AL47']:
 t=by[tid];file=(project.parent/t['review']).resolve()
 t['draft_hash_history']=[{'old_sha256':t['artifact_sha256'],'old_completed_at':t['completed_at'],
   'reason':'In-turn report expanded with full proof and precise null/support assumptions before final commit; final bytes now bound'}]
 t.update(artifact_sha256=sha(file),completed_at=now,finalized_at=now,dispatch_status='completed_scoped_manual_review',
   evidence_kind='manual_symbolic_or_protocol_design; no numerical test batch claimed')
 if tid=='AL47':
  t['artifacts']=list(dict.fromkeys(t['artifacts']+[t['review']]))
  t['next_action']='AL48 removed as duplicate ofAL16; followAL51 soft mixing decomposition, not repeated error propagation'
by['AL48'].update(review_scope='Deduplicated against AL16; proposed draft not accepted as a new execution or new result',
 evidence_kind='deduplication_decision',
 artifact_sha256=sha(reviews/'AL48_DEDUPLICATION_DECISION_20260919.md'))
by['AL48']['artifacts']=list(dict.fromkeys(by['AL48']['artifacts']+['../reviews/AL48_DEDUPLICATION_DECISION_20260919.md']))
by['AL48']['unexecuted_draft_receipt']={'path':'../reviews/AL48_OR1_ERROR_AWARE_DECISION_MARGIN_EXACT_20260919.json',
 'sha256':sha(reviews/'AL48_OR1_ERROR_AWARE_DECISION_MARGIN_EXACT_20260919.json'),'role':'manual_checklist_not_execution_evidence','pass_not_accepted':True}
# Reject AL50's ungrounded global conclusion while retaining all actual arithmetic outputs.
original_report=reviews/'AL50_MATCHING_PERTURBATION_MARGIN_REVIEW_20260919.md'
original_receipt=reviews/'AL50_MATCHING_PERTURBATION_EXACT_20260919.json'
exact=json.loads(original_receipt.read_text(encoding='utf-8'))
assert len(exact['checks'])==7 and exact['d_alternative'][-1]=='1/2'
correction=reviews/'AL50_REVIEW_CORRECTION_20260919.md'
by['AL50'].update(status='done',gate_result='fail',completed_at=now,reviewed_by='planagent',
 review='../reviews/AL50_REVIEW_CORRECTION_20260919.md',artifact_sha256=sha(correction),
 hypothesis_result='heterogeneous_two_matching_bound_not_sufficient; numeric_lists_do_not_define_verified_common_graph',
 review_scope='Symbolic correction; original seven arithmetic checks preserved but no global matching identity certificate',
 execution_stage='original_receipt_not_accepted_after_review',
 next_action='Do not rerun or extend AL50 lists; retain corrected all-competitor margin formula for future preregistration')
by['AL50']['artifacts']+=['../reviews/AL50_MATCHING_PERTURBATION_EXACT_20260919.json',
 '../reviews/AL50_REVIEW_CORRECTION_20260919.md']
by['AL50']['superseded_original_claim']={'report_sha256':sha(original_report),'receipt_sha256':sha(original_receipt),
 'original_report_check_count':8,'actual_archive_assertion_categories':7,'original_report_pass_not_accepted':True,
 'unified_graph_or_competing_matchings_specified':False,'nominal_competitor_at_caliper_boundary':True}
by['AL49']['artifacts']=list(dict.fromkeys(by['AL49']['artifacts']))
by['AL49']['dispatch_status']='completed_failed_execution_contract'
by['AL49']['evidence_kind']='fixed_math_counterexample_with_disclosed_failed_assertion_and_reruns'
# Close outstanding duplicate/inconsistent package labels with a transparent archive.
seen=set(); cleaned=[]; duplicate_history=[]
for h in cc['dispatch_history']:
 if h['id'] in seen:
  duplicate_history.append(h)
  continue
 seen.add(h['id'])
 if h['id']=='cc-al48-planner-error-margin-20260919':
  h.update(status='closed_as_duplicate',gate_result='not_applicable')
 if h['id']=='cc-al46-planner-matched-direction-20260919':
  h['draft_completion_recorded_at']=h.get('completed_at');h['completed_at']=now
 if h['id']=='cc-al47-planner-null-probe-design-20260919':
  h['draft_completion_recorded_at']=h.get('completed_at');h['completed_at']=now
 cleaned.append(h)
cc['dispatch_history']=cleaned
cc['current_dispatch'].update(status='completed_failed_review',completed_at=now,review=by['AL50']['review'],
 outcome='Reject only-second-best heterogeneous error certificate; preserve7 arithmetic assertions, no real matching')
cc['dispatch_history'].append(cc['current_dispatch'])
order=root/'research-plan/AL51_SOFT_MIXING_DECOMPOSITION_AUDIT_20260919.md'
new={'id':'AL51','milestone':'M2','title':'软混合响应的原次序项与插值曲率项分解',
 'assignee':'planagent','parents':['AL12','AL19','AL43','AL49'],'requires_pass':['AL12','AL19','AL43'],
 'status':'ready','gate_result':'not_evaluated','gate_scope':'soft_mixing_mechanism_decomposition',
 'hypothesis':'有限h顺序响应可能同时含原R次序与插值弦偏离；仅K非零不足以归因为原解码次序。',
 'work':['逐项推导K_h=C+(J_a-J_b)/h并说明作用域','审查C2条件下插值项尺度及极限，分开线性和非线性','设计至多一个未执行的分解对照并明确额外调用成本'],
 'acceptance':['不重跑AL49或改变其fail','未知平滑性/真实作用域不填已证','仅条件机制设计，不把分解当原创算法或实证'],
 'artifacts':['../reviews/AL51_SOFT_MIXING_DECOMPOSITION_REVIEW_20260919.md'],
 'work_order':'../AL51_SOFT_MIXING_DECOMPOSITION_AUDIT_20260919.md','work_order_sha256':sha(order),
 'plan_version':data['plan_version'],'prepared_at':now,'due_at':'2026-09-23T22:00:00+08:00',
 'execution_thread_id':cc['plan_thread_id'],'implementation_authorized':False,'scientific_innovation_gate_passed':False,
 'resource_policy':{'local_cpu':True,'threads':2,'server_access':False,'real_media':False,'gpu':False,
  'classifier_training':False,'large_downloads':False,'research_runtime_execution':False},
 'hypothesis_result':'not_evaluated','failure_parent_pass_not_required_reason':'AL49 arithmetic is a question cue; its failed execution protocol remains failed and is not used as a success gate'}
data['tasks'].append(new)
cc['current_dispatch']={'id':'cc-al51-planner-soft-decomposition-20260919','task_ids':['AL51'],'executor_role':'planagent',
 'executor_thread_id':cc['plan_thread_id'],'host_id':'local','status':'prepared','prepared_at':now,
 'work_order':new['work_order'],'work_order_sha256':new['work_order_sha256'],'plan_version':data['plan_version'],
 'plan_sha256':sha(root/'research-plan/WORK_PLAN.md'),'scope':'Direct soft-path mechanism decomposition; no model/media/server/GPU',
 'remote_send_required':False,'background_process_running':False}
cc.update(last_coordinator_activity_at=now,last_local_review_at=now,last_substantive_review=by['AL50']['review'],
 prepared_independent_task_ids=['AL51','AL36'],active_and_prepared_work={'running':[],'prepared_independent':['AL51','AL36'],
 'executor_blocked':['AL36'],'source_blocked':['AL45']},
 local_execution={'task_ids':['AL46','AL47','AL48','AL49','AL50'],'executor_role':'planagent',
 'status':'scoped_reviews_finalized_with_explicit_failures_and_deduplication','finalized_at':now,
 'work_area':'research-plan/reviews','next_prepared_task_id':'AL51','background_process_running':False})
data['candidate_protocols']['OR1'].update(matched_direction_rank_review_task='AL46',
 null_probe_envelope_task='AL47',duplicate_score_margin_task='AL48',
 original_to_soft_commutation_counterexample='AL49 fixed arithmetic verified, one-run contract failed',
 matching_stability_review='AL50 failed; corrected global margin in separate report',
 next_independent_tasks=['AL51','AL36'])
data['plan_revisions'].append({'at':now,'plan_version':data['plan_version'],'type':'comparison_gap_and_null_mechanism_audits',
 'plan_sha256':sha(root/'research-plan/WORK_PLAN.md'),'reason':'AL45 remains source-blocked; scoped AL46/AL47 design; AL48 duplicate; AL49 execution fail; AL50 global certificate withdrawn; direct AL51 decomposition prepared','budget_dates_thresholds_changed':False})
data['updated_at']=now
audit_files=['AL45_SELECTION_PROOF_AND_LIMITS_20260919.md','AL45_SOURCE_AND_REVIEW_LIMITS_20260919.json',
 'AL46_MATCHED_DIRECTION_RANK_REVIEW_20260919.md','AL47_OR1_NULL_PROBE_ENVELOPE_DESIGN_20260919.md',
 'AL47_OR1_NULL_PROBE_ENVELOPE_REVIEW_20260919.md','AL48_DEDUPLICATION_DECISION_20260919.md',
 'AL49_SOFT_COMPOSITION_NULL_REVIEW_20260919.md','AL49_POLYNOMIAL_REVIEW_20260919.json',
 'AL50_REVIEW_CORRECTION_20260919.md']
review_record={'recorded_at':now,'evidence_kind':'final_manual_review_and_digest_binding',
 'task_verdicts':{tid:[by[tid]['status'],by[tid]['gate_result']] for tid in ['AL45','AL46','AL47','AL48','AL49','AL50']},
 'authoritative_files':{name:sha(reviews/name) for name in audit_files},'duplicate_dispatch_entries_removed_from_active_history':duplicate_history,
 'original_source_and_failure_outputs_preserved':True,'actual_new_numeric_outputs':['AL49 nested and expanded arithmetic with disclosed failures','AL50 seven assert categories insufficient for claimed global matching certificate'],
 'no_new_numeric_replay_this_finalization':True,'independent_scientific_review':False,'task_table_structural_validation_not_scientific_validation':True,
 'prior_project_sha256':hashlib.sha256(before).hexdigest(),
 'latest_committed_project':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
receipt_path=reviews/'AL45_AL50_FINAL_REVIEW_RECORD_20260919.json'
assert not receipt_path.exists()
assert not board.validate(data),board.validate(data)
assert [t['id'] for t in board.available(data)]==['AL51']
assert not {'RS06','RS07','RS08'} & {t['id'] for t in board.available(data)}
assert data['budget']['spent_cny'] is None and data['budget']['used_gpu_hours'] is None
assert project.read_bytes()==before
with receipt_path.open('x',encoding='utf-8',newline='\n') as f:json.dump(review_record,f,ensure_ascii=False,indent=2);f.write('\n')
tmp=project.with_name('project.review-final.tmp')
tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
assert project.read_bytes()==before
os.replace(tmp,project)
print(json.dumps({'finalized_at':now,'tasks':len(data['tasks']),'AL45':'not_evaluated_source_blocked','AL48':'deduplicated','AL49':'fail','AL50':'fail','ready':'AL51','no_research_thread_retry':True}))
