"""Recompute completed source-only QC tables; no detector metrics or ancestry claims."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def summarize(root):
    summary = read(root / 'qc_summary.json')
    lock = read(root / 'qc_lock.json')
    if not summary.get('complete'):
        raise ValueError('Full QC has not completed')
    inputs = {}
    rows = []
    for path in sorted((root / 'records').glob('*.json')):
        rows.append(read(path))
        inputs[path.relative_to(root).as_posix()] = digest(path)
    ids = [r['sample_id'] for r in rows]
    if len(ids) != len(set(ids)) or len(rows) != summary['requested'] or len(rows) != lock['requested']:
        raise ValueError('Duplicate identities or incomplete record coverage')
    if summary['completed'] != len(rows):
        raise ValueError('Summary count differs from record count')
    groups = {k: defaultdict(list) for k in ('file_sha256', 'sampled_frame_sha256', 'phash_three_frames')}
    sources = {}
    for source in sorted({r['source'] for r in rows}):
        selected = [r for r in rows if r['source'] == source]
        counts = dict(Counter(r['status'] for r in selected))
        if counts != summary['counts'][source]:
            raise ValueError('Source status counts differ from saved summary')
        stream_counts = Counter()
        for r in selected:
            stream = r.get('stream', {})
            key = {k: stream.get(k) for k in ('codec_name', 'width', 'height', 'avg_frame_rate', 'nb_frames', 'duration')}
            stream_counts[json.dumps(key, sort_keys=True)] += 1
        sources[source] = {
            'requested': len(selected), 'counts': counts,
            'non_ok_fraction': sum(r['status'] != 'ok' for r in selected) / len(selected),
            'failure_reasons': dict(Counter(r.get('reason', 'unspecified') for r in selected if r['status'] != 'ok')),
            'stream_groups': [{'stream': json.loads(k), 'count': n} for k, n in sorted(stream_counts.items())],
            'videos_with_repeated_sampled_pixels': sum(r.get('duplicate_sampled_content', 0) > 0 for r in selected),
            'worker_seconds_sum': sum(r.get('seconds', 0) for r in selected),
        }
    for r in rows:
        for key in groups:
            value = r.get(key)
            if not value:
                continue
            if key == 'sampled_frame_sha256' and len(value) != 16:
                raise ValueError('Unexpected sampled-frame identity length')
            if key == 'phash_three_frames' and len(value) != 3:
                raise ValueError('Unexpected perceptual-hash length')
            groups[key][json.dumps(value, sort_keys=True)].append({'sample_id': r['sample_id'], 'source': r['source'], 'status': r['status']})
    duplicate_groups = {}
    duplicate_counts = {}
    for key, mapping in groups.items():
        matches = [{'identity': json.loads(value), 'members': members} for value, members in sorted(mapping.items()) if len(members) > 1]
        duplicate_groups[key] = matches
        duplicate_counts[key] = {
            'groups': len(matches),
            'participating_videos': sum(len(g['members']) for g in matches),
            'redundant_entries_if_collapsed': sum(len(g['members']) - 1 for g in matches),
            'cross_source_groups': sum(len({r['source'] for r in g['members']}) > 1 for g in matches),
        }
    for name in ('qc_summary.json', 'qc_lock.json', 'extraction_ms.json', 'extraction_vc2.json'):
        inputs[name] = digest(root / name)
    result = {
        'complete': True, 'requested': len(rows), 'sources': sources,
        'duplicate_counts': duplicate_counts,
        'classification_metrics_computed': False,
        'limitations': [
            'Only two generated sources; no real/fake or generalization performance.',
            'Native 16-frame supplemental protocol; not the original physical-time primary protocol.',
            'Pixel identity refers to sampled resized decoded frames, not necessarily whole native videos.',
            'Equal three-frame perceptual hashes are candidates only; no distance-based search or ancestry verification.',
            'Original Pair1 archives only; repair bundle not applied or validated.',
            'Worker seconds are summed work, not elapsed time or billed GPU hours.',
        ],
        'input_sha256': inputs, 'script_sha256': digest(Path(__file__)),
    }
    return result, duplicate_groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result, groups = summarize(args.run_dir)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, value in [('summary.json', result), ('duplicate_groups.json', groups)]:
        (args.output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('complete', 'requested', 'duplicate_counts')}))


if __name__ == '__main__':
    main()
