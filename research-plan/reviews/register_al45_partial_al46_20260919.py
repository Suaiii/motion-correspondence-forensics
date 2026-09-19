from pathlib import Path
from datetime import datetime
import hashlib,json,os,sys,subprocess,copy
root=Path.cwd()
sys.path.insert(0,str(root/'research-plan/task-hermes'))
import board
project=root/'research-plan/task-hermes/project.json'
before=project.read_bytes(); data=json.loads(before); cc=data['continuous_collaboration']
now=datetime.now().astimezone().isoformat(timespec='seconds')
by=board.index(data)
assert len(by)==74 and by['AL45']['status']=='done' and by['AL45']['gate_result']=='pass' and 'AL46' not in by
assert cc['current_dispatch']['id']=='cc-al36-research-admission-review-20260919'
reviews=root/'research-plan/reviews'
report=reviews/'AL45_SELECTION_PROOF_AND_LIMITS_20260919.md'
old_report=reviews/'AL45_STRONG_BASELINE_SELECTION_REVIEW_20260919.md'
old_receipt=reviews/'AL45_STRONG_BASELINE_SELECTION_EXACT_20260919.json'
raw_draft=json.loads(old_receipt.read_text(encoding='utf-8'))
assert raw_draft['gate_result']=='pass'
cawley=json.loads((root/'tmp/al45_cawley_source.json').read_text(encoding='utf-8'))
berger=json.loads((root/'tmp/al45_berger_source.json').read_text(encoding='utf-8'))
assert cawley['status']==200 and cawley['bytes']==6655
assert berger['status']==200 and berger['content_type']=='text/html' and berger['article_retrieved'] is False
sources={
 'task_id':'AL45','recorded_at':now,'gate_result':'not_evaluated',
 'evidence_kind':'primary_retrieval_status_and_manual_conditional_probability_proofs',
 'search_gateway':{'result':'404_not_found','reason':'provider gateway does not support /v1/alpha/search','content_received':False},
 'primary_entry_limit':3,
 'primary_entries':[
  dict(cawley,read_scope='Official metadata and abstract only; selection-bias warning, not IUT theorem',full_paper_read=False,payload_saved=False),
  {'url':'https://www.fda.gov/media/102657/download','observed_at':'2026-09-19T09:25:37.424705+00:00','result':'HTTP404','article_retrieved':False},
  dict(berger,read_scope='Returned HTML identification only; requested paper PDF not obtained',full_paper_read=False,payload_saved=False)],
 'conditional_proofs_in_current_note':['calibration choice defines conditional comparator; CI validity remains separate',
  'IUT rejection event subset of each component event under fixed true null',
  'minimum component lower bound is valid for the minimum parameter under stated component validity',
  'observed strongest baseline need not maximize candidate advantage; direction depends on selection'],
 'unverified':['Original IUT methodology full text','Project cluster CI validity and finite-sample coverage','Real trained model/sample identity'],
 'old_draft_receipt':{'path':str(old_receipt.relative_to(root)),'sha256':hashlib.sha256(old_receipt.read_bytes()).hexdigest(),'role':'superseded_manual_checklist_not_executed_evidence','pass_not_accepted':True},
 'old_draft_report':{'path':str(old_report.relative_to(root)),'sha256':hashlib.sha256(old_report.read_bytes()).hexdigest(),'role':'superseded_draft_with_selection_direction_and_bound_overstatements'},
 'authoritative_review':str(report.relative_to(root)),'authoritative_review_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
 'numeric_checks_executed':0,'bootstrap_runs':0,'real_prediction_access':False,'model_calls':0,'server_calls':0,'gpu_calls':0,
 'formal_independent_scientific_review':False,'work_order_limits_respected':True}
source_path=reviews/'AL45_SOURCE_AND_REVIEW_LIMITS_20260919.json'
assert not source_path.exists()
t=by['AL45']
t['superseded_in_turn_assessment']={'status':t['status'],'gate_result':t['gate_result'],
 'completed_at':t.get('completed_at'),'review':t['review'],'artifact_sha256':t['artifact_sha256'],
 'corrected_at':now,'reason':'Initial close relied on self-authored checklist and abstract-only source; explicit work-order full methodology condition not satisfied'}
for key in ['completed_at','exact_artifact_sha256']:
 t.pop(key,None)
t.update(status='blocked',gate_result='not_evaluated',observed_work_at=now,dispatch_status='partial_design_delivered_primary_IUT_source_unavailable',
 review='../reviews/AL45_SELECTION_PROOF_AND_LIMITS_20260919.md',
 artifact_sha256=sources['authoritative_review_sha256'],
 hypothesis_result='conditional_selection_and_IUT_algebra_written_external_methodology_verification_incomplete',
 blocker='Within3 primary entries, selection-bias abstract read but original IUT/full methodology text unavailable. No actual CI verification; do not accept self-authored exact/checklist pass.',
 next_action='Resume only unresolved primary methodology/CI scope when source access changes; independent local AL46 can proceed',
 review_scope='Partial design with conditional set-inclusion proofs; not completed external source verification')
t['artifacts']=['../reviews/AL45_SELECTION_PROOF_AND_LIMITS_20260919.md','../reviews/AL45_SOURCE_AND_REVIEW_LIMITS_20260919.json',
 '../reviews/AL45_BASELINE_SELECTION_PRIMARY_RECORD_20260919.json']
