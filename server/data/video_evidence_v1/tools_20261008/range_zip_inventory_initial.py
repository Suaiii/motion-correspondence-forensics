"""Read ZIP central directories over validated HTTP ranges, without full archives."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import urllib.parse
import zipfile

REVISION = 'bf48acaa4920990af3dd2a511ea88e63354df305'
ARCHIVES = {
    'Luma': 'AIGVDBench/ClosedSource/Luma.zip',
    'Pika': 'AIGVDBench/ClosedSource/pika.zip',
    'Vidu': 'AIGVDBench/ClosedSource/vidu.zip',
    'OpenVidHD': 'AIGVDBench/Real/Real.zip',
}


def read_range(url, size, start, count):
    if count <= 0:
        return b''
    end = min(size-1, start+count-1)
    request = urllib.request.Request(url + f'?download=true&range_hint={start}-{end}',
        headers={'Range': f'bytes={start}-{end}', 'User-Agent': 'video-evidence-research/1.0', 'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(request, timeout=40) as response:
        if response.status != 206:
            raise ValueError(f'range not honored: HTTP {response.status}')
        content_range = response.headers.get('Content-Range')
        if content_range != f'bytes {start}-{end}/{size}':
            raise ValueError('unexpected content range: '+str(content_range))
        data = response.read(end-start+2)
        if len(data) != end-start+1:
            raise ValueError('range length mismatch')
        return data


class RangeFile(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0
        self.requests = self.received = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos+offset if whence == 1 else self.size+offset)
        if self.pos < 0 or self.pos > self.size:
            raise ValueError('out of bounds seek')
        return self.pos

    def read(self, n=-1):
        n = self.size-self.pos if n < 0 else min(n, self.size-self.pos)
        if n > 32*1024*1024:
            raise ValueError('central directory read exceeds cap')
        data = read_range(self.url, self.size, self.pos, n)
        self.pos += len(data)
        self.received += len(data)
        self.requests += 1
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    tree = {x['path']: x for x in json.loads(args.tree.read_text())}
    for cell, name in ARCHIVES.items():
        upstream = tree[name]
        url = f'https://hf-mirror.com/datasets/AIGVDBench/AIGVDBench/resolve/{REVISION}/' + urllib.parse.quote(name)
        try:
            source = RangeFile(url, upstream['size'])
            with zipfile.ZipFile(source) as archive:
                members = [{'member': i.filename, 'file_size': i.file_size, 'compressed_size': i.compress_size,
                    'header_offset': i.header_offset, 'crc32': i.CRC, 'method': i.compress_type,
                    'flags': i.flag_bits} for i in archive.infolist() if not i.is_dir()]
            receipt = {'cell': cell, 'repo': 'AIGVDBench/AIGVDBench', 'revision': REVISION,
                'archive_path': name, 'archive_bytes': upstream['size'], 'archive_lfs_sha256': upstream['lfs']['oid'],
                'archive_hash_fully_verified': False, 'transport_base': 'https://hf-mirror.com',
                'range_requests': source.requests, 'range_bytes_received': source.received, 'members': members}
            (args.output / (cell+'.json')).write_text(json.dumps(receipt, indent=2)+'\n')
            print(json.dumps({'cell':cell, 'members':len(members), 'video_members':sum(x['member'].lower().endswith('.mp4') for x in members),
                'range_bytes':source.received, 'examples':members[:2]}), flush=True)
        except Exception as exc:
            receipt = {'cell':cell, 'error_type':type(exc).__name__, 'error':str(exc)}
            (args.output / (cell+'.error.json')).write_text(json.dumps(receipt, indent=2)+'\n')
            print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
