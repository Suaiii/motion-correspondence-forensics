"""Execute only the committed AL15 inputs. Dependencies: NumPy and stdlib."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from collections import Counter,defaultdict
import ctypes
from datetime import datetime,timezone
import hashlib
import inspect
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import core

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def gap(a,b):return float(np.max(np.abs(np.asarray(a,dtype=float)-np.asarray(b,dtype=float))))


def thread_receipt():
    receipts=[]
    for dll in (Path(np.__file__).resolve().parent.parent/'numpy.libs').glob('*openblas*.dll'):
        handle=ctypes.CDLL(str(dll))
        for symbol in ('scipy_openblas_get_num_threads64_','scipy_openblas_get_num_threads','openblas_get_num_threads64_','openblas_get_num_threads'):
            try:getter=getattr(handle,symbol)
            except AttributeError:continue
            setter=getattr(handle,symbol.replace('get_num_threads','set_num_threads'))
            setter.argtypes=[ctypes.c_int];setter.restype=None;setter(2)
            getter.restype=ctypes.c_int
            receipts.append(dict(dll=str(dll),get_symbol=symbol,configured_threads=getter(),
                instrumentation='ctypes call to NumPy-vendored OpenBLAS; no threadpoolctl/scipy import'))
            break
    if not receipts or any(r['configured_threads']!=2 for r in receipts):
        raise RuntimeError('Could not verify strict two-thread NumPy BLAS configuration')
    return receipts


def validate_arms(arms):
    expected={'C':('camera',0,0,None),'R':('camera',0,1,'C'),'R2':('camera',0,2,'R'),
              'G':('generated',1,1,None),'G2':('generated',1,2,'G')}
    if {r['arm'] for r in arms}!=set(expected):raise core.ContractError('Missing/extra arm')
    for row in arms:
        if (row['origin'],row['origin_label'],row['known_D_count'],row['parent'])!=expected[row['arm']]:
            raise core.ContractError('Origin label, known processing depth or ancestry mismatch')
        chain=row['transform_chain']
        expected_chain=(['native_export']+['R_i']*row['known_D_count']) if row['origin_label']==0 else ['D_i_generate']+['R_i']*(row['known_D_count']-1)
        if chain!=expected_chain+['A_kappa'] or row['root_origin_id']!='mock_'+row['origin']:
            raise core.ContractError('Base-arm chain/root differs from declared origin contract')
        if chain[-1]!='A_kappa' or chain.count('A_kappa')!=1:
            raise core.ContractError('Common final propagation must follow base-arm formation')
        actual=sum(t in ('R_i','D_i_generate') for t in chain)
        if actual!=row['known_D_count']:raise core.ContractError('D-call accounting mismatch')
        if row['historical_other_processing']!='unknown':raise core.ContractError('Do not silently fill unknown history')
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT/'AL15_evidence.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    freeze_path=OUT/'AL15_freeze.json';lock=json.loads(freeze_path.read_text(encoding='utf-8'))
    def unchanged():
        for rel,want in dict(lock['files'],**lock['preserved']).items():
            if sha(ROOT/rel)!=want:raise ValueError('Frozen/preserved file changed: '+rel)
        for path,want in lock['dependency_files'].items():
            if sha(path)!=want:raise ValueError('Frozen dependency changed: '+path)
    unchanged()
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    data=json.loads((OUT/'AL15_inputs.json').read_text(encoding='utf-8'))
    start=time.perf_counter();cpu_start=time.process_time();ledger=core.Ledger();rows=[];failures=[];stored={};distributions=defaultdict(lambda:defaultdict(list))
    blas=thread_receipt()
    if np.__version__!=lock['numpy_distribution']:raise ValueError('NumPy version mismatch')
    tol=cfg['tolerance']
    for index,record in enumerate(data['records']):
        row=dict(id=record['id'],family=record['family'],variant=record['variant'],h=record['h'],
            input_index=index,checks={})
        expected=record['expected'];family=record['family'];n=record['dimension'];base=record['base_dimension'];eta=record['eta_mean']
        try:
            probes=[core.MockProbe(spec) for spec in record['operators']]
            result=core.evaluate(record['x'],*probes,record['h'],eta,record['support'],ledger,f'evaluation_{index:04}',purpose='core')
            row['result']=result
            checks=row['checks']
            row['errors']=dict(K=gap(result['K'],expected['K']),v_a=gap(result['v_a'],expected['v_a']),v_b=gap(result['v_b'],expected['v_b']))
            checks['closed_form_vectors']=max(row['errors'].values())<=tol
            checks['expected_sum_energies']=all(abs(result['energy_sum'][key]-value)<=tol for key,value in expected['energy_sum'].items())
            checks['explicit_sum_mean_scaling']=all(abs(result['energy_sum'][key]/n-result['energy_mean'][key])<=tol for key in result['energy_sum'])
            checks['primary_mean_ratio']=abs(result['q_mean_fixed_eta']-expected['q_mean_fixed_eta'])<=tol
            checks['secondary_sum_ratio']=abs(result['q_sum_fixed_eta']-expected['q_sum_fixed_eta'])<=tol
            checks['sum_equivalent_eta']=abs(result['q_sum_eta_equivalent_to_mean']-result['q_mean_fixed_eta'])<=tol
            ek=result['energy_sum']['K'];den=result['energy_sum']['a']+result['energy_sum']['b']
            scaled_eta=base/n*eta
            row['embedding_diagnostic']=dict(eta_mean_scaled=scaled_eta,
                q_mean_scaled_eta=(ek/n)/(den/n+scaled_eta),
                note='Diagnostic only; main mean ratio keeps eta=1e-12 at every dimension')
            checks['scaled_eta_diagnostic']=abs(row['embedding_diagnostic']['q_mean_scaled_eta']-expected['q_mean_scaled_eta'])<=tol
            calls=[ledger.records[i-1] for i in result['call_ids']]
            checks['exactly_four_core_calls']=result['successful_core_calls']==4 and len(calls)==4
            checks['one_a_one_b_per_path']=all(sorted(path)==['a','b'] for path in result['paths'].values())
            checks['shared_first_nodes']= [r['parent'] for r in calls]==['input','input','Pb','Pa']
            checks['fresh_initial_cache']=all(r['cache_initial']=={'history':[]} and r['cache_identity_unique'] and r['cache_after']=={'history':['one_mock_call']} for r in calls)
            checks['same_h_support_conditions']=all(r['soft_step']==record['h'] and r['support']==record['support'] for r in calls)
            checks['no_source_or_latent_passed']=all(r['received_fields']==['vector','cache','support'] for r in calls)
            if family=='nonlinear_remainder':
                residual=np.asarray(result['K'])-np.asarray(expected['bracket'])
                row['nonlinear_remainder']=dict(vector=residual.tolist(),norm=float(np.linalg.norm(residual)),expected_norm=expected['remainder_norm'])
                checks['exact_nonlinear_remainder']=abs(row['nonlinear_remainder']['norm']-expected['remainder_norm'])<=tol
            key=(family,record['variant'],tuple(record['base_x']),record['h'])
            if family=='probe_order_swap':
                original=stored[('matched_scalar_errors',record['variant'],tuple(record['base_x']),record['h'])]
                checks['swap_sign']=gap(result['K'],[-v for v in original['K']])<=tol
                checks['swap_energy_and_ratio']=abs(result['q_mean_fixed_eta']-original['q_mean_fixed_eta'])<=tol and abs(ek-original['energy_sum']['K'])<=tol
            if family=='noncommuting_but_redundant':
                checks['redundancy_not_hidden']=abs(ek-result['energy_sum']['input'])<=tol and abs(den-ek)<=tol
                row['scientific_interpretation']='Noncommuting response fully explained by simple energies on this declared case; no new source information'
            if record['variant']!='development_base':
                original=stored[(family,'development_base',tuple(record['base_x']),record['h'])]
                checks['embedding_sum_invariant']=all(abs(result['energy_sum'][key]-original['energy_sum'][key])<=tol for key in original['energy_sum'])
                checks['embedding_scaled_eta_ratio_invariant']=abs(row['embedding_diagnostic']['q_mean_scaled_eta']-original['q_mean_fixed_eta'])<=tol
                row['embedding_diagnostic']['primary_ratio_change_from_base']=result['q_mean_fixed_eta']-original['q_mean_fixed_eta']
            if family=='equal_output_distribution':
                # Audit group is attached only after inference and never passed to a probe.
                signature=json.dumps(dict(K=result['K'],energies=result['energy_sum'],q=result['q_mean_fixed_eta']),sort_keys=True)
                distributions[(record['variant'],record['h'])][record['audit_only_set']].append(signature)
            stored[key]=result
        except Exception as exc:
            row.update(status='unexpected_failure',error=type(exc).__name__+': '+str(exc));failures.append(row['id'])
        row['checks']={k:bool(v) for k,v in row['checks'].items()}
        if not all(row['checks'].values()):failures.append(row['id'])
        row.setdefault('status','pass' if all(row['checks'].values()) else 'failed_check')
        rows.append(row)
    distribution_rows=[]
    for (variant,h),sets in distributions.items():
        passed=len(sets['Y0'])==len(sets['Y1'])==2 and sorted(sets['Y0'])==sorted(sets['Y1'])
        distribution_rows.append(dict(variant=variant,h=h,same_empirical_output_multiset=passed,count_per_set=[len(sets['Y0']),len(sets['Y1'])],
            interpretation='Same declared output distribution is indistinguishable; no fitted detector or accuracy metric'))
        if not passed:failures.append('distribution_'+variant+'_'+str(h))
    negative_rows=[]
    for index,case in enumerate(data['negative_contracts']):
        x=[float('nan') if isinstance(v,dict) and v.get('float64_special')=='NaN' else v for v in case['x']]
        before=len(ledger.records);observed='returned';detail=None
        try:
            core.evaluate(x,*[core.MockProbe(spec) for spec in case['operators']],case['h'],case['eta_mean'],case['support'],ledger,f'contract_{index:02}',purpose='contract_negative')
        except Exception as exc:observed=type(exc).__name__;detail=str(exc)
        calls=len(ledger.records)-before
        passed=observed==case['expected_exception'] and calls==case['expected_probe_calls']
        negative_rows.append(dict(id=case['id'],observed=observed,reason=detail,probe_calls=calls,expected_probe_calls=case['expected_probe_calls'],passed=passed))
        if not passed:failures.append(case['id'])
    repeat_rows=[]
    repeats=data['repeat_diagnostics']
    for case in repeats['cases']:
        result=core.repeat_diagnostic(core.MockProbe(case['operator']),repeats['x'],repeats['support'],ledger,case['id'])
        result.update(id=case['id'],expected_equal=case['expected_equal'],passed=result['exactly_equal']==case['expected_equal'])
        repeat_rows.append(result)
        if not result['passed']:failures.append(case['id'])
    arm_rows=[]
    for name,arms,expected_valid in [('valid_arms',data['valid_mock_arms'],True)]+[(r['id'],r['arms'],False) for r in data['invalid_mock_arm_sets']]:
        try:valid=validate_arms(arms);reason=None
        except core.ContractError as exc:valid=False;reason=str(exc)
        arm_rows.append(dict(id=name,accepted=valid,expected_valid=expected_valid,reason=reason,probe_calls=0,passed=valid==expected_valid))
        if valid!=expected_valid:failures.append(name)
    counts=dict(Counter(r['purpose'] for r in ledger.records))
    if counts!={'core':840,'contract_negative':4,'diagnostic_repeat':6}:failures.append('total_call_accounting')
    unchanged()
    if 'torch' in sys.modules or 'scipy' in sys.modules or 'threadpoolctl' in sys.modules:failures.append('disallowed_dependency_import')
    evidence=dict(task_id='AL15',dispatch_id=cfg['dispatch_id'],observed_at=datetime.now(timezone.utc).isoformat(),
        authorization=cfg['current_authorization'],archived_draft_sha256=cfg['draft_sha256'],archived_draft_status_unchanged=True,
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),command=sys.argv,
        freeze_sha256=sha(freeze_path),frozen_files=lock['files'],dependency_files=lock['dependency_files'],
        inputs_and_previous_artifacts_unchanged=True,status='pass_software_algebra_mock_scope' if not failures else 'failure_preserved',
        failures=failures,evaluations=rows,distribution_checks=distribution_rows,negative_contracts=negative_rows,
        repeat_diagnostics=repeat_rows,source_label_contracts=arm_rows,call_counts=counts,total_probe_calls=len(ledger.records),
        call_ledger=ledger.records,core_signature=str(inspect.signature(core.evaluate)),
        resources=dict(wall_seconds=time.perf_counter()-start,process_cpu_seconds=time.process_time()-cpu_start,
            numpy=np.__version__,python=sys.version,environment_threads={k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
            blas_runtime=blas,max_observed_explicit_task_array_bytes=core.MAX_OBSERVED_ARRAY_BYTES,process_peak_RSS='not_measured',
            server_access=False,media_read=False,torch_imported=False,gpu_used=False,classifier_fitting=False,
            cumulative_project_spend_and_GPU_hours='unknown; unchanged'),
        pending=['real four-filter readout','paired logistic fitting','video VAE wrapper','checkpoint and output clock binding','innovation and real mechanism gate'],
        limitations=['Fixed embeddings are mechanical checks, not independent real seeds',
                    'Repeat agreement does not certify numerical accuracy or general determinism',
                    'Mock clock/coordinate slots do not establish pixel physical correspondence',
                    'AL16 numeric error contract is independent and not implemented here'],scientific_breakthrough=False)
    save(args.output,evidence)
    print(json.dumps(dict(status=evidence['status'],evaluations=len(rows),calls=counts,total_calls=len(ledger.records),failures=failures,
        max_K_error=max((r.get('errors',{}).get('K',0) for r in rows),default=0),
        max_array_bytes=core.MAX_OBSERVED_ARRAY_BYTES,wall_seconds=evidence['resources']['wall_seconds']),indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        failure=OUT/'AL15_startup_or_unhandled_failure.json'
        if not failure.exists():
            save(failure,dict(task_id='AL15',status='unhandled_failure_preserved',
                observed_at=datetime.now(timezone.utc).isoformat(),error=repr(exc),
                script_sha256=sha(Path(__file__)),command=sys.argv,scientific_breakthrough=False))
        raise