t['superseded_draft_artifacts']=[sources['old_draft_receipt'],sources['old_draft_report']]
prior_dispatch=next(h for h in reversed(cc['dispatch_history']) if h['id']=='cc-al45-planner-baseline-selection-20260919')
prior_dispatch['superseded_in_turn_status']=prior_dispatch['status']
prior_dispatch.update(status='partial_delivery_blocked_source_verification',reviewed_at=now,gate_result='not_evaluated',
 review=t['review'],outcome='Conditional proofs delivered; full IUT primary methodology unavailable; prior draft-only pass not accepted')
blocked_dispatch=copy.deepcopy(cc['current_dispatch'])
blocked_dispatch['last_observed_at']=cc['configuration_faults']['research_task_api_auth_401']['observed_at']
blocked_dispatch['observation_note']='Historical status from existing401 receipt; not polled anew during local work'
cc['queued_dispatch']=blocked_dispatch
order=root/'research-plan/AL46_MATCHED_DIRECTION_RANK_AUDIT_20260919.md'
new={'id':'AL46','milestone':'M2','title':'匹配基线后OR1读出的局部方向与秩条件审查',
 'assignee':'planagent','parents':['AL12','AL20','AL29','AL43'],'requires_pass':['AL12','AL20','AL29','AL43'],
 'status':'ready','gate_result':'not_evaluated','gate_scope':'matched_direction_local_rank_math',
 'hypothesis':'存在原单步匹配描述的一阶零方向并不保证实际q可见；核/行空间条件应明确弱基线和完整同信息基线的区别。',
 'work':['给B=J_b,Q=J_q的核空间/行空间/秩与伪逆条件','分开固定评分、坐标度量和数值误差','不重复既有场、标签、模型或真实媒体运行'],
 'acceptance':['公式前提与必要充分性推导完整','实际可微性和数值秩未知保留','不把弱基线方向当同信息强基线之外的新增信息'],
 'artifacts':['../reviews/AL46_MATCHED_DIRECTION_RANK_REVIEW_20260919.md'],
 'work_order':'../AL46_MATCHED_DIRECTION_RANK_AUDIT_20260919.md',
 'work_order_sha256':hashlib.sha256(order.read_bytes()).hexdigest(),
 'plan_version':data['plan_version'],'prepared_at':now,'due_at':'2026-09-21T22:00:00+08:00',
 'resource_policy':{'local_cpu':True,'threads':2,'server_access':False,'real_media':False,'gpu':False,'classifier_training':False,'large_downloads':False,'research_runtime_execution':False},
 'execution_thread_id':cc['plan_thread_id'],'implementation_authorized':False,'scientific_innovation_gate_passed':False,
 'hypothesis_result':'not_evaluated','next_action':'Begin local symbolic audit, independent of AL45 source gap and research401'}
data['tasks'].append(new)
cc['current_dispatch']={'id':'cc-al46-planner-matched-direction-20260919','task_ids':['AL46'],'executor_role':'planagent',
 'executor_thread_id':cc['plan_thread_id'],'host_id':'local','status':'prepared','prepared_at':now,
 'work_order':new['work_order'],'work_order_sha256':new['work_order_sha256'],'plan_version':data['plan_version'],
 'scope':'Matched-direction sensitivity design; symbolic only, no repeated prototype or model/media/server',
 'remote_send_required':False,'background_process_running':False}
cc.update(last_coordinator_activity_at=now,last_local_review_at=now,last_substantive_review=t['review'],
 prepared_independent_task_ids=['AL46','AL36'],active_and_prepared_work={'running':[],'prepared_independent':['AL46','AL36'],'executor_blocked':['AL36'],'source_blocked':['AL45']},
 local_execution={'task_ids':['AL45'],'executor_role':'planagent','status':'partial_review_delivered_source_gap',
 'last_progress_at':now,'work_area':'research-plan/reviews','next_prepared_task_id':'AL46','background_process_running':False},
 last_state_transition_snapshot={'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'project_sha256':hashlib.sha256(before).hexdigest(),'contains_current_turn_local_start_update':True})
data['candidate_protocols']['OR1'].update(strong_baseline_selection_review_task='AL45',
 strong_baseline_selection_status='Partial design; primary IUT methodology/source and actual CI acceptance pending',
 next_independent_tasks=['AL46','AL36'])
data['updated_at']=now
assert not board.validate(data),board.validate(data)
assert [t['id'] for t in board.available(data)]==['AL46']
for package in [cc['current_dispatch'],cc['queued_dispatch'],*cc['additional_dispatches']]:
 assert all(tid in board.index(data) for tid in package['task_ids'])
assert data['budget']['spent_cny'] is None and data['budget']['used_gpu_hours'] is None
assert project.read_bytes()==before
with source_path.open('x',encoding='utf-8',newline='\n') as f:json.dump(sources,f,ensure_ascii=False,indent=2);f.write('\n')
tmp=project.with_name('project.al45-partial.tmp')
tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
assert project.read_bytes()==before
os.replace(tmp,project)
print(json.dumps({'at':now,'tasks':len(data['tasks']),'AL45':'blocked_not_evaluated','ready':'AL46','research_AL36':'blocked_unsent','draft_pass_not_used':True}))
