"""Execute exactly the AL30 frozen batch; refuse output overwrite or source drift."""
import os
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
    os.environ[_key] = '2'
import ctypes
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'research-runs/algorithm_search_20260918'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT/('AL30_'+name+'.json')).read_text(encoding='utf-8'))


def save(name, data):
    with (OUT/('AL30_'+name+'.json')).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def read_old_gate():
    return json.loads((OUT/'AL27_evidence.json').read_text(encoding='utf-8'))['gate_result']


def main():
    if (OUT/'AL30_evidence.json').exists() or (OUT/'AL30_started.json').exists():
        raise RuntimeError('batch already started: never silently rerun')
    frozen = read('freeze')
    for category in ['inputs','dependencies','historical']:
        for relative, digest in frozen[category].items():
            assert sha(ROOT/relative) == digest, (category, relative)
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(), 'commit first'
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for relative in [*frozen['inputs'], 'research-runs/algorithm_search_20260918/AL30_freeze.json']:
        blob = subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == sha(ROOT/relative), ('uncommitted_freeze',relative)
    save('started', dict(commit=commit, started_at=datetime.now(timezone.utc).isoformat(),
                         freeze_sha256=sha(OUT/'AL30_freeze.json'), batch='single_fixed_batch'))
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    evidence = dict(commit=commit, freeze_sha256=sha(OUT/'AL30_freeze.json'), checks=[],
                    panels=[], boundaries=[], failures=[], resources={})
    try:
        import numpy as np
        from independent import exact_panel, scalar_reference
        from objective import solve
        config, inputs = read('config'), read('inputs')
        tolerance = config['comparison_tolerance']
        evidence['old_AL27_gate_result'] = read_old_gate()
        assert evidence['old_AL27_gate_result'] == 'fail'
        evidence['gradient_rounding_error_bound'] = None
        evidence['parameter_error_certified'] = False
        dll_paths = list((Path(np.__file__).parent.parent/'numpy.libs').glob('*openblas*.dll'))
        assert len(dll_paths) == 1, 'require identified NumPy BLAS'
        dll = ctypes.CDLL(str(dll_paths[0]))
        getter = getattr(dll, 'scipy_openblas_get_num_threads64_')
        setter = getattr(dll, 'scipy_openblas_set_num_threads64_')
        setter.argtypes = [ctypes.c_int]
        getter.restype = ctypes.c_int
        setter(2)
        assert getter() == 2
        evidence['resources'].update(numpy_version=np.__version__, python=sys.version,
            native_threads=getter(), native_library=str(dll_paths[0]),
            parallel_head_workers=1, arrays=[], maximum_observed_array_bytes=0,
            peak_rss_bytes=None, peak_rss_note='not measured; array cap is not an RSS claim',
            gpu_calls=0, server_calls=0, probe_calls=0, readout_calls=0,
            real_classifier_training_calls=0, objective_head_attempts=0,
            newton_invocations=0, scalar_reference_invocations=0)
        def record_array(name, array):
            assert array.ndim <= 2 and all(d <= 24 for d in array.shape)
            assert array.nbytes <= config['maximum_array_bytes']
            evidence['resources']['arrays'].append(dict(name=name,shape=list(array.shape),bytes=array.nbytes))
            evidence['resources']['maximum_observed_array_bytes'] = max(
                array.nbytes, evidence['resources']['maximum_observed_array_bytes'])
            return array
        def check(name, passed, **details):
            evidence['checks'].append(dict(name=name, passed=bool(passed), **details))
            if not passed:
                evidence['failures'].append(dict(check=name, details=details))
        t = record_array('T',np.array(inputs['transform'],dtype=np.float64))
        check('T_transpose_T', np.array_equal(t.T@t,6*np.eye(4)))
        old_inputs = json.loads((ROOT/inputs['regression_reference']['path']).read_text(encoding='utf-8'))
        check('regression_original_bytes',sha(ROOT/inputs['regression_reference']['path'])==inputs['regression_reference']['sha256'])
        check('regression_original_rows', [{k:v for k,v in p.items() if k!='case_role'} for p in inputs['panels'][:3]] == old_inputs['panels'])
        check('original_boundaries',inputs['boundaries']==old_inputs['boundaries'])
        def prepare(panel, head):
            n = len(panel['plus'])
            assert n <= 12 and 2*n <= 24 and len(panel['minus']) == n
            def convert(rows):
                return np.array([[float('nan') if v == 'NaN' else float(F(v)) for v in row]
                                  for row in rows], dtype=np.float64).reshape(n,12)
            plus = record_array(panel['name']+'/'+head+'/plus',convert(panel['plus']))
            minus = record_array(panel['name']+'/'+head+'/minus',convert(panel['minus']))
            if not np.isfinite(plus).all() or not np.isfinite(minus).all():
                raise ValueError('nonfinite_input')
            dz = record_array(panel['name']+'/'+head+'/dz',plus-minus)
            return record_array(panel['name']+'/'+head+'/differences', dz@t if head=='candidate' else dz)
        def run_head(panel, head):
            evidence['resources']['objective_head_attempts'] += 1
            differences = prepare(panel,head)
            evidence['resources']['newton_invocations'] += 1
            reg = float(F(config[head+'_regularizer']))
            solver_config = dict(config['solver'], gradient_l2_tolerance=config['stopping'][head]['tau_float'])
            result, ledger = solve(differences,reg,solver_config)
            result['stopping_contract'] = config['stopping'][head]
            return result, ledger
        for panel in inputs['panels']:
            entry = dict(name=panel['name'], case_role=panel['case_role'], pairs=len(panel['plus']), heads={})
            evidence['panels'].append(entry)
            exact = exact_panel(panel, [[F(v) for v in row] for row in inputs['transform']])
            entry['exact'] = exact
            expectation = config['expected'][panel['name']]
            check(panel['name']+'/ranks_and_zero_gradient', all(exact[k]==v for k,v in expectation.items()))
            check(panel['name']+'/individual_gram_feasibility', exact['gram_feasible'])
            ledgers = {}
            for head in ['candidate','free']:
                result, ledger = run_head(panel, head)
                entry['heads'][head] = result
                ledgers[head] = ledger
                check(panel['name']+'/'+head+'/solver_stop',result['status']=='gradient_l2_tolerance',status=result['status'])
                initial = result['evaluations'][0]
                exact_g = [float(F(v)) for v in exact['gradient_at_zero'][head]]
                error = max(abs(a-b) for a,b in zip(initial['gradient'],exact_g))
                check(panel['name']+'/'+head+'/initial_gradient',error==0,max_abs_error=error)
                for ev in result['evaluations']:
                    # Internal arrays are bounded by n<=12 and d<=12 as well.
                    check(panel['name']+'/'+head+'/finite_eval_'+str(ev['id']),
                          math.isfinite(ev['objective']) and np.isfinite(ev['gradient']).all() and np.isfinite(ev['hessian']).all())
            candidate, free = entry['heads']['candidate'],entry['heads']['free']
            w, beta = np.array(candidate['parameters']), np.array(free['parameters'])
            cend = candidate['evaluations'][candidate['terminal_evaluation_id']]
            fend = free['evaluations'][free['terminal_evaluation_id']]
            lift, _, _ = ledgers['free'].evaluate(t@w,'candidate_lift')
            entry['candidate_lift_evaluation_id'] = lift['id']
            entry['lifted_beta'] = (t@w).tolist()
            entry['lift_objective_gap'] = abs(lift['objective']-cend['objective'])
            check(panel['name']+'/subspace_objective_identity',entry['lift_objective_gap']<=tolerance,
                  absolute_error=entry['lift_objective_gap'])
            check(panel['name']+'/free_optimum_inclusion',fend['objective']<=cend['objective']+tolerance)
            if panel['name'] in ['aligned','full_rank','full_rank_scale']:
                evidence['resources']['scalar_reference_invocations'] += 1
                scalar = scalar_reference(panel['name'],config['scalar'])
                entry['scalar_reference'] = scalar
                check(panel['name']+'/scalar_stop',scalar['status']=='width_tolerance')
                scalar_w = np.full(4,scalar['root']) if panel['name']=='aligned' else np.zeros(4)
                scalar_beta = t@scalar_w if panel['name']=='aligned' else np.full(12,scalar['root'])
                for head, actual, expected in [('candidate',w,scalar_w),('free',beta,scalar_beta)]:
                    error = float(np.max(np.abs(actual-expected)))
                    check(panel['name']+'/'+head+'/scalar_vector_agreement',error<=tolerance,max_abs_error=error)
                    target_objective = scalar['objective'] if head=='free' or panel['name']=='aligned' else math.log(2)
                    end = cend if head=='candidate' else fend
                    error = abs(end['objective']-target_objective)
                    check(panel['name']+'/'+head+'/scalar_objective_agreement',error<=tolerance,absolute_error=error)
                if panel['name']=='aligned':
                    error = float(np.max(np.abs(beta-t@w)))
                    check('aligned/free_beta_equals_Tw',error<=tolerance,max_abs_error=error)
                else:
                    fixed,_,_ = ledgers['free'].evaluate(np.ones(12),'fixed_feasible_ones')
                    entry['fixed_feasible_evaluation_id'] = fixed['id']
                    check(panel['name']+'/fixed_feasible_below_log2',fixed['objective']<math.log(2))
                    check(panel['name']+'/free_positive_and_better',bool(np.all(beta>0)) and
                          fend['objective']<math.log(2) and fend['objective']<=fixed['objective']+tolerance)
            else:
                check('symmetric/unique_zero_reference',np.array_equal(w,np.zeros(4)) and np.array_equal(beta,np.zeros(12))
                      and candidate['iterations']==0 and free['iterations']==0)
        for boundary in inputs['boundaries']:
            for head in ['candidate','free']:
                try:
                    result, ledger = run_head(boundary,head)
                    entry = dict(name=boundary['name'],head=head,result=result)
                    check(boundary['name']+'/'+head, boundary['name']=='empty' and
                          result['status']=='no_training_support' and result['parameters'] is None and not result['evaluations'])
                except ValueError as exc:
                    entry = dict(name=boundary['name'],head=head,status='rejected',reason=str(exc))
                    check(boundary['name']+'/'+head, boundary['name']=='nonfinite' and str(exc)=='nonfinite_input')
                evidence['boundaries'].append(entry)
        evidence['resources']['objective_evaluations'] = sum(len(h['evaluations']) for p in evidence['panels'] for h in p['heads'].values())
        evidence['resources']['linear_solves'] = sum(len(h['steps']) for p in evidence['panels'] for h in p['heads'].values())
        evidence['resources']['scalar_derivative_evaluations'] = sum(len(p.get('scalar_reference',{}).get('evaluations',[])) for p in evidence['panels'])
        evidence['resources']['native_threads_after'] = getter()
        check('native_thread_cap_after',getter()==2)
        for category in ['inputs','dependencies','historical']:
            changed = [p for p,digest in frozen[category].items() if sha(ROOT/p)!=digest]
            check(category+'/unchanged_after',not changed,changed=changed)
        evidence['gate_result'] = 'pass' if not evidence['failures'] else 'fail'
    except Exception as exc:
        evidence['failures'].append(dict(exception=repr(exc),traceback=traceback.format_exc()))
        evidence['gate_result']='fail'
    finally:
        evidence['resources']['wall_seconds'] = time.perf_counter()-wall_start
        evidence['resources']['process_cpu_seconds'] = time.process_time()-cpu_start
        evidence['completed_at'] = datetime.now(timezone.utc).isoformat()
        evidence['scope'] = 'accuracy_budgeted_optimizer_reference'
        evidence['scientific_innovation_gate_passed'] = False
        evidence['rigorous_numeric_error_certificate'] = False
        save('evidence',evidence)
    print(json.dumps(dict(gate_result=evidence['gate_result'],failures=evidence['failures'],
                         resources={k:v for k,v in evidence['resources'].items() if k!='arrays'}),ensure_ascii=False))
    return 0 if evidence['gate_result']=='pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
