"""Read AL40 archive, compute its four fixed responses using Gaussian integers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'research-plan/reviews'
ORDER = ROOT / 'research-plan/AL41_FIXED_KERNEL_CORRECTION_AUDIT_20260919.md'
OLD_JSON = REVIEW / 'AL40_FIXED_KERNEL_PHASE_RESPONSE_EXACT_20260919.json'
OLD_MD = REVIEW / 'AL40_FIXED_KERNEL_PHASE_RESPONSE_REVIEW_20260919.md'
OUTPUT = REVIEW / 'AL41_FIXED_KERNEL_CORRECTION_20260919.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mul(a, b):
    x, y = a
    u, v = b
    return x*u-y*v, x*v+y*u


def power(z, n):
    result = (1, 0)
    for _ in range(n):
        result = mul(result, z)
    return result


def response(coefficients, z):
    real = imag = 0
    terms = []
    for r, a in enumerate(coefficients):
        z_power = power(z, r)
        term = (a*z_power[0], a*z_power[1])
        real += term[0]
        imag += term[1]
        terms.append({'r': r, 'coefficient': a, 'z_power': z_power, 'term': term})
    return (real, imag), terms


def main():
    assert not OUTPUT.exists(), 'Preserve prior review output; no overwrite'
    started = datetime.now(timezone.utc).isoformat()
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [ORDER, OLD_JSON, OLD_MD, Path(__file__)]}
    assert hashes[str(OLD_JSON.relative_to(ROOT))] == '0ab481133e71560ce9b87f16bed461c229b3da917da3f68283f03ad5d3bd8699'
    original = json.loads(OLD_JSON.read_text(encoding='utf-8'))
    assert original['fixed_stride'] == 4
    assert original['frequencies'] == {'omega': 'pi', 'alias': '3pi/2', 'alias_offset': '2pi/s'}
    root1, root2 = (-1, 0), (0, -1)
    assert power(root1, 4) == power(root2, 4) == (1, 0)
    # Four responses only; closed forms use separately expanded degree2 polynomials.
    kernels = [('a_equal_111', (1, 1, 1)), ('a_diff_10m1', (1, 0, -1))]
    rows = []
    for name, coefficients in kernels:
        first, terms1 = response(coefficients, root1)
        second, terms2 = response(coefficients, root2)
        if name == 'a_equal_111':
            assert first == (1-1+1, 0) and second == (1-1, -1)
        else:
            assert first == (1-1, 0) and second == (1-(-1), 0)
        rows.append({'kernel': name, 'coefficients_r0_r1_r2': coefficients,
                     'first_response': first, 'alias_response': second,
                     'first_terms': terms1, 'alias_terms': terms2,
                     'complex_equal': first == second,
                     'first_power': first[0]**2+first[1]**2,
                     'alias_power': second[0]**2+second[1]**2,
                     'old_claim': original['kernels'][name]})
    assert rows[0]['first_power'] == rows[0]['alias_power'] == 1
    assert rows[1]['first_power'] == 0 and rows[1]['alias_power'] == 4
    assert all(not row['complex_equal'] for row in rows)
    al39 = json.loads((REVIEW/'AL39_FEATURE_CONTAINMENT_EXACT_20260919.json').read_text(encoding='utf-8'))
    al39_note = {'declared_check_categories': len(al39['checks']),
                'field_records': len(al39['field_checks']),
                'fixed_weight_vectors': len(al39['fixed_weight_checks']),
                'reported_count_15_supported_as_explicit_archive_categories': False,
                'runtime_replayed': False,
                'scope': 'Archive count only; no new numerical evidence beyond AL29/AL32 is claimed.'}
    for rel, digest in hashes.items():
        assert sha(ROOT/rel) == digest
    result = {'task_id': 'AL41', 'started_at': started, 'completed_at': datetime.now(timezone.utc).isoformat(),
              'source_commit_at_execution': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'gate_scope': 'correction_of_fixed_kernel_arithmetic', 'review_computation_result': 'pass',
              'AL40_review_verdict': 'fail', 'old_AL40_files_preserved': True,
              'hashes': hashes, 'tap_indexing': [0,1,2], 'roots': {'exp_i_pi':root1,'exp_i_3pi_over2':root2},
              'pure_sampling_factor_both': (1,0), 'computed_responses': rows,
              'AL40_false_claims': ['H_10m1(pi)=2', 'H_10m1(pi)=H_10m1(3pi/2)', 'difference kernel retains this exact complex-output alias'],
              'correct_interpretation': 'Both selected kernels distinguish the fixed known unit-amplitude complex exponentials. The111 kernel has equal power at the two frequencies; the10m1 kernel has powers0 and4. No alternate frequency or kernel selected.',
              'AL39_report_count_note': al39_note,
              'independent_scientific_review': False,
              'resources': {'gaussian_integer_arithmetic': True, 'fixed_kernel_frequency_evaluations':4,
                            'model_calls':0, 'media_access':False,'training_calls':0,'server_calls':0,'gpu_calls':0}}
    with OUTPUT.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
    print(json.dumps({'AL40_verdict':'fail','111_response':[[1,0],[0,-1]],
                      '10m1_response':[[0,0],[2,0]],'source_files_unchanged':True}))


if __name__ == '__main__':
    main()
