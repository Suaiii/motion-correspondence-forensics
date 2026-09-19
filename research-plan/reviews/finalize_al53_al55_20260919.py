from pathlib import Path
from datetime import datetime
import hashlib,json,os,sys,copy,subprocess
root=Path.cwd()
sys.path.insert(0,str(root/'research-plan/task-hermes'))
import board
project=root/'research-plan/task-hermes/project.json'
before=project.read_bytes(); data=json.loads(before); cc=data['continuous_collaboration']; by=board.index(data)
now=datetime.now().astimezone().isoformat(timespec='seconds')
assert len(by)==84 and by['AL53']['status']=='done' and by['AL54']['status']=='done'
assert by['AL55']['status']=='ready' and 'AL56' not in by
assert cc['current_dispatch']['id']=='cc-al55-planner-minimum-info-20260919'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reviews=root/'research-plan/reviews'
source_files=[
 'research-plan/AL53_ENDPOINT_PARTIAL_IDENTIFICATION_AUDIT_20260919.md',
 'research-plan/reviews/AL51_SOFT_MIXING_DECOMPOSITION_REVIEW_20260919.md',
 'research-plan/reviews/AL52_FINITE_PROBE_IDENTIFIABILITY_REVIEW_20260919.md',
 'research-plan/reviews/AL16_OR1_NUMERICAL_REVIEW_20260919.md',
 'research-plan/reviews/AL35_MINIMUM_MECHANISM_PROTOCOL_DRAFT_20260919.md',
 'research-plan/reviews/AL45_SELECTION_PROOF_AND_LIMITS_20260919.md']
drafts=[
 'AL53_ENDPOINT_PARTIAL_IDENTIFICATION_REVIEW_20260919.md',
 'AL53_ENDPOINT_PARTIAL_IDENTIFICATION_EXACT_20260919.json',
 'AL54_OR1_CLAIM_EVIDENCE_NO_GO_REVIEW_20260919.md',
 'AL54_OR1_CLAIM_EVIDENCE_NO_GO_EXACT_20260919.json',
 'AL55_OR1_MINIMUM_NEW_INFORMATION_REVIEW_20260919.md']
finals=[
 'AL53_ENDPOINT_BOUNDS_FINAL_REVIEW_20260919.md',
 'AL54_PLANNER_ADMISSION_REVIEW_20260919.md',
 'AL55_DEDUPLICATION_DECISION_20260919.md']
record={
 'recorded_at':now,'evidence_kind':'manual_final_review_with_conditional_derivations_and_deduplication',
 'input_sha256':{rel:sha(root/rel) for rel in source_files},
 'authoritative_final_sha256':{name:sha(reviews/name) for name in finals},
 'retained_draft_sha256':{name:sha(reviews/name) for name in drafts},
 'draft_exact_json_role':'Manually authored checklist, not executable tests or proof certificates; pass flags not acceptance input.',
 'AL53_corrections':['Necessary outer enclosure, not automatic equality to true feasible set','Explicit empty-intersection inconsistency state',
 'Conservative radius about fixed estimate and target/input error propagation',
 'C is not the sole argument of original q; AL51/AL52 compensation prevents such a substitution'],
 'AL54_scope':'Planner no-go for presently unsupported theories and experimental admission; only one unproven inductive-bias claim retained; independentAL36 missing',
 'AL55_scope':'Duplicate of AL13/AL35/AL54, not a new result',
 'mathematical_review':'Triangle inequalities and set inclusions in declared norms; manual, no machine certificate',
 'numeric_tests_executed':0,'model_calls':0,'server_calls':0,'gpu_calls':0,'real_samples_accessed':False,
 'independent_scientific_review':False,'scientific_innovation_admitted':False,
 'no_failed_candidate_reactivated':True}
