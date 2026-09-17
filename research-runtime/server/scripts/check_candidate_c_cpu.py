"""DX03 evidence runner. Synthetic local CPU only, no optimizer/backbone."""
import argparse
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--work-plan',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Preserve existing evidence; use a new output')
    root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'tests')]
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2);start=time.perf_counter();stream=io.StringIO()
    modules=['test_composability','test_static_composability','test_candidate_c']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    from forensics.composability_config import C,load_candidate_c_config,descriptor
    from forensics.composability_torch import correspondence_response
    from forensics.local_composability import make_candidate_control_models
    from forensics.composability import shift_permutation
    config=load_candidate_c_config(root/'configs/candidate_c_centered3_v1.json')
    torch.manual_seed(713)
    z=torch.from_numpy(np.random.default_rng(713).normal(size=(1,3,256,768)).astype(np.float32))
    g=torch.from_numpy(np.random.default_rng(714).normal(size=(1,3,768)).astype(np.float32))
    models=make_candidate_control_models(713);observed={}
    for mode,model in models.items():
        model.eval()
        with torch.no_grad():
            maps=correspondence_response(z,candidate_id=C,branch_mode=mode)
            out=model.classify_maps(maps,g)
        observed[mode]=dict(head_parameters=sum(p.numel() for p in model.parameters()),
            response_shape=list(maps['responses'].shape),affinity_matrices=maps['unique_affinity_matrices'],
            composition_products=13*len(maps['triplets']),finite_logits=bool(torch.isfinite(out['logits']).all()),
            descriptor=descriptor(C,mode))
    base=np.random.default_rng(71).normal(size=(256,8));rng=np.random.default_rng(72)
    offsets=[(0,0),(1,2),(2,3)]
    cases={}
    for name,orders,interior in [
        ('translation_full',[shift_permutation((16,16),*d)[0] for d in offsets],False),
        ('translation_interior',[shift_permutation((16,16),*d)[0] for d in offsets],True),
        ('noncommuting_full',[rng.permutation(256) for _ in range(3)],False)]:
        tokens=torch.tensor(np.stack([base[o] for o in orders])[None],dtype=torch.float64)
        t=correspondence_response(tokens,candidate_id=C,interior_control=interior)
        s=correspondence_response(tokens,candidate_id=C,branch_mode='anchor_static',interior_control=interior)
        cases[name]=dict(response_max_gap=float((t['responses']-s['responses']).abs().max()),
            direct_js_max_gap=float((t['direct_js']-s['direct_js']).abs().max()))
    assert not torch.cuda.is_initialized()
    names=['forensics/composability.py','forensics/composability_torch.py','forensics/local_composability.py',
        'forensics/mechanism_sampling.py','forensics/composability_config.py','configs/candidate_c_centered3_v1.json',
        'tests/test_composability.py','tests/test_static_composability.py','tests/test_candidate_c.py',
        'scripts/check_candidate_c_cpu.py']
    record=dict(dispatch_id='cc-round-3-c-software-20260918',task_id='DX03',
        plan_version='cvpr27-20260918-v1.2',
        work_plan_sha256=hashlib.sha256(a.work_plan.read_bytes()).hexdigest(),
        status='pass' if result.wasSuccessful() else 'fail',tests_run=result.testsRun,
        old_A_regression_tests=21,new_C_tests=result.testsRun-21,test_log=stream.getvalue(),
        observed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-start,
        python=sys.version.split()[0],torch=torch.__version__,numpy=np.__version__,device='cpu',
        cpu_threads=torch.get_num_threads(),cuda_initialized=False,optimizer_steps=0,
        backward_checks_performed=True,backbone_executed=False,real_media_read=False,
        server_accessed=False,real_source_joint_support_established=False,scientific_gate_passed=False,
        config=config,observed_interfaces=observed,null_conditions=cases,
        source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
        limitations=['Software and synthetic feature-space evidence only',
            'No trained baseline, real-video discrimination or GPU profile',
            'Anchor-static is not an all-frame local baseline',
            'Legacy raw state_dict must not bypass the new compatible-checkpoint interface'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps({k:record[k] for k in ('status','tests_run','elapsed_seconds','null_conditions')},indent=2))
    if not result.wasSuccessful():
        print(stream.getvalue());raise SystemExit(1)


if __name__=='__main__':main()
