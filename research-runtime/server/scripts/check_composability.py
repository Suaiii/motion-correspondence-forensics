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
        from forensics.local_composability import LocalComposability
        torch.manual_seed(1729)
        head=LocalComposability(feature_dim=32).cuda().eval()
        global_tokens=torch.randn(2,6,32,device='cuda',requires_grad=True)
        patch_tokens=torch.from_numpy(x).cuda().requires_grad_()
        output=head(patch_tokens,global_tokens)
        assert output['logits'].shape==(2,) and torch.isfinite(output['logits']).all()
        output['logits'].sum().backward()
        assert patch_tokens.grad is None and global_tokens.grad is None
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters())
        maps=implementation(patch_tokens.detach())
        order=torch.tensor([5,2,1,4,0,3],device='cuda')
        permuted={k:(v[:,order] if k in ('responses','direct_js','correspondence_entropies','support','middle_probability_mass') else v) for k,v in maps.items()}
        with torch.no_grad():
            np.testing.assert_allclose(head.classify_maps(maps,global_tokens)['logits'].cpu(),
                head.classify_maps(permuted,global_tokens)['logits'].cpu(),atol=1e-6,rtol=1e-5)
            torch.testing.assert_close(head.classify_maps(maps,global_tokens)['logits'],
                head.classify_maps(dict(maps,direct_js=maps['direct_js']+100),global_tokens)['logits'])
            empty=dict(maps,support=torch.zeros_like(maps['support']),responses=torch.full_like(maps['responses'],float('nan')),
                direct_js=torch.full_like(maps['direct_js'],float('nan')))
            fallback=head.classify_maps(empty,global_tokens)
            assert fallback['diagnostics']['semantic_fallback'].all() and torch.isfinite(fallback['logits']).all()
        production_parameters=sum(p.numel() for p in LocalComposability().parameters())
        assert production_parameters<1_000_000
        gpu['head_interface_checks']=dict(logit_shape=[2],backbone_inputs_detached=True,head_gradients_finite=True,
            unordered_triplet_readout=True,direct_js_diagnostic_only=True,empty_support_semantic_fallback=True,production_parameter_count=production_parameters,
            trained_on_real_data=False)
    else:gpu=None
    files=['forensics/composability.py','forensics/composability_torch.py','forensics/local_composability.py','forensics/mechanism_sampling.py',
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
