"""Read locked source text only; never import author/torch/model code."""
import ast,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(ROOT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    monitor=BASE/'monitor';freeze=monitor/'B8_FROZEN_INPUT_030.json'
    assert sha(freeze)=='b67c2bdfb87ad238baeabe7acc400004d4f358969d53260dfd7e330417b48a2c'
    lock=json.loads(freeze.read_text(encoding='utf-8-sig'))
    assert sha(monitor/lock['workorder'])==lock['workorder_SHA256']
    actual=[]
    for rel,h in lock['input_SHA256'].items():
        p=BASE/rel;assert sha(p)==h,rel;actual.append({'path':rel,'sha256':h,'bytes':p.stat().st_size})
    save('INPUT_LOCK.json',{'B8_frozen_input_SHA':sha(freeze),'frozen_inputs':actual,'scope':lock,'source_bytes_checked':True})
    src=BASE/'baselines/sources/d3';dst=ROOT/'author_snapshot';dst.mkdir(exist_ok=True)
    for rel in ['models/D3_model.py','data/datasets.py','eval.py','utils/video2frame.py','commit.json','requirements.txt']:
        target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/rel,target)
    model=(src/'models/D3_model.py').read_text(encoding='utf-8-sig');data=(src/'data/datasets.py').read_text(encoding='utf-8-sig')
    mt=ast.parse(model);dt=ast.parse(data);cls=next(x for x in mt.body if isinstance(x,ast.ClassDef) and x.name=='D3_model')
    forward=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='forward')
    names={'crop_center_by_percentage','get_number_from_filename','read_video','set_preprocessing'}
    funcs=[x for x in dt.body if isinstance(x,ast.FunctionDef) and x.name in names];assert len(funcs)==4
    forward_text=ast.unparse(forward);reader_text='\n\n'.join(ast.unparse(x) for x in funcs)
    code='"""Frozen author definitions; runtime compilation only after explicit run."""\n'
    code+='FORWARD_SOURCE='+repr(forward_text)+'\nREADER_SOURCE='+repr(reader_text)+'\n'
    code+='TRANSFORMERS='+repr(['CLIP-16','CLIP-32','XCLIP-16','XCLIP-32','DINO-base','DINO-large'])+'\n'
    (ROOT/'author_definitions.py').write_text(code,encoding='utf-8')
    assert ast.dump(ast.parse(forward_text).body[0],include_attributes=False)==ast.dump(forward,include_attributes=False)
    for generated,original in zip(ast.parse(reader_text).body,funcs):assert ast.dump(generated,include_attributes=False)==ast.dump(original,include_attributes=False)
    evaluator=BASE/'baselines/input_contract_recovery_v1/evaluator_v4';own=ROOT/'evaluator_v4';own.mkdir(exist_ok=True)
    copied=[]
    for p in sorted(evaluator.iterdir()):
        if p.is_file() and p.suffix in ['.py','.json']:
            target=own/p.name;shutil.copyfile(p,target);assert sha(p)==sha(target)
            copied.append({'path':str(target.relative_to(ROOT)),'source':str(p.relative_to(BASE)),'sha256':sha(target),'diff':'byte_identical'})
    save('SOURCE_ADAPTATION.json',{'author_forward_AST_unchanged':True,'author_reader_four_functions_AST_unchanged':True,
        'model_constructor':'explicit offline local asset loader; no original from_pretrained/hub fallback constructor invoked',
        'selection_loop':'ordered frozen execution manifest replaces author two CSV head1000; no per-class cap',
        'A7_adapter_entry_called':False,'A7_preparation_or_old27_replayed':False,
        'prepared_inputs':'reuse frozen JPEG folders and scoreless v4 input records; no new video sampler or metric implementation',
        'evaluator_copies':copied,'original_namespaces_written':False})
    save('PREPROCESS_IDENTITY.json',{'method':'d3','reader_source_SHA':sha(src/'data/datasets.py'),
        'profile':'frozen author prepared JPEG prefix8or16','color':'cv2 BGR retained','crop':'0.1 from both sides of longer raster axis, integer author rounding',
        'resize':[224,224],'normalize_mean':[0.485,0.456,0.406],'normalize_std':[0.229,0.224,0.225],'max_pixel_value':255,
        'augmentation':[None,None],'prepared_frame_clock':'provided frozen input record, not nearest-index substitute',
        'sampling_reimplemented':False,'native_reference_only':True,'historical_dependency_equivalence':'not_certified'})
    print(json.dumps({'source_hashes':len(actual),'author_forward_AST_unchanged':True,'reader_functions':4,'evaluator_byte_identical_files':len(copied),'model_initializations':0}))
if __name__=='__main__':main()
