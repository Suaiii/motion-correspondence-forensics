"""Scoreless metadata contract. All functions are safe for import/help/plan."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HEX=re.compile(r'^[0-9a-f]{64}$')
ROLES={'fit','calibration','development_audit','held_generator_audit','external_audit'}
DEPS=['torch','torchvision','transformers','numpy','albumentations','safetensors','jsonschema','psutil']
CV2_DISTRIBUTIONS={'opencv-python','opencv-python-headless'}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha_file(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def read_locked(path,expected):
    if not expected or not HEX.fullmatch(expected):raise ValueError('external_SHA256_required')
    p=Path(path);raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('metadata_file_hash_mismatch:'+str(p))
    return json.loads(raw.decode('utf-8-sig'))
def relative_path(value):
    if not isinstance(value,str) or not value or '\\' in value:raise ValueError('POSIX_relative_path_required')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or ':' in value:raise ValueError('relative_path_escapes_root')
    return p
def contained(root,relative):
    root=Path(root).resolve();p=(root/relative_path(relative)).resolve()
    if not p.is_relative_to(root):raise ValueError('resolved_path_escapes_root')
    return p
def require_hash(value,name):
    if not isinstance(value,str) or not HEX.fullmatch(value):raise ValueError('invalid_SHA256:'+name)
def validate_manifest(m):
    if m.get('version')!='d3_execution_manifest/1.0' or m.get('status')!='frozen' or m.get('fixture') is not False:raise ValueError('frozen_real_execution_manifest_required')
    if m.get('method_id')!='d3' or m.get('encoder_type')!='XCLIP-16' or m.get('loss_type')!='l2':raise ValueError('fixed_D3_XCLIP16_l2_required')
    if m.get('track')!='native_reference':raise ValueError('B8_first_scope_is_prepared_author_native_reference; matched_runtime_inputs_not_frozen')
    if m.get('preprocessing_sha256')!=sha_file(ROOT/'PREPROCESS_IDENTITY.json'):raise ValueError('runner_preprocessing_identity_mismatch')
    for k in ['selection_sha256','split_sha256','protocol_sha256','support_lock_sha256','public_gate_overlay_sha256','A10_delivery_sha256']:require_hash(m.get(k),k)
    if not isinstance(m.get('cohort_id'),str) or not m['cohort_id']:raise ValueError('cohort_id_required')
    if type(m.get('seed')) is not int:raise ValueError('explicit_integer_seed_required')
    if m.get('method_revision')!=json.loads((ROOT/'METHOD_IDENTITY.json').read_text())['author_commit']:raise ValueError('method_revision_mismatch')
    rows=m.get('members')
    if not isinstance(rows,list) or not rows or type(m.get('expected_members')) is not int or m.get('expected_members')!=len(rows):raise ValueError('nonempty_complete_manifest_denominator_required')
    provider=m.get('cv2_provider',{})
    if provider.get('distribution') not in CV2_DISTRIBUTIONS or not isinstance(provider.get('version'),str) or not provider['version']:raise ValueError('actual_cv2_distribution_and_version_required; no_alias_install_fallback')
    for k in ['module_source_sha256','distribution_record_sha256']:require_hash(provider.get(k),'cv2_'+k)
    relative_path(provider.get('module_relative_path'))
    if not isinstance(provider.get('native_extensions'),dict) or not provider['native_extensions']:raise ValueError('cv2_native_extension_source_lock_required')
    for path,h in provider['native_extensions'].items():relative_path(path);require_hash(h,'cv2_native_extension')
    required=DEPS+[provider['distribution']]
    if not isinstance(m.get('dependency_versions'),dict) or set(m['dependency_versions'])!=set(required) or any(not m['dependency_versions'].get(k) for k in required):raise ValueError('future_runtime_dependency_versions_must_be_frozen')
    if m['dependency_versions'][provider['distribution']]!=provider['version']:raise ValueError('cv2_distribution_version_lock_conflict')
    ids=set()
    for ordinal,r in enumerate(rows):
        if type(r.get('ordinal')) is not int or r.get('ordinal')!=ordinal or not isinstance(r.get('sample_id'),str) or r['sample_id'] in ids:raise ValueError('unique_sample_id_and_exact_manifest_order_required')
        ids.add(r['sample_id']);require_hash(r.get('source_sha256'),'source_sha256')
        if type(r.get('approved_public_candidate')) is not bool or not isinstance(r.get('public_gate_reasons'),list):raise ValueError('explicit_A10_conservative_public_gate_required')
        if not r['approved_public_candidate'] and not r['public_gate_reasons']:raise ValueError('excluded_member_needs_preserved_A10_reason')
        if r.get('role') not in ROLES or r.get('ancestry_status')!='unknown':raise ValueError('descriptive_role_and_unknown_ancestry_required; final_remains_sealed')
        if type(r.get('label_fake')) is not int or r['label_fake'] not in [0,1]:raise ValueError('binary_published_label_required')
        for k in ['ancestor_id','source_family','generator_family','processing_id']:
            if not isinstance(r.get(k),str) or not r[k]:raise ValueError('identity_field_required:'+k)
        if (r['label_fake']==0)!=(r['generator_family']=='real'):raise ValueError('real_label_generator_semantics')
        relative_path(r.get('prepared_folder'));frames=r.get('prepared_frames')
        if not isinstance(frames,list) or len(frames)<8:raise ValueError('author_prepared_minimum8_metadata_required')
        numbers=[]
        for f in frames:
            name=f.get('name','');match=re.fullmatch(r'([1-9][0-9]*)\.jpg',name)
            if not match:raise ValueError('author_numeric_JPEG_names_required')
            numbers.append(int(match[1]));require_hash(f.get('sha256'),'prepared_frame_sha256')
        if numbers!=sorted(set(numbers)):raise ValueError('prepared_frame_numeric_order_or_duplicates')
        record=r.get('input_record')
        if not isinstance(record,dict) or record.get('method')!='d3' or record.get('sample_id')!=r['sample_id'] or record.get('input_sha256')!=r['source_sha256']:raise ValueError('scoreless_input_record_source_binding')
        if record.get('source_binding')!='actual_current_backend_observation':raise ValueError('ambiguous_or_metadata_only_prepared_input_not_encoder_ready')
        recorded_role={'in_domain_audit':'development_audit'}.get(record.get('source_role'),record.get('source_role'))
        if r['role']!=recorded_role:raise ValueError('prepared_source_role_cannot_be_relabelled; first12fit_stays_fit')
        require_hash(r.get('input_record_sha256'),'input_record_sha256')
        if digest(record)!=r['input_record_sha256']:raise ValueError('canonical_input_record_hash_mismatch')
        t=8 if len(frames)<16 else 16
        if record.get('actual_input_slots')!=t or record.get('actual_tensor_shape')!=[t,3,224,224]:raise ValueError('author_reader_prefix_or_shape_contract')
        require_hash(record.get('actual_tensor_SHA256'),'actual_tensor_SHA256')
        if r.get('pts_field') not in ['pts','pkt_pts']:raise ValueError('native_integer_PTS_field_required')
        if record.get('encoder_head_calls')!=0 or record.get('GPU_started') is not False:raise ValueError('prepared_input_record_must_remain_scoreless_original')
    return rows
def validate_asset_lock(a):
    if a.get('version')!='d3_asset_lock/1.0' or a.get('status')!='frozen':raise ValueError('frozen_asset_lock_required')
    if a.get('repository')!='microsoft/xclip-base-patch16' or a.get('revision')!='d6184e3fd8780d04c85d0f1eabe5f94bf44d98f6':raise ValueError('fixed_author_XCLIP_asset_revision_required')
    for field in ['checkpoint_path','config_path']:relative_path(a.get(field))
    for field in ['checkpoint_sha256','config_sha256','C9_delivery_sha256']:require_hash(a.get(field),field)
    if type(a.get('checkpoint_bytes')) is not int or a['checkpoint_bytes']<1:raise ValueError('verified_checkpoint_size_required')
    if Path(a['checkpoint_path']).suffix not in ['.safetensors','.bin']:raise ValueError('supported_safe_checkpoint_format_required')
    if a['checkpoint_path'] not in ['model.safetensors','pytorch_model.bin'] or a['config_path']!='config.json':raise ValueError('canonical_local_HF_asset_directory_required')
    if Path(a['config_path']).name!='config.json':raise ValueError('locked_full_XCLIP_config_json_required')
    return a
def code_identity():
    lock=json.loads((ROOT/'CODE_LOCK.json').read_text(encoding='utf-8-sig'))
    for rel,h in lock['runtime_files'].items():
        if sha_file(ROOT/rel)!=h:raise ValueError('runner_code_or_evaluator_changed:'+rel)
    return digest(lock['runtime_files'])
