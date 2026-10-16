"""Resume validated public HTTP ranges when the single-stream model transfer stalls."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from gpu_night_queue import MODELS, ROOT, REV, launch

URL = 'https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth'
SIZE = 346378731
ETAG = '"f1eac11803a0452f9cb34a7a98c4c002-42"'
CHUNK = 8 * 1024 * 1024


def fetch(i):
    first = i * CHUNK; last = min(SIZE, first + CHUNK) - 1
    root = MODELS / 'dinov2_vitb14_ranges'; root.mkdir(exist_ok=True)
    target = root / ('%03d.bin' % i); receipt = target.with_suffix('.json')
    if target.exists() and receipt.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() == json.loads(receipt.read_text())['sha256']:
            return target
    for attempt in range(3):
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            request = urllib.request.Request(URL, headers={'Range': 'bytes=%d-%d' % (first, last), 'If-Match': ETAG})
            with opener.open(request, timeout=60) as response:
                if response.status != 206 or response.headers.get('Content-Range') != 'bytes %d-%d/%d' % (first, last, SIZE):
                    raise ValueError('Invalid public range response')
                if response.headers.get('ETag') != ETAG: raise ValueError('Model object changed')
                data = response.read(last - first + 2)
            if len(data) != last - first + 1: raise ValueError('Truncated range')
            tmp = target.with_suffix('.tmp'); tmp.write_bytes(data); os.replace(tmp, target)
            receipt.write_text(json.dumps({'first': first, 'last': last, 'etag': ETAG,
                                          'sha256': hashlib.sha256(data).hexdigest()}))
            print('range_complete', i, flush=True); return target
        except Exception:
            if attempt == 2: raise
            time.sleep(2)


def main():
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(fetch, range((SIZE + CHUNK - 1) // CHUNK)))
    target = MODELS / 'dinov2_vitb14_pretrain.pth'
    if target.exists(): raise RuntimeError('Another model transfer completed; inspect before replacing')
    temp = target.with_suffix('.assembled')
    with temp.open('wb') as out:
        for path in paths: out.write(path.read_bytes())
    if temp.stat().st_size != SIZE: raise ValueError('Assembled size mismatch')
    os.replace(temp, target)
    (MODELS / 'dinov2_vitb14_pretrain.pth.receipt.json').write_text(json.dumps({
        'url': URL, 'bytes': SIZE, 'etag': ETAG, 'range_checked': True,
        'sha256_observed': hashlib.sha256(target.read_bytes()).hexdigest(),
        'publisher_full_sha256_available': False}, indent=2))
    launch('dino', target, MODELS / ('dinov2-' + REV))


if __name__ == '__main__': main()
