"""Planner-owned CPU checks beyond the researchagent's DX03 test suite."""
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / 'research-runtime/server'
sys.path.insert(0, str(SERVER))
import numpy as np
import torch
from forensics.composability import correspondence_response as np_response
from forensics.composability_torch import correspondence_response as th_response
from forensics.composability_config import C
from forensics.local_composability import LocalComposability
from forensics.mechanism_sampling import choose_six, choose_centered_three


def main():
    started = time.perf_counter()
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    original = ROOT / 'research-runs/shared_plan_20260917/candidate_c_cpu_validation.json'
    original_bytes = original.read_bytes()
    receipt = json.loads(original_bytes)
    hashes = receipt['source_sha256']
    for name, digest in hashes.items():
        assert hashlib.sha256((SERVER / name).read_bytes()).hexdigest() == digest, name

    # A batch of distinct clips must agree with per-clip NumPy evaluation.
    rng = np.random.default_rng(91801)
    tokens = rng.normal(size=(2, 3, 256, 8))
    batch_errors = {}
    for mode in ('temporal', 'static', 'anchor_static'):
        batched = th_response(torch.tensor(tokens), candidate_id=C, branch_mode=mode)
        expected = np.stack([np_response(z, candidate_id=C, branch_mode=mode)['responses'] for z in tokens])
        gap = float(np.max(np.abs(batched['responses'].numpy() - expected)))
        assert gap < 1e-12, (mode, gap)
        batch_errors[mode] = gap

    # Independently generated VFR sequences and nonzero PTS origins.
    subset_cases = 0
    for _ in range(256):
        pts = float(rng.uniform(-100, 100)) + np.cumsum(rng.uniform(.025, .08, size=80))
        ia, ma = choose_six(pts)
        ic, mc = choose_centered_three(pts)
        assert np.array_equal(ic, ia[[1, 3, 5]])
        assert np.allclose(mc['targets'], np.asarray(ma['targets'])[[1, 3, 5]], rtol=0, atol=1e-12)
        subset_cases += 1

    # Rejection must precede any parameter mutation, including cases omitted
    # from the delivered test: missing/extra keys, dtype and infinity.
    model = LocalComposability(feature_dim=8, width=4, hidden=8, candidate_id=C)
    payload = model.checkpoint_payload()
    before = {k: v.clone() for k, v in model.state_dict().items()}
    key = next(iter(payload['state_dict']))
    malformed = {}
    item = copy.deepcopy(payload); item['state_dict'][key] = item['state_dict'][key].double()
    malformed['wrong_dtype'] = item
    item = copy.deepcopy(payload); del item['state_dict'][key]
    malformed['missing_key'] = item
    item = copy.deepcopy(payload); item['state_dict']['unexpected'] = torch.zeros(1)
    malformed['extra_key'] = item
    item = copy.deepcopy(payload); item['state_dict'][key].fill_(float('inf'))
    malformed['infinite_value'] = item
    for name, item in malformed.items():
        try:
            model.load_compatible_checkpoint(item)
        except ValueError:
            pass
        else:
            raise AssertionError('Accepted ' + name)
        assert all(torch.equal(v, before[k]) for k, v in model.state_dict().items()), name

    assert not torch.cuda.is_initialized()
    assert original.read_bytes() == original_bytes
    for name, digest in hashes.items():
        assert hashlib.sha256((SERVER / name).read_bytes()).hexdigest() == digest, name
    result = dict(status='pass', scope='independent_mechanical_software_checks_only',
        observed_at=datetime.datetime.now().astimezone().isoformat(),
        source_commit='e074ca7', original_receipt_sha256=hashlib.sha256(original_bytes).hexdigest(),
        batch_size=2, numpy_torch_response_max_error=batch_errors,
        independent_vfr_subset_cases=subset_cases, checkpoint_rejections=list(malformed),
        checkpoint_mutations=0, cpu_threads=torch.get_num_threads(),
        cuda_initialized=torch.cuda.is_initialized(), optimizer_steps=0,
        real_media_read=False, server_accessed=False, scientific_gate_passed=False,
        elapsed_seconds=time.perf_counter()-started, source_sha256=hashes)
    out = Path(__file__).with_name('dx03_extra_checks_20260918.json')
    with out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'source_sha256'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
