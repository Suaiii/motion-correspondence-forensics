"""Recover already-failed transport rows using small, receipted byte ranges."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import acquire_range_subset as acquisition
from range_zip_inventory import read_range as http_range


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--v1-manifest',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    plan=json.loads((root/'acquisition_plan.json').read_text())
    plan_by_id={r['asset_id']:r for r in plan['rows']}
    failed=[]
    for path in (root/'records').glob('*.json'):
        r=json.loads(path.read_text())
        if r.get('status')=='error' and r.get('error_type') in ('ConnectionError','ReadTimeout','TimeoutError','URLError'):
            failed.append((path,r))
    recovery=root/'network_recovery_20261008'
    recovery.mkdir(exist_ok=False)
    original_hashes=set()
    with args.v1_manifest.open() as f:
        for line in f:
            original_hashes.add(json.loads(line)['sha256'])
    results=[]
    for path,previous in failed:
        cell=recovery/previous['asset_id']
        cell.mkdir()
        shutil.copy2(path,cell/'original_error_record.json')
        def chunked(url,size,start,count):
            pieces=[]
            for offset in range(start,start+count,2*1024*1024):
                wanted=min(2*1024*1024,start+count-offset)
                piece=None
                for attempt in range(2):
                    try:
                        piece=http_range(url,size,offset,wanted)
                        break
                    except Exception as exc:
                        with (cell/'transport_errors.jsonl').open('a') as f:
                            f.write(json.dumps({'offset':offset,'length':wanted,'attempt':attempt+1,'error_type':type(exc).__name__,'error':str(exc)})+'\n')
                        if attempt:
                            raise
                        time.sleep(1)
                filename=f'{offset}-{offset+wanted-1}.bin'
                (cell/filename).write_bytes(piece)
                with (cell/'chunks.jsonl').open('a') as f:
                    f.write(json.dumps({'start':offset,'bytes':len(piece),'sha256':hashlib.sha256(piece).hexdigest(),'file':filename})+'\n')
                pieces.append(piece)
            return b''.join(pieces)
        acquisition.read_range=chunked
        result=acquisition.acquire((plan_by_id[previous['asset_id']],root,original_hashes))
        record={'asset_id':previous['asset_id'],'previous_status':previous['status'],'recovery_status':result['status'],
                'same_frozen_sample':True,'new_sample_substitution':False,'record_sha256':acquisition.sha(path.read_bytes())}
        results.append(record)
        print(json.dumps(record),flush=True)
    acquisition.save(recovery/'receipt.json',{'recovered_rows':results,'selection_changed':False})


if __name__=='__main__':
    main()
