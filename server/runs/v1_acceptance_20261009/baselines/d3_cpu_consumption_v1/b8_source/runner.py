"""Safe default plan; future run is an explicit separate subcommand."""
import argparse,importlib.metadata,json,os,subprocess,sys,time
from pathlib import Path
from contract import ROOT,read_locked,validate_manifest,validate_asset_lock,code_identity,DEPS,sha_file
def parser():
    p=argparse.ArgumentParser(description='D3 offline XCLIP-16/l2, frozen prepared JPEG native-reference runner')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['plan','run']:
        c=sub.add_parser(name);c.add_argument('--execution-manifest');c.add_argument('--manifest-sha256');c.add_argument('--asset-lock');c.add_argument('--asset-lock-sha256')
        c.add_argument('--asset-dir');c.add_argument('--prepared-root');c.add_argument('--output');c.add_argument('--dependency-path',action='append',default=[])
        c.add_argument('--cpu-affinity',default=None,help='comma separated at most2 allowed CPU ids; default first2 available')
        c.add_argument('--max-output-mib',type=int,default=32);c.add_argument('--checkpoint-every',type=int,default=1)
        c.add_argument('--retry-failed',action='store_true',help='explicit retry of failed members under same complete locks, old failures retained')
    return p
def plan(args):
    missing=[x for x in ['execution_manifest','manifest_sha256','asset_lock','asset_lock_sha256','asset_dir','prepared_root','output'] if not getattr(args,x)]
    result={'mode':'plan','model_initializations':0,'encoder_calls':0,'media_bytes_read':0,'GPU_calls':0,'network_calls':0,
        'writes':0,'dependency_paths':args.dependency_path,'missing_future_inputs':missing,'status':'awaiting_C9_A10_frozen_execution_and_asset_locks',
        'method':'D3 XCLIP-16/l2','batch_size':1,'track':'prepared_author_native_reference','logical_frame_prefix':'8 if prepared<16 else16',
        'score_direction':'raw sample_std large=real; score_fake=-raw','scope':'metadata only; no fixture predictions',
        'runtime_dependencies':DEPS,'cv2_distribution_must_be_explicitly_locked':['opencv-python','opencv-python-headless'],
        'local_distribution_metadata':{n:version(n) for n in DEPS+['opencv-python','opencv-python-headless']}}
    if not missing:
        try:
            m=read_locked(args.execution_manifest,args.manifest_sha256);a=read_locked(args.asset_lock,args.asset_lock_sha256)
            members=validate_manifest(m);validate_asset_lock(a);identity=code_identity()
            result.update(status='metadata_plan_valid_not_model_validated',members=len(members),expected_members=m['expected_members'],
                class_counts={'real':sum(r['label_fake']==0 for r in members),'fake':sum(r['label_fake']==1 for r in members)},
                A10_public_approved=sum(r['approved_public_candidate'] for r in members),A10_excluded_retained=sum(not r['approved_public_candidate'] for r in members),
                no_per_class1000_cap=True,selection_sha256=m['selection_sha256'],asset_checkpoint_sha256=a['checkpoint_sha256'],
                runner_code_identity=identity,asset_and_JPEG_payloads_not_read=True,asset_load_and_real_score_review='pending_future_explicit_encoder_command')
        except Exception as e:result.update(status='metadata_plan_rejected_or_dependencies_unfrozen',error_type=type(e).__name__,error=str(e))
    return result
def version(name):
    try:return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:return None
