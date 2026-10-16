"""Local finite B8 delivery; no cloud/media/model/dependency imports."""
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,x):(ROOT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert not (ROOT/'DELIVERY.json').exists(),'packet already sealed'
    inputs=read(ROOT/'INPUT_LOCK.json');assert all(sha(BASE/x['path'])==x['sha256'] for x in inputs['frozen_inputs'])
    code=read(ROOT/'CODE_LOCK.json');assert all(sha(ROOT/p)==h for p,h in code['runtime_files'].items())
    check=read(ROOT/'SOFTWARE_VERIFICATION.json');assert check['status']=='syntax_and_no_side_effect_import_help_plan_pass'
    assert len(check['stages'])==6 and all(s['exit_code']==0 and s['filesystem_changes']==0 for s in check['stages'])
    assert all(check[k]==0 for k in ['model_initializations','encoder_calls','GPU_calls','cloud_calls','media_decode_or_read','real_or_fixture_prediction_rows'])
    save('CHECKPOINT.json',{'dispatch_id':'v1-monitor-20261009-B8-d3-inference-runner','stage':'finite_code_packet_complete_stopped',
        'source_SHA_checks':18,'runtime_syntax_modules':18,'safe_import_help_plan_stages':6,
        'encoder_model_media_cloud_GPU_calls':0,'ready_scope':'executable_offline_entry_not_model_runtime_validation',
        'cv2':'actual provider headless4.12 supported, source/distribution/native hashes explicit',
        'A11_full_producer_role_compatibility':'separate followup, not extended here','observed_local_unix':time.time()})
    save('HANDOFF.json',{'dispatch_id':'v1-monitor-20261009-B8-d3-inference-runner','status':'completed_finite_code_delivery',
        'entry':'runner.py plan/run','metadata_join':'assemble_manifest.py','environment_metadata':'environment_lock.py',
        'method':'D3 XCLIP-16/l2 frozen forward float32/sample_std, score_fake=-raw','author_forward_reader_AST_unchanged':True,
        'evaluator_v4_byte_identical_files':13,'old_A7_wrapper_or_27_media_replay':False,
        'selection':'all requested manifest members ordered; no per-class1000 cap; failed/pending remain denominator',
        'resume':'identical lock+eventchecksum+prediction identity; explicit failed retry; interruption bytes preserved',
        'cv2_distribution_compatibility':'explicit opencv-python-headless=4.12.0.88 with source andnative extension lock; no alias version or install',
        'first12':'original/current fit stays fit; overlay A10 conservativepublic exclusions before encoder; no audit metrics for fit',
        'A11_full_source_role_producer':'separate assignment, not claimed supported or expanded byB8',
        'validation':'syntax andno side-effect import/help/plan only; heavy dependency imports0',
        'real_or_fixture_predictions':0,'models_media_cloud_GPU_calls':0,'remaining_runtime_checks':['actual visual checkpoint keys/shapes/load','actual encoderHW/score','resume andRSS/output enforcement underreal CPU call'],
        'remaining_coordinated_inputs':['typed A10-approved complete execution manifest andexternal SHA','C9 asset-lock/config/payload exactidentities','prepared JPEG index hashes','target cv2/whole dependency source descriptor'],
        'coordination_status_as_reported':'C9 completed verified128local/39cloud members; C10 hasfirst12/199JPEG/12native probes and128MiB reservation; B8 didnotcallcloud',
        'next_commands':'NEXT_RUN.md','source_packets_main_PLAN_DAG_DEVLOG_written':False,'new_branches_windows_agents':0,'science_gate_passed':False})
    (ROOT/'README.md').write_text('# B8 D3入口\n\n执行说明：NEXT_RUN.md。实现及边界：REPORT.md。当前验证：SOFTWARE_VERIFICATION.json。\n\n默认显式plan；仅后续run子命令可初始化模型。完整execution/asset锁由协调端给出，原始fit不改名audit，A10排除项保留账本不进encoder。\n\ncv2分发和源身份显式锁定，D4 headless4.12无需另装opencv-python。当前包没有真实或fixture预测。\n',encoding='utf-8')
    report=ROOT/'REPORT.md'
    with report.open('a',encoding='utf-8') as f:
        f.write('\n## 最终交付停止点\n\n按最后集成指令，本包完成有限验证即停止，不继续新增合同检查范围。全量source_role const=fit与in_domain_audit/development_audit producer兼容由A11接续；当前first12原fit不受影响。C9/C10的云端/输入状态仅记录协调端给出的事实，本包没有云端验证或真实encoder调用。下一步以真实CPU回执暴露的问题作必要修复。\n')
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name not in ['SHA_MANIFEST.json','DELIVERY.json']:
            files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    total=sum(x['bytes'] for x in files);assert total<32*1024**2
    save('SHA_MANIFEST.json',{'files':files,'exclude':['SHA_MANIFEST.json','DELIVERY.json'],'local_only':True,'media_model_payload_bytes':0})
    save('DELIVERY.json',{'dispatch_id':'v1-monitor-20261009-B8-d3-inference-runner','status':'completed_sealed_finite_code_packet',
        'code_lock_SHA':sha(ROOT/'CODE_LOCK.json'),'input_lock_SHA':sha(ROOT/'INPUT_LOCK.json'),
        'software_validation_SHA':sha(ROOT/'SOFTWARE_VERIFICATION.json'),'next_run_SHA':sha(ROOT/'NEXT_RUN.md'),
        'report_SHA':sha(ROOT/'REPORT.md'),'handoff_SHA':sha(ROOT/'HANDOFF.json'),'SHA_manifest_SHA':sha(ROOT/'SHA_MANIFEST.json'),
        'entry':'runner.py','members':len(files),'logical_member_bytes':total,'local_cap_bytes':33554432,
        'tested':'syntax_import_help_plan_only','runtime_model_loading_or_scores_validated':False,
        'models_encoder_media_cloud_GPU_calls':0,'new_environment_installs':0,'weight_payload_bytes_copied':0,
        'cv2_provider':'explicit_frozen_distribution_no_opencv_python_hard_requirement',
        'C10_first12_interface_ready':'pending concrete frozen CLIinputs andactual CPU execution; not experimental pass',
        'A11_full_role_producer':'separate','scientific_gate_passed':False})
    assert sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())<=33554432
    print(json.dumps(read(ROOT/'DELIVERY.json')))
if __name__=='__main__':main()
