"""Pinned non-solid RAR5 members: compare original headers, decompress and check CRC.

Only an explicitly frozen selection is downloaded. Partial-archive acquisition
does not verify the full archive LFS hash or the sample's ancestry.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from rar5_index_probe import block


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, r):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf-8');os.replace(tmp,p)


def header(body):
    if len(body)>127:raise ValueError('Minimal header too large')
    data=bytes([len(body)])+body;return struct.pack('<I',zlib.crc32(data))+data


def get_range(url,start,n,total):
    if not 0<n<=64*2**20 or start<0 or start+n>total:raise ValueError('Invalid bounded member range')
    end=start+n-1;u=url+'?member_range=%d-%d'%(start,end)
    for attempt in range(3):
        try:
            request=urllib.request.Request(u,headers={'Range':'bytes=%d-%d'%(start,end)})
            with urllib.request.urlopen(request,timeout=30) as r:
                if r.status!=206 or r.headers.get('Content-Range')!='bytes %d-%d/%d'%(start,end,total):raise ValueError('Wrong member range response')
                data=r.read(n+1)
            if len(data)!=n:raise ValueError('Short member range')
            return data
        except Exception:
            if attempt==2:raise
            time.sleep(2)


def worker(row, entry, index, root, deadline):
    key=hashlib.sha256(row['sample_id'].encode()).hexdigest();record=root/'records'/(key+'.json')
    if record.exists():
        r=read(record)
        if r['status']=='ok' and sha(root/r['raw_file'])!=r['sha256']:raise ValueError('Existing raw member changed')
        return r
    result={**row,'status':'error','full_archive_hash_verified':False};started=time.perf_counter()
    try:
        if datetime.now(timezone.utc)>=deadline or (root.parent/'STOP_NEW_JOBS').exists():raise RuntimeError('Acquisition cutoff reached')
        if entry is None:raise ValueError('Member not present in audited quick-open index; no replacement')
        name=PurePosixPath(entry['name'])
        if name.is_absolute() or '..' in name.parts or len(name.parts)!=2 or name.parts[0] not in ('vript','cogvideo'):
            raise ValueError('Unsafe member path')
        if entry['solid'] or entry['flags']&0x38 or entry['file_flags']&9 or any(e['type'] in (1,5) for e in entry['extras']):raise ValueError('Unsupported dependent/encrypted/redirected member')
        if entry['crc32'] is None or entry['size']>64*2**20:raise ValueError('Unbounded or unchecked member')
        if shutil.disk_usage(root).free<3*2**30:raise RuntimeError('Preserve 3GiB disk reserve')
        data=get_range(index['url'],entry['archive_offset'],entry['header_size']+entry['packed_size'],index['archive_size'])
        raw_header=data[:entry['header_size']]
        if raw_header.hex()!=entry['header_hex'] or block(raw_header)['name']!=entry['name']:raise ValueError('Original and quick-open headers differ')
        mini=root/'compressed_members'/(key+'.rar')
        mini.write_bytes(b'Rar!\x1a\x07\x01\x00'+header(b'\x01\x00\x00')+data+header(b'\x05\x00\x00'))
        target=root/'raw'/name.name;partial=target.with_suffix('.partial')
        if target.exists():raise FileExistsError('Unreceipted raw member exists')
        with partial.open('wb') as out:
            proc=subprocess.run(['unrar','p','-inul','-p-',str(mini)],stdout=out,stderr=subprocess.PIPE,timeout=60)
        if proc.returncode:raise RuntimeError('UnRAR member check failed: '+proc.stderr.decode(errors='replace')[-500:])
        if partial.stat().st_size!=entry['size'] or zlib.crc32(partial.read_bytes())!=entry['crc32']:raise ValueError('Unpacked size/CRC mismatch')
        os.replace(partial,target)
        result.update(status='ok',raw_file=target.relative_to(root).as_posix(),sha256=sha(target),
                      packed_source_span_sha256=hashlib.sha256(data).hexdigest(),archive_offset=entry['archive_offset'],
                      packed_bytes=entry['packed_size'],raw_bytes=entry['size'],member_crc32=entry['crc32'],
                      original_header_matches_quickopen=True,verification='pinned TLS object, original header equality, RAR CRC32, raw SHA256')
        from forensics.video import decode as strict_decode
        from index16_decode import decode as native_decode
        for mode,decoder in [('strict_2s',strict_decode),('native16',native_decode)]:
            try:
                _,meta=decoder(str(target),{'frames':16,'fps':8,'window_sec':2,'size':224})
                result[mode]={'status':'ok','sampling':meta}
            except Exception as exc:result[mode]={'status':'not_eligible_or_error','reason':type(exc).__name__+': '+str(exc)}
    except Exception as exc:result['reason']=type(exc).__name__+': '+str(exc)
    result['seconds']=time.perf_counter()-started;save(record,result);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--index',type=Path,required=True);p.add_argument('--limit',type=int,required=True);p.add_argument('--runtime',required=True)
    p.add_argument('--decode-scripts',required=True);p.add_argument('--deadline',required=True);a=p.parse_args()
    sys.path[:0]=[a.runtime,a.decode_scripts]
    root=a.run_dir;root.mkdir(parents=True,exist_ok=True)
    for name in ['records','raw','compressed_members']:(root/name).mkdir(exist_ok=True)
    selected=read(a.selection);index=read(a.index)
    if sha(a.index)!=selected['quickopen_index_sha256']:raise ValueError('Frozen index changed')
    if not 0<a.limit<=len(selected['rows']):raise ValueError('Explicit subset limit out of range')
    rows=selected['rows'][:a.limit];mapping={r['name']:r for r in index['members']}
    if len(mapping)!=len(index['members']):raise ValueError('Ambiguous indexed member names')
    if sum(mapping[r['archive_member']]['size']+mapping[r['archive_member']]['packed_size'] for r in rows if r['archive_member'] in mapping)>12*2**30:raise ValueError('Selected acquisition exceeds 12GiB cap')
    lock={'selection_sha256':sha(a.selection),'index_sha256':sha(a.index),'script_sha256':sha(__file__),'limit':a.limit,
          'deadline':a.deadline,'workers':4,'ancestry_verified':False,'full_archive_hash_verified':False}
    if (root/'lock.json').exists() and read(root/'lock.json')!=lock:raise ValueError('Run configuration differs')
    save(root/'lock.json',lock);deadline=datetime.fromisoformat(a.deadline);results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(worker,r,mapping.get(r['archive_member']),index,root,deadline) for r in rows]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results)%10==0:print('members',len(results),'/',len(rows),flush=True)
    from collections import Counter
    summary={'complete':len(results)==len(rows),'requested':len(rows),'download_statuses':dict(Counter(r['status'] for r in results)),
             'strict_2s_statuses':dict(Counter(r.get('strict_2s',{}).get('status','not_run') for r in results)),
             'native16_statuses':dict(Counter(r.get('native16',{}).get('status','not_run') for r in results)),
             'classification_metrics_computed':False}
    save(root/'summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
