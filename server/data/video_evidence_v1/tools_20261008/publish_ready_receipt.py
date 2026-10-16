"""Publish a convenient alias and compact receipt after both inventories verify."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    v1=Path('/srv/video_evidence_v1').resolve()
    extension=Path('/root/autodl-tmp/cvpr27/data/video_evidence_expansion_20261008/range_subset_v1')
    old=json.loads((v1/'operational_20261008/receipt.json').read_text())
    new=json.loads((extension/'operational/receipt.json').read_text())
    recovered=json.loads((extension/'receipt.recovered.json').read_text())
    features=json.loads((v1/'operational_20261008/feature_verification.json').read_text())
    assert old['file_hash_verified']==9236 and new['file_sha256_reverified']==3000
    assert new['qc_status_counts']=={'qc_pass':2999,'qc_excluded':1}
    assert not new['duplicate_of_v1_count'] and not new['duplicate_hash_groups']
    assert features['feature_checks_passed']==4425 and features['quality_selection_exactly_matches_valid_features']
    alias=Path('/srv/video_evidence_v1_extension')
    if alias.exists() or alias.is_symlink():
        assert alias.resolve()==extension
    else:
        alias.symlink_to(extension,target_is_directory=True)
    disk=shutil.disk_usage(v1)
    receipt={'created_at':datetime.now(timezone.utc).isoformat(),
        'endpoint':{'host':'connect.westc.seetacloud.com','port':22647,'user':'root','authentication':'existing SSH key verified'},
        'v1_root':str(v1),'v1_alias':'/srv/video_evidence_v1','extension_root':str(extension),'extension_alias':str(alias),
        'v1_files':9236,'extension_files':3000,'total_media_files':12236,
        'unique_media_sha256_total':old['unique_file_sha256_count']+new['unique_file_sha256_count'],
        'clean_files_total_including_rejected':old['clean_rows']+3000,'derived_files_total':old['derived_rows'],
        'extension_quality_pass':2999,'extension_quality_rejected':1,'existing_verified_feature_cache':4425,
        'v1_media_bytes':old['total_video_bytes'],'extension_media_bytes':recovered['media_bytes'],
        'duplicate_transfer_tar_removed':not (v1/'video_evidence_v1_complete.tar').exists(),
        'disk_total_bytes':disk.total,'disk_free_bytes':disk.free,'disk_free_gib':round(disk.free/1024**3,3),
        'scientific_gate_passed':False,'independent_scientific_review_completed':False,'new_model_training_performed':False,
        'evidence_sha256':{'v1_receipt':sha(v1/'operational_20261008/receipt.json'),
            'extension_receipt':sha(extension/'operational/receipt.json'),'feature_verification':sha(v1/'operational_20261008/feature_verification.json'),
            'extension_effective_manifest':sha(extension/'manifest.recovered.jsonl')},
        'important_limits':['v1 has 400 byte-identical OSN/WhatsApp duplicate pairs',
            'v1 has 31 unresolved propagation receipts and unverified ancestry/licensing fields',
            'extension per-file CRC/SHA verified; full upstream archive SHA not computed',
            'extension release metadata and filename groups are not per-sample provenance or camera-origin proof',
            'no uniform physical-time/resolution propagation protocol or independent scientific review completed']}
    (v1/'operational_20261008/cloud_ready_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
