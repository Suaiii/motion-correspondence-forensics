"""Frozen GPU feature cache and estimator diagnostics on native-frame development assets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, obj):
    p = Path(p); tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8'); os.replace(tmp, p)


class Videos(Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        import cv2
        from index16_decode import decode
        cv2.setNumThreads(1)
        r = self.rows[i]
        try:
            if sha(r['path']) != r['sha256']: raise ValueError('Input hash changed')
            frames, meta = decode(r['path'], {'frames': 16, 'size': 224})
            return r, frames, meta, None
        except Exception as exc:
            return r, None, None, type(exc).__name__ + ': ' + str(exc)


def collate(batch): return batch


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--qc-dir', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--model-repo', type=Path, required=True)
    p.add_argument('--weights', type=Path, required=True)
    p.add_argument('--mode', choices=['dino', 'raft'], required=True)
    p.add_argument('--deadline', required=True)
    a = p.parse_args(); sys.path.insert(0, str(a.runtime))
    root = a.run_dir; root.mkdir(parents=True, exist_ok=True)
    for name in ('records', 'features'): (root / name).mkdir(exist_ok=True)
    deadline = datetime.fromisoformat(a.deadline)
    def cutoff():
        return datetime.now(timezone.utc) >= deadline or (root.parent / 'STOP_NEW_JOBS').exists()
    if cutoff(): raise RuntimeError('GPU task cutoff reached')
    torch.set_num_threads(1)
    torch.manual_seed(20260911)
    rows = read(a.selection)['rows']; mapping = {}
    for source in ('ms', 'vc2'):
        for r in read(a.qc_dir / ('extraction_' + source + '.json'))['files']:
            mapping[(source, r['basename'])] = r
    lock = {'selection_sha256': sha(a.selection), 'weights_sha256': sha(a.weights),
            'mode': a.mode, 'script_sha256': sha(__file__),
            'decode_sha256': sha(Path(__file__).with_name('index16_decode.py')),
            'runtime_video_sha256': sha(a.runtime / 'forensics/video.py'),
            'torch': torch.__version__, 'cuda': torch.version.cuda,
            'gpu': torch.cuda.get_device_name(), 'requested': len(rows),
            'sampling': 'center 16 native frames, center square crop, area resize 224; preserves PTS',
            'scope': 'Development frozen features/estimator diagnostics; no classifier training or final evaluation',
            'deadline': a.deadline, 'video_batch': 8 if a.mode == 'dino' else 1,
            'workers': 4, 'model': 'dinov2_vitb14' if a.mode == 'dino' else 'torchvision_raft_small_C_T_V2',
            'precision': 'bfloat16 autocast' if a.mode == 'dino' else 'float32',
            'raft_pair_indices': [0, 1] if a.mode == 'raft' else None}
    if a.mode == 'dino':
        lock['repo_commit'] = subprocess.check_output(['git', '-C', str(a.model_repo), 'rev-parse', 'HEAD'], text=True).strip()
    if (root / 'lock.json').exists() and read(root / 'lock.json') != lock:
        raise ValueError('GPU protocol changed; use a new run directory')
    save(root / 'lock.json', lock)
    pending = []; completed = []
    for r in rows:
        key = hashlib.sha256(r['sample_id'].encode()).hexdigest(); record = root / 'records' / (key + '.json')
        if record.exists():
            old = read(record)
            if old['status'] == 'ok' and a.mode == 'dino' and sha(root / old['feature_file']) != old['feature_sha256']:
                raise ValueError('Cached feature hash changed')
            completed.append(old); continue
        entry = mapping.get((r['source'], r['basename']))
        if entry is None:
            out = {**r, 'status': 'excluded', 'reason': 'missing_archive_member'}
            save(record, out); completed.append(out)
        else: pending.append({**r, **entry, 'key': key})
    if a.mode == 'dino':
        from forensics.backbones import dinov2
        model = dinov2(a.model_repo, a.weights, lock['weights_sha256'], 'cuda', 'dinov2_vitb14')
    else:
        from torchvision.models.optical_flow import raft_small
        model = raft_small(weights=None).cuda().eval()
        model.load_state_dict(torch.load(a.weights, map_location='cpu', weights_only=True))
    loader = DataLoader(Videos(pending), batch_size=lock['video_batch'], num_workers=4,
                        collate_fn=collate, multiprocessing_context='spawn', prefetch_factor=2)
    started = time.perf_counter(); torch.cuda.reset_peak_memory_stats()
    for batch in loader:
        if cutoff(): break
        valid = []
        for row, frames, meta, err in batch:
            if err:
                out = {**row, 'status': 'error', 'reason': err}
                save(root / 'records' / (row['key'] + '.json'), out); completed.append(out)
            else: valid.append((row, frames, meta))
        if not valid: continue
        with torch.inference_mode():
            if a.mode == 'dino':
                arr = np.concatenate([x[1] for x in valid])
                x = torch.from_numpy(arr[..., ::-1].copy()).permute(0, 3, 1, 2).to('cuda', dtype=torch.float32) / 255
                mean = torch.tensor([.485, .456, .406], device='cuda')[None, :, None, None]
                std = torch.tensor([.229, .224, .225], device='cuda')[None, :, None, None]
                with torch.autocast('cuda', dtype=torch.bfloat16): features = model((x - mean) / std)
                features = features.float().cpu().numpy().reshape(len(valid), 16, -1)
                if not np.isfinite(features).all(): raise ValueError('Nonfinite DINO features')
            for j, (row, frames, meta) in enumerate(valid):
                out = {**row, 'status': 'ok', 'sampling': meta}
                if a.mode == 'dino':
                    rel = 'features/' + row['key'] + '.npy'; target = root / rel
                    with open(str(target) + '.tmp', 'wb') as f: np.save(f, features[j])
                    os.replace(str(target) + '.tmp', target)
                    out.update(feature_file=rel, feature_sha256=sha(target), shape=list(features[j].shape))
                else:
                    import cv2
                    pair = torch.from_numpy(frames[:2, ..., ::-1].copy()).permute(0, 3, 1, 2).float().cuda() / 127.5 - 1
                    # Backward correspondence: current frame (1) to previous frame (0).
                    flow = model(pair[1:2], pair[:1], num_flow_updates=12)[-1][0].permute(1, 2, 0).cpu().numpy()
                    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames[:2]]
                    fb = cv2.calcOpticalFlowFarneback(gray[1], gray[0], None, .5, 3, 15, 3, 5, 1.2, 0)
                    if not np.isfinite(flow).all(): raise ValueError('Nonfinite RAFT flow')
                    yy, xx = np.mgrid[:224, :224].astype(np.float32)
                    stats = {}
                    for name, field in [('raft', flow), ('farneback', fb)]:
                        bounded = np.clip(field, -12, 12)
                        warped = cv2.remap(frames[0].astype(np.float32) / 255, xx + bounded[..., 0], yy + bounded[..., 1], cv2.INTER_LINEAR)
                        error = np.abs(warped - frames[1].astype(np.float32) / 255)[16:-16, 16:-16]
                        stats[name] = {'interior_mean_abs_residual': float(error.mean()),
                                       'mean_flow_magnitude': float(np.linalg.norm(field, axis=-1).mean()),
                                       'clipped_pixel_fraction': float(np.any(np.abs(field) > 12, axis=-1).mean())}
                    out.update(estimator_stats=stats, estimator_disagreement_mean=float(np.linalg.norm(flow - fb, axis=-1).mean()))
                save(root / 'records' / (row['key'] + '.json'), out); completed.append(out)
        if len(completed) % 80 < lock['video_batch']:
            elapsed = time.perf_counter() - started
            status = {'completed': len(completed), 'requested': len(rows), 'elapsed_sec': elapsed,
                      'peak_gpu_allocated_gib': torch.cuda.max_memory_allocated() / 2**30}
            save(root / 'progress.json', status); print(json.dumps(status), flush=True)
    from collections import Counter
    save(root / 'summary.json', {'complete': len(completed) == len(rows), 'requested': len(rows),
         'completed': len(completed), 'statuses': dict(Counter(r['status'] for r in completed)),
         'wall_seconds_this_attempt': time.perf_counter() - started,
         'peak_gpu_allocated_gib': torch.cuda.max_memory_allocated() / 2**30,
         'classification_metrics_computed': False})


if __name__ == '__main__': main()
