"""Snapshot official public repository inventories; downloads metadata only."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from datetime import datetime, timezone


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'video-evidence-research/1.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        data = response.read(25*1024*1024+1)
        if len(data) > 25*1024*1024:
            raise ValueError('metadata size cap exceeded')
        return data, response.headers.get('Link', '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    for repo in ('AIGVDBench/AIGVDBench', 'jian-0/GenVidBench'):
        folder = args.output / repo.split('/')[1]
        folder.mkdir()
        try:
            info_bytes, _ = get('https://huggingface.co/api/datasets/' + repo)
            info = json.loads(info_bytes)
            revision = info['sha']
            (folder / 'repository_info.json').write_bytes(info_bytes)
            url = f'https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true&expand=false'
            entries = []
            for _ in range(10):
                raw, link = get(url)
                entries.extend(json.loads(raw))
                if 'rel="next"' not in link:
                    break
                url = next(x.split('>')[0].strip().lstrip('<') for x in link.split(',') if 'rel="next"' in x)
                if not url.startswith('https://huggingface.co/api/datasets/'):
                    raise ValueError('unexpected pagination domain')
            else:
                raise ValueError('pagination cap reached')
            (folder / 'tree.json').write_text(json.dumps(entries, indent=2)+'\n')
            receipt = {'repo': repo, 'revision': revision, 'acquired_at': datetime.now(timezone.utc).isoformat(),
                'repository_info_sha256': hashlib.sha256(info_bytes).hexdigest(),
                'tree_sha256': hashlib.sha256((folder / 'tree.json').read_bytes()).hexdigest(),
                'license_release_metadata': info.get('cardData', {}).get('license'),
                'entries': len(entries), 'media_downloaded': False}
            (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
            print(json.dumps(receipt), flush=True)
            print(json.dumps([{'path': e['path'], 'bytes': e.get('size'), 'sha256': e.get('lfs', {}).get('oid')} for e in entries if e['type']=='file']), flush=True)
        except Exception as exc:
            error = {'repo': repo, 'error_type': type(exc).__name__, 'error': str(exc), 'media_downloaded': False}
            (folder / 'error.json').write_text(json.dumps(error, indent=2)+'\n')
            print(json.dumps(error), flush=True)


if __name__ == '__main__':
    main()
