"""Candidate-only public source probe with fixed selection and bounded HTTP ranges."""
import argparse
import binascii
import csv
import hashlib
import json
import random
import re
import struct
import time
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from msrvtt_source_probe import RUN,ROOT,RangeFile,save


def origin(url):
    value=parse_qs(urlparse(url).query).get('v',[None])[0]
    return value if value and re.fullmatch(r'[A-Za-z0-9_-]{11}',value)else None


def select():
    if (RUN/'candidate_selection.json').exists():raise FileExistsError('Selection already frozen')
    data=json.loads((RUN/'metadata/raw_data/MSRVTT_data.json').read_text(encoding='utf-8'))
    train_path=RUN/'metadata/raw_data/MSRVTT_train.7k.csv'
    with train_path.open(encoding='utf-8-sig',newline='')as f:
        csvrows=list(csv.DictReader(f))
    train_ids={r.get('video_id',r.get('video',''))for r in csvrows}
    if len(train_ids)<6000:raise ValueError('Unexpected training CSV schema')
    meta_root=ROOT/'research-plan/artifacts/cvpr27/metadata/jian-0/GenVidBench/GenVidBench'
    vript=set(re.findall(r'Pair1/vript/([A-Za-z0-9_-]{11})-Scene-',(meta_root/'Pair1_labels.txt').read_text(encoding='utf-8')))
    hdvg=set(re.findall(r'Pair2/hd_vg_130m/\d+___([A-Za-z0-9_-]{11})\.',(meta_root/'Pair2_labels.txt').read_text(encoding='utf-8')))
    all_ids={origin(r['url'])for r in data['videos']};all_ids.discard(None)
    pool=[r for r in data['videos']if r['video_id']in train_ids and r['split']=='train'and origin(r['url'])and origin(r['url'])not in vript|hdvg]
    rng=random.Random(20260912);rng.shuffle(pool)
    picked=[];used=set();by_category={}
    # Three per category when available, then a fixed-seed fill to 64; one source video per selected clip.
    for cat in range(20):
        for row in pool:
            group=origin(row['url'])
            if row['category']==cat and group not in used:
                picked.append(row);used.add(group);by_category[cat]=by_category.get(cat,0)+1
                if by_category[cat]>=3:break
    for row in pool:
        if len(picked)>=64:break
        if origin(row['url'])not in used:picked.append(row);used.add(origin(row['url']))
    assert len(picked)==64
    repo='friedrichor/MSR-VTT';rev=json.loads((RUN/'repo.json').read_text(encoding='utf-8'))['sha']
    meta=next(r for r in json.loads((RUN/'tree.json').read_text(encoding='utf-8'))if r['path']=='MSRVTT_Videos.zip')
    url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/MSRVTT_Videos.zip'
    reader=RangeFile(url,meta['size'])
    with zipfile.ZipFile(reader)as z:
        for row in picked:
            vid=row['video_id']
            if not re.fullmatch(r'video\d+',vid):raise ValueError('Invalid public video ID')
            info=z.getinfo('video/'+vid+'.mp4')
            if info.file_size>8*2**20 or info.compress_size>8*2**20:raise ValueError('Candidate member too large')
            row.update(source_origin_id=origin(row['url']),member=info.filename,size=info.file_size,compressed_size=info.compress_size,header_offset=info.header_offset,crc32=info.CRC,compression=info.compress_type,
                       ancestry_status='public_metadata_origin_candidate_not_content_verified',license_status='mirror_card_has_no_explicit_data_license;upstream_review_pending',label_status='not_admitted_to_real_training_set',scope='candidate_source_access_and_qc_only')
    if sum(r['compressed_size']for r in picked)>128*2**20:raise ValueError('Byte budget exceeded')
    save('source_overlap_audit.json',{'msrvtt_rows':len(data['videos']),'msrvtt_unique_origin_candidates':len(all_ids),'vript_overlap_count':len(all_ids&vript),'hdvg_overlap_count':len(all_ids&hdvg),'vript_overlap_ids':sorted(all_ids&vript),'hdvg_overlap_ids':sorted(all_ids&hdvg),'eligible_original_train_clips':len(pool),'selected':64,'selected_unique_origins':len(used),'category_counts':by_category,'metadata_sha256':hashlib.sha256((RUN/'metadata/raw_data/MSRVTT_data.json').read_bytes()).hexdigest(),'scope':'Public URL and filename origin candidates, not decoded-content identity proof'})
    save('candidate_selection.json',{'repo':repo,'revision':rev,'archive':meta['path'],'archive_bytes':meta['size'],'archive_lfs_sha256':meta['lfs']['oid'],'selection_seed':20260912,'created_utc':datetime.now(timezone.utc).isoformat(),'max_transfer_bytes':128*2**20,'selected_uncompressed_bytes':sum(r['size']for r in picked),'selected_compressed_bytes':sum(r['compressed_size']for r in picked),'records':picked,'rule':'original train split intersect mirror train_7k; exclude all current Vript/HDVG origin candidates; category-spread deterministic probe, not a prevalence sample'})
    print('SELECTED 64 candidate clips; overlap Vript/HDVG:',len(all_ids&vript),len(all_ids&hdvg),'compressed bytes',sum(r['compressed_size']for r in picked),flush=True)


