"""Read archived AL32 only; independent Fraction/Decimal checks, no runtime replay."""
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess

MAIN = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN = Path('research-runs/algorithm_search_20260918')
FREEZE = '0685fbf17d16b1a639037924266e1257e0b3abcd'
RESULT = '551b0958e8cc94e2df7294b96f710df587d0b2b0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((SOURCE / RUN / name).read_text(encoding='utf-8'))


def flatten(value):
    if isinstance(value, list):
        return [x for part in value for x in flatten(part)]
    return [value]


def mv(matrix, vector):
    return [sum(a*b for a, b in zip(row, vector)) for row in matrix]


def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def fraction(value):
    return F.from_float(value) if isinstance(value, float) else F(value)


def decimal(value):
    f = fraction(value)
    return D(f.numerator) / D(f.denominator)


def max_error(a, b):
    return max((abs(decimal(x)-decimal(y)) for x, y in zip(flatten(a), flatten(b))), default=D(0))


def diagnostics(rows, params, metric):
    """60-digit direct scalar formula, independent of NumPy kernel implementation."""
    x = [decimal(v) for v in params]
    rows = [[decimal(v) for v in row] for row in rows]
    metric = [[decimal(v) for v in row] for row in metric]
    n = D(len(rows))
    margins = mv(rows, x)
    factors = [1 / (1 + m.exp()) for m in margins]
    curves = [f*(1-f) for f in factors]
    data = sum((1 + (-m).exp()).ln() for m in margins) / n
    mx = mv(metric, x)
    reg = D(1)/6000
    penalty = reg*sum(v*w for v, w in zip(x, mx))
    grad = [-sum(row[j]*f for row, f in zip(rows, factors))/n + 2*reg*mx[j]
            for j in range(12)]
    hess = [[sum(row[j]*row[k]*c for row, c in zip(rows, curves))/n + 2*reg*metric[j][k]
             for k in range(12)] for j in range(12)]
    return {'objective': data+penalty, 'data_term': data, 'penalty': penalty,
            'gradient': grad, 'hessian': hess, 'margins': margins}