record_path=reviews/'AL53_AL55_FINAL_REVIEW_RECORD_20260919.json'
assert not record_path.exists()
for tid,name in [('AL53',finals[0]),('AL54',finals[1])]:
 t=by[tid]
 t['draft_assessment_history']=[{'recorded_completed_at':t.get('completed_at'),'draft_review':t['review'],
  'draft_sha256':t.get('artifact_sha256'),'draft_checklist_sha256':t.get('exact_artifact_sha256'),
  'superseded_at':now,'reason':'Final manuscript-level mathematical/planning review completed; manual checklist not numerical evidence'}]
 t.update(completed_at=now,finalized_at=now,reviewed_by='planagent',review='../reviews/'+name,
  artifact_sha256=record['authoritative_final_sha256'][name],evidence_kind='manual_review_no_numerical_execution',
  final_review_record='../reviews/AL53_AL55_FINAL_REVIEW_RECORD_20260919.json',dispatch_status='completed_scoped_review')
 t.pop('exact_artifact_sha256',None)
 t['artifacts']=list(dict.fromkeys(t['artifacts']+['../reviews/'+name,'../reviews/AL53_AL55_FINAL_REVIEW_RECORD_20260919.json']))
by['AL53']['hypothesis_result']='Credible error/regularity can give necessary endpoint outer bounds; no actual constants or C-only original-score propagation'
by['AL53']['review_scope']='Full conditional ball-intersection/difference/radius design; actual regularity and efficacy not established'
by['AL54']['hypothesis_result']='OR1 not admitted on current evidence; one transferable-inductive-bias hypothesis retained for independently gated falsification'
by['AL54']['review_scope']='Planner synthesis only; does not decide final novelty or replace scientific review'
by['AL54']['nonblocking_reference_tasks']=['AL45']
by['AL54']['dependency_note']='AL45 partial status/source gap cited as such, not used as passed evidence or bypassed experiment dependency'
t=by['AL55'];t.update(status='done',gate_result='not_applicable',completed_at=now,reviewed_by='planagent',
 review='../reviews/'+finals[2],artifact_sha256=record['authoritative_final_sha256'][finals[2]],
 evidence_kind='deduplication_decision',hypothesis_result='No new question or evidence beyond AL13/AL35/AL54',
 review_scope='Close duplicate planning item; no new pass or experiment',dispatch_status='closed_as_duplicate',
 next_action='AL56 checks a previously unread recovery prior; stop repeating minimum-information plans')
t['artifacts']=list(dict.fromkeys(t['artifacts']+['../reviews/'+finals[2]]))
old=copy.deepcopy(cc['current_dispatch']);old.update(status='closed_as_duplicate',completed_at=now,
 review=t['review'],gate_result='not_applicable',outcome='Existing minimum-information fields reused, no new evidence count')
cc['dispatch_history'].append(old)
for h in cc['dispatch_history']:
 if h['id'] in ['cc-al53-planner-endpoint-bounds-20260919','cc-al54-planner-claim-matrix-20260919']:
  h['draft_completion_recorded_at']=h.get('completed_at')
  h['completed_at']=now
  tid='AL53' if 'al53' in h['id'] else 'AL54'
  h['review']=by[tid]['review']
  h['finalization_note']='Final supported assumptions and evidence kind bound after in-turn draft review'
order=root/'research-plan/AL56_RECOVERY_DETECTION_PRIOR_AUDIT_20260919.md'
new={'id':'AL56','milestone':'M2','title':'未读恢复检测直接先例的身份与方法审查',
 'assignee':'planagent','parents':['AL26','AL54'],'requires_pass':['AL26','AL54'],
 'status':'ready','gate_result':'not_evaluated','gate_scope':'unread_recovery_prior_review',
 'hypothesis':'AL26留下的恢复检测先例可能限制或覆盖OR1的探针/信息权限/目标，需要真正核对而非从题名推断。',
 'work':['至多3个公开primary记录/查询定位唯一标题','仅一个正文版本核对恢复算子、访问权限、标签与调用','给具体重叠或未读缺口，不复现模型或引入性能结果'],
 'acceptance':['身份与方法主张可追溯，不凭二手标题归类','不可访问写缺口不绕过或改账号','不重复已读先例计数，不产生算法准入'],
 'artifacts':['../reviews/AL56_RECOVERY_DETECTION_PRIOR_REVIEW_20260919.md'],
 'work_order':'../AL56_RECOVERY_DETECTION_PRIOR_AUDIT_20260919.md','work_order_sha256':sha(order),
 'plan_version':data['plan_version'],'prepared_at':now,'due_at':'2026-09-24T22:00:00+08:00',
 'execution_thread_id':cc['plan_thread_id'],
 'resource_policy':{'local_cpu':True,'server_access':False,'real_media':False,'gpu':False,'classifier_training':False,'large_downloads':False,'research_runtime_execution':False},
 'implementation_authorized':False,'scientific_innovation_gate_passed':False,'hypothesis_result':'not_evaluated',
 'next_action':'Read-only primary-source identity/method audit, independent of research401'}
