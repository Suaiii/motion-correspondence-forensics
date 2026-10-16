"""Exercise the published index and preserve a compact, mechanical usage receipt."""
import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time


def main():
    root = Path('/srv/video_evidence_v1').resolve()
    output = root / 'operational_20261008'
    tool = root / 'tools_20261008/query_catalog.py'
    catalog = output / 'catalog.sqlite'
    start = time.monotonic()
    base = [sys.executable, str(tool), '--catalog', str(catalog), '--package',
            'AAGenvid_RoboVidSM_v02', '--split', 'train', '--variant', 'clean',
            '--generator', 'OpenSora', '--limit', '3']
    compact = [json.loads(x) for x in subprocess.check_output(base, text=True).splitlines()]
    full = [json.loads(x) for x in subprocess.check_output(base + ['--full-record'], text=True).splitlines()]
    assert len(compact) == len(full) == 3
    for a, b in zip(compact, full):
        assert a['sha256'] == b['sha256'] and a['path'] == b['path']
        assert b['local_path'].replace('\\', '/').startswith('E:/AAGenvid/')
        assert Path(a['path']).is_file()
        assert len(b['ffprobe']['pts']) == a['native_frame_count']
        assert a['generator'] == 'OpenSora' and a['split'] == 'train'
    conn = sqlite3.connect(catalog.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    assert conn.execute('select count(*) from assets').fetchone()[0] == 9236
    duplicates = []
    for duplicate in conn.execute('select sha256,count(*) as n from assets group by sha256 having count(*)>1'):
        group = conn.execute('select relative_path,variant from assets where sha256=?', (duplicate['sha256'],)).fetchall()
        duplicates.append({'sha256': duplicate['sha256'], 'rows': [dict(x) for x in group]})
    dupe_patterns = collections.Counter('|'.join(sorted(x['variant'] for x in d['rows'])) for d in duplicates)
    candidates = conn.execute("select * from assets where package='AAGenvid_RoboVidSM_v02' and variant='clean' and native_frame_count < 8").fetchall()
    # Decoder metadata smoke check on one file per source/variant cell.
    examples = conn.execute('select min(relative_path) as relative_path from assets group by package,variant,label').fetchall()
    probes = []
    for example in examples:
        row = conn.execute('select * from assets where relative_path=?', (example['relative_path'],)).fetchone()
        raw = subprocess.check_output(['/usr/bin/ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,width,height,time_base', '-of', 'json', row['path']], timeout=30)
        stream = json.loads(raw)['streams'][0]
        assert stream['time_base'] == row['time_base']
        assert stream['width'] == row['width'] and stream['height'] == row['height']
        probes.append({'relative_path': row['relative_path'], **stream})
    receipt = {
        'query_compact_full_record_matching': True, 'query_sample_count': len(compact),
        'catalog_sha256': hashlib.sha256(catalog.read_bytes()).hexdigest(),
        'query_tool_sha256': hashlib.sha256(tool.read_bytes()).hexdigest(),
        'smoke_probes': probes, 'duplicate_hash_groups': len(duplicates),
        'duplicate_variant_patterns': dict(dupe_patterns),
        'under_8_frame_clean_rows': [dict(x) for x in candidates],
        'source_split_is_training_authorization': False,
        'formal_independent_review': False, 'new_training_started': False,
        'elapsed_seconds': time.monotonic() - start,
    }
    (output / 'duplicate_groups.json').write_text(json.dumps(duplicates, ensure_ascii=False, indent=2)+'\n')
    (output / 'usage_verification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('smoke_probes','under_8_frame_clean_rows')}))
    conn.close()


if __name__ == '__main__':
    main()
