"""Publish an explicit recovered manifest while preserving the initial run receipt."""
import collections
import hashlib
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root=Path(sys.argv[1]).resolve()
    initial=json.loads((root/'receipt.json').read_text())
    assert digest(root/'manifest.jsonl')==initial['manifest_sha256']
    recovery=json.loads((root/'network_recovery_20261008/receipt.json').read_text())
    ids={r['asset_id'] for r in recovery['recovered_rows']}
    counts=collections.Counter()
    cells=collections.defaultdict(collections.Counter)
    media_bytes=0
    name='manifest.recovered.jsonl'
    with (root/name).open('x') as out, (root/'manifest.jsonl').open() as source:
        for line in source:
            row=json.loads(line)
            if row['asset_id'] in ids:
                assert row['status']=='error'
                row=json.loads((root/'records'/(row['asset_id']+'.json')).read_text())
            out.write(json.dumps(row,separators=(',',':'))+'\n')
            counts[row['status']]+=1
            cells[row['cell']][row['status']]+=1
            if row.get('path'):
                media_bytes+=row['file_size']
    receipt=dict(initial,manifest_name=name,manifest_sha256=digest(root/name),
        original_manifest_sha256=initial['manifest_sha256'],original_receipt_sha256=digest(root/'receipt.json'),
        network_recovery_receipt_sha256=digest(root/'network_recovery_20261008/receipt.json'),
        status_counts=dict(counts),cell_status_counts=dict(cells),media_bytes=media_bytes,
        network_recovery_attempted=len(ids),selection_changed=False)
    (root/'receipt.recovered.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status_counts':dict(counts),'manifest_sha256':receipt['manifest_sha256'],'same_plan_sha256':receipt['plan_sha256']}))


if __name__=='__main__':
    main()
