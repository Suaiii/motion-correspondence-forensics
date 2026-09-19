"""One-time, compare-and-swap planner correction and continuation registration."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'research-plan/task-hermes'))
import board


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path=ROOT/'research-plan/task-hermes/project.json'
    before=path.read_bytes()
    data=json.loads(before)
    by={t['id']:t for t in data['tasks']}
    assert len(by)==69 and not {'AL41','AL42','AL43'} & set(by)
    now=datetime.now().astimezone().isoformat(timespec='seconds')
    cc=data['continuous_collaboration']
    correction=ROOT/'research-plan/reviews/AL41_FIXED_KERNEL_CORRECTION_20260919.json'
    receipt=json.loads(correction.read_text(encoding='utf-8'))
    assert receipt['AL40_review_verdict']=='fail' and receipt['review_computation_result']=='pass'
    for rel,sha in receipt['hashes'].items():
        assert digest(ROOT/rel)==sha,rel
    assert by['AL40']['gate_result']=='pass'
    by['AL40']['previous_gate_assessments']=[{'gate_result':'pass','recorded_completed_at':by['AL40']['completed_at'],
        'review':by['AL40']['review'],'artifact_sha256':by['AL40']['artifact_sha256'],
        'exact_artifact_sha256':by['AL40']['exact_artifact_sha256'],'superseded_at':now,'reason':'Gaussian integer recalculation contradicts stored H10m1(pi)=2'}]
    by['AL40'].update(gate_result='fail',hypothesis_result='fixed_kernel_retained_alias_claim_refuted_by_exact_arithmetic',
        reviewed_at=now,review='../reviews/AL41_CORRECTION_REVIEW_20260919.md',
        artifact_sha256=digest(ROOT/'research-plan/reviews/AL41_CORRECTION_REVIEW_20260919.md'),
        review_scope='Original arithmetic verdict withdrawn; immutable original report preserved, correction is authoritative',
        dispatch_status='completed_with_failed_evidence_review',correction_task_id='AL41',
        next_action='Do not cite original pass or replace its fixed frequencies/kernels to repair the claim')
    by['AL40']['artifacts']+=['../reviews/AL41_CORRECTION_REVIEW_20260919.md','../reviews/AL41_FIXED_KERNEL_CORRECTION_20260919.json']
    by['AL39']['review_errata']={'recorded_at':now,'review':'../reviews/AL41_CORRECTION_REVIEW_20260919.md',
        'actual_archive_counts':{'check_categories':5,'fields':3,'fixed_weights':2},
        'claim_15_independent_checks_withdrawn':True,'numerical_result_replayed':False,
        'incremental_information_over_AL29_AL32':'none; archival consistency only'}
    by['AL37']['remaining_protocol_fields']=['Actual ancestor components and target weights','Fully specified missing-draw distribution treatment (AL42)','Training randomness and model identities','Real statistical implementation/review']
    by['AL37']['next_action']='AL42 quantifies discarded-draw conditioning; AL37 pass remains limited design, not formal bootstrap acceptance'
    by['AL36']['blocker']='Latest observed research executor turn failed with401 authentication; previous usage-limit resolution unknown. Package not sent; await supported recovery evidence.'
    by['AL36']['next_action']='After genuine supported API recovery, read main DAG and correction AL41 before independent AL36; never rerun AL32'
    resource={'local_cpu':True,'threads':2,'server_access':False,'real_media':False,'gpu':False,'classifier_training':False,'large_downloads':False,'research_runtime_execution':False}
    specifications=[
      ('AL41','核频响归档的精确纠错审查',['AL40'],[], 'done','pass','correction_of_fixed_kernel_arithmetic',
       '实际高斯整数计算可能否定AL40写入的相等响应，不能以自填passed认证数学结论。',
       'AL41_FIXED_KERNEL_CORRECTION_AUDIT_20260919.md',
       ['AL41_CORRECTION_REVIEW_20260919.md','AL41_FIXED_KERNEL_CORRECTION_20260919.json']),
      ('AL42','祖先簇重抽缺类质量及区间条件审查',['AL21','AL35','AL37'],['AL21','AL35','AL37'],'running','not_evaluated','cluster_missing_mass_estimand_design',
       '丢弃缺类重抽会改变目标分布；必须保留其质量并检验是否会改变正下界判断。',
       'AL42_CLUSTER_MISSING_MASS_AUDIT_20260919.md',
       ['AL42_CLUSTER_MISSING_MASS_REVIEW_20260919.md','AL42_CLUSTER_MISSING_MASS_EXACT_20260919.json']),
      ('AL43','OR1能量读出局部敏感性条件审查',['AL12','AL16','AL20','AL29'],['AL12','AL16','AL20','AL29'],'ready','not_evaluated','energy_readout_local_sensitivity_math',
       'J_K delta非零可能仍不能提供q的一阶增量，需要分开场变化与实际能量比读出敏感性。',
       'AL43_OR1_ENERGY_SENSITIVITY_AUDIT_20260919.md',
       ['AL43_OR1_ENERGY_SENSITIVITY_REVIEW_20260919.md'])]
    for tid,title,parents,requires,status,gate,scope,hypothesis,order,artifacts in specifications:
        t={'id':tid,'milestone':'M2','title':title,'assignee':'planagent','parents':parents,'requires_pass':requires,
           'status':status,'gate_result':gate,'gate_scope':scope,'hypothesis':hypothesis,
           'work':['按独立工作单的固定输入/符号条件完成推导','保留反例、历史字节与未知项；不改变真实实验授权'],
           'acceptance':['产生具体推导或实际计算证据而非自填pass','如失败保留原始输入不扩大搜索','限定数学审查不作为创新准入或正式独立复核'],
           'artifacts':['../reviews/'+a for a in artifacts],'work_order':'../'+order,
           'work_order_sha256':digest(ROOT/'research-plan'/order),'plan_version':data['plan_version'],'recorded_at':now,
           'due_at':'2026-09-21T22:00:00+08:00','resource_policy':resource.copy(),'execution_thread_id':cc['plan_thread_id'],
           'implementation_authorized':False,'scientific_innovation_gate_passed':False,'hypothesis_result':'not_evaluated'}
        if tid=='AL41':
            t.update(started_at=receipt['started_at'],execution_completed_at=receipt['completed_at'],completed_at=now,
                prepared_at_source='Local work-order file written before arithmetic; no prior committed preregistration claimed',
                registration_mode='retrospective_registration_of_planner_correction',
                review='../reviews/AL41_CORRECTION_REVIEW_20260919.md',reviewed_by='planagent',
                hypothesis_result='AL40 fixed retained-alias assertion falsified; no actual decoder conclusion',
                failure_parent_pass_not_required_reason='Audit of a now failed numerical claim; no success-dependent branch',
                next_action='Preserve AL40 done/fail and use AL41 correction; no alternate frequency search')
        else:
            t['prepared_at']=now
            if status=='running': t['started_at']=now
        data['tasks'].append(t)
    current=cc['current_dispatch']
    assert current['id']=='cc-al36-research-admission-review-20260919' and not current.get('sent_at')
    cc['queued_dispatch']=current
    cc['current_dispatch']={'id':'cc-al42-planner-missing-mass-20260919','task_ids':['AL42'],'executor_role':'planagent',
        'executor_thread_id':cc['plan_thread_id'],'host_id':'local','status':'running','prepared_at':now,'started_at':now,
        'work_order':'../AL42_CLUSTER_MISSING_MASS_AUDIT_20260919.md',
        'work_order_sha256':digest(ROOT/'research-plan/AL42_CLUSTER_MISSING_MASS_AUDIT_20260919.md'),
        'plan_version':data['plan_version'],'scope':'New missing-mass mathematics; no true data resampling/model/server, independent of research401',
        'remote_send_required':False,'background_process_running':False}
    cc.update(last_coordinator_activity_at=now,last_local_review_at=now,last_substantive_review='../reviews/AL41_CORRECTION_REVIEW_20260919.md',
        prepared_independent_task_ids=['AL43'],active_and_prepared_work={'running':['AL42'],'prepared_independent':['AL43'],'executor_blocked':['AL36']},
        local_execution={'task_ids':['AL42'],'executor_role':'planagent','status':'in_progress','started_at':now,'work_area':'research-plan/reviews','background_process_running':False},
        last_state_transition_snapshot={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'path':'research-plan/task-hermes/project.json','sha256':hashlib.sha256(before).hexdigest()})
    fault=cc['configuration_faults']['research_task_api_auth_401']
    fault.update(notification_state='confirmed_final_output',notification_confirmed_at=now,
        confirmation_evidence='Completed heartbeat final for2026-09-19T06:46:15.667Z is visible in conversation; no OS push-delivery assertion')
    cc['material_decision_notices'].append({'id':'al40-arithmetic-verdict-withdrawal','status':'prepared_for_current_final_not_confirmed',
        'prepared_at':now,'message':'AL40差分核响应误写导致原通过判定无效，已撤销并保留纠错回执。',
        'evidence':'../reviews/AL41_CORRECTION_REVIEW_20260919.md','not_a_milestone_receipt':True})
    data['updated_at']=now
    assert not board.validate(data),board.validate(data)
    assert not {'RS06','RS07','RS08'} & {t['id'] for t in board.available(data)}
    assert all(next(t for t in data['tasks'] if t['id']==tid)['gate_result']=='fail' for tid in ['AL05','AL09','AL27','AL40'])
    assert data['budget']['spent_cny'] is None and data['budget']['used_gpu_hours'] is None
    assert path.read_bytes()==before,'concurrent change'
    tmp=path.with_name('project.al41-correction.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    assert path.read_bytes()==before,'concurrent change before replace'
    os.replace(tmp,path)
    print(json.dumps({'recorded_at':now,'tasks':len(data['tasks']),'AL40':'done_fail','current':'AL42','prepared':'AL43','AL36':'unsent_blocked'}))


if __name__ == '__main__':
    main()
