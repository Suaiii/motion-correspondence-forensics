"""Runtime-only offline vision load and exact frozen author reader/forward."""
import hashlib,json,os,time,types
from pathlib import Path
from contract import ROOT,contained,sha_file
from author_definitions import FORWARD_SOURCE,READER_SOURCE,TRANSFORMERS

def load_offline(asset_dir,lock,seed):
    # No heavy dependency is imported until the explicit future worker command.
    import torch
    from transformers import XCLIPConfig,XCLIPVisionModel
    if torch.get_default_dtype()!=torch.float32:torch.set_default_dtype(torch.float32)
    torch.set_num_threads(2);torch.set_num_interop_threads(2)
    torch.random.default_generator.manual_seed(seed)
    config_path=contained(asset_dir,lock['config_path']);weight=contained(asset_dir,lock['checkpoint_path'])
    if sha_file(config_path)!=lock['config_sha256'] or weight.stat().st_size!=lock['checkpoint_bytes'] or sha_file(weight)!=lock['checkpoint_sha256']:raise ValueError('offline_asset_bytes_not_frozen_lock')
    cfg=json.loads(config_path.read_text(encoding='utf-8-sig'))
    if cfg.get('model_type')!='xclip':raise ValueError('XCLIP_config_model_type_required_actual_xclip')
    config=XCLIPConfig.from_dict(cfg)  # pure local JSON, no from_pretrained/hub request
    if config.vision_config.patch_size!=16 or config.vision_config.image_size!=224:raise ValueError('author_XCLIP16_patch16_raster224_config_required')
    if weight.suffix=='.bin':
        version=tuple(int(x) for x in torch.__version__.split('+')[0].split('.')[:2])
        if version<(2,6):raise ValueError('torch>=2.6_required_for_safe_bin_weights_only; no unsafe_fallback')
    # Keep the author HF constructor path, with explicit local-only/full-float32 options.
    encoder,loading=XCLIPVisionModel.from_pretrained(str(Path(asset_dir).resolve()),local_files_only=True,
        torch_dtype=torch.float32,output_loading_info=True,use_safetensors=weight.suffix=='.safetensors',
        weights_only=True,ignore_mismatched_sizes=False)
    expected=encoder.state_dict();required=set(expected)
    if weight.suffix=='.safetensors':
        from safetensors import safe_open
        with safe_open(str(weight),framework='pt',device='cpu') as reader:
            keys=set(reader.keys());missing=sorted(required-keys)
            shape_errors=[{'key':k,'checkpoint':list(reader.get_slice(k).get_shape()),'expected':list(expected[k].shape)} for k in sorted(required&keys) if list(reader.get_slice(k).get_shape())!=list(expected[k].shape)]
    else:
        full=torch.load(str(weight),map_location='cpu',weights_only=True,mmap=True)
        if not isinstance(full,dict):raise ValueError('flat_official_checkpoint_state_dict_required')
        keys=set(full);missing=sorted(required-keys);shape_errors=[k for k in required&keys if not isinstance(full[k],torch.Tensor) or tuple(full[k].shape)!=tuple(expected[k].shape)];del full
    text_unused=sorted(k for k in keys-required if k.startswith(('text_model.','text_projection')))
    unexpected_visual=sorted(k for k in keys-required if k.startswith('vision_model.'))
    other_unused=sorted(keys-required-set(text_unused)-set(unexpected_visual))
    if missing or shape_errors or loading.get('missing_keys') or loading.get('mismatched_keys') or loading.get('error_msgs'):
        raise ValueError(json.dumps({'missing_visual_keys':missing,'visual_shape_errors':shape_errors,'HF_loading':loading,'unused_text_keys':text_unused}))
    for k,tensor in expected.items():
        if tensor.is_floating_point() and not bool(torch.isfinite(tensor).all()):raise ValueError('nonfinite_checkpoint_visual_weight:'+k)
    encoder=encoder.to(device='cpu',dtype=torch.float32).eval();del expected
    ns={'torch':torch,'F':torch.nn.functional,'Transformers':TRANSFORMERS};exec(compile(FORWARD_SOURCE,'<frozen_D3_forward>','exec'),ns)
    def init(self):
        torch.nn.Module.__init__(self);self.encoder=encoder;self.encoder_type='XCLIP-16';self.loss_type='l2'
    model=type('OfflineFrozenAuthorD3',(torch.nn.Module,),{'__init__':init,'forward':ns['forward']})().eval()
    receipt={'checkpoint_sha256':lock['checkpoint_sha256'],'config_sha256':lock['config_sha256'],'expected_visual_keys':len(required),
        'missing_visual_keys':[],'visual_shape_errors':[],'unused_visual_buffer_keys':unexpected_visual,'HF_loading_info':loading,'unused_text_keys':text_unused,'unused_other_multimodal_keys':other_unused,
        'random_missing_weights_accepted':False,'class':'XCLIPVisionModel','encoder_type':'XCLIP-16','loss_type':'l2',
        'dtype':'float32','device':'cpu','forward_AST_unchanged':True,'network_fallback':False,'projection_or_detection_head_used':False}
    return torch,model,receipt

