"""One frozen AL65 batch with exact evidence. Stdlib only."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc
import traceback

from selection_controls import selected_law, auc, match_z, marginal_z, inverse_probability

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encoded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='run_v1')
    args = parser.parse_args()
    output = HERE / args.output
    if output.exists():
        raise RuntimeError('Output already exists; refusing a silent rerun/overwrite')
    freeze = json.loads((HERE / 'freeze.json').read_bytes())
    for item in freeze['files']:
        if digest(HERE / item['path']) != item['sha256']:
            raise RuntimeError('Frozen source/input changed: ' + item['path'])
    for item in freeze['protected_inputs']:
        if digest(Path(item['absolute_path'])) != item['sha256']:
            raise RuntimeError('Protected historical input changed: ' + item['absolute_path'])
    output.mkdir()
    began = datetime.now(timezone.utc).isoformat()
    wall, cpu = time.perf_counter(), time.process_time()
    tracemalloc.start()
    config = json.loads((HERE / 'cases.json').read_bytes())
    refs = json.loads((HERE / 'reference.json').read_bytes())['cases']
    cells = tuple(tuple(v) for v in config['cell_order'])
    base = tuple(F(x) for x in config['base_conditional'])
    if len(set(cells)) != 6 or len(base) != 6 or sum(base) != 1:
        raise ValueError('Unexpected fixed support')
    scores = {'f_Z': tuple(abs(z) for z, _ in cells), 'f_Q': tuple(int(q == 1) for _, q in cells)}
    case_results, checks, errors = [], [], []
    def check(name, actual, expected):
        checks.append({'name': name, 'actual': encoded(actual), 'expected': encoded(expected), 'passed': actual == expected})
    for cfg in config['cases']:
        name = cfg['id']
        try:
            ref = refs[name]
            s0, s1 = (tuple(F(x) for x in cfg[k]) for k in ('s0', 's1'))
            retain0, mass0, law0 = selected_law(base, s0)
            retain1, mass1, law1 = selected_law(base, s1)
            zmatch = match_z(cells, law0, law1)
            ipw0, ipw1 = inverse_probability(law0, s0, cells), inverse_probability(law1, s1, cells)
            observed = {k: auc(law0, law1, sc) for k, sc in scores.items()}
            matched = {k: auc(zmatch['matched0'], zmatch['matched1'], sc) for k, sc in scores.items()}
            can_recover = ipw0['recovered_law'] is not None and ipw1['recovered_law'] is not None
            recovered_auc = ({k: auc(ipw0['recovered_law'], ipw1['recovered_law'], sc) for k, sc in scores.items()} if can_recover else None)
            joint_total = (retain0 + retain1) / 2
            rows = []
            for i, (z, q) in enumerate(cells):
                rows.append({'Z': z, 'Q': q, 'base_given_Y0': base[i], 'base_given_Y1': base[i],
                    'selection0': s0[i], 'selection1': s1[i], 'selected_unnormalized0': mass0[i], 'selected_unnormalized1': mass1[i],
                    'observed_given_Y0': law0[i], 'observed_given_Y1': law1[i],
                    'observed_joint_Y0': mass0[i]/(2*joint_total), 'observed_joint_Y1': mass1[i]/(2*joint_total),
                    'matched_given_Y0': zmatch['matched0'][i], 'matched_given_Y1': zmatch['matched1'][i],
                    'ipw_given_Y0': ipw0['recovered_law'][i] if ipw0['recovered_law'] is not None else None,
                    'ipw_given_Y1': ipw1['recovered_law'][i] if ipw1['recovered_law'] is not None else None})
            case_results.append({'id': name, 'rows': rows, 'retention': [retain0, retain1],
                'observed_class_prior': [retain0/(2*joint_total), retain1/(2*joint_total)],
                'observed_auc': observed, 'Z_matching': zmatch, 'matched_auc': matched,
                'oracle_IPW': [ipw0, ipw1], 'oracle_IPW_auc': recovered_auc})
            check(name + '/retention', [retain0, retain1], [F(v) for v in ref['retention']])
            for y, law in enumerate((law0, law1)):
                check(name + f'/observed_mass_Y{y}', sum(law), F(1))
            check(name + '/joint_mass', sum(row['observed_joint_Y0'] + row['observed_joint_Y1'] for row in rows), F(1))
            check(name + '/overlap_Z', zmatch['overlap_mass'], F(ref['overlap_mass_Z']))
            check(name + '/outside_common_support_Y1', zmatch['outside1'], F(ref['Y1_mass_outside_common_Z']))
            check(name + '/matched_Z_marginals', marginal_z(cells, zmatch['matched0']), marginal_z(cells, zmatch['matched1']))
            for y, law in enumerate((zmatch['matched0'], zmatch['matched1'])):
                check(name + f'/matched_mass_Y{y}', sum(law), F(1))
            for z, gap in zmatch['conditional_Q1_gap'].items():
                check(name + f'/Q1_gap_given_Z{z}', gap, F(ref['conditional_Q_gap']))
            for j, score in enumerate(scores):
                check(name + '/observed_' + score, observed[score], F(ref['observed_auc'][j]))
                check(name + '/matched_' + score, matched[score], F(ref['matched_auc'][j]))
                # This reference uses binary score marginals rather than the pairwise AUC implementation.
                r0 = sum(p for p, s in zip(law0, scores[score]) if s == 1)
                r1 = sum(p for p, s in zip(law1, scores[score]) if s == 1)
                check(name + '/binary_marginal_' + score, observed[score], F(1,2)+(r1-r0)/2)
            check(name + '/full_IPW_identifiability', can_recover, ref['ipw_full_population_identifiable'])
            for y, ipw in enumerate((ipw0, ipw1)):
                if ipw['recovered_law'] is not None:
                    check(name + f'/full_IPW_law_Y{y}', ipw['recovered_law'], base)
            if can_recover:
                for k, val in recovered_auc.items(): check(name + '/IPW_' + k, val, F(1,2))
            else:
                check(name + '/IPW_unavailable_score_is_null', recovered_auc, None)
            if s0 == s1:
                check(name + '/same_selection_same_observed_law', law0, law1)
        except Exception as exc:
            errors.append({'case': name, 'error': repr(exc), 'traceback': traceback.format_exc()})
    check('all_five_cases_delivered', [x['id'] for x in case_results], [x['id'] for x in config['cases']])
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    posthashes = {x['path']: digest(HERE/x['path']) for x in freeze['files']}
    check('frozen_sources_unchanged', posthashes, {x['path']: x['sha256'] for x in freeze['files']})
    protected_after = {x['absolute_path']: digest(Path(x['absolute_path'])) for x in freeze['protected_inputs']}
    check('historical_inputs_unchanged', protected_after, {x['absolute_path']: x['sha256'] for x in freeze['protected_inputs']})
    good = not errors and all(x['passed'] for x in checks)
    evidence = {'task_id': 'AL65', 'protocol': config['protocol'], 'executor': 'planagent_fallback',
        'started_at_utc': began, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable] + sys.argv, 'python': sys.version, 'platform': platform.platform(),
        'freeze_sha256': digest(HERE/'freeze.json'), 'frozen_inputs': freeze['files'],
        'cases': case_results, 'checks': checks, 'errors': errors, 'software_pass': good,
        'resources': {'wall_seconds': time.perf_counter()-wall, 'process_cpu_seconds': time.process_time()-cpu,
            'measured_python_alloc_peak_bytes_during_batch': peak, 'largest_law_cell_count': len(cells),
            'pair_terms_per_auc': len(cells)**2, 'OMP_NUM_THREADS': os.environ.get('OMP_NUM_THREADS'),
            'network_requests': 0, 'server_calls': 0, 'model_calls': 0, 'media_reads': 0,
            'classifier_fits': 0, 'dense_numeric_arrays': False},
        'limits': ['Hand-labelled finite-population arithmetic only, not real detection AUROC',
                   'Inverse selection probabilities are oracle inputs; do not assume them for actual datasets',
                   'Support-restricted matching does not restore unobserved source mass',
                   'No new algorithm or OR1 innovation/efficacy accepted; independent review pending']}
    (output/'evidence.json').write_text(json.dumps(encoded(evidence), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    summary = {'task_id': 'AL65', 'software_pass': good, 'checks': len(checks),
               'failed_checks': [x['name'] for x in checks if not x['passed']], 'errors': errors,
               'case_aucs': [{'id': x['id'], 'observed': encoded(x['observed_auc']), 'matched': encoded(x['matched_auc'])} for x in case_results]}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary))
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
