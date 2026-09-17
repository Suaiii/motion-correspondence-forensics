"""Join author indices, source-video IDs and CogVideo prompt filenames.

This is stronger than an ordinal guess but remains author-metadata provenance,
not independent visual confirmation of real labels or generation ancestry.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def text_key(value):
    return ''.join(c.casefold() for c in value if c.isalnum())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--hdvg', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    metadata = a.base / 'HDVG_14k_classes.txt'; data = metadata.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert blob == '9ebfc67dbe27d2827a0b8cf37029e4a66708736c'
    mapping = {}
    for line in data.decode('utf-8-sig').splitlines():
        parts = line.split('|||', 3)
        assert len(parts) == 4 and re.fullmatch(r'[A-Za-z0-9_-]{11}', parts[1])
        key = int(parts[0]); assert key not in mapping
        mapping[key] = dict(origin_id=parts[1], prompt=parts[3])
    pair1 = a.base / 'Pair1_labels.txt'
    vript_origins = set()
    for line in pair1.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('Pair1/vript/'):
            m = re.fullmatch(r'Pair1/vript/([A-Za-z0-9_-]{11})-Scene-\d+\.mp4 0', line)
            assert m, line
            vript_origins.add(m[1])
    old = read(a.base / 'runs/paired_dino_time_v1/manifest.json')
    old_hashes = {r['sha256'] for r in old}
    exclusions = read(a.base / 'releases/v0.1.3/cvpr27-server/configs/historical_exclusions.json')
    old_hashes.update(exclusions['sha256'])
    manifest = []
    for source, folder in [('hd_vg_130m', a.hdvg), ('cogvideo', a.base / 'data/cogvideo_cached_recovery_v1')]:
        for path in sorted((folder / 'records').glob('*.json')):
            r = read(path)
            raw = folder / r['raw_file']; assert sha(raw) == r['sha256']
            name = Path(r['archive_member']).name
            match = re.fullmatch(r'(\d+)___(.+)\.mp4', name); assert match, name
            number = int(match[1]); meta = mapping.get(number)
            assert meta is not None
            if source == 'hd_vg_130m':
                source_match = match[2].split('.', 1)[0] == meta['origin_id']
                prompt_match = None
            else:
                source_match = None
                prompt_match = text_key(match[2]) == text_key(meta['prompt'])
            joined = source_match is True or prompt_match is True
            reasons = []
            if not joined:
                reasons.append('author_index_join_failed')
            if meta['origin_id'] in vript_origins:
                reasons.append('shared_origin_with_pair1_vript')
            if r['sha256'] in old_hashes:
                reasons.append('historical_exact_hash')
            manifest.append(dict(sample_id=r['sample_id'], source=source, label_fake=int(source=='cogvideo'),
                raw_path=str(raw.resolve()), sha256=r['sha256'], archive_member=r['archive_member'],
                author_index=number, group='youtube:' + meta['origin_id'], origin_id=meta['origin_id'],
                author_origin_match=source_match, author_prompt_match=prompt_match,
                metadata_lineage_join=joined, ancestry_content_verified=False,
                exclusion_reasons=reasons, development_eligible_before_qc=not reasons,
                role='external_development_only', formal_training_released=False))
    counts = Counter(r['sha256'] for r in manifest)
    for r in manifest:
        if counts[r['sha256']] > 1:
            r['exclusion_reasons'].append('duplicate_candidate_hash')
            r['development_eligible_before_qc'] = False
    (a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    groups = {}
    for r in manifest:
        groups.setdefault(r['group'], []).append(r['sample_id'])
    report = dict(script_sha256=sha(__file__), metadata_git_blob_sha1=blob, metadata_sha256=sha(metadata),
        pair1_labels_sha256=sha(pair1), metadata_rows=len(mapping),
        counts=dict(Counter(r['source'] for r in manifest)),
        metadata_join_counts=dict(Counter(str(r['metadata_lineage_join']) for r in manifest)),
        source_origin_matches=sum(r['author_origin_match'] is True for r in manifest),
        generator_prompt_matches=sum(r['author_prompt_match'] is True for r in manifest),
        exclusions=dict(Counter(reason for r in manifest for reason in r['exclusion_reasons'])),
        eligible_before_qc=dict(Counter(r['source'] for r in manifest if r['development_eligible_before_qc'])),
        ancestry_groups=len(groups), multisample_groups=sum(len(v)>1 for v in groups.values()),
        manifest_sha256=sha(a.output / 'manifest.json'), formal_training_released=False,
        limitations=['Archive-prefix selection is non-random and unsuitable as a definitive benchmark.',
                    'Author ordinal plus origin/prompt join is not independent visual ancestry proof.',
                    'HD-VG declares academic-only use and no redistribution; videos remain server-side.',
                    'Declared author real labels are not independent confirmation of camera capture.',
                    'Do not split generated prompts and reference videos across train and evaluation.'])
    (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
