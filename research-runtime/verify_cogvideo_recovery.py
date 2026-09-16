"""Recompute recovery integrity and match author labels; never certify ancestry."""
import json
from collections import Counter
from pathlib import Path
import sys
import zlib
from recover_cogvideo_cached import digest, read, write, ROOT


def main():
    root = Path(sys.argv[1]).resolve()
    lock = read(root/'lock.json')
    assert digest(ROOT/'research-runtime/recover_cogvideo_cached.py') == lock['script_sha256']
    assert digest(ROOT/'research-runtime/server/forensics/video.py') == lock['decoder_sha256']
    for relative, expected in read(root/'artifact_hashes.json').items():
        assert digest(root/relative) == expected, relative
    selection = ROOT/'research-runs/cogvideo_pair2_selection_20260916.json'
    index_path = ROOT/'research-runs/cogvideo_pair2_index_20260916.json'
    assert digest(selection) == lock['selection_sha256']
    assert digest(index_path) == lock['index_sha256']
    selected = read(selection)['rows']
    idx = {r['name']:r for r in read(index_path)['members']}
    label_path = ROOT/'research-plan/artifacts/cvpr27/metadata/jian-0/GenVidBench/GenVidBench/Pair2_labels.txt'
    labels = {}
    for line in label_path.read_text(encoding='utf-8-sig').splitlines():
        name, label = line.rsplit(' ', 1)
        if name.startswith('Pair2/cogvideo/'):
            labels[name.removeprefix('Pair2/')] = int(label)
    records = [read(p) for p in (root/'records').glob('*.json')]
    assert len(records) == len(selected) == 100
    assert {r['sample_id'] for r in records} == {r['sample_id'] for r in selected}
    historical = set(read(ROOT/'research-runtime/server/configs/historical_exclusions.json')['sha256'])
    overlaps = []; parents = Counter(); deltas = Counter()
    for r in records:
        assert r['recovery_status'] == 'ok'
        entry = idx[r['archive_member']]
        assert labels[r['archive_member']] == r['label_fake'] == 1
        data = (root/r['raw_file']).read_bytes()
        assert digest(root/r['raw_file']) == r['sha256']
        assert len(data) == entry['size'] == r['bytes']
        assert zlib.crc32(data) == entry['crc32'] == r['crc32']
        for fps in (4, 8):
            q = r['sampling'][str(fps)]
            assert q['status'] == 'ok' and q['frames'] == 2*fps
            meta = q['metadata']; times = meta['pts']; ids = meta['indices']
            assert len(set(ids)) == len(ids) == len(times) == 2*fps
            assert all(b > a for a, b in zip(times, times[1:]))
            assert meta['duration'] >= 2
            deltas[str(fps)+':'+str(round(times[1]-times[0], 6))] += 1
        if r['sha256'] in historical:
            overlaps.append(r['sample_id'])
        parents[r['ancestry_status']] += 1
    assert len({r['sha256'] for r in records}) == 100
    report = dict(status='pass', reviewer='primary implementer mechanical verification',
        independent_scientific_review=False, records=100, labels_matched=100,
        all_member_crc_and_sha_recomputed=True, sampling_first_interval_counts=dict(deltas),
        historical_exact_hash_matches=overlaps, ancestry_status_counts=dict(parents),
        label_file_sha256=digest(label_path), verifier_sha256=digest(__file__),
        qualifications=['Exact hash exclusion does not establish ancestor independence.',
                        'Author binary labels do not establish T2V versus I2V task.',
                        'No new classifier results; licensing and upstream mapping remain open.'])
    write(root/'verification.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
