"""Independent code path for stored GPU head replay; never trains a model."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from sklearn.metrics import roc_auc_score
import torch
from torch import nn


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    a = parser.parse_args()
    output = a.root / 'verification.json'
    assert not output.exists()
    for rel, digest in read(a.root / 'artifact_hashes.json').items():
        assert sha(a.root / rel) == digest, rel
    report = read(a.root / 'report.json'); protocol = read(a.root / 'protocol.json')
    assert report['complete'] and report['total_fits'] == 60
    parent = a.base / 'runs/paired_dino_time_v1'
    assert sha(parent / 'manifest.json') == protocol['parent_manifest_sha256']
    rows = read(parent / 'manifest.json')
    cache = a.base / 'runs/time_matched_dino_v1'
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    observed = []
    for held in protocol['holdouts']:
        ids = np.array([i for i, r in enumerate(rows) if r['role'] == 'audit' and r['source'] in ('vript', held)])
        tensors = {k: [] for k in ('semantic_duplicate', 'time_std', 'time_delta')}
        for i in ids:
            row = rows[i]; key = hashlib.sha256(row['sample_id'].encode()).hexdigest()
            record = read(cache / 'records' / (key + '.json'))
            path = cache / record['time_feature_file']
            assert sha(path) == row['time_feature_sha256']
            z = np.load(path).astype(np.float64)
            z /= np.maximum(np.sqrt(np.sum(z*z, axis=1, keepdims=True)), 1e-12)
            mean = np.mean(z, axis=0)
            tensors['semantic_duplicate'].append(np.concatenate([mean, mean]))
            tensors['time_std'].append(np.concatenate([mean, np.std(z, axis=0)]))
            tensors['time_delta'].append(np.concatenate([mean, np.mean(np.abs(z[1:]-z[:-1]), axis=0)]))
        tensors = {k: torch.tensor(np.asarray(v, dtype=np.float32), device='cuda') for k, v in tensors.items()}
        # Each held-out fitting set actually has unique groups. Thus the
        # source-preserving shuffled control also preserves ancestor weights.
        fit_counts = Counter(r['group'] for r in rows if r['role'] == 'fit' and r['source'] != held)
        assert max(fit_counts.values()) == 1
        for seed in protocol['seeds']:
            for arm in protocol['arms']:
                folder = a.root / (held + '_' + str(seed) + '_' + arm)
                for rel, digest in read(folder / 'hashes.json').items():
                    assert sha(folder / rel) == digest, folder / rel
                done = read(folder / 'complete.json')
                assert (done['held_generator'], done['seed'], done['arm']) == (held, seed, arm)
                history = read(folder / 'history.json')['calibration_bce']
                assert len(history) == protocol['epochs']
                assert done['selected_epoch'] == int(np.argmin(history)) + 1
                assert done['calibration_bce'] == min(history)
                saved = torch.load(folder / 'best.pt', weights_only=True)
                assert saved['epoch'] == done['selected_epoch']
                net = nn.Sequential(nn.Linear(1536, 256), nn.GELU(), nn.Dropout(.1), nn.Linear(256, 1)).cuda().eval()
                net.load_state_dict(saved['model'])
                key = arm if arm in tensors else 'time_delta'
                x = (tensors[key] - saved['mean'].cuda()) / saved['scale'].cuda()
                with torch.no_grad():
                    logits = net(x).ravel().cpu().numpy()
                predictions = np.load(folder / 'predictions.npz', allow_pickle=False)
                assert np.array_equal(predictions['ids'], ids)
                assert np.array_equal(predictions['labels'], [rows[i]['label_fake'] for i in ids])
                err = float(np.max(np.abs(logits - predictions['logits'])))
                assert err < 1e-5, (folder, err)
                measured = roc_auc_score(predictions['labels'], expit(predictions['logits']))
                assert abs(measured - done['auc']) < 1e-12
                assert sum(p.numel() for p in net.parameters()) == done['parameters'] == 393729
                observed.append(dict(held_generator=held, seed=seed, arm=arm, max_logit_error=err))
    result = dict(status='pass', replayed_heads=len(observed), main_models_refitted=False,
        script_sha256=sha(__file__), parent_report_sha256=sha(a.root / 'report.json'),
        epoch_selection_verified=True, head_parameter_counts_verified=True,
        shuffled_control_ancestor_weights_preserved=True, details=observed,
        scope='mechanical integrity and inference replay, not independent scientific replication')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'details'}), flush=True)


if __name__ == '__main__':
    main()
