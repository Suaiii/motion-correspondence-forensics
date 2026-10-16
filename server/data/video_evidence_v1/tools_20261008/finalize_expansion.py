"""Publish a completed range subset's inventory and reconcile every selected ID."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import sys
from datetime import datetime, timezone


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    root = Path(sys.argv[1]).resolve()
    receipt_path = root / ('receipt.recovered.json' if (root/'receipt.recovered.json').is_file() else 'receipt.json')
    acquisition = json.loads(receipt_path.read_text())
    manifest = root / acquisition.get('manifest_name','manifest.jsonl')
    plan = json.loads((root/'acquisition_plan.json').read_text())
    assert acquisition['planned'] == 3000 and len(plan['rows']) == 3000
    assert sha(root/'acquisition_plan.json') == acquisition['plan_sha256']
    assert sha(manifest) == acquisition['manifest_sha256']
    rows, offsets = [], []
    with manifest.open('rb') as f:
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            rows.append(json.loads(line))
            offsets.append(offset)
    assert len(rows) == len({r['asset_id'] for r in rows}) == 3000
    assert {r['asset_id'] for r in rows} == {r['asset_id'] for r in plan['rows']}
    out = root/'operational'
    out.mkdir(exist_ok=False)
    hash_groups = collections.defaultdict(list)
    stats = collections.defaultdict(lambda: {'frames':[], 'fps':[], 'widths':[], 'heights':[], 'codecs':collections.Counter()})
    conn = sqlite3.connect(out/'catalog.sqlite')
    conn.execute('CREATE TABLE assets(asset_id TEXT PRIMARY KEY,path TEXT,relative_path TEXT,sha256 TEXT,file_size INTEGER,package TEXT,split TEXT,variant TEXT,label TEXT,generator TEXT,source TEXT,status TEXT,cell TEXT,source_video_id_candidate TEXT,time_base TEXT,native_frame_count INTEGER,manifest_byte_offset INTEGER)')
    fields = [r[1] for r in conn.execute('PRAGMA table_info(assets)')]
    errors, checked = [], 0
    with (out/'catalog.jsonl').open('w') as compact:
        for row,offset in zip(rows,offsets):
            if row.get('path'):
                path = Path(row['path'])
                assert path.is_relative_to(root/'media') and path.is_file()
                assert path.stat().st_size == row['file_size'] and sha(path) == row['sha256']
                checked += 1
                hash_groups[row['sha256']].append(row['asset_id'])
            if row['status'] != 'qc_pass':
                diagnostic = {k:v for k,v in row.items() if k not in ('ffprobe',)}
                diagnostic['qc_diagnostics'] = {k:row.get('ffprobe',{}).get(k) for k in
                    ('frame_count_probed','integer_pts_complete','native_pts_strictly_increasing','time_base','stderr')}
                errors.append(diagnostic)
            p = row.get('ffprobe',{})
            cat = dict(row, relative_path=str(Path(row['path']).relative_to(root)) if row.get('path') else None,
                package='AIGVDBench_range_subset_20261008',split='external_candidate',variant='clean',
                time_base=p.get('time_base'),native_frame_count=p.get('frame_count_probed'),manifest_byte_offset=offset)
            minimal = {k:cat.get(k) for k in fields}
            conn.execute('INSERT INTO assets VALUES('+','.join('?' for _ in fields)+')',[minimal[k] for k in fields])
            compact.write(json.dumps(minimal, separators=(',',':'))+'\n')
            if p.get('frame_count_probed'):
                s = stats[row['cell']]
                s['frames'].append(p['frame_count_probed'])
                s['widths'].append(p['width'])
                s['heights'].append(p['height'])
                s['codecs'][p['codec_name']] += 1
                numerator,denominator = p['avg_frame_rate'].split('/')
                if float(denominator):
                    s['fps'].append(float(numerator)/float(denominator))
    conn.execute('CREATE INDEX filter_cells ON assets(package,split,variant,label,generator,status)')
    conn.execute('CREATE INDEX hashes ON assets(sha256)')
    conn.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)')
    conn.executemany('INSERT INTO metadata VALUES(?,?)', [('source_manifest',str(manifest)),('source_manifest_sha256',acquisition['manifest_sha256'])])
    conn.commit()
    sqlite_ok = conn.execute('PRAGMA integrity_check').fetchone()[0]
    conn.close()
    compact_stats = {}
    for cell,s in stats.items():
        compact_stats[cell] = {'count':len(s['frames']),'codecs':dict(s['codecs'])}
        for field in ('frames','fps','widths','heights'):
            compact_stats[cell][field] = {'min':min(s[field]),'median':statistics.median(s[field]),'max':max(s[field])} if s[field] else None
    duplicates = {h:ids for h,ids in hash_groups.items() if len(ids)>1}
    for name,obj in [('metadata_coverage.json',compact_stats),('exceptions.json',errors),('duplicate_groups.json',duplicates)]:
        (out/name).write_text(json.dumps(obj,indent=2)+'\n')
    source_groups = {}
    source_metadata = root.parent/'sources/AIGVDBench'
    for split in ('train','val','test'):
        ids = set()
        with (source_metadata/('Split_'+split+'.jsonl')).open() as f:
            for line in f:
                match = re.match(r'^([A-Za-z0-9_-]{11})_\d+_',json.loads(line)['Video_id'])
                if match:
                    ids.add(match[1])
        source_groups[split] = ids
    selected_ids = {r['source_video_id_candidate'] for r in rows if r['cell']=='OpenVidHD'}
    source_audit = {'evidence':'archive and official split filenames only; source identity not independently verified',
        'upstream_split_candidate_origin_counts':{s:len(ids) for s,ids in source_groups.items()},
        'selected_real_candidate_origins':len(selected_ids),
        'selected_real_origins_also_in_upstream_train':len(selected_ids & source_groups['train']),
        'selected_real_origins_also_in_upstream_val':len(selected_ids & source_groups['val']),
        'interpretation':'Do not treat official clip-level test membership as proof of ancestor separation. This acquisition does not train on the upstream train or val assets.'}
    (out/'upstream_origin_audit.json').write_text(json.dumps(source_audit,indent=2)+'\n')
    tools_root = Path('/srv/video_evidence_v1/tools_20261008')
    query = subprocess.check_output([sys.executable,str(tools_root/'query_catalog.py'),'--catalog',str(out/'catalog.sqlite'),'--generator','Luma','--status','qc_pass','--limit','3'],text=True)
    queried = [json.loads(x) for x in query.splitlines()]
    assert len(queried)==3 and all(Path(x['path']).is_file() for x in queried)
    receipt = {'created_at':datetime.now(timezone.utc).isoformat(),'selected':3000,'rows_reconciled':len(rows),
        'source_acquisition_receipt':str(receipt_path),'source_acquisition_receipt_sha256':sha(receipt_path),
        'file_sha256_reverified':checked,'qc_status_counts':dict(collections.Counter(r['status'] for r in rows)),
        'qc_pass_label_counts':dict(collections.Counter(r['label'] for r in rows if r['status']=='qc_pass')),
        'unique_file_sha256_count':len(hash_groups),'duplicate_hash_groups':len(duplicates),
        'duplicate_of_v1_count':sum(bool(r.get('duplicate_of_v1')) for r in rows),
        'real_source_ids_unique':len({r['source_video_id_candidate'] for r in rows if r['cell']=='OpenVidHD'}),
        'source_id_evidence':'filename-derived grouping only; not verified ancestral independence',
        'sqlite_integrity':sqlite_ok,'query_smoke_count':len(queried),
        'license_scope':'CC-BY-4.0 release metadata; underlying per-item rights not verified',
        'checksum_scope':'all selected files checked against ZIP member CRC and local SHA256; full upstream ZIP LFS hash not computed',
        'new_training_started':False,'model_scores_computed':False,'formal_independent_review':False,'scientific_gate_passed':False,
        'ffprobe_version':subprocess.check_output(['/usr/bin/ffprobe','-version'],text=True).splitlines()[0],
        'tool_sha256':{n:sha(tools_root/n) for n in ('acquire_range_subset.py','range_zip_inventory.py','finalize_expansion.py','query_catalog.py')},
        'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
