"""Recover a frozen archive-order prefix without storing an 80 GB nested RAR.

Pinned range chunks -> raw LZMA2 -> sequential non-solid RAR5 members. Verifies
7z metadata identity, RAR headers, file CRC/size and raw hashes. Full-archive
hash and source rights remain unverified. No classification is performed.
"""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import time
import urllib.request
import zlib

from rar5_index_probe import block, vint


REV = '701cafb6f999d7ea0cbf3c354df6177311a4d824'
URL = 'https://huggingface.co/datasets/jian-0/GenVidBench/resolve/' + REV + '/GenVidBench/Pair2/hd_vg_130m.7z.001'
PART_BYTES = 21474836480


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(value, indent=2) + '\n'); os.replace(tmp, path)


def header(body):
    assert len(body) < 128
    raw = bytes([len(body)]) + body
    return struct.pack('<I', zlib.crc32(raw)) + raw


class Prefix:
    def __init__(self, root, budget, range_root=None):
        self.root = root; self.budget = budget; self.position = 0; self.network_bytes = 0
        self.range_root = range_root or root / 'ranges'
        self.dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW,
            filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 16777216}])
        self.buffer = bytearray(); self.unpacked_consumed = 0

    def chunk(self):
        n = min(8 * 2**20, self.budget - self.position)
        if n <= 0:
            raise RuntimeError('Explicit byte budget exhausted; incomplete prefix preserved')
        start = self.position; end = start + n - 1
        path = self.range_root / (str(start) + '.bin')
        receipt = path.with_suffix('.json')
        if path.exists() and receipt.exists():
            data = path.read_bytes()
            assert sha(data) == json.loads(receipt.read_text())['sha256'] and len(data) == n
        else:
            for attempt in range(3):
                try:
                    req = urllib.request.Request(URL + '?prefix_range=%d-%d' % (start, end), headers={'Range': 'bytes=%d-%d' % (start, end)})
                    with urllib.request.urlopen(req, timeout=60) as response:
                        assert response.status == 206
                        assert response.headers['Content-Range'] == 'bytes %d-%d/%d' % (start, end, PART_BYTES)
                        data = response.read(n + 1)
                    assert len(data) == n
                    path.write_bytes(data)
                    save(receipt, dict(offset=start, size=n, sha256=sha(data)))
                    self.network_bytes += n
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2)
        self.position += n
        if start == 0:
            expected = (self.root / 'start_header.bin').read_bytes()
            assert data[:32] == expected
            data = data[32:]
        return data

    def read(self, n):
        assert 0 <= n <= 512 * 2**20
        while len(self.buffer) < n:
            if shutil.disk_usage(self.root).free < 3 * 2**30:
                raise RuntimeError('Preserve 3 GiB disk reserve')
            data = self.chunk() if self.dec.needs_input else b''
            self.buffer.extend(self.dec.decompress(data, max_length=min(8 * 2**20, n-len(self.buffer))))
            if self.dec.eof and len(self.buffer) < n:
                raise EOFError('Nested RAR ended unexpectedly')
        result = bytes(self.buffer[:n]); del self.buffer[:n]
        self.unpacked_consumed += n
        return result

    def read_header(self):
        data = self.read(4)
        for _ in range(10):
            byte = self.read(1); data += byte
            if byte[0] < 128:
                break
        length, _ = vint(data, 4)
        assert length <= 2**21
        data += self.read(length)
        return data, block(data)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--count', type=int, default=100)
    p.add_argument('--max-bytes', type=int, default=2 * 2**30)
    p.add_argument('--range-cache', type=Path, help='Reuse verified chunks from a previous prefix attempt')
    a = p.parse_args(); started = time.monotonic()
    assert 1 <= a.count <= 100 and 8*2**20 <= a.max_bytes <= 2*2**30
    root = a.output; root.mkdir(parents=True, exist_ok=True)
    for name in ('ranges', 'raw', 'records', 'work'):
        (root / name).mkdir(exist_ok=True)
    probe = a.base / 'runs/overnight_20260911/hdvg_header_probe_v1'
    outer = json.loads((probe / 'outer_archive_info.json').read_text())
    assert outer['compression_blocks'] == 1 and outer['coders'] == [[{'method_hex': '21', 'properties_hex': '18'}]]
    assert outer['files'][0]['name'] == 'hd_vg_130m.rar'
    start_header = (probe / 'start_header.bin').read_bytes()
    assert start_header[:6] == b'7z\xbc\xaf\x27\x1c'
    assert zlib.crc32(start_header[12:32]) == struct.unpack_from('<I', start_header, 8)[0]
    next_header = (probe / 'next_header.bin').read_bytes()
    assert zlib.crc32(next_header) == struct.unpack_from('<I', start_header, 28)[0]
    assert len(next_header) == struct.unpack_from('<Q', start_header, 20)[0]
    assert struct.unpack_from('<Q', start_header, 12)[0] == outer['files'][0]['compressed_bytes']
    (root / 'start_header.bin').write_bytes(start_header)
    labels = {line.rsplit(' ', 1)[0]: int(line.rsplit(' ', 1)[1]) for line in a.labels.read_text(encoding='utf-8-sig').splitlines() if line}
    lock = dict(revision=REV, url=URL, first_part_bytes=PART_BYTES, count=a.count,
        selection='first 100 non-directory MP4 members in archive order; no outcome-based selection',
        max_compressed_prefix_bytes=a.max_bytes, max_member_bytes=512*2**20,
        range_cache=str(a.range_cache.resolve()) if a.range_cache else None,
        labels_sha256=sha(a.labels.read_bytes()), script_sha256=sha(Path(__file__).read_bytes()),
        outer_metadata_sha256=sha((probe / 'outer_archive_info.json').read_bytes()), walltime_cap=None,
        full_archive_hash_verified=False, ancestry_verified=False, licence_accepted=False, formal_training_released=False)
    if (root / 'lock.json').exists():
        assert json.loads((root / 'lock.json').read_text()) == lock
    else:
        save(root / 'lock.json', lock)
    if a.range_cache:
        old_lock = json.loads((a.range_cache.parent / 'lock.json').read_text())
        assert old_lock['revision'] == REV and old_lock['url'] == URL
    stream = Prefix(root, a.max_bytes, a.range_cache); recovered = []; skipped = []; failure = None
    try:
        assert stream.read(8) == b'Rar!\x1a\x07\x01\x00', 'Nested archive is not RAR5'
        main_bytes, main = stream.read_header()
        assert main['type'] == 1 and not main['archive_flags'] & 7, 'Unsupported multi-volume or solid archive'
        while len(recovered) < a.count:
            offset = stream.unpacked_consumed
            raw_header, entry = stream.read_header()
            if entry['type'] == 5:
                raise EOFError('Fewer members than requested')
            assert entry['packed_size'] <= 512*2**20, 'Individual packed member exceeds bound'
            payload = stream.read(entry['packed_size'])
            if entry['type'] != 2 or entry.get('file_flags', 0) & 1:
                continue
            name = PurePosixPath(entry['name'].replace('\\', '/'))
            assert not name.is_absolute() and '..' not in name.parts
            assert not entry['solid'] and not entry['flags'] & 0x38 and not entry['file_flags'] & 8
            assert not any(e['type'] in (1, 5) for e in entry['extras'])
            if name.suffix.lower() != '.mp4':
                skipped.append(str(name)); continue
            assert entry['crc32'] is not None and 0 < entry['size'] <= 512*2**20
            sample_id = 'Pair2/hd_vg_130m/' + name.name
            assert labels.get(sample_id) == 0, 'Member not in author real label list'
            key = hashlib.sha256(sample_id.encode()).hexdigest()
            record = root / 'records' / (key + '.json')
            target = root / 'raw' / (key + '.mp4')
            if record.exists():
                info = json.loads(record.read_text()); data = target.read_bytes()
                assert info['sha256'] == sha(data)
            else:
                mini = root / 'work' / (key + '.rar')
                mini.write_bytes(b'Rar!\x1a\x07\x01\x00' + header(b'\x01\x00\x00') + raw_header + payload + header(b'\x05\x00\x00'))
                partial = target.with_suffix('.partial')
                with partial.open('wb') as out:
                    result = subprocess.run(['unrar', 'p', '-inul', '-p-', str(mini)], stdout=out, stderr=subprocess.PIPE, timeout=120)
                assert result.returncode == 0, result.stderr.decode(errors='replace')[-500:]
                data = partial.read_bytes()
                assert len(data) == entry['size'] and zlib.crc32(data) == entry['crc32']
                os.replace(partial, target)
                # Remove only this generated transient mini-archive after CRC verification.
                assert mini.resolve().parent == (root / 'work').resolve()
                mini.unlink()
                origin = re.fullmatch(r'\d+___([A-Za-z0-9_-]{11})\..+\.mp4', name.name)
                info = dict(sample_id=sample_id, source='hd_vg_130m', author_label_fake=0,
                    archive_member=str(name), nested_offset=offset, header_sha256=sha(raw_header),
                    packed_span_sha256=sha(raw_header+payload), bytes=len(data), crc32=entry['crc32'],
                    crc_verified=True, sha256=sha(data), raw_file=str(target.relative_to(root)),
                    origin_id_candidate=origin[1] if origin else None, ancestry_verified=False,
                    full_archive_hash_verified=False, licence_accepted=False, formal_training_released=False)
                save(record, info)
            assert len(data) == entry['size'] and zlib.crc32(data) == entry['crc32']
            recovered.append(info)
            save(root / 'progress.json', dict(recovered=len(recovered), requested=a.count,
                compressed_prefix_bytes=stream.position, seconds=time.monotonic()-started))
            if len(recovered) % 10 == 0:
                print('Recovered', len(recovered), 'prefix bytes', stream.position, flush=True)
    except Exception as exc:
        failure = repr(exc)
        print('Stopped:', failure, flush=True)
    save(root / 'summary.json', dict(complete=len(recovered)==a.count, requested=a.count, recovered=len(recovered),
        raw_bytes=sum(r['bytes'] for r in recovered), prefix_bytes=stream.position, this_attempt_network_bytes=stream.network_bytes,
        seconds=time.monotonic()-started, failure=failure, nonvideo_skips=skipped,
        unique_origin_candidates=len({r['origin_id_candidate'] for r in recovered}),
        full_archive_hash_verified=False, ancestry_verified=False, licence_accepted=False, formal_training_released=False))
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
