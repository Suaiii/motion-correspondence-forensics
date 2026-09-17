"""Read existing server timestamps to test nominal-grid and half-second support."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forensics.lag_support import support_report


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    parent=a.base/'runs/paired_dino_time_v1';cache=a.base/'runs/time_matched_dino_v1'
    extra=a.base/'runs/pair2_frozen_transfer_v2'
    for folder in (parent,extra):
        for rel,digest in read(folder/'artifact_hashes.json').items():
            if rel in ('manifest.json','accepted_manifest.json','protocol.json'):
                assert sha(folder/rel)==digest
    assert sha(cache/'lock.json')==read(parent/'protocol.json')['time_cache_lock_sha256']
    rows=[]
    for r in read(parent/'manifest.json'):
        key=hashlib.sha256(r['sample_id'].encode()).hexdigest()
        timed=read(cache/'records'/(key+'.json'))
        assert timed['status']=='ok' and timed['sha256']==r['sha256']
        rows.append(dict(r,sampling=timed['sampling']))
    for r in read(extra/'accepted_manifest.json'):
        rows.append(dict(r,role='external_development'))
    protocol=dict(script_sha256=sha(__file__),core_sha256=sha(Path(__file__).resolve().parents[1]/'forensics/lag_support.py'),
        parent_manifest_sha256=sha(parent/'manifest.json'),external_manifest_sha256=sha(extra/'accepted_manifest.json'),
        views=['all_adjacent','half_second'],quanta_seconds=[.001,.002,.005],
        half_second_indices=[0,4],half_second_target=.5,half_second_tolerance=.002,
        classification_performed=False,final_access=False,
        scope='descriptive support census; not a confirmatory cohort or algorithm result')
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    reports=[]
    for view in protocol['views']:
        for quantum in protocol['quanta_seconds']:
            report,annotated=support_report(rows,view,quantum)
            reports.append(report)
            if view=='half_second' and quantum==.002:
                (a.output/'half_second_records.json').write_text(json.dumps(annotated,indent=2)+'\n')
    (a.output/'report.json').write_text(json.dumps(dict(complete=True,rows=len(rows),audits=reports,formal_claim_released=False),indent=2)+'\n')
    (a.output/'artifact_hashes.json').write_text(json.dumps({p.name:sha(p) for p in a.output.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps(reports,indent=2),flush=True)


if __name__=='__main__':
    main()
