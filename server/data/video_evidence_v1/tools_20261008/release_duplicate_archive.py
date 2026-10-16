"""Release only the verified duplicate transfer tar after full media verification."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone


def main():
    root = Path('/root/autodl-tmp/cvpr27/data/video_evidence_v1')
    output = root / 'operational_20261008'
    audit = json.loads((output / 'receipt.json').read_text())
    assert audit['file_hash_verified'] == audit['row_count'] == 9236
    assert audit['native_pts_checks_passed'] == 9236
    assert audit['archive']['verified'] and audit['sqlite_integrity'] == 'ok'
    archive = root / 'video_evidence_v1_complete.tar'
    assert root.resolve() == root and archive.resolve() == archive
    assert not archive.is_symlink() and archive.is_file()
    expected = '5c6267f99827de3ea7dc26111410c9d6c2dd47facd0c2c4a213eb06aa5900719'
    h = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(chunk)
    assert h.hexdigest() == expected
    assert archive.stat().st_size == 23997983232
    receipt = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'action': 'unlink_verified_duplicate_transfer_archive_only',
        'path': str(archive), 'bytes': archive.stat().st_size, 'sha256': expected,
        'local_recovery_path': 'E:/AAGenvid/external_datasets/video_evidence_v1_remote.tar',
        'local_recovery_sha256_observed_20261008': expected,
        'video_files_revalidated_before_action': 9236,
        'free_bytes_before': shutil.disk_usage(root).free,
        'archive_removed': False,
    }
    destination = output / 'archive_cleanup_receipt.json'
    with destination.open('x', encoding='utf-8') as f:
        json.dump(receipt, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    archive.unlink()
    receipt.update(archive_removed=not archive.exists(), free_bytes_after=shutil.disk_usage(root).free)
    destination.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
