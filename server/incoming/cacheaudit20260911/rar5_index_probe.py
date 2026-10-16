"""Bounded RAR5 quick-open index audit, based on https://www.rarlab.com/technote.htm.

Does not download video payloads. Cached headers must be checked against original
headers before any subsequent member extraction. Full archive SHA is not verified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import urllib.request
import zlib


def vint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        c = data[pos]; pos += 1; value |= (c & 127) << shift
        if c < 128: return value, pos
    raise ValueError('Oversized RAR vint')


def block(data, pos=0):
    start = pos; expected = struct.unpack_from('<I', data, pos)[0]; pos += 4
    length, pos = vint(data, pos); end = pos + length
    if length > 2**21 or end > len(data): raise ValueError('Truncated/oversized header')
    if zlib.crc32(data[start + 4:end]) != expected: raise ValueError('Header CRC32 mismatch')
    kind, pos = vint(data, pos); flags, pos = vint(data, pos)
    extra = packed = 0
    if flags & 1: extra, pos = vint(data, pos)
    if flags & 2: packed, pos = vint(data, pos)
    r = {'type': kind, 'flags': flags, 'packed_size': packed, 'header_size': end - start,
         'header_hex': data[start:end].hex()}
    if kind == 1:
        r['archive_flags'], pos = vint(data, pos)
        if r['archive_flags'] & 3: raise ValueError('Multi-volume archive not supported by this probe')
    if kind in (2, 3):
        ff, pos = vint(data, pos); size, pos = vint(data, pos); attrs, pos = vint(data, pos)
        if ff & 2: pos += 4
        crc = None
        if ff & 4: crc = struct.unpack_from('<I', data, pos)[0]; pos += 4
        comp, pos = vint(data, pos); host, pos = vint(data, pos); n, pos = vint(data, pos)
        if pos + n > end - extra: raise ValueError('Invalid RAR name length')
        name = data[pos:pos+n].decode('utf-8'); pos += n
        r.update(name=name, size=size, file_flags=ff, crc32=crc, compression_info=comp,
                 method=(comp >> 7) & 7, solid=bool(comp & 64), attributes=attrs, host=host)
    extras = []; pos = end - extra
    while pos < end:
        n, pos = vint(data, pos); stop = pos + n
        if stop > end: raise ValueError('Extra field overrun')
        kind_extra, payload = vint(data, pos)
        entry = {'type': kind_extra, 'data_hex': data[payload:stop].hex()}
        if kind == 1 and kind_extra == 1:
            locator_flags, payload = vint(data, payload)
            if locator_flags & 1: r['quick_open_relative'], payload = vint(data, payload)
        extras.append(entry); pos = stop
    r['extras'] = extras
    return r


class Remote:
    def __init__(self, url, size): self.url=url; self.size=size; self.transferred=0
    def get(self, start, length):
        if length > 16 * 2**20 or self.transferred + length > 24 * 2**20: raise ValueError('Probe byte budget exceeded')
        end = start + length - 1
        if start < 0 or end >= self.size: raise ValueError('Range outside pinned archive')
        # Range-specific query prevents a shared HTTP cache reusing another partial response.
        u = self.url + ('&' if '?' in self.url else '?') + 'probe_range=%d-%d' % (start, end)
        req = urllib.request.Request(u, headers={'Range': 'bytes=%d-%d' % (start, end)})
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status != 206 or response.headers.get('Content-Range') != 'bytes %d-%d/%d' % (start,end,self.size):
                raise ValueError('Exact HTTP range not honored')
            data = response.read(length + 1)
        if len(data) != length: raise ValueError('Range length mismatch')
        self.transferred += length; return data


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--size',type=int,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    remote=Remote(a.url,a.size);head=remote.get(0,65536);(a.output_dir/'head.bin').write_bytes(head)
    if head[:8] != b'Rar!\x1a\x07\x01\x00': raise ValueError('Only RAR5 without SFX supported')
    main_header=block(head,8);qpos=8+main_header.get('quick_open_relative',0)
    if qpos<=8: raise ValueError('No quick-open locator; no full archive scan attempted')
    qhead=remote.get(qpos,min(65536,a.size-qpos));service=block(qhead)
    if service.get('name')!='QO' or service['method']!=0 or service['size']!=service['packed_size']:
        raise ValueError('Unsupported quick-open service')
    payload=remote.get(qpos+service['header_size'],service['packed_size'])
    if service['crc32'] is not None and zlib.crc32(payload)!=service['crc32']:raise ValueError('Quick-open data CRC mismatch')
    (a.output_dir/'quick_open.bin').write_bytes(payload)
    pos=0;rows=[]
    while pos<len(payload):
        start=pos;crc=struct.unpack_from('<I',payload,pos)[0];length,pos=vint(payload,pos+4);end=pos+length
        if end>len(payload) or zlib.crc32(payload[start+4:end])!=crc:raise ValueError('Quick-open structure CRC mismatch')
        flags,pos=vint(payload,pos);offset,pos=vint(payload,pos);n,pos=vint(payload,pos)
        if flags!=0 or pos+n!=end:raise ValueError('Unsupported quick-open structure')
        h=block(payload[pos:pos+n]);h['archive_offset']=qpos-offset
        if h['header_size']!=n:raise ValueError('Multiple cached headers in one structure unsupported')
        if h['type']==2:rows.append(h)
        pos=end
    result={'url':a.url,'archive_size':a.size,'full_archive_hash_verified':False,
            'quick_open_position':qpos,'quick_open_sha256':hashlib.sha256(payload).hexdigest(),
            'transferred_bytes':remote.transferred,'members':rows,
            'limitations':'Quick-open may cover only part of archive. Original headers not yet compared. No video payload downloaded.'}
    (a.output_dir/'index.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'members':len(rows),'transferred_bytes':remote.transferred,'quick_open_position':qpos,
                      'solid_members':sum(r['solid'] for r in rows),'method_counts':{str(k):sum(r['method']==k for r in rows) for k in range(6)}}))


if __name__=='__main__':main()
