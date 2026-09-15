"""Verify every frozen QC input in a transferred checkpoint without extracting videos."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    digest = hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()
    if digest != a.expected_sha256: raise ValueError('Transferred checkpoint hash differs')
    with zipfile.ZipFile(a.checkpoint) as z:
        if len(z.namelist()) != len(set(z.namelist())): raise ValueError('Duplicate ZIP names')
        summary = json.loads(z.read('full_native_qc_aggregate_v1/summary.json'))
        checked = 0
        for name, expected in summary['input_sha256'].items():
            if hashlib.sha256(z.read('full_native_qc/' + name)).hexdigest() != expected:
                raise ValueError('Input digest differs: ' + name)
            checked += 1
    result = {'checkpoint_sha256': digest, 'all_frozen_inputs_verified': checked,
              'qc_requested': summary['requested'], 'scope': 'primary implementer mechanical transfer verification; not independent scientific review'}
    a.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__': main()
