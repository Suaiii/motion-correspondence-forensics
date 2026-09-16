"""Resolve known source aliases without promoting inferred ancestry to verified.

Reads server video hashes and the historic RoboVid source mapping. No training,
no media download and no writes to old manifests. Filenames supply only a
metadata link; exact byte matches are reported separately.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def load_lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--source-map', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError('Use a new audit version')
    mapped = load_lines(a.source_map)
    real_map, fake_map = {}, {}
    for r in mapped:
        if r.get('real_file') and r.get('vript_clip_id'):
            real_map[PureWindowsPath(r['real_file']).name] = r
        if r.get('fake_file'):
            fake_map[PureWindowsPath(r['fake_file']).name] = r
    old = load_lines(a.manifest); records=[]; by_hash=defaultdict(list)
    data_root = a.data_root.resolve()
    for r in old:
        file = (data_root/r['path']).resolve()
        if not file.is_relative_to(data_root) or sha(file) != r['sha256']:
            raise ValueError('Video outside root or hash mismatch: '+r['sample_id'])
        # Uploaded filenames have a four-digit packaging prefix, not a source ID.
        name = re.sub(r'^\d{4}_', '', file.name)
        real = r['label_fake'] == 0
        source = r['source']; generator = r.get('generator')
        group = None; mapping_evidence = 'unresolved'
        link = real_map.get(name) if real else fake_map.get(name)
        if real and (source == 'vript_real' or link):
            source = 'vript'
            clip = link['vript_clip_id'] if link else Path(name).stem
            origin = re.sub(r'-Scene-\d+$', '', clip)
            group = 'vript:'+origin
            mapping_evidence = 'local_original_source_metadata' if link else 'filename_original_video_proxy'
        elif not real:
            if r['source'] == 'videoOSN_raw':
                generator = 'openai_sora' if link else None
                mapping_evidence = 'local_source_metadata_filename_link' if link else 'unresolved_generator'
            else:
                mapping_evidence = 'inherited_generator_label'
            source = generator or 'unknown_generator'
            group = (generator+':'+Path(name).stem) if generator else None
        records.append(dict(sample_id=r['sample_id'],path=r['path'],sha256=r['sha256'],
            label_fake=r['label_fake'],previous_source=r['source'],previous_generator=r.get('generator'),
            canonical_source_candidate=source,generator_candidate=generator,
            ancestor_group_candidate=group,evidence=mapping_evidence,
            mapping_file_sha256=sha(a.source_map) if link else None,
            ancestry_status='unknown',training_released=False))
        by_hash[r['sha256']].append(r['sample_id'])
    groups=defaultdict(list)
    for r in records:
        if r['ancestor_group_candidate']:
            groups[r['ancestor_group_candidate']].append(r['sample_id'])
    summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),
        inputs={'manifest_sha256':sha(a.manifest),'source_map_sha256':sha(a.source_map),'script_sha256':sha(Path(__file__))},
        n=len(records),previous_counts=dict(Counter(r['source']+'/'+str(r['label_fake']) for r in old)),
        canonical_candidate_counts=dict(Counter(r['canonical_source_candidate']+'/'+str(r['label_fake']) for r in records)),
        duplicate_byte_groups=[v for v in by_hash.values() if len(v)>1],
        shared_ancestor_candidate_groups={k:v for k,v in groups.items() if len(v)>1},
        independent_real_source_count_established=False,
        training_released=False,
        conclusions=['videoOSN is not an independently established generator or real source.',
                     'Do not split known or suspected common ancestors across fit/calibration/audit.',
                     'Filename metadata links are not full content-level or licence verification.'],
        records=records)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(summary,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('records','shared_ancestor_candidate_groups')},indent=2))
    print('shared ancestor groups:',len(summary['shared_ancestor_candidate_groups']))


if __name__ == '__main__':
    main()
