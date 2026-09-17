"""Offline evidence checks: stdlib only; never imports downloaded author code."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research-runs/shared_plan_20260917'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    a = [(0, 1, 2), (1, 2, 3), (2, 3, 4), (3, 4, 5), (0, 2, 4), (1, 3, 5)]
    designs = {'A': (6, a), 'B': (6, a[-2:]), 'C': (3, [(0, 1, 2)])}
    counts = {}
    for name, (frames, triples) in designs.items():
        degrees = Counter(i for triple in triples for i in triple)
        pairs = {(x, y) for x, m, z in triples for x, y in [(x, m), (m, z), (x, z)]}
        weights = [Fraction(degrees[i], 3 * len(triples)) for i in range(frames)]
        assert sum(weights) == 1
        counts[name] = dict(frame_roles=[degrees[i] for i in range(frames)],
            role_specific=[[sum(t[j] == i for t in triples) for i in range(frames)] for j in range(3)],
            static_weights=[str(w) for w in weights],
            temporal_affinities=len(pairs), static_affinities=frames,
            temporal_compositions=len(triples)*13, static_compositions=frames*13)
    assert counts['A']['frame_roles'] == [2, 3, 4, 4, 3, 2]
    assert counts['A']['temporal_affinities'] == 11
    assert counts['B']['temporal_affinities'] == 6
    assert counts['C']['temporal_affinities'] == 3
    assert counts['B']['static_weights'] == ['1/6']*6
    assert counts['C']['static_weights'] == ['1/3']*3
    # Exact algebra: identical coefficient D/2+p0, check the constant offsets.
    a_odd_offsets = [-Fraction(3, 4)+Fraction(i, 4) for i in (1, 3, 5)]
    assert a_odd_offsets == [Fraction(-1, 2), Fraction(0), Fraction(1, 2)]
    contract = json.loads((RUN/'pts_acquisition_contract_draft.json').read_text(encoding='utf-8'))
    assert contract['execution_authorized'] is False
    assert contract['executed_this_round'] is False
    assert contract['approved_by'] is None and contract['approval_receipt'] is None
    assert contract['budget']['approved_batch_max_cny'] is None
    assert contract['acceptance_scope']['formal_gate_released'] is False
    assert contract['operations']['gpu_kernels_allowed'] is False
    assert contract['inputs']['final_confirmation_set_allowed'] is False
    source = json.loads((RUN/'round2_author_sources.json').read_text())
    selection = json.loads((RUN/'round2_source_selection.json').read_text())
    checked = 0
    total_bytes = 0
    for repo, record in source['repositories'].items():
        assert len(record['commit']) == 40
        assert {x['path'] for x in record['inspected_files']} == set(selection[repo])
        for item in record['inspected_files']:
            data = Path(item['local_cache']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == item['sha256']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == item['git_blob_sha1']
            checked += 1
            total_bytes += len(data)
    assert checked == 38
    old_pts = RUN/'joint_lag_feasibility.json'
    assert digest(old_pts) == '0b81cf16ad18925c755ffc1406d806e3edff5ab28f0da9ec9fca1898f49f41e7'
    files = [ROOT/'research-plan/SAMPLING_REVISION_PROPOSAL_20260917.md',
        ROOT/'research-plan/STATIC_CONTROL_FAIRNESS_20260917.md',
        ROOT/'research-plan/LOCAL_COMPOSABILITY_PRIOR_ART.md',
        RUN/'pts_acquisition_contract_draft.json', RUN/'round2_author_sources.json',
        RUN/'round2_source_selection.json', Path(__file__),
        ROOT/'research-runtime/review_author_sources.py']
    report = dict(dispatch_id='cc-round-2-offline-20260917',
        checked_utc=datetime.now(timezone.utc).isoformat(),
        scope='offline_arithmetic_contract_and_digest_validation_not_scientific_review',
        passed=True, design_counts=counts, centered_targets_equal_A_135_algebraically=True,
        author_files_verified=checked, author_source_bytes=total_bytes,
        author_code_executed=False, real_video_sampled=False, server_accessed=False,
        models_or_datasets_downloaded=False, new_gpu_job=False,
        scientific_gate_passed=False, pts_contract_execution_authorized=False,
        artifacts={str(p.relative_to(ROOT)).replace('\\','/'): digest(p) for p in files},
        shared_state_read_only_hashes={str(p.relative_to(ROOT)).replace('\\','/'):digest(p)
            for p in [ROOT/'research-plan/WORK_PLAN.md',ROOT/'research-plan/task-hermes/project.json']})
    (RUN/'round2_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['passed','author_files_verified','author_source_bytes','scope']}))


if __name__ == '__main__':
    main()
