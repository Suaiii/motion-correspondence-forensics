"""Read-only verification of a transferred run before removing local payloads."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = root / 'artifact_hashes.json'
    if sha(manifest) != args.manifest_sha256:
        raise ValueError('Transfer manifest differs from local original')
    expected = json.loads(manifest.read_text(encoding='utf-8'))
    total = 0
    for rel, digest in expected.items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or sha(path) != digest:
            raise ValueError('Artifact mismatch: ' + rel)
        total += path.stat().st_size
    videos = list((root / 'raw').glob('*.mp4'))
    print(json.dumps({'status': 'pass', 'root': str(root),
                      'verified_files': len(expected), 'verified_bytes': total,
                      'videos': len(videos), 'video_bytes': sum(p.stat().st_size for p in videos),
                      'manifest_sha256': args.manifest_sha256}))


if __name__ == '__main__':
    main()
