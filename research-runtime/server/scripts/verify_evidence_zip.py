"""Verify a transferred evidence ZIP and its per-entry SHA256 inventory."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import zipfile


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--expected-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    digest=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()
    if digest!=a.expected_sha256:raise ValueError('Transfer SHA differs')
    with zipfile.ZipFile(a.checkpoint) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP member')
        manifest=json.loads(z.read('ARCHIVE_INDEX.json'));entries=manifest['entries']
        if set(names)!={r['name'] for r in entries}|{'ARCHIVE_INDEX.json'}:raise ValueError('Manifest coverage differs')
        for row in entries:
            name=PurePosixPath(row['name'])
            if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe ZIP member')
            data=z.read(row['name'])
            if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Artifact differs: '+row['name'])
    result={'checkpoint_sha256':digest,'entries_verified':len(entries),'all_entries_match':True,
            'scope':'Mechanical transfer verification by primary implementer, not independent scientific review'}
    a.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
