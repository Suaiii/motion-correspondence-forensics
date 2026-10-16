"""Run useful frozen-model GPU work under the existing overnight guard."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path('/root/autodl-tmp/cvpr27')
ROOT = BASE / 'runs/overnight_20260911'
ASSETS = Path(__file__).resolve().parent
MODELS = BASE / 'models'
REV = '7764ea0f912e53c92e82eb78a2a1631e92725fc8'


def run(cmd, timeout=900):
    subprocess.run([str(x) for x in cmd], check=True, timeout=timeout)


def download(url, name):
    path = MODELS / name
    if not path.exists():
        run(['curl', '-fL', '--retry', '2', '--connect-timeout', '20', '--max-time', '600',
             '-o', str(path) + '.part', url], timeout=700)
        os.replace(str(path) + '.part', path)
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    (MODELS / (name + '.receipt.json')).write_text(json.dumps({'url': url, 'sha256_observed': value,
        'publisher_full_sha256_available': False, 'bytes': path.stat().st_size}, indent=2))
    return path


def acquire_dino():
    repo = MODELS / ('dinov2-' + REV)
    if not repo.exists():
        run(['git', 'clone', '--depth', '1', 'https://github.com/facebookresearch/dinov2.git', repo])
    actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != REV: raise RuntimeError('DINO source revision differs from frozen revision')
    weights = download('https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth', 'dinov2_vitb14_pretrain.pth')
    return repo, weights


def launch(mode, weights, repo):
    guard = json.loads((ROOT / 'guard_status.json').read_text())
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(guard['observed_utc'])).total_seconds()
    if guard['phase'] != 'running' or age > 20 or (ROOT / 'STOP_NEW_JOBS').exists():
        raise RuntimeError('Fresh running deadline guard required')
    target = ROOT / ('gpu_' + mode + '_v1')
    selection = BASE / ('incoming/night20260911/night_qc_selection_20260911.json' if mode == 'raft'
                        else 'incoming/fullqc20260911/full_qc_selection_20260911.json')
    cmd = [sys.executable, ASSETS / 'gpu_night_features.py', '--run-dir', target,
           '--qc-dir', ROOT / 'full_native_qc', '--selection', selection,
           '--runtime', BASE / 'releases/v0.1.3/cvpr27-server', '--model-repo', repo,
           '--weights', weights, '--mode', mode, '--deadline', '2026-09-11T09:40:00+08:00']
    print(json.dumps({'launch': mode, 'target': str(target)}), flush=True)
    with open(ROOT / ('gpu_' + mode + '.log'), 'a') as log:
        subprocess.run([str(x) for x in cmd], stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    MODELS.mkdir(exist_ok=True)
    results = {}
    with ThreadPoolExecutor(max_workers=1) as pool:
        dino = pool.submit(acquire_dino)
        try:
            weights = download('https://download.pytorch.org/models/raft_small_C_T_V2-01064c6d.pth', 'raft_small_C_T_V2-01064c6d.pth')
            if not hashlib.sha256(weights.read_bytes()).hexdigest().startswith('01064c6d'):
                raise ValueError('RAFT publisher hash prefix mismatch')
            launch('raft', weights, MODELS)
            results['raft'] = 'completed'
        except Exception as exc:
            results['raft'] = type(exc).__name__ + ': ' + str(exc)
            print(json.dumps(results), flush=True)
        try:
            repo, weights = dino.result()
            launch('dino', weights, repo)
            results['dino'] = 'completed'
        except Exception as exc:
            results['dino'] = type(exc).__name__ + ': ' + str(exc)
    (ROOT / 'gpu_queue_result.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results), flush=True)


if __name__ == '__main__': main()
