"""Finite B8 syntax/import/help/plan verification only. No inference/metric fixtures."""
import ast,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file()}
def main():
    code=json.loads((ROOT/'CODE_LOCK.json').read_text());syntax=[]
    for name,h in code['runtime_files'].items():
        p=ROOT/name;assert sha(p)==h
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'));syntax.append(name)
    stages=[]
    commands=[('help',[sys.executable,'-X','utf8','-B',str(ROOT/'runner.py'),'--help']),
        ('run_help',[sys.executable,'-X','utf8','-B',str(ROOT/'runner.py'),'run','--help']),
        ('plan',[sys.executable,'-X','utf8','-B',str(ROOT/'runner.py'),'plan']),
        ('environment_help',[sys.executable,'-X','utf8','-B',str(ROOT/'environment_lock.py'),'--help']),
        ('assembler_help',[sys.executable,'-X','utf8','-B',str(ROOT/'assemble_manifest.py'),'--help'])]
    before_all=snapshot()
    for name,argv in commands:
        before=snapshot();r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
        after=snapshot();assert r.returncode==0 and before==after,(name,r.stderr.decode(errors='replace'))
        if name=='plan':
            info=json.loads(r.stdout);assert info['model_initializations']==info['encoder_calls']==info['media_bytes_read']==info['GPU_calls']==info['network_calls']==info['writes']==0
            assert info['status']=='awaiting_C9_A10_frozen_execution_and_asset_locks' and info['missing_future_inputs']
        stages.append({'stage':name,'argv':argv,'exit_code':r.returncode,'filesystem_changes':0,
            'stdout':r.stdout.decode('utf-8'),'stderr':r.stderr.decode('utf-8'),'wall_seconds_bound':30})
    child="""import sys,json,importlib.abc
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','torchvision','transformers','numpy','cv2','albumentations','safetensors','psutil','jsonschema','timm'}:raise RuntimeError('heavy_import_forbidden:'+fullname)
sys.meta_path.insert(0,Block())
import contract,author_definitions,backend,run_state,worker,runner,environment_lock,assemble_manifest
runner.main(['plan'])
assert not any(k.split('.')[0] in {'torch','torchvision','transformers','numpy','cv2','albumentations','safetensors','psutil','jsonschema','timm'} for k in sys.modules)
print(json.dumps({'side_effect_import_and_plan':'pass','heavy_dependencies_imported':0,'real_scores_generated':0}))
"""
    r=subprocess.run([sys.executable,'-X','utf8','-B','-c',child],cwd=ROOT,capture_output=True,timeout=30)
    assert r.returncode==0 and snapshot()==before_all,r.stderr.decode(errors='replace')
    stages.append({'stage':'blocked_heavy_import_and_plan','exit_code':r.returncode,'stdout':r.stdout.decode('utf-8'),'stderr':r.stderr.decode('utf-8'),'filesystem_changes':0})
    inputs=json.loads((ROOT/'INPUT_LOCK.json').read_text());base=ROOT.parents[1]
    assert all(sha(base/x['path'])==x['sha256'] for x in inputs['frozen_inputs'])
    (ROOT/'SOFTWARE_VERIFICATION.json').write_text(json.dumps({'status':'syntax_and_no_side_effect_import_help_plan_pass',
        'syntax_modules':syntax,'stages':stages,'frozen_input_SHA_recheck_count':len(inputs['frozen_inputs']),
        'model_initializations':0,'encoder_calls':0,'GPU_calls':0,'cloud_calls':0,'media_decode_or_read':0,
        'real_or_fixture_prediction_rows':0,'old27_media_or_full_contract_suite_replayed':False,
        'tested_runtime_model_loading_or_resume':False,'observed_local_unix':time.time()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'stages':len(stages),'syntax_modules':len(syntax),'heavy_imports':0,'source_bytes_unchanged':True,'models_media_cloud_GPU':0}))
if __name__=='__main__':main()
