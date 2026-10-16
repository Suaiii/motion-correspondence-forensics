"""Acquire one frozen, bounded public benchmark subset, with no model evaluation."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import threading
import time
import urllib.parse
import zlib
from datetime import datetime, timezone
from fractions import Fraction
from range_zip_inventory import read_range

SEED = 'video-evidence-v1-extension-20261008-no-model-scores'
GIB = 1024**3
PROBE_LIMIT = threading.Semaphore(2)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def get_member(row):
    count = min(row['archive_bytes']-row['header_offset'], row['compressed_size']+131100)
    payload = read_range(row['transport_url'], row['archive_bytes'], row['header_offset'], count)
    header = struct.unpack_from('<4s5H3I2H', payload)
    if header[0] != b'PK\x03\x04' or header[2] & 1 or header[3] != row['method']:
        raise ValueError('unsupported or inconsistent ZIP header')
    name_end = 30+header[9]
    member = payload[30:name_end].decode('utf-8' if header[2] & 0x800 else 'cp437')
    if member != row['member']:
        raise ValueError('ZIP member name mismatch')
    offset = name_end+header[10]
    compressed = payload[offset:offset+row['compressed_size']]
    if len(compressed) != row['compressed_size']:
        raise ValueError('ZIP compressed member truncated')
    if row['method'] == 0:
        data = compressed
    elif row['method'] == 8:
        decoder = zlib.decompressobj(-15)
        data = decoder.decompress(compressed, row['file_size']+1)
        if not decoder.eof:
            raise ValueError('deflate stream incomplete or exceeds declared size')
    else:
        raise ValueError('unsupported ZIP compression')
    if len(data) != row['file_size'] or zlib.crc32(data) != row['crc32']:
        raise ValueError('ZIP member size/CRC mismatch')
    return data, len(payload)


def acquire(task):
    row, output, old_hashes = task
    started = time.monotonic()
    record = dict(row)
    errors = []
    try:
        destination = output / 'media' / row['cell'] / (row['asset_id']+'.mp4')
        destination.parent.mkdir(parents=True, exist_ok=True)
        reused = destination.is_file()
        if reused:
            data = destination.read_bytes()
            transferred = 0
            if len(data) != row['file_size'] or zlib.crc32(data) != row['crc32']:
                raise ValueError('existing media differs from frozen ZIP CRC/size; preserve for inspection')
        else:
            for attempt in range(2):
                try:
                    data, transferred = get_member(row)
                    break
                except Exception as exc:
                    errors.append({'attempt': attempt+1, 'error_type': type(exc).__name__, 'error': str(exc)})
                    if attempt:
                        raise
                    time.sleep(1)
            with destination.open('xb') as f:
                f.write(data)
        file_hash = sha(data)
        del data
        record.update(path=str(destination), sha256=file_hash, zip_member_crc_verified=True,
                      range_bytes_received=transferred, reused_previously_downloaded_media=reused,
                      duplicate_of_v1=file_hash in old_hashes)
        with PROBE_LIMIT:
            probe = subprocess.run(['/usr/bin/ffprobe', '-v', 'error', '-threads', '1', '-select_streams', 'v:0',
                '-show_streams', '-show_frames', '-show_entries',
                'stream=codec_name,width,height,time_base,avg_frame_rate,nb_frames,duration:frame=pts,pkt_pts,best_effort_timestamp',
                '-of', 'json', str(destination)], capture_output=True, timeout=75, check=True)
        result = json.loads(probe.stdout)
        stream = result['streams'][0]
        frames = result.get('frames', [])
        pts = [x.get('pts') if type(x.get('pts')) is int else x.get('pkt_pts') for x in frames]
        timestamp_fields = collections.Counter('pts' if type(x.get('pts')) is int else ('pkt_pts' if type(x.get('pkt_pts')) is int else 'missing') for x in frames)
        integer = bool(pts) and all(type(x) is int for x in pts)
        strict = integer and all(a < b for a,b in zip(pts, pts[1:]))
        positive_time_base = Fraction(stream['time_base']) > 0
        record['ffprobe'] = dict(stream, pts=pts, frame_count_probed=len(pts),
            native_pts_field_counts=dict(timestamp_fields), best_effort_timestamp_used_as_native=False,
            native_pts_sequence_sha256=sha(json.dumps(pts, separators=(',', ':')).encode()),
            native_pts_strictly_increasing=strict, integer_pts_complete=integer,
            stderr=probe.stderr.decode('utf-8', errors='replace')[:4000])
        record['status'] = 'qc_pass' if integer and strict and positive_time_base and len(pts)>=8 and not record['duplicate_of_v1'] and not probe.stderr.strip() else 'qc_excluded'
        record['qc_scope'] = 'ZIP CRC, local SHA256, ffprobe native frame PTS and minimum 8 frames; no visual-quality or causal validation'
    except Exception as exc:
        record.update(status='error', error_type=type(exc).__name__, error=str(exc))
    record.update(attempt_errors=errors, elapsed_seconds=time.monotonic()-started)
    save(output / 'records' / (row['asset_id']+'.json'), record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--v1-manifest', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    start = time.monotonic()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=args.resume)
    if args.resume:
        backup = output / 'initial_reader_evidence'
        backup.mkdir(exist_ok=False)
        for record in (output / 'records').glob('*.json'):
            shutil.copy2(record, backup / record.name)
        shutil.copy2(output / 'manifest.jsonl', backup / 'manifest.jsonl')
        save(backup / 'repair.json', {'reason':'remote ffprobe uses native pkt_pts; initial reader requested only pts',
            'preserved_record_count': len(list((output/'records').glob('*.json'))),
            'selection_changed':False,'reusing_media_after_crc_size_check':True})
    (output / 'records').mkdir(exist_ok=args.resume)
    old_hashes, old_ids = set(), set()
    with args.v1_manifest.open() as f:
        for line in f:
            r = json.loads(line)
            old_hashes.add(r['sha256'])
            if r['source'] == 'Vript':
                old_ids.add(r['sample_id'].split('-Scene-')[0])
    source_dir = root / 'sources/AIGVDBench'
    test_bytes = (source_dir / 'Split_test.jsonl').read_bytes()
    test_rows = [json.loads(x) for x in test_bytes.splitlines() if x.strip()]
    official_test = {x['Video_id']: x for x in test_rows}
    plan, source_stats = [], {}
    for cell, target in [('Luma',500), ('Pika',500), ('Vidu',500), ('OpenVidHD',1500)]:
        inventory_path = root / 'zip_inventory' / (cell+'.json')
        source = json.loads(inventory_path.read_text())
        candidates = [m for m in source['members'] if m['member'].lower().endswith('.mp4') and 0 < m['file_size'] <= 256*1024**2 and m['method'] in (0,8) and not m['flags']&1]
        if cell == 'OpenVidHD':
            candidates = [m for m in candidates if Path(m['member']).name in official_test]
        ranked = sorted(candidates, key=lambda m: sha((SEED+'|'+cell+'|'+m['member']).encode()))
        chosen, seen_ids, overlapping_source = [], set(), 0
        for member in ranked:
            inferred_id = None
            if cell == 'OpenVidHD':
                match = re.match(r'^([A-Za-z0-9_-]{11})_\d+_', Path(member['member']).name)
                if not match:
                    continue
                inferred_id = match[1]
                if inferred_id in old_ids:
                    overlapping_source += 1
                    continue
                if inferred_id in seen_ids:
                    continue
                seen_ids.add(inferred_id)
            asset_id = sha((cell+'|'+member['member']).encode())
            chosen.append(dict(member, asset_id=asset_id, cell=cell, label='real' if cell=='OpenVidHD' else 'fake',
                generator=None if cell=='OpenVidHD' else cell,
                source='OpenVid-HD via AIGVDBench' if cell=='OpenVidHD' else 'AIGVDBench closed-source release',
                source_video_id_candidate=inferred_id, source_video_id_evidence='archive_filename_only' if inferred_id else None,
                generator_evidence='official_release_archive_membership', ancestor_status='not_verified',
                license_status='release_cc_by_4_0_upstream_not_individually_verified',
                license_record_sha256=sha((source_dir/'README.md').read_bytes()),
                official_split='test' if cell=='OpenVidHD' else 'closed_source_test_only_per_project_readme',
                intended_role='external_candidate_no_model_evaluation', formal_final_set=False,
                repo=source['repo'], revision=source['revision'], archive_path=source['archive_path'],
                archive_bytes=source['archive_bytes'], archive_lfs_sha256=source['archive_lfs_sha256'],
                archive_hash_fully_verified=False, inventory_sha256=sha(inventory_path.read_bytes()),
                official_url=f"https://huggingface.co/datasets/{source['repo']}/resolve/{source['revision']}/"+urllib.parse.quote(source['archive_path']),
                transport_url=f"https://hf-mirror.com/datasets/{source['repo']}/resolve/{source['revision']}/"+urllib.parse.quote(source['archive_path']),
                official_test_metadata_sha256=sha(test_bytes) if cell=='OpenVidHD' else None))
            if len(chosen) == target:
                break
        if len(chosen) != target:
            raise ValueError(f'{cell}: requested {target}, eligible {len(chosen)}')
        plan.extend(chosen)
        source_stats[cell] = {'archive_members':len(source['members']), 'eligible_candidates':len(candidates),
                              'selected':len(chosen), 'known_v1_source_id_matches_skipped':overlapping_source}
    planned_bytes = sum(r['file_size'] for r in plan)
    free = shutil.disk_usage(output).free
    if planned_bytes > 18*GIB or free - planned_bytes*1.2 < 10*GIB:
        raise ValueError('bounded subset does not fit with working-space reserve')
    plan_record = {'created_at':datetime.now(timezone.utc).isoformat(), 'seed':SEED,
        'selection_basis':'SHA256 rank of source cell/member before media or model observation; real restricted to official test and one filename-derived source ID, excluding known v1 Vript IDs',
        'source_id_is_verified_ancestry':False, 'source_counts':source_stats,
        'planned_media_bytes':planned_bytes, 'free_bytes_before':free,
        'no_replacement_of_failed_samples':True, 'rows':plan}
    if args.resume:
        frozen = json.loads((output / 'acquisition_plan.json').read_text())
        if frozen['rows'] != plan_record['rows'] or frozen['seed'] != SEED:
            raise ValueError('resume attempted to change frozen selection')
    else:
        save(output / 'acquisition_plan.json', plan_record)
    plan_hash = sha((output / 'acquisition_plan.json').read_bytes())
    print(json.dumps({'stage':'plan_frozen','rows':len(plan),'planned_gib':round(planned_bytes/GIB,3),'plan_sha256':plan_hash,'counts':source_stats}), flush=True)
    counts, cells = collections.Counter(), collections.defaultdict(collections.Counter)
    received = saved = 0
    with (output / 'manifest.jsonl').open('w', encoding='utf-8') as manifest, concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(acquire, (row, output, old_hashes)) for row in plan]
        for i, future in enumerate(concurrent.futures.as_completed(jobs), 1):
            record = future.result()
            manifest.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
            manifest.flush()
            counts[record['status']] += 1
            cells[record['cell']][record['status']] += 1
            received += record.get('range_bytes_received',0)
            saved += record['file_size'] if record.get('path') else 0
            if i%25 == 0 or i == len(plan):
                progress = {'completed':i,'total':len(plan),'counts':dict(counts),'received_gib':round(received/GIB,3),'elapsed_seconds':round(time.monotonic()-start,1)}
                save(output / 'progress.json', progress)
                print(json.dumps(progress), flush=True)
    receipt = {'created_at':datetime.now(timezone.utc).isoformat(), 'planned':len(plan),'status_counts':dict(counts),
        'cell_status_counts':dict(cells), 'plan_sha256':plan_hash,'manifest_sha256':sha((output/'manifest.jsonl').read_bytes()),
        'media_bytes':saved, 'range_bytes_received_successful_attempts':received,'source_counts':source_stats,
        'archive_hash_fully_verified':False, 'per_file_crc_and_sha256_recorded':True,
        'full_archive_extraction_performed':False,'media_downloaded_to_local_machine':False,
        'formal_independent_review':False,'scientific_gate_passed':False,'model_evaluation_performed':False,
        'elapsed_seconds':time.monotonic()-start,'free_bytes_after':shutil.disk_usage(output).free}
    save(output / 'receipt.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