def run(args,info):
    if info['status']!='metadata_plan_valid_not_model_validated':raise ValueError('valid_frozen_metadata_plan_required_before_run')
    if args.max_output_mib<1 or args.checkpoint_every<1:raise ValueError('positive_resource_and_checkpoint_limits')
    from run_state import write_json,file_bytes
    output=Path(args.output).resolve();base=ROOT.parents[1]
    forbidden=[ROOT,Path(args.asset_dir).resolve(),Path(args.prepared_root).resolve(),Path(args.execution_manifest).resolve().parent,Path(args.asset_lock).resolve().parent]
    forbidden+=[base/p for p in ['baselines/input_contract_recovery_v1','baselines/sources/d3','baselines/inference_assets_v1','fingerprint_cpu/author_input_parity_v1','data_audit/unified_release_candidate_v1','propagation/independent_unified_release_v1']]
    if any(output.is_relative_to(p) for p in forbidden):raise ValueError('output_must_be_new_owned_runtime_namespace_not_any_frozen_input_root')
    if output.exists() and not (output/'RUN_IDENTITY.json').exists() and not (output/'PLANNED_IDENTITY.json').exists():raise ValueError('existing_output_without_locked_run_identity')
    output.mkdir(parents=True,exist_ok=True)
    for name in ['tmp','cache']:(output/name).mkdir(exist_ok=True)
    affinity=[int(s) for s in args.cpu_affinity.split(',')] if args.cpu_affinity else None
    if affinity is not None and (len(affinity)>2 or len(set(affinity))!=len(affinity)):raise ValueError('at_most2_distinct_CPUs')
    req={'execution_manifest':str(Path(args.execution_manifest).resolve()),'manifest_sha256':args.manifest_sha256,
        'asset_lock':str(Path(args.asset_lock).resolve()),'asset_lock_sha256':args.asset_lock_sha256,'asset_dir':str(Path(args.asset_dir).resolve()),
        'prepared_root':str(Path(args.prepared_root).resolve()),'output':str(output),'dependency_paths':args.dependency_path,
        'CPU_affinity':affinity,'max_output_bytes':args.max_output_mib*1024**2,'checkpoint_every':args.checkpoint_every,'retry_failed':args.retry_failed}
    from contract import digest
    planned={'manifest_SHA':args.manifest_sha256,'asset_lock_SHA':args.asset_lock_sha256,'runner_code_identity':code_identity(),
        'dependency_paths':args.dependency_path,'CPU_affinity':affinity,'output_cap':req['max_output_bytes']}
    planned_sha=digest(planned);planned_file=output/'PLANNED_IDENTITY.json'
    if planned_file.exists() and json.loads(planned_file.read_text())['sha256']!=planned_sha:raise ValueError('planned_or_actual_resume_identity_changed')
    write_json(planned_file,{'sha256':planned_sha,'identity':planned,'no_model_or_scores_yet':True})
    # Preserve the complete future metadata denominator even on dependency/model preflight failure.
    write_json(output/'EXECUTION_MANIFEST.json',read_locked(args.execution_manifest,args.manifest_sha256))
    write_json(output/'ASSET_LOCK.json',read_locked(args.asset_lock,args.asset_lock_sha256))
    if file_bytes(output)>req['max_output_bytes']:raise ValueError('frozen_metadata_snapshot_exceeds_output_capacity_no_worker_started')
    request=output/('REQUEST.'+str(time.time_ns())+'.json');write_json(request,req)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',TMPDIR=str(output/'tmp'),TEMP=str(output/'tmp'),TMP=str(output/'tmp'),
        HF_HOME=str(output/'cache'),HF_HUB_CACHE=str(output/'cache'),MPLCONFIGDIR=str(output/'cache'),TORCH_HOME=str(output/'cache'))
    for path in reversed(args.dependency_path):sys.path.insert(0,path)
    import psutil
    parent=psutil.Process();allowed=parent.cpu_affinity();chosen=affinity or allowed[:2]
    if len(chosen)>2 or not set(chosen)<=set(allowed):raise ValueError('unavailable_CPU_affinity')
    parent.cpu_affinity(chosen);cap=4*1024**3;peak=0;guard_error=None;tick=time.perf_counter()
    stdout=output/('worker.'+str(time.time_ns())+'.stdout.log');stderr=output/(stdout.name.replace('stdout','stderr'))
    with stdout.open('xb',buffering=0) as out,stderr.open('xb',buffering=0) as err:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'worker.py'),'--request',str(request)],cwd=output,env=env,
            stdin=subprocess.DEVNULL,stdout=out,stderr=err)
        try:created=psutil.Process(child.pid).create_time()
        except psutil.NoSuchProcess:created=None
        write_json(output/'PROCESS_START.json',{'PID':child.pid,'create_time':created,'parent_PID':os.getpid(),
            'worker_code_SHA':sha_file(ROOT/'worker.py'),'stdin':'DEVNULL','stdout':stdout.name,'stderr':stderr.name,'group_RSS_cap':cap,'CPU_affinity':chosen})
        try:
            while child.poll() is None:
                group=[parent]+parent.children(recursive=True);rss=0
                for proc in group:
                    try:rss+=proc.memory_info().rss
                    except psutil.NoSuchProcess:pass
                peak=max(peak,rss)
                if rss>cap or file_bytes(output)>req['max_output_bytes']:raise RuntimeError('physical_group_RSS_or_output_cap_exceeded')
                write_json(output/'RESOURCE_HEARTBEAT.json',{'observed_unix':time.time(),'group_RSS':rss,'peak_group_RSS':peak,'owned_output_bytes':file_bytes(output)})
                time.sleep(.1)
        except Exception as e:
            guard_error={'type':type(e).__name__,'error':str(e)}
            for proc in reversed(parent.children(recursive=True)):
                try:proc.terminate()
                except psutil.NoSuchProcess:pass
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        code=child.wait()
    write_json(output/'PROCESS_EXIT.json',{'worker_exit_code':code,'guard_failure':guard_error,'peak_group_RSS':peak,
        'wall_seconds':time.perf_counter()-tick,'stdout_SHA':sha_file(stdout),'stderr_SHA':sha_file(stderr),
        'fixed_manifest_denominator':info['expected_members'],'new_environment_installed':False,'scientific_gate_passed':False})
    # Re-materialize preserved events after guard/crash without generating any missing score.
    identity=output/'RUN_IDENTITY.json'
    if identity.exists():
        from run_state import journal,materialize
        m=read_locked(args.execution_manifest,args.manifest_sha256);key=json.loads(identity.read_text())['sha256']
        current=journal(output/'events.jsonl',key,m['members']);materialize(output,key,m['members'],current)
    else:
        from run_state import materialize
        m=read_locked(args.execution_manifest,args.manifest_sha256);materialize(output,planned_sha,m['members'],{})
        write_json(output/'PREFLIGHT_FAILURE_SCOPE.json',{'worker_exit_code':code,'all_members_pending':len(m['members']),
            'actual_encoder_not_established':True,'original_failure_log':stderr.name,'placeholder_scores_generated':False})
    print(json.dumps({'output':str(output),'worker_exit_code':code,'guard_failure':guard_error,'peak_group_RSS':peak,'metrics_computed':False}))
    return 0 if code==0 and guard_error is None else 2
def main(argv=None):
    args=parser().parse_args(argv);info=plan(args)
    if args.command=='plan':print(json.dumps(info,ensure_ascii=False,indent=2));return 0 if info['status']!='metadata_plan_rejected_or_dependencies_unfrozen' else 2
    return run(args,info)
if __name__=='__main__':raise SystemExit(main())