def main():
    manifest = load('AL32_artifact_manifest.json')
    frozen = load('AL32_freeze.json')
    evidence = load('AL32_evidence.json')
    inputs = load('AL32_inputs.json')
    config = load('AL32_config.json')
    start = load('AL32_started.json')
    assert manifest['gate_scope'] == evidence['scope'] == 'stable_readout_metric_integration_reference'
    assert evidence['gate_result'] == 'pass' and not evidence['failures']
    assert len(evidence['checks']) == 85 and all(c['passed'] for c in evidence['checks'])
    for rel, record in manifest['files'].items():
        data = (SOURCE/rel).read_bytes()
        assert sha(data) == record['sha256'] and len(data) == record['bytes'], rel
        blob = subprocess.check_output(['git', 'show', RESULT+':'+rel], cwd=SOURCE)
        assert sha(blob) == record['sha256'], rel
    for category in ['inputs', 'historical', 'dependencies']:
        for rel, expected in frozen[category].items():
            assert sha((SOURCE/rel).read_bytes()) == expected, (category, rel)
            if category == 'historical':
                assert sha((MAIN/rel).read_bytes()) == expected, ('main', rel)
    for rel, expected in frozen['inputs'].items():
        assert sha(subprocess.check_output(['git', 'show', FREEZE+':'+rel], cwd=SOURCE)) == expected
    assert start['commit'] == evidence['commit'] == FREEZE
    assert start['freeze_sha256'] == evidence['freeze_sha256'] == sha((SOURCE/RUN/'AL32_freeze.json').read_bytes())
    freeze_time = subprocess.check_output(['git', 'show', '-s', '--format=%cI', FREEZE], cwd=SOURCE, text=True).strip()
    assert datetime.fromisoformat(freeze_time) < datetime.fromisoformat(start['started_at'])
    for rel, expected in frozen['upstream_at_freeze'].items():
        assert sha(Path(rel).read_bytes()) == expected, ('upstream', rel)
    assert load('AL27_evidence.json')['gate_result'] == 'fail'
    assert load('AL30_evidence.json')['gate_result'] == 'pass'

    # Check identities against original archive, not just a self-consistent copy.
    original_fields = {c['id']: c['result'] for c in load('AL25_evidence.json')['cases'] if 'result' in c}
    field_diagnostics = []
    weights = [float(F(v)) for v in config['weights']]
    assert weights == [1., -2., .5, 0.]
    for chosen, actual in zip(inputs['archived_fields'], evidence['archived_field_processing']):
        assert chosen['id'] == actual['id']
        original = original_fields[chosen['id']]
        assert chosen['q4_direct'] == original['q4_direct']
        assert chosen['q4_compact_raw'] == original['q4_compact_raw']
        for selected, rec, old in zip(chosen['filters'], actual['filters'], original['filters']):
            assert selected['filter'] == rec['filter'] == old['filter']
            for key, value in selected.items():
                if key == 'expected_q_hex':
                    assert value == old['q_direct'].hex()
                elif key == 'filtered_fields':
                    assert all(value[k] == old[key][k] for k in value)
                else:
                    assert value == old[key], (chosen['id'], key)
            arrays = [flatten(selected['filtered_fields'][key]) for key in ['d_a', 'd_b', 'K']]
            assert all(len(v) == 54 for v in arrays)
            a, b, k = [[F.from_float(v) for v in values] for values in arrays]
            summed = [x+y for x, y in zip(a, b)]
            denominator = F.from_float(old['D'])
            expected = [sum(v*v for v in summed)/54/denominator,
                        F.from_float(old['q_direct']), sum(x*y for x, y in zip(summed, k))/54/denominator]
            assert rec['D'].hex() == old['D'].hex()
            assert rec['stable']['r_hex'][1] == old['q_direct'].hex()
            assert all(abs(float(x)-y) <= 1e-12 for x, y in zip(expected, rec['stable']['r']))
            assert flatten(rec['stable']['s_H']) == [float(v) for v in summed]
            assert rec['raw']['C'] == old['C'] and rec['raw']['q_compact_raw'] == old['q_compact_raw']
        score = 0.
        for w, q in zip(weights, original['q4_direct']):
            score += w*q
        assert score.hex() == actual['candidate_four_score']['hex'] == actual['stable_four_score']['hex']
        field_diagnostics.append({'id': chosen['id'], 'score_hex': score.hex(), 'q_hex_reuses': 4})

    # Exact change of coordinates; separate 60-digit derivative calculation.
    M = [[F(v) for v in row] for row in config['M']]
    inverse = [[F(v) for v in row] for row in config['M_inverse']]
    assert mm(M, inverse) == mm(inverse, M) == [[F(i == j) for j in range(3)] for i in range(3)]
    B = [[F(v) for v in row] for row in config['B']]
    Bt = [list(row) for row in zip(*B)]
    G = mm(B, Bt)
    assert G == config['expected_BBt']
    identity = [[F(i == j) for j in range(12)] for i in range(12)]
    originals = [p for p in load('AL30_inputs.json')['panels'] if p['name'] in ['aligned','full_rank','symmetric']]
    assert originals == inputs['abstract_panels']
    assert [p['name'] for p in originals] == ['aligned','full_rank','symmetric']
    result_points = []
    with localcontext() as ctx:
        ctx.prec = 60
        for panel, record in zip(originals, evidence['abstract_fixed_point_processing']):
            assert panel['name'] == record['name'] and panel['case_role'] == 'known_regression'
            plus, minus = [[[F(v) for v in row] for row in panel[k]] for k in ['plus', 'minus']]
            dz = [[a-b for a,b in zip(p,m)] for p,m in zip(plus,minus)]
            dr = [mv(B, row) for row in dz]
            assert max_error(record['delta_z'], dz) == max_error(record['delta_r'], dr) == 0
            for point, configured in zip(record['points'], config['points']):
                gamma = [F(v) for v in configured['gamma']]
                beta = mv(Bt, gamma)
                assert beta == [F(v) for v in configured['expected_beta']]
                assert mv(dz, beta) == mv(dr, gamma)
                penalty = F(1,6000)*sum(v*v for v in beta)
                assert penalty == F(configured['expected_penalty']) == F(1,6000)*sum(v*w for v,w in zip(gamma,mv(G,gamma)))
                for coordinate, rows, params, metric in [('beta', dz, beta, identity), ('gamma', dr, gamma, G)]:
                    computed = diagnostics(rows, params, metric)
                    archived = point[coordinate+'_evaluation']
                    errors = {key: max_error(archived[key], value) for key,value in computed.items()}
                    assert max(errors.values()) <= D('1e-12'), (panel['name'], point['name'], coordinate, errors)
                    result_points.append({'panel':panel['name'], 'point':point['name'], 'coordinate':coordinate,
                                          'decimal_max_error': str(max(errors.values()))})
    for name in ['optimizer_calls','old_readout_calls','probe_calls','AE_calls','filtering_calls']:
        assert evidence['calls'][name] == 0
    assert evidence['calls']['fixed_objective_evaluations'] == 12
    assert evidence['resources']['max_array_bytes'] == 1152
    assert evidence['resources']['native_threads_before'] == evidence['resources']['native_threads_after'] == 2
    assert evidence['real_AE_error_bound'] is None and not evidence['scientific_innovation_gate_passed']
    result = {'task_id':'AL32','reviewer':'planagent','reviewed_at':datetime.now(timezone.utc).isoformat(),
              'gate_result':'pass','gate_scope':evidence['scope'],'manifest_files_verified':len(manifest['files']),
              'historical_files_verified_in_both_roots':len(frozen['historical']),
              'dependencies_verified':len(frozen['dependencies']), 'freeze_inputs_verified':len(frozen['inputs']),
              'upstream_at_freeze_verified':len(frozen['upstream_at_freeze']),
              'freeze_commit':FREEZE,'result_commit':RESULT,'archived_checks':85,
              'field_diagnostics':field_diagnostics,'decimal_fixed_point_diagnostics':result_points,
              'source_or_model_replayed':False,'formal_independent_scientific_review':False,
              'real_efficacy_or_breakthrough':False,'old_AL27_gate_result':'fail',
              'audit_source_sha256':sha(Path(__file__).read_bytes())}
    path=Path(__file__).with_name('AL32_ARCHIVE_REVIEW_20260919.json')
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
    print(json.dumps({'gate_result':'pass','manifest_files':len(manifest['files']),
                      'historical_files':len(frozen['historical']), 'fixed_point_diagnostics':len(result_points)}))


if __name__ == '__main__':
    main()