data['tasks'].append(new)
cc['current_dispatch']={'id':'cc-al56-planner-recovery-prior-20260919','task_ids':['AL56'],'executor_role':'planagent',
 'executor_thread_id':cc['plan_thread_id'],'host_id':'local','status':'prepared','prepared_at':now,
 'work_order':new['work_order'],'work_order_sha256':new['work_order_sha256'],'plan_version':data['plan_version'],
 'scope':'Unreviewed recovery-method primary source; no model/media/server/GPU','remote_send_required':False,'background_process_running':False}
cc.update(last_coordinator_activity_at=now,last_local_review_at=now,last_substantive_review=by['AL54']['review'],
 prepared_independent_task_ids=['AL56','AL36'],active_and_prepared_work={'running':[],'prepared_independent':['AL56','AL36'],
 'executor_blocked':['AL36'],'source_blocked':['AL45']},
 local_execution={'task_ids':['AL53','AL54','AL55'],'executor_role':'planagent',
 'status':'completed_scoped_reviews_and_deduplication','finalized_at':now,
 'work_area':'research-plan/reviews','next_prepared_task_id':'AL56','background_process_running':False})
cc['last_state_transition_snapshot']={'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'path':'research-plan/task-hermes/project.json','sha256':hashlib.sha256(before).hexdigest(),'includes_in_turn_draft_records':True}
# Persist the actual already-observed check output; no rerun, no simulated --at, no notification ack.
checked={'plan_version':'cvpr27-20260919-v1.5','checked_at':'2026-09-19T19:02:29.886563+08:00',
 'timezone':'Asia/Shanghai','notifications':[],'quiet':True,'should_pause':False,
 'next_planned_notification_at':'2026-09-23T19:00:00+08:00'}
receipt=root/'research-plan/task-hermes/checks/20260919T190229.json'
assert not receipt.exists()
receipt.parent.mkdir(parents=True,exist_ok=True)
checked['_recorded_at']=now
checked['_source']='Actual milestones.py check stdout observed in this heartbeat; copied verbatim fields after command, not rerun or ack.'
data['reminders'].update(last_check_local_date='2026-09-19',last_checked_at=checked['checked_at'],
 last_check_notifications=0,last_check_receipt='checks/20260919T190229.json',
 last_check_recorded_at=now,next_planned_notification_at=checked['next_planned_notification_at'])
data['candidate_protocols']['OR1'].update(endpoint_partial_identification_status='Necessary outer enclosures only; C alone does not determine original q',
 claim_evidence_matrix_status='Planner no-go for formal admission on current evidence; one unproven inductive-bias hypothesis remains',
 minimum_new_information_status='AL55 deduplicated against AL13/AL35/AL54; no new gate',
 next_independent_tasks=['AL56','AL36'])
data['updated_at']=now
assert not board.validate(data),board.validate(data)
assert [t['id'] for t in board.available(data)]==['AL56']
assert all(by[tid]['gate_result']=='fail' for tid in ['AL05','AL09','AL27','AL40','AL49','AL50'])
assert data['budget']['spent_cny'] is None and data['budget']['used_gpu_hours'] is None
ids=board.index(data)
for pkg in [cc['current_dispatch'],cc['queued_dispatch'],*cc['additional_dispatches']]:
 assert set(pkg['task_ids'])<=set(ids)
assert project.read_bytes()==before
for p,obj in [(record_path,record),(receipt,checked)]:
 with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
temp=project.with_name('project.al53-55-final.tmp')
temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
assert project.read_bytes()==before
os.replace(temp,project)
print(json.dumps({'finalized_at':now,'task_count':len(data['tasks']),'AL53':'conditional_math_only','AL54':'planner_scope_only_no_innovation_admission',
 'AL55':'deduplicated_not_applicable','ready':'AL56','milestone_check':'actual_190229_saved_notifications_empty','notification_ack':False}))
