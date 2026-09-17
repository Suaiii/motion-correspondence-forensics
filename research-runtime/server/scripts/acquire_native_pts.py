"""Server-only original-PTS collector. Default is metadata-only planning.

No SSH, instance startup, downloads, features, transcode or shutdown. A separately
adopted, hash-bound contract is required for --execute. All outputs are metadata.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path = Path(path)
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    os.replace(temp, path)


def select_rows(manifest, contract):
    sources = contract['inputs']['sources']
    if len(set(sources)) != len(sources):
        raise ValueError('Duplicate source definitions')
    n = contract['inputs']['initial_per_source']
    if type(n) is not int or not 0 < n <= 50:
        raise ValueError('Invalid per-source limit')
    candidates = manifest['candidates']
    ids = set()
    for row in candidates:
        if row['sample_id'] in ids:
            raise ValueError('Duplicate sample ID')
        ids.add(row['sample_id'])
        if not re.fullmatch('[0-9a-f]{64}', row['source_sha256']):
            raise ValueError('Missing original SHA256')
        if not row.get('ancestry_status') or not row.get('origin_group'):
            raise ValueError('Explicit origin and ancestry status required')
        if row.get('data_role') != 'development_candidate':
            raise ValueError('Only development candidates; final/test input refused')
    selected = []
    for source in sources:
        origins = set()
        for row in sorted((r for r in candidates if r['source'] == source),
                          key=lambda r: (r['source_sha256'], r['sample_id'])):
            if row['origin_group'] in origins:
                continue
            origins.add(row['origin_group'])
            selected.append(row)
            if len(origins) == n:
                break
    if len(selected) > contract['inputs']['initial_max_files']:
        raise ValueError('Selected count exceeds contract')
    if not selected:
        raise ValueError('No candidates')
    return selected


def normalized_pts(raw):
    streams = raw.get('streams', [])
    if raw.get('error') or len(streams) != 1:
        raise ValueError('Probe error or ambiguous video stream')
    stream = streams[0]
    try:
        base = Fraction(stream['time_base'])
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError('Invalid time base') from exc
    if base <= 0:
        raise ValueError('Invalid time base')
    frames = raw.get('frames', [])
    if not frames:
        raise ValueError('No frame metadata; acquisition incomplete')
    ticks, best = [], []
    for frame in frames:
        def tick(key):
            value = frame.get(key)
            if value in (None, 'N/A'):
                return None
            if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)):
                raise ValueError('Noninteger timestamp')
            return int(value)
        ticks.append(tick('pts'))
        best.append(tick('best_effort_timestamp'))
    present = [v for v in ticks if v is not None]
    complete = len(present) == len(ticks)
    increasing = complete and all(b > a for a, b in zip(ticks, ticks[1:]))
    return dict(time_base_numerator=base.numerator, time_base_denominator=base.denominator,
        pts_ticks=ticks, best_effort_ticks=best, timestamp_kind='native_pts_no_fallback',
        frame_count=len(frames), missing_pts=len(ticks)-len(present),
        duplicate_pts=len(present)-len(set(present)),
        nonincreasing_adjacent_pairs=sum(a is not None and b is not None and b <= a
                                        for a,b in zip(ticks,ticks[1:])),
        strictly_increasing_native_pts=increasing,
        source_order_preserved=True, pts_synthesized_from_fps=False,
        sampling_eligibility_evaluated=False,
        note='Successful metadata collection is separate from sampling eligibility; best-effort values do not fill native PTS gaps')


def authorization_errors(contract, manifest_path):
    errors = []
    required = {'status': 'adopted', 'execution_authorized': True}
    for key, expected in required.items():
        if contract.get(key) != expected:
            errors.append(key)
    for key in ('approved_by', 'approval_receipt', 'parent_gate_receipt', 'existing_instance_receipt'):
        if not contract.get(key):
            errors.append(key)
    if contract['inputs'].get('source_manifest_sha256') != sha(manifest_path):
        errors.append('source_manifest_sha256')
    if contract.get('collector_sha256') != sha(Path(__file__)):
        errors.append('collector_sha256')
    budget = contract['budget']
    for key in ('approved_batch_max_cny', 'approved_batch_max_hours',
                'current_hourly_rate_cny', 'next_file_reserve_cny'):
        value = budget.get(key)
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value <= 0:
            errors.append(key)
    for key, cap_key, used_key in (
        ('approved_batch_max_cny','cumulative_cap_cny','actual_paid_cny'),
        ('approved_batch_max_hours','initial_cumulative_gpu_hours_cap','actual_billed_gpu_hours')):
        allowance, cap, used = budget.get(key), budget.get(cap_key), budget.get(used_key)
        if isinstance(allowance,(int,float)) and not isinstance(allowance,bool):
            if isinstance(cap,bool) or not isinstance(cap,(int,float)) or not math.isfinite(cap) or allowance > cap:
                errors.append(cap_key)
            elif used is not None and (isinstance(used,bool) or not isinstance(used,(int,float))
                                       or not math.isfinite(used) or used < 0 or used+allowance > cap):
                errors.append(used_key)
    if not errors and budget['next_file_reserve_cny'] >= budget['approved_batch_max_cny']:
        errors.append('next_file_reserve_cny_exceeds_batch')
    cap = contract['outputs'].get('server_metadata_max_bytes_proposed')
    if type(cap) is not int or not 0 < cap <= 268435456:
        errors.append('metadata_cap')
    if not budget.get('batch_allowance_receipt'):
        errors.append('batch_allowance_receipt')
    try:
        started = datetime.fromisoformat(budget['billing_started_utc'])
        if started.tzinfo is None or started > datetime.now(timezone.utc):
            raise ValueError('Invalid billing start')
    except (KeyError, ValueError, TypeError):
        errors.append('billing_started_utc')
    for key in ('new_instances_or_purchases_allowed','gpu_kernels_allowed',
                'feature_extraction_allowed','transcoding_or_frame_image_outputs_allowed'):
        if contract['operations'].get(key) is not False:
            errors.append(key)
    if contract['inputs'].get('final_confirmation_set_allowed') is not False:
        errors.append('final_confirmation_set_allowed')
    if contract['inputs'].get('additional_downloads_allowed') is not False:
        errors.append('additional_downloads_allowed')
    return errors


def remaining(contract):
    budget = contract['budget']
    elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(budget['billing_started_utc'])).total_seconds()
    hours = max(0,elapsed)/3600
    return min(budget['approved_batch_max_cny']-hours*budget['current_hourly_rate_cny'],
               (budget['approved_batch_max_hours']-hours)*budget['current_hourly_rate_cny'])


def within_root(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Original path must remain relative to server root')
    path = (root/rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Missing source or path escapes server root')
    return path


def reusable(path, binding):
    if not path.is_file():
        return False
    try:
        receipt = read(path)
        outputs = receipt['outputs']
        if not outputs or not any(Path(item['path']).name == 'normalized.json' for item in outputs):
            return False
        return (receipt.get('status') == 'probe_complete' and receipt.get('binding') == binding
                and all(sha(within_root(path.parent.resolve(),item['path'])) == item['sha256'] for item in outputs))
    except (ValueError, KeyError, OSError):
        return False


def execute_one(row, root, out, contract, binding, ffprobe):
    source = within_root(root, row['relative_path'])
    before = source.stat()
    if sha(source) != row['source_sha256']:
        raise ValueError('Source digest differs from frozen original')
    file_id = hashlib.sha256(row['sample_id'].encode()).hexdigest()
    pointer = out/(file_id+'.receipt.json')
    binding = dict(binding, source_sha256=row['source_sha256'], sample_id=row['sample_id'])
    if reusable(pointer, binding):
        return {'sample_id':row['sample_id'], 'status':'reused_verified_metadata'}
    attempt = out/(file_id+'.'+uuid.uuid4().hex)
    attempt.mkdir()
    stdout, stderr = attempt/'probe.json', attempt/'probe.stderr.txt'
    argv = [ffprobe, '-v','error','-threads','1','-select_streams','v:0',
        '-show_frames','-show_streams','-show_error','-show_entries',
        'stream=index,time_base,start_pts,start_time,duration_ts,duration,nb_frames:frame=pts,pts_time,best_effort_timestamp,best_effort_timestamp_time,duration,duration_time,pkt_duration,pkt_duration_time',
        '-of','json',str(source)]
    cap = contract['outputs']['server_metadata_max_bytes_proposed']
    status, reason = 'acquisition_failed', None
    with stdout.open('wb') as sout, stderr.open('wb') as serr:
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='')
        process = subprocess.Popen(argv, stdout=sout, stderr=serr, env=env)
        try:
            while process.poll() is None:
                used = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
                if remaining(contract) <= 0 or used >= cap:
                    reason = 'resource_partial_not_video_quality_failure'
                    process.kill()
                    process.wait()
                    break
                time.sleep(.1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    after = source.stat()
    normalized = None
    if reason is None and sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) >= cap:
        reason = 'resource_partial_not_video_quality_failure'
    if reason is None and (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        reason = 'source_changed_during_probe'
    if reason is None and (process.returncode != 0 or stderr.stat().st_size):
        reason = 'probe_exit_or_error_stderr'
    if reason is None:
        try:
            normalized = normalized_pts(read(stdout))
            write(attempt/'normalized.json', normalized)
            status = 'probe_complete'
        except (ValueError, KeyError, TypeError) as exc:
            reason = 'metadata_parse_failure: '+str(exc)
    output_files = [stdout, stderr]+([attempt/'normalized.json'] if normalized else [])
    receipt = dict(binding=binding, sample=row, status=status, reason=reason,
        probe_exit_code=process.returncode, full_stream_probe_requested=True,
        eof_process_completed=(process.returncode == 0 and reason is None),
        scientific_or_sampling_gate_passed=False, argv=argv,
        argv_sha256=hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
        original_size=before.st_size, original_mtime_ns=before.st_mtime_ns,
        observed_utc=datetime.now(timezone.utc).isoformat(),
        outputs=[dict(path=str(p.relative_to(out)),sha256=sha(p)) for p in output_files])
    write(pointer, receipt)
    write(attempt/'receipt.json', receipt)
    return dict(sample_id=row['sample_id'],status=status,reason=reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--server-root',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--ffprobe',default='ffprobe')
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    contract = read(args.contract)
    rows = select_rows(read(args.manifest),contract)
    errors = authorization_errors(contract,args.manifest)
    if not args.execute:
        print(json.dumps(dict(mode='metadata_plan_only',selected=rows,authorization_errors=errors,
            execution_authorized=False,media_read=False,probe_started=False),indent=2))
        return
    if errors:
        raise SystemExit('Execution refused: '+', '.join(errors))
    if sys.platform != 'linux' or args.server_root is None or args.output is None:
        raise SystemExit('Execution requires explicit Linux server paths')
    root = args.server_root.resolve()
    out = args.output.resolve()
    if not out.is_relative_to(root) or out == root:
        raise SystemExit('Metadata output must be a child of server root')
    out.mkdir(parents=True,exist_ok=True)
    lock = out/'acquisition.lock'
    with lock.open('x') as handle:
        handle.write(str(os.getpid()))
    try:
        version = subprocess.run([args.ffprobe,'-version'],capture_output=True,text=True,check=True,timeout=10).stdout
        binding = dict(contract_sha256=sha(args.contract),manifest_sha256=sha(args.manifest),
            collector_sha256=sha(Path(__file__)),ffprobe_version=version)
        outcomes = []
        for row in rows:
            used = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
            if used >= contract['outputs']['server_metadata_max_bytes_proposed']:
                outcomes.append(dict(status='storage_admission_stopped'))
                break
            if remaining(contract) <= contract['budget'].get('next_file_reserve_cny',float('inf')):
                outcomes.append(dict(status='budget_admission_stopped'))
                break
            try:
                outcomes.append(execute_one(row,root,out,contract,binding,args.ffprobe))
            except (ValueError,OSError) as exc:
                outcomes.append(dict(sample_id=row['sample_id'],status='acquisition_failed',reason=str(exc)))
            write(out/'batch.json',dict(binding=binding,outcomes=outcomes,
                actual_paid_cny=None,estimated_remaining_cny=remaining(contract),training_authorized=False))
        write(out/'batch.json',dict(binding=binding,outcomes=outcomes,
            actual_paid_cny=None,estimated_remaining_cny=remaining(contract),training_authorized=False))
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
