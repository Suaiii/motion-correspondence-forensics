"""Numerical and optional CUDA replay for the canonical composability prototype."""
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


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cuda',action='store_true')
    a=p.parse_args();root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root),str(root/'tests')]
    start=time.monotonic();stream=io.StringIO()
    tests=unittest.defaultTestLoader.loadTestsFromName('test_composability')
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    if not result.wasSuccessful():raise RuntimeError(stream.getvalue())
    cuda=[]
    if a.cuda:
        import torch
        from forensics.composability import six_frame_response as reference
        from forensics.composability_torch import six_frame_response as implementation
        torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
        torch.cuda.reset_peak_memory_stats()
        x=np.random.default_rng(1729).normal(size=(2,6,256,32)).astype(np.float32)
        for interior in (False,True):
            expect=[reference(t,interior_control=interior) for t in x]
            begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
            actual_input=torch.from_numpy(x).cuda();begin.record()
            actual=implementation(actual_input,interior_control=interior)
            end.record();torch.cuda.synchronize()
            errors={}
            for key in ('responses','direct_js','correspondence_entropies','middle_probability_mass'):
                measured=actual[key].cpu().numpy();expected=np.stack([r[key] for r in expect])
                np.testing.assert_allclose(measured,expected,atol=5e-6,rtol=1e-5,equal_nan=True)
                errors[key]=float(np.nanmax(np.abs(measured-expected)))
            np.testing.assert_array_equal(actual['support'].cpu().numpy(),np.stack([r['support'] for r in expect]))
            cuda.append(dict(interior_control=interior,max_absolute_errors=errors,
                cuda_wall_ms_including_validation_sync=begin.elapsed_time(end)))
        gpu=dict(device=torch.cuda.get_device_name(0),torch=torch.__version__,peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
                 replay=cuda,scope='synthetic operator check; no DINO, video decode, training or end-to-end profile')
    else:gpu=None
    files=['forensics/composability.py','forensics/composability_torch.py','forensics/mechanism_sampling.py',
           'tests/test_composability.py','scripts/check_composability.py']
    report=dict(status='pass',plan_version='cvpr27-20260917-v1',observed_utc=datetime.now(timezone.utc).isoformat(),
        unit_tests=result.testsRun,seconds=time.monotonic()-start,numpy=np.__version__,gpu=gpu,
        source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},
        test_log=stream.getvalue(),real_data_efficacy_measured=False,classifier_trained=False,formal_gate_passed=False,
        limitations=['Software invariants are not mechanism efficacy or novelty evidence.',
                    'New six-frame joint timing support is not validated by the old half-second pair census.',
                    'Cyclic wrap is explicit; the alternate control restricts middle nodes, not merely anchor rows.'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','unit_tests','seconds','gpu')},indent=2),flush=True)


if __name__=='__main__':main()
