"""Recover frozen RAR members locally with bsdtar; no network or GPU use.

Old failed acquisitions are read-only. Every mini archive must contain exactly
the selected header/payload and a terminal header. CRC/size are checked after
decompression; original full-archive SHA and ancestry remain unverified.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'research-runtime/server/scripts'), str(ROOT/'research-runtime/server')]
from rar5_index_probe import block
from forensics.video import decode, QualityExclusion


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def check_container(data, entry):
    if data[:8] != b'Rar!\x1a\x07\x01\x00':
        raise ValueError('Not a RAR5 member container')
    main = block(data, 8)
    if main['type'] != 1 or main.get('archive_flags') != 0:
        raise ValueError('Unexpected archive header')
    offset = 8 + main['header_size']
    member = block(data, offset)
    name = PurePosixPath(member['name'])
    if name.is_absolute() or '..' in name.parts or len(name.parts) != 2 or name.parts[0] != 'cogvideo':
        raise ValueError('Unexpected member name')
    if member['header_hex'] != entry['header_hex'] or member['name'] != entry['name']:
        raise ValueError('Frozen header mismatch')
    if member['solid'] or member['flags'] & 0x38 or member['file_flags'] & 9:
        raise ValueError('Dependent/encrypted/directory member')
    if any(e['type'] in (1, 5) for e in member['extras']):
        raise ValueError('Encrypted or redirected member')
    if not 0 < member['size'] <= 64*2**20 or member['crc32'] is None:
        raise ValueError('Unbounded/unchecked output')
    end = offset + member['header_size'] + member['packed_size']
    terminal = block(data, end)
    if terminal['type'] != 5 or end + terminal['header_size'] != len(data):
        raise ValueError('Unexpected trailing archive content')
    return hashlib.sha256(data[offset:end]).hexdigest()


def recover(row, entry, cache, out, tar):
    started = time.monotonic()
    key = hashlib.sha256(row['sample_id'].encode()).hexdigest()
    archive = cache/'compressed_members'/(key+'.rar')
    result = dict(row, recovery_status='error', ancestry_status='unknown',
                  full_archive_hash_verified=False, training_released=False)
    try:
        packed = archive.read_bytes()
        result['packed_span_sha256'] = check_container(packed, entry)
        result['mini_archive_sha256'] = hashlib.sha256(packed).hexdigest()
        target = out/'raw'/(key+'.mp4')
        partial = target.with_suffix('.partial')
        with partial.open('xb') as f:
            proc = subprocess.run([tar, '-xOf', str(archive), entry['name']],
                                  stdout=f, stderr=subprocess.PIPE, timeout=30)
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode(errors='replace')[-400:])
        data = partial.read_bytes()
        if len(data) != entry['size'] or zlib.crc32(data) != entry['crc32']:
            raise ValueError('Decompressed size/CRC mismatch')
        os.replace(partial, target)
        result.update(recovery_status='ok', raw_file=target.relative_to(out).as_posix(),
                      sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                      crc32=entry['crc32'], crc_verified=True, header_matches_index=True)
        result['sampling'] = {}
        for fps in (4, 8):
            cfg = {'frames':2*fps, 'fps':fps, 'window_sec':2, 'size':224}
            try:
                frames, meta = decode(target, cfg)
                result['sampling'][str(fps)] = dict(status='ok', metadata=meta,
                    decoded_tensor_sha256=hashlib.sha256(frames.tobytes()).hexdigest(),
                    frames=int(frames.shape[0]))
            except QualityExclusion as exc:
                result['sampling'][str(fps)] = dict(status='excluded', reason=str(exc))
            except Exception as exc:
                result['sampling'][str(fps)] = dict(status='error', reason=repr(exc))
    except Exception as exc:
        result['reason'] = repr(exc)
    result['seconds'] = time.monotonic()-started
    write(out/'records'/(key+'.json'), result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    selection = ROOT/'research-runs/cogvideo_pair2_selection_20260916.json'
    index = ROOT/'research-runs/cogvideo_pair2_index_20260916.json'
    cache = ROOT/'research-runs/cogvideo_acquire_20260916_v2'
    chosen, idx = read(selection), read(index)
    if digest(index) != chosen['quickopen_index_sha256']:
        raise ValueError('Index does not match frozen selection')
    mapping = {e['name']:e for e in idx['members']}
    if len(mapping) != len(idx['members']):
        raise ValueError('Duplicate indexed names')
    rows = chosen['rows']
    if len(rows) != 100 or len({r['sample_id'] for r in rows}) != 100:
        raise ValueError('Unexpected selection')
    tar = shutil.which('tar.exe') or shutil.which('bsdtar')
    if not tar or not shutil.which('ffprobe'):
        raise RuntimeError('bsdtar and ffprobe required')
    version = subprocess.check_output([tar,'--version'], text=True).strip()
    if 'bsdtar' not in version:
        raise RuntimeError('This recovery requires libarchive bsdtar')
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out/'records').mkdir(); (out/'raw').mkdir()
    write(out/'lock.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        selection_sha256=digest(selection), index_sha256=digest(index), script_sha256=digest(__file__),
        decoder_sha256=digest(ROOT/'research-runtime/server/forensics/video.py'),
        tar_version=version, tar_sha256=digest(tar), network=False, gpu=False,
        scope='acquisition and decoded-PTS QC only; no model selection', requested=100))
    started = time.monotonic(); results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(recover,r,mapping[r['archive_member']],cache,out,tar) for r in rows]
        for job in as_completed(jobs):
            results.append(job.result())
            if len(results)%10 == 0:
                print('recovered/QC',len(results),'of',len(rows),flush=True)
    ok=[r for r in results if r['recovery_status']=='ok']
    summary=dict(requested=len(rows), processed=len(results),
        recovered=len(ok), recovery_errors=[{'id':r['sample_id'],'reason':r.get('reason')} for r in results if r['recovery_status']!='ok'],
        unique_sha256=len({r['sha256'] for r in ok}), raw_bytes=sum(r['bytes'] for r in ok),
        sampling={str(fps):dict(Counter(r['sampling'][str(fps)]['status'] for r in ok)) for fps in (4,8)},
        wall_seconds=time.monotonic()-started, full_archive_hash_verified=False,
        ancestry_verified=False, licence_accepted=False, formal_training_released=False)
    write(out/'summary.json',summary)
    write(out/'artifact_hashes.json',{f.relative_to(out).as_posix():digest(f) for f in out.rglob('*') if f.is_file()})
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == '__main__':
    main()