def prepared_tensor(torch,prepared_root,member):
    import numpy as np
    import cv2
    import albumentations
    import re
    cv2.setNumThreads(1)
    folder=contained(prepared_root,member['prepared_folder']);expected=[f['name'] for f in member['prepared_frames']]
    ns={'torch':torch,'np':np,'cv2':cv2,'albumentations':albumentations,'os':os,'re':re}
    exec(compile(READER_SOURCE,'<frozen_D3_reader>','exec'),ns)
    actual=sorted(os.listdir(folder),key=ns['get_number_from_filename'])
    if actual!=expected:raise ValueError('prepared_folder_members_or_author_numeric_order_changed')
    for f in member['prepared_frames']:
        if not (folder/f['name']).resolve().is_relative_to(Path(prepared_root).resolve()):raise ValueError('prepared_JPEG_symlink_escapes_locked_root')
        if sha_file(folder/f['name'])!=f['sha256']:raise ValueError('prepared_JPEG_hash_changed:'+f['name'])
    tick=time.perf_counter();tensor=ns['read_video'](str(folder),ns['set_preprocessing'](None,None));wall=time.perf_counter()-tick
    record=member['input_record'];shape=list(tensor.shape)
    if shape!=record['actual_tensor_shape'] or str(tensor.dtype)!='torch.float32' or tensor.device.type!='cpu':raise ValueError('actual_prepared_tensor_shape_dtype_device_mismatch')
    observed=hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
    if observed!=record['actual_tensor_SHA256']:raise ValueError('actual_preprocessing_tensor_not_frozen_record')
    return tensor,{'wall_seconds':wall,'tensor_sha256':observed,'tensor_shape':shape,'native_unique':record['unique_native_frames'],
        'logical_slots':record['actual_input_slots'],'original_video_decode_repeated':False,'JPEG_hashes_checked':len(expected),'BGR_retained':True}

def score_one(torch,model,tensor):
    timing={};raster={}
    def before(module,args):timing['start']=time.perf_counter();raster['input_shape']=list(args[0].shape)
    def after(module,args,output):timing['end']=time.perf_counter()
    a=model.encoder.register_forward_pre_hook(before);b=model.encoder.register_forward_hook(after)
    tick=time.perf_counter()
    try:
        with torch.no_grad():features,mean,std=model(tensor.unsqueeze(0))
        if features.dtype!=torch.float32 or std.dtype!=torch.float32:raise ValueError('author_forward_float32_required')
        raw=float(std.detach().cpu().item())
    finally:a.remove();b.remove()
    total=time.perf_counter()-tick;encoder=timing['end']-timing['start']
    return raw,{'encoder_wall_seconds':encoder,'head_wall_seconds':max(0,total-encoder),'model_consumed_shape':raster['input_shape'],
        'pooler_output_shape':list(features.shape),'author_std_correction':1,'head_is_L2_first_difference_sample_std':True}
