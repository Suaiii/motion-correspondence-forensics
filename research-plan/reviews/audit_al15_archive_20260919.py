"""Read-only AL15 archive audit; stdlib exact arithmetic, no candidate imports."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('E:/aNB/TECH/脉冲神经网络')
SOURCE = Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN = Path('research-runs/algorithm_search_20260918')
OUT = ROOT / 'research-plan/reviews/AL15_ARCHIVE_REVIEW_20260919.json'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def read(name):
    return json.loads((SOURCE / RUN / name).read_text(encoding='utf-8'))

def git(*args):
    return subprocess.check_output(['git', *args], cwd=SOURCE)

def vf(values):
    return [F(v) for v in values]

def probe(spec, x):
    kind = spec['kind']
    if kind == 'linear':
        return [sum(F(a) * b for a, b in zip(row, x)) for row in spec['matrix']]
    if kind == 'translation':
        return [a + F(b) for a, b in zip(x, spec['offset'])]
    y = x.copy()
    i, j = spec['active_slots']
    if kind == 'nonlinear_a':
        y[j] += x[i] ** 2
    elif kind == 'nonlinear_b':
        y[i] += x[j]
    else:
        raise AssertionError(kind)
    return y

def mix(x, y, h):
    return [(1-h)*a+h*b for a,b in zip(x,y)]

def eq_vector(got, want):
    assert vf(got) == want, (got, [str(v) for v in want])

def main():
    assert not OUT.exists(), 'Do not overwrite earlier audit'
    manifest = read('AL15_artifact_manifest.json')
    lock = read('AL15_freeze.json')
    inputs = read('AL15_inputs.json')
    evidence = read('AL15_evidence.json')
    sha_checked = []
    for item in manifest['files']:
        raw = (SOURCE/item['path']).read_bytes()
        assert len(raw) == item['bytes'] and digest(raw) == item['sha256']
        sha_checked.append(item['path'])
    for name, expected in lock['files'].items():
        assert digest((SOURCE/name).read_bytes()) == expected
        assert digest(git('show', 'f897e0c:'+name)) == expected
    for name, expected in lock['preserved'].items():
        assert digest((SOURCE/name).read_bytes()) == expected
    for name, expected in lock['dependency_files'].items():
        assert digest(Path(name).read_bytes()) == expected
    assert digest((SOURCE/RUN/'AL15_freeze.json').read_bytes()) == evidence['freeze_sha256']
    assert git('rev-parse','f897e0c').decode().strip() == evidence['git_revision']
    subprocess.check_call(['git','merge-base','--is-ancestor','f897e0c','7f93f8c'],cwd=SOURCE)
    assert not evidence['failures'] and not evidence['scientific_breakthrough']
    records, rows, ledger = inputs['records'], evidence['evaluations'], evidence['call_ledger']
    assert len(records) == len(rows) == 210
    seen_calls = set()
    for index, (record, row) in enumerate(zip(records, rows)):
        assert record['id'] == row['id'] and row['input_index'] == index
        assert row['status'] == 'pass' and all(row['checks'].values())
        x, h = vf(record['x']), F(record['h'])
        a, b = record['operators']
        ra, rb = probe(a,x), probe(b,x)
        pa, pb = mix(x,ra,h), mix(x,rb,h)
        rapb, rbpa = probe(a,pb), probe(b,pa)
        eab, eba = mix(pb,rapb,h), mix(pa,rbpa,h)
        k = [(u-v)/(h*h) for u,v in zip(eab,eba)]
        va, vb = [u-v for u,v in zip(ra,x)], [u-v for u,v in zip(rb,x)]
        result = row['result']
        for name, want in dict(x=x,ra=ra,rb=rb,pa=pa,pb=pb,ra_pb=rapb,rb_pa=rbpa,
                               endpoint_ab=eab,endpoint_ba=eba,K=k,v_a=va,v_b=vb).items():
            eq_vector(result[name],want)
        assert k == [F(t) for t in record['expected']['K_exact']]
        for name, values in dict(K=k,a=va,b=vb,input=x).items():
            energy = sum(v*v for v in values)
            assert F(result['energy_sum'][name]) == energy
            assert abs(result['energy_mean'][name]-float(energy/len(x))) <= 1e-10
        ek = sum(v*v for v in k)
        den = sum(v*v for v in va+vb)
        exact_q = ek/(den+len(x)*F('1e-12'))
        assert abs(result['q_mean_fixed_eta']-float(exact_q)) <= 1e-10
        ids = result['call_ids']
        assert len(ids) == 4 and result['successful_core_calls'] == 4
        calls = [ledger[i-1] for i in ids]
        assert not (seen_calls & set(ids))
        seen_calls.update(ids)
        for call, spec, xx, yy, node, parent in zip(calls,[a,b,a,b],[x,x,pb,pa],[ra,rb,rapb,rbpa],
                  ['Ra_x','Rb_x','Ra_Pb','Rb_Pa'],['input','input','Pb','Pa']):
            assert call['purpose']=='core' and call['status']=='returned'
            assert call['probe']==spec['name'] and call['node']==node and call['parent']==parent
            assert call['evaluation_id']==f'evaluation_{index:04}'
            assert call['support']==record['support'] and call['soft_step']==record['h']
            assert call['received_fields']==['vector','cache','support']
            assert call['cache_initial']=={'history':[]} and call['cache_identity_unique']
            assert call['cache_after']=={'history':['one_mock_call']}
            eq_vector(call['input'],xx); eq_vector(call['output'],yy)
    counts = dict(Counter(r['purpose'] for r in ledger))
    assert counts == {'core':840,'contract_negative':4,'diagnostic_repeat':6}
    assert len(ledger)==850 and [r['call_id'] for r in ledger]==list(range(1,851))
    for key in ('negative_contracts','repeat_diagnostics','source_label_contracts'):
        assert all(r['passed'] for r in evidence[key])
    assert len(evidence['negative_contracts'])==10 and len(evidence['repeat_diagnostics'])==3
    assert len(evidence['source_label_contracts'])==5
    assert len(evidence['distribution_checks'])==15
    assert all(r['same_empirical_output_multiset'] for r in evidence['distribution_checks'])
    summary = dict(task_id='AL15',reviewer='planagent',observed_at=datetime.now(timezone.utc).isoformat(),
        source_worktree=str(SOURCE),source_result_commit=git('rev-parse','7f93f8c').decode().strip(),
        source_freeze_commit=evidence['git_revision'],status='pass_archival_exact_trace_review',
        scope='Hashes, source review, exact arithmetic reconstruction from archived input/trace; not independent scientific replication',
        manifest_files_verified=len(sha_checked),frozen_source_input_blobs_verified=len(lock['files']),
        preserved_artifacts_verified=len(lock['preserved']),dependency_hashes_verified=len(lock['dependency_files']),
        exact_trace_evaluations=210,call_counts=counts,total_calls=850,
        family_counts=dict(Counter(r['family'] for r in records)),
        steps=sorted(set(r['h'] for r in records)),
        pending=['actual four filters','matching and trained readout','real probe wrappers/checkpoints/clock',
                 'numerical uncertainty contract','scientific innovation and real detection evidence'],
        audit_candidate_imports=False,audit_candidate_calls=0,audit_numpy_imported=False,
        server_or_media_or_gpu=False,
        qualification='Archive assertions do not prove process chronology beyond recorded freeze commit or object identity beyond reviewed implementation',
        source_evidence_sha256=digest((SOURCE/RUN/'AL15_evidence.json').read_bytes()),
        audit_source_sha256=digest(Path(__file__).read_bytes()))
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