def member(row,plan):
    out=RUN/'candidate_videos';out.mkdir(exist_ok=True)
    dest=out/(row['video_id']+'.mp4');receipt=dest.with_suffix('.receipt.json')
    if receipt.exists():
        r=json.loads(receipt.read_text(encoding='utf-8'))
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Candidate bytes changed')
        return {'video_id':row['video_id'],'status':'verified_existing','bytes':dest.stat().st_size}
    if dest.exists():raise FileExistsError('Unreceipted file')
    url=f"https://huggingface.co/datasets/{plan['repo']}/resolve/{plan['revision']}/{plan['archive']}"
    reader=RangeFile(url,plan['archive_bytes']);reader.seek(row['header_offset'])
    header=reader.read(30);parts=struct.unpack('<4s5H3I2H',header)
    if parts[0]!=b'PK\x03\x04' or parts[2]&1:raise ValueError('Invalid/encrypted local ZIP header')
    compression=parts[3];name_len,extra_len=parts[-2:]
    if compression!=row['compression']or name_len+extra_len>128*1024:raise ValueError('Header mismatch')
    raw=reader.read(name_len+extra_len+row['compressed_size'])
    name=raw[:name_len].decode('utf-8'if parts[2]&0x800 else 'cp437')
    if name!=row['member']:raise ValueError('Wrong member')
    payload=raw[name_len+extra_len:]
    if compression==0:decoded=payload
    elif compression==8:
        d=zlib.decompressobj(-15);decoded=d.decompress(payload,row['size']+1)
        if not d.eof or d.unconsumed_tail:raise ValueError('Incomplete or oversized member')
    else:raise ValueError('Unsupported compression')
    if len(decoded)!=row['size']or binascii.crc32(decoded)&0xffffffff!=row['crc32']:raise ValueError('Size/CRC mismatch')
    with dest.open('xb')as handle:handle.write(decoded)
    save('candidate_videos/'+receipt.name,dict(row,repo=plan['repo'],revision=plan['revision'],archive_lfs_sha256=plan['archive_lfs_sha256'],full_archive_sha256_verified=False,
         sha256=hashlib.sha256(decoded).hexdigest(),local_path=str(dest),transferred_bytes=reader.transferred,
         verification='Pinned TLS object range + ZIP CRC + local SHA256, not full archive verification'))
    return {'video_id':row['video_id'],'status':'downloaded','bytes':len(decoded),'transferred_bytes':reader.transferred}


def fetch():
    plan=json.loads((RUN/'candidate_selection.json').read_text(encoding='utf-8'))
    results=[];start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=4)as pool:
        fs={pool.submit(member,r,plan):r for r in plan['records']}
        for future in as_completed(fs):
            row=fs[future]
            try:results.append(future.result())
            except Exception as exc:results.append({'video_id':row['video_id'],'status':'error','error':repr(exc)})
            if len(results)%8==0:print('FETCH',len(results),'/64 errors',sum(r['status']=='error'for r in results),flush=True)
    save('candidate_download_receipt.json',{'selection_sha256':hashlib.sha256((RUN/'candidate_selection.json').read_bytes()).hexdigest(),'results':results,'seconds':time.perf_counter()-start,'count_ok':sum(r['status']!='error'for r in results),'bytes_downloaded':sum(r.get('bytes',0)for r in results),'no_replacements':True,'accepted_for_training':False})
    if any(r['status']=='error'for r in results):raise RuntimeError('Candidate retrieval incomplete; failed members retained in receipt')
    print('FETCH COMPLETE',len(results),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['select','fetch']);a=p.parse_args();{'select':select,'fetch':fetch}[a.stage]()
