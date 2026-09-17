"""Synthetic feature-space identifiability diagnostic; no video/GPU/training.

Uses the unchanged NumPy reference. A toroidal translation is a permutation of
one fixed patch-token field, not an assertion that DINO is translation equivariant.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forensics.composability import TRIPLETS, shift_permutation, six_frame_response


def spatial_readout(maps, seed=811):
    """Fixed random two-conv/GELU readout matching the spatial architecture only.

    Not a trained detector. The same weights apply to every map and condition.
    """
    rng = np.random.default_rng(seed)
    x = maps
    for channels in (32, 32):
        k = rng.normal(size=(channels, x.shape[1], 3, 3)) / np.sqrt(x.shape[1]*9)
        windows = np.lib.stride_tricks.sliding_window_view(
            np.pad(x, ((0, 0), (0, 0), (1, 1), (1, 1))), (3, 3), axis=(-2, -1))
        x = np.einsum('bchwij,ocij->bohw', windows, k, optimize=True)
        x = .5*x*(1+np.vectorize(math.erf)(x/np.sqrt(2)))
    return x.mean(axis=(-1, -2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    offsets = [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3)]
    indices = [shift_permutation((16, 16), *d)[0] for d in offsets]
    anchors = np.array([t[0] for t in TRIPLETS])
    anchor_counts = Counter(anchors.tolist())
    wa = np.array([anchor_counts[i]/6 for i in range(6)])
    wd = np.array([2, 3, 4, 4, 3, 2])/18
    cases = []
    for seed in (17, 29, 43):
        rng = np.random.default_rng(seed)
        base = rng.normal(size=(256, 12))
        tokens = np.stack([base[i] for i in indices])
        temporal = six_frame_response(tokens)
        static = six_frame_response(tokens, branch_mode='static')
        rm = float(np.max(np.abs(temporal['responses']-static['responses'][anchors])))
        dm = float(np.max(np.abs(temporal['direct_js']-static['direct_js'][anchors])))
        np.testing.assert_allclose(temporal['responses'],static['responses'][anchors],atol=1e-12,rtol=0)
        np.testing.assert_allclose(temporal['direct_js'],static['direct_js'][anchors],atol=1e-12,rtol=0)
        hs = spatial_readout(static['responses'])
        ht = spatial_readout(temporal['responses'])
        anchor_gap = float(np.linalg.norm(ht.mean(0)-wa@hs))
        assert anchor_gap < 1e-12
        interior_t = six_frame_response(tokens, interior_control=True)
        interior_s = six_frame_response(tokens, interior_control=True, branch_mode='static')
        scrambled = np.stack([base[rng.permutation(256)] for _ in range(6)])
        scramble_t = six_frame_response(scrambled)
        scramble_s = six_frame_response(scrambled, branch_mode='static')
        scramble_gap = float(np.max(np.abs(scramble_t['responses']-scramble_s['responses'][anchors])))
        assert scramble_gap > 1e-6
        cases.append(dict(seed=seed,response_map_max_error=rm,direct_js_max_error=dm,
            temporal_vs_anchor_static_readout_l2=anchor_gap,
            temporal_vs_uniform_static_readout_l2=float(np.linalg.norm(ht.mean(0)-hs.mean(0))),
            temporal_vs_degree_static_readout_l2=float(np.linalg.norm(ht.mean(0)-wd@hs)),
            fixed_interior_response_map_gap=float(np.max(np.abs(interior_t['responses']-interior_s['responses'][anchors]))),
            arbitrary_reindex_response_map_gap=scramble_gap))
    source_files = [Path(__file__),Path(__file__).resolve().parents[1]/'forensics/composability.py']
    record = dict(work='offline_translation_null_followup',plan_version='cvpr27-20260917-v1.1',
        observed_utc=datetime.now(timezone.utc).isoformat(),seeds=[17,29,43],
        grid=[16,16],feature_dim=12,temperature=.1,scales=[1,2,4],offsets=offsets,
        triplets=TRIPLETS,anchor_counts=[anchor_counts[i] for i in range(6)],
        anchor_weights=wa.tolist(),degree_weights=wd.tolist(),cases=cases,
        tolerance=1e-12,checks_passed=True,elapsed_local_seconds=time.perf_counter()-start,
        numpy_version=np.__version__,python_version=sys.version.split()[0],
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        classification_training=False,real_data=False,backbone_executed=False,server_accessed=False,
        gpu_used=False,scientific_gate_passed=False,
        limitations=['Exact permuted synthetic tokens, not pixels or measured DINO equivariance',
            'Equality requires full middle support and translations commuting with perturbations',
            'Fixed random spatial head only; readout distances are not detection metrics',
            'Neither a general failure theorem nor evidence of a new detector'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks_passed=True,elapsed_local_seconds=record['elapsed_local_seconds'],cases=cases)))


if __name__ == '__main__':
    main()
