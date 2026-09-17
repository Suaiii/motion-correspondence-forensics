"""CPU-only software evidence for six-frame static control preparation."""
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
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'tests')]
    assert not torch.cuda.is_initialized(),'CPU-only check must start without CUDA initialization'
    torch.set_num_threads(2);start=time.monotonic();stream=io.StringIO()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in ('test_composability','test_static_composability'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    if not result.wasSuccessful():raise RuntimeError(stream.getvalue())
    from forensics.composability_torch import six_frame_response
    tokens=torch.from_numpy(np.random.default_rng(713).normal(size=(1,6,256,32)).astype(np.float32))
    times={};matrix_counts={}
    for mode in ('temporal','static'):six_frame_response(tokens,branch_mode=mode)
    # Alternate order to reduce one-sided warm-cache effects; this remains a
    # tiny synthetic CPU measurement, never an end-to-end cost comparison.
    observations={m:[] for m in ('temporal','static')}
    for order in [('temporal','static'),('static','temporal'),('temporal','static')]:
        for mode in order:
            tick=time.perf_counter();r=six_frame_response(tokens,branch_mode=mode)
            observations[mode].append(time.perf_counter()-tick);matrix_counts[mode]=r['unique_affinity_matrices']
    assert not torch.cuda.is_initialized()
    names=['forensics/composability.py','forensics/composability_torch.py','forensics/local_composability.py',
           'forensics/mechanism_sampling.py','tests/test_composability.py','tests/test_static_composability.py','scripts/check_static_control_cpu.py']
    output=dict(work_package='cc-round-1-20260917',plan_version='cvpr27-20260917-v1.1',status='pass',
        observed_utc=datetime.now(timezone.utc).isoformat(),tests_run=result.testsRun,wall_seconds=time.monotonic()-start,
        torch=torch.__version__,numpy=np.__version__,device='cpu',cpu_threads=torch.get_num_threads(),cuda_initialized=False,
        source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
        shared_frame_count=6,temporal_triplet_count=6,static_triplets=[[i,i,i] for i in range(6)],
        head_parameters_each=217057,semantic_input='the same original six global vectors in both branches',
        unique_cached_affinity_matrices=matrix_counts,composition_products_each=78,
        synthetic_cpu_benchmark=dict(token_shape=list(tokens.shape),seconds_by_mode=observations,
            median_seconds={m:float(np.median(v)) for m,v in observations.items()},end_to_end=False),
        strong_static_baseline_trained=False,training_recipe_frozen=False,optimizer_steps=0,
        real_research_inputs_read=0,formal_gate_passed=False,test_log=stream.getvalue(),
        limitations=['Only interface, numerical and gradient contracts are verified.',
                    'Same head capacity and six-frame information do not imply identical compute.',
                    'A fixed-model branch replacement does not provide the retrained static-baseline result.'])
    with a.output.open('x',encoding='utf-8') as f:json.dump(output,f,indent=2);f.write('\n')
    print(json.dumps({k:output[k] for k in ('status','tests_run','wall_seconds','cuda_initialized','unique_cached_affinity_matrices','synthetic_cpu_benchmark')},indent=2))


if __name__=='__main__':main()
