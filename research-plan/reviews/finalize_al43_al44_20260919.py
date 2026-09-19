"""Finalize reviewed local notes with actual timestamps and CAS project update."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research-plan/task-hermes'))
import board


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path,data):
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')


def main():
    project=ROOT/'research-plan/task-hermes/project.json'
    before=project.read_bytes(); data=json.loads(before)
    by={t['id']:t for t in data['tasks']}
    cc=data['continuous_collaboration']
    assert len(by)==72 and 'AL44' not in by and 'AL45' not in by
    assert by['AL43']['status']=='done'
    assert cc['current_dispatch']['id']=='cc-al44-planner-prior-provenance-20260919'
    now=datetime.now().astimezone().isoformat(timespec='seconds')
    reviews=ROOT/'research-plan/reviews'
    report=reviews/'AL43_OR1_ENERGY_SENSITIVITY_REVIEW_20260919.md'
    old_note=reviews/'AL43_SYMBOLIC_REVIEW_RECORD_20260919.json'
    note=json.loads(old_note.read_text(encoding='utf-8'))
    assert note['report_sha256']!=sha(report),'Expected recorded draft digest mismatch; inspect state'
    for rel,digest in note['inputs_sha256'].items():
        assert sha(ROOT/rel)==digest,rel
    finalization={
        'task_id':'AL43','finalized_at':now,'evidence_kind':'manual_symbolic_review_final_hash_binding',
        'report':'AL43_OR1_ENERGY_SENSITIVITY_REVIEW_20260919.md','report_sha256':sha(report),
        'draft_record':'AL43_SYMBOLIC_REVIEW_RECORD_20260919.json','draft_record_sha256':sha(old_note),
        'draft_report_sha256_recorded':note['report_sha256'],
        'draft_record_retained_unchanged':True,'draft_report_payload_separately_retained':False,
        'revision_reason':'Report edited before final commit after initial note; old note binds earlier draft only. This new record binds final supported assumptions/derivations.',
        'numeric_tests_executed':0,'formal_independent_review':False,'real_AE_efficacy':'not_evaluated',
        'verified_inputs_sha256':note['inputs_sha256']}
    finalization_path=reviews/'AL43_FINALIZATION_20260919.json'
    html=ROOT/'tmp/al44_2605.html'
    assert sha(html)=='57f90cc05a43f087d9ae8e0d76657f7de34dcd3df4df998d90f13c051479fabc'
    metadata=json.loads((ROOT/'tmp/al44_metadata_receipt.json').read_text(encoding='utf-8'))
    assert metadata['status']==200 and metadata['citation_metadata']['citation_arxiv_id']==['2605.23449']
    assert metadata['citation_metadata']['citation_title']==['Commutator-Induced Uncertainty in VAEs']
    source={
        'task_id':'AL44','reviewed_at':now,'evidence_kind':'primary_identity_and_selected_method_scope_review',
        'web_route':{'result':'failed_before_content','code':'404_not_found','reason':'provider gateway does not support /v1/alpha/search'},
        'html':{'url':'https://arxiv.org/html/2605.23449v1','bytes':html.stat().st_size,'sha256':sha(html),
                'retrieval_time_source':'Exact call time not separately recorded; file modified time below is local cache metadata',
                'cache_modified_at':datetime.fromtimestamp(html.stat().st_mtime,timezone.utc).isoformat(),
                'read_sections':['document title/authors','abstract and section3 context','S3.SS1.SSS0.Px2','S3.E1','S3.E2','S3.SS2; equations4/5'],
                'payload_retained_in_repository':False},
        'record_page':{k:metadata[k] for k in ['url','final_url','status','retrieved_at','bytes','sha256','submission_history']},
        'citation_metadata':{k:v for k,v in metadata['citation_metadata'].items() if k!='citation_abstract'},
        'scope_findings':{'id_title_version_match':True,'decoder_order_swap_formula_present':True,
            'learned_latent_action_not_two_fixed_complete_reconstructors':True,
            'equation4_is_explicit_modeling_assumption_not_derived_guarantee':True,
            'forensic_detection_experiment_verified':False,'authors_experiments_reproduced':False},
        'prior_project_files_sha256':{rel:sha(ROOT/rel) for rel in ['research-plan/reviews/AL14_RECONSTRUCTION_BASELINES_20260919.md',
             'research-plan/reviews/AL26_CROSS_RECONSTRUCTION_PRIOR_REVIEW_20260919.md','research-runs/algorithm_search_20260918/AL12_prior_comparison.md']},
        'new_prior_count':0,'review_report_sha256':sha(reviews/'AL44_CRITICAL_PRIOR_PROVENANCE_REVIEW_20260919.md'),
        'access_route':'ordinary public HTTPS without credentials; no account/model/organization changes',
        'model_calls':0,'media_accessed':False,'server_calls':0,'gpu_calls':0,'innovation_admitted':False}
    source_path=reviews/'AL44_SOURCE_RECORD_20260919.json'
    t=by['AL43']
    t['finalization_history']=[{'superseded_completed_at':t.get('completed_at'),'old_record_sha256':t.get('exact_artifact_sha256'),
                               'reason':'Correct pre-final draft hash binding and replace manually assigned completion time with actual finalization time'}]
    t.update(completed_at=now,reviewed_at=now,dispatch_status='completed_scoped_symbolic_review',
        artifact_sha256=sha(report),symbolic_review_finalization='../reviews/AL43_FINALIZATION_20260919.json')
    t.pop('exact_artifact_sha256',None)
    t['artifacts']+=['../reviews/AL43_SYMBOLIC_REVIEW_RECORD_20260919.json','../reviews/AL43_FINALIZATION_20260919.json']
    resources={'local_cpu':True,'server_access':False,'gpu':False,'real_media':False,'classifier_training':False,'large_downloads':False,'research_runtime_execution':False}
    for tid,title,parents,gate_scope,order,artifacts,work,acceptance in [
       ('AL44','关键顺序响应近邻的身份与公式追溯',['AL14','AL26'],'critical_prior_provenance_review','AL44_CRITICAL_PRIOR_PROVENANCE_AUDIT_20260919.md',
        ['AL44_CRITICAL_PRIOR_PROVENANCE_REVIEW_20260919.md','AL44_SOURCE_RECORD_20260919.json'],
        ['核对唯一arXiv v1身份及已引方法范围','区分建模下界、定理与模型调用域，保留访问方式'],
        ['ID/版本/正文可追溯，不以自身摘要作来源','不将元数据或先例差异当创新准入']),
       ('AL45','最强基线选择与比较统计目标审查',['AL35','AL37','AL42'],'strong_baseline_selection_design','AL45_STRONG_BASELINE_SELECTION_AUDIT_20260919.md',
        ['AL45_STRONG_BASELINE_SELECTION_REVIEW_20260919.md'],
        ['区分calibration选定基线与固定集合同时优势','核对相应假设检验/区间选择前提，不改原门槛'],
        ['提供明确比较对象与失败处理','主张多重性保证前核对primary方法学依据，无依据则保留未评估'])]:
        item={'id':tid,'milestone':'M2','title':title,'assignee':'planagent','parents':parents,'requires_pass':parents.copy(),
              'status':'done' if tid=='AL44' else 'ready','gate_result':'pass' if tid=='AL44' else 'not_evaluated',
              'gate_scope':gate_scope,'hypothesis':'关键来源和统计比较身份必须明确可证，不能由相似术语或选择性报告推成方法优势。',
              'work':work,'acceptance':acceptance,'artifacts':['../reviews/'+a for a in artifacts],
              'work_order':'../'+order,'work_order_sha256':sha(ROOT/'research-plan'/order),
              'resource_policy':resources.copy(),'plan_version':data['plan_version'],'recorded_at':now,
              'due_at':'2026-09-21T22:00:00+08:00','execution_thread_id':cc['plan_thread_id'],
              'scientific_innovation_gate_passed':False,'implementation_authorized':False}
        if tid=='AL44':
            item.update(completed_at=now,reviewed_by='planagent',review='../reviews/AL44_CRITICAL_PRIOR_PROVENANCE_REVIEW_20260919.md',
              artifact_sha256=source['review_report_sha256'],hypothesis_result='identity_and_scope_confirmed_empirical_lower_bound_is_postulate',
              evidence_kind='Manual primary passage review with retrieval hashes; no model replication',
              registration_mode='Registered after retrieval, no prospective frozen preregistration claimed',
              next_action='Give AL36 the verified postulate boundary on recovery; does not support OR1 novelty or true efficacy')
        else:item.update(prepared_at=now,hypothesis_result='not_evaluated')
        data['tasks'].append(item)
    current=cc['current_dispatch']
    current.update(status='completed_scoped_source_review',completed_at=now,review='../reviews/AL44_CRITICAL_PRIOR_PROVENANCE_REVIEW_20260919.md',
                   recording_note='Original prepared timestamp was manually assigned; this completion is actual clock time')
    cc['dispatch_history'].append(current)
    order=ROOT/'research-plan/AL45_STRONG_BASELINE_SELECTION_AUDIT_20260919.md'
    cc['current_dispatch']={'id':'cc-al45-planner-baseline-selection-20260919','task_ids':['AL45'],'executor_role':'planagent',
        'executor_thread_id':cc['plan_thread_id'],'host_id':'local','status':'prepared','prepared_at':now,
        'work_order':'../AL45_STRONG_BASELINE_SELECTION_AUDIT_20260919.md','work_order_sha256':sha(order),
        'plan_version':data['plan_version'],'remote_send_required':False,'background_process_running':False,
        'scope':'Independent comparison-estimand review; no repeated prototype, true data or model execution'}
    cc.update(last_coordinator_activity_at=now,last_local_review_at=now,last_substantive_review='../reviews/AL44_CRITICAL_PRIOR_PROVENANCE_REVIEW_20260919.md',
        prepared_independent_task_ids=['AL45','AL36'],active_and_prepared_work={'running':[],'prepared_independent':['AL45','AL36'],'executor_blocked':['AL36']},
        local_execution={'task_ids':['AL43','AL44'],'executor_role':'planagent','status':'completed_scoped_reviews',
                         'completed_at':now,'work_area':'research-plan/reviews','next_prepared_task_id':'AL45','background_process_running':False})
    cc['last_state_transition_snapshot']={'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'prior_project_sha256':hashlib.sha256(before).hexdigest(),'prior_state_includes_uncommitted_current_turn_changes':True}
    data['candidate_protocols']['OR1'].update(energy_readout_sensitivity_review_task='AL43',
        critical_prior_provenance_task='AL44',critical_prior_lower_bound_status='Explicit modeling assumption in2605.23449v1; no OR1 theorem imported',next_independent_tasks=['AL45','AL36'])
    data['updated_at']=now
    assert not board.validate(data),board.validate(data)
    ids=set(board.index(data))
    for package in [cc['current_dispatch'],cc['queued_dispatch'],*cc['additional_dispatches']]:
        assert all(tid in ids for tid in package['task_ids'])
    assert not {'RS06','RS07','RS08'} & {t['id'] for t in board.available(data)}
    assert data['budget']['spent_cny'] is None and data['budget']['used_gpu_hours'] is None
    assert project.read_bytes()==before
    save_new(finalization_path,finalization)
    save_new(source_path,source)
    tmp=project.with_name('project.al44-finalize.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    assert project.read_bytes()==before,'concurrent DAG change before replace'
    os.replace(tmp,project)
    print(json.dumps({'at':now,'tasks':len(data['tasks']),'AL43_final_report':sha(report),'AL44':'scoped_provenance_pass',
                      'current':'AL45','AL36':'prepared_unsent_auth_blocked','server_or_model_calls':0}))


if __name__=='__main__':
    main()
