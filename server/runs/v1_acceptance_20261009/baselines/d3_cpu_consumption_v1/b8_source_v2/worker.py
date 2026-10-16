"""Future explicit CPU encoder worker. Never executed by B8 validation."""
import argparse,importlib.metadata,json,math,os,random,sys,time
from pathlib import Path
from contract import ROOT,read_locked,validate_manifest,validate_asset_lock,code_identity,digest,DEPS
from run_state import write_json,append,journal,materialize,failure,file_bytes

def load_gates():
    sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'evaluator_v4'))
    from input_record import validate_input_record
    from admission import validate_rows
    return validate_input_record,validate_rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);a=p.parse_args();req=json.loads(Path(a.request).read_text())
    root=Path(req['output']).resolve();manifest=read_locked(req['execution_manifest'],req['manifest_sha256']);assets=read_locked(req['asset_lock'],req['asset_lock_sha256'])
    members=validate_manifest(manifest);validate_asset_lock(assets)
    for path in reversed(req['dependency_paths']):sys.path.insert(0,path)
    # Freeze actual dependency versions before any torch/model import, and bind resume to them.
    provider=manifest['cv2_provider'];versions={name:importlib.metadata.version(name) for name in DEPS+[provider['distribution']]}
    if versions!=manifest['dependency_versions']:raise ValueError('actual_runtime_dependency_versions_not_frozen_manifest')
    # Bind the module selected by Python to the explicit wheel distribution, not an invented alias version.
    import importlib.util as import_util
    from contract import sha_file
    distribution=importlib.metadata.distribution(provider['distribution']);source=Path(distribution.locate_file(provider['module_relative_path'])).resolve()
    spec=import_util.find_spec('cv2')
    if not spec or Path(spec.origin).resolve()!=source or sha_file(source)!=provider['module_source_sha256']:raise ValueError('actual_cv2_module_source_not_locked_distribution')
    records=[Path(distribution.locate_file(f)) for f in (distribution.files or []) if str(f).endswith('.dist-info/RECORD')]
    if len(records)!=1 or sha_file(records[0])!=provider['distribution_record_sha256']:raise ValueError('cv2_distribution_RECORD_identity_mismatch')
    for rel,h in provider['native_extensions'].items():
        if sha_file(Path(distribution.locate_file(rel)))!=h:raise ValueError('cv2_native_extension_identity_mismatch')
    import psutil
    process=psutil.Process();allowed=process.cpu_affinity();chosen=req['CPU_affinity'] or allowed[:2]
    if len(chosen)>2 or not set(chosen)<=set(allowed):raise ValueError('two_CPU_affinity_contract')
    process.cpu_affinity(chosen)
    identity={'execution_manifest_SHA':req['manifest_sha256'],'asset_lock_SHA':req['asset_lock_sha256'],
        'checkpoint_SHA':assets['checkpoint_sha256'],'config_SHA':assets['config_sha256'],
        'runner_code_SHA':code_identity(),'dependency_versions':versions,'cv2_provider':provider,'python_version':sys.version,
        'device':'cpu','dtype':'float32','batch_size':1,'threads':2,'CPU_affinity':chosen,'group_RSS_cap':4294967296,
        'output_cap_bytes':req['max_output_bytes'],'manifest_order_preserved':True,'support_lock_SHA':manifest['support_lock_sha256']}
    identity_sha=digest(identity);idfile=root/'RUN_IDENTITY.json'
    if idfile.exists():
        previous=json.loads(idfile.read_text());assert previous['sha256']==identity_sha and previous['identity']==identity,'resume_full_identity_changed'
    else:write_json(idfile,{'sha256':identity_sha,'identity':identity})
    latest=journal(root/'events.jsonl',identity_sha,members)
    materialize(root,identity_sha,members,latest)
    validate_input,validate_pred=load_gates()
    for i,event in latest.items():
        if event['status']!='success':continue
        m=members[i];prediction=event['prediction'];validate_pred([prediction])
        binding={k:m[k] for k in ['sample_id','ancestor_id','source_family','generator_family','label_fake','role','processing_id']}
        binding.update(input_sha256=m['source_sha256'],checkpoint_sha256=assets['checkpoint_sha256'],
            preprocessing_sha256=manifest['preprocessing_sha256'],split_sha256=manifest['split_sha256'],protocol_sha256=manifest['protocol_sha256'],
            cohort_id=manifest['cohort_id'],seed=manifest['seed'],method_id='d3',method_revision=manifest['method_revision'],track='native_reference',runner_identity_sha256=identity_sha)
        if any(prediction.get(k)!=v for k,v in binding.items()):raise ValueError('cached_success_identity_source_or_role_changed')
    pending=[]
    for i,m in enumerate(members):
        if i in latest and (latest[i]['status']=='success' or not req['retry_failed']):continue
        try:
            if not m['approved_public_candidate']:raise ValueError('frozen_A10_public_gate_excluded:'+json.dumps(m['public_gate_reasons']))
            validate_input(m['input_record'],m.get('timeline_evidence'));pending.append(i)
        except Exception as e:
            event=failure(identity_sha,i,m,'v4_scoreless_input_admission_before_model_init',e);append(root/'events.jsonl',event);latest[i]=event
    if not pending:
        summary=materialize(root,identity_sha,members,latest)
        return 0 if summary['failed']==summary['pending']==0 else 2
    random.seed(manifest['seed']);stage='offline_model_initialization'
    try:
        from backend import load_offline,prepared_tensor,score_one
        torch,model,receipt=load_offline(req['asset_dir'],assets,manifest['seed'])
        write_json(root/'MODEL_LOAD_RECEIPT.json',receipt)
    except Exception as e:
        write_json(root/'MODEL_LOAD_FAILURE.json',{'error_type':type(e).__name__,'error':str(e),'random_missing_visual_weights_accepted':False})
        for i in pending:
            m=members[i]
            event=failure(identity_sha,i,m,stage,e);append(root/'events.jsonl',event);latest[i]=event
        materialize(root,identity_sha,members,latest);return 2
    for i in pending:
        m=members[i]
        stage='v4_scoreless_input_admission'
        try:
            record=m['input_record'];verdict=validate_input(record,m.get('timeline_evidence'))
            stage='frozen_prepared_JPEG_reader';tensor,prepared=prepared_tensor(torch,req['prepared_root'],m)
            stage='author_XCLIP16_l2_forward';raw,timing=score_one(torch,model,tensor)
            if not math.isfinite(raw):raise ValueError('nonfinite_real_author_score')
            memory=process.memory_info().rss
            heartbeat=root/'RESOURCE_HEARTBEAT.json'
            if heartbeat.exists():memory=max(memory,json.loads(heartbeat.read_text())['peak_group_RSS'])
            prediction={'schema_version':'v1_baseline_prediction/1.0','sample_id':m['sample_id'],'ancestor_id':m['ancestor_id'],
                'ancestry_status':'unknown','input_sha256':m['source_sha256'],'source_family':m['source_family'],'generator_family':m['generator_family'],
                'label_fake':m['label_fake'],'role':m['role'],'evaluation_unit':'video','method_id':'d3','method_revision':manifest['method_revision'],
                'checkpoint_sha256':assets['checkpoint_sha256'],'preprocessing_sha256':manifest['preprocessing_sha256'],
                'split_sha256':manifest['split_sha256'],'track':'native_reference','processing_id':m['processing_id'],'seed':manifest['seed'],
                'score_raw':raw,'score_fake':-raw,'score_transform':'negate','fixture':False,
                'frame_indices':record['frame_indices'],'native_time':{'pts_field':m['pts_field'],'time_base':record['native_time_base'],'selected_pts':record['selected_native_integer_PTS']},
                'reference_frame_policy':record['reference_frame_policy'],'cohort_id':manifest['cohort_id'],'protocol_sha256':manifest['protocol_sha256'],
                'compute_budget':{'decode_wall_seconds':prepared['wall_seconds'],'encoder_wall_seconds':timing['encoder_wall_seconds'],
                    'head_wall_seconds':timing['head_wall_seconds'],'peak_memory_bytes':int(memory),'n_frames':record['actual_input_slots'],
                    'n_unique_native_frames':record['unique_native_frames'],'input_hw':timing['model_consumed_shape'][-2:]},
                'timing_scope':'prepared_JPEG_read_preprocess_and_encoder; original_video_preparation_cost_not_measured_here',
                'memory_scope':'observed_process_group_peak_to_checkpoint','actual_encoder_consumed_HW':timing['model_consumed_shape'][-2:],
                'prepared_tensor_sha256':prepared['tensor_sha256'],'prepared_input_record_sha256':m['input_record_sha256'],
                'runner_identity_sha256':identity_sha,'scientific_gate_passed':False}
            stage='v4_prediction_schema_admission';validate_pred([prediction])
            event={'run_identity_sha256':identity_sha,'ordinal':i,'sample_id':m['sample_id'],'source_sha256':m['source_sha256'],
                'input_record_sha256':m['input_record_sha256'],'status':'success','prediction':prediction,'prepared_input':prepared,
                'input_admission':verdict,'encoder_observation':timing,'observed_unix':time.time()}
        except Exception as e:event=failure(identity_sha,i,m,stage,e)
        append(root/'events.jsonl',event);latest[i]=event
        if file_bytes(root)>req['max_output_bytes']:raise RuntimeError('output_capacity_guard_after_persisted_event; remaining denominator stays pending')
        if (i+1)%req['checkpoint_every']==0:materialize(root,identity_sha,members,latest)
    summary=materialize(root,identity_sha,members,latest)
    return 0 if summary['failed']==summary['pending']==0 else 2
if __name__=='__main__':raise SystemExit(main())
