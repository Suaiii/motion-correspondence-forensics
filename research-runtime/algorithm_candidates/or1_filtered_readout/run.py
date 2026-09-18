"""One AL25 frozen run with analytic references; no model/probe invocation."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='2'
import argparse
import ctypes
from datetime import datetime,timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import readout

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'research-runs/algorithm_search_20260918'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def decode(v):
    if isinstance(v,dict):
        if set(v)=={'nonfinite'}:return float(v['nonfinite'])
        return {k:decode(x) for k,x in v.items()}
    if isinstance(v,list):return [decode(x) for x in v]
    return v
def save(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(data),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def flat(v):
    if isinstance(v,list):return [x for child in v for x in flat(child)]
    return [v]
def error(actual,exact):return F.from_float(float(actual))-F(exact)


def thread_audit():
    rows=[]
    for dll in (Path(np.__file__).resolve().parent.parent/'numpy.libs').glob('*openblas*.dll'):
        library=ctypes.CDLL(str(dll))
        for name in ('scipy_openblas_get_num_threads64_','scipy_openblas_get_num_threads','openblas_get_num_threads64_','openblas_get_num_threads'):
            try:getter=getattr(library,name)
            except AttributeError:continue
            setter=getattr(library,name.replace('get_num_threads','set_num_threads'))
            setter.argtypes=[ctypes.c_int];setter(2);getter.restype=ctypes.c_int
            rows.append(dict(library=str(dll),symbol=name,threads=getter()));break
    if not rows or any(r['threads']!=2 for r in rows):raise RuntimeError('Native thread cap not verified')
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT/'AL25_evidence.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    lock_path=OUT/'AL25_freeze.json';lock=json.loads(lock_path.read_text(encoding='utf-8'))
    def unchanged():
        for rel,want in dict(lock['files'],**lock['preserved']).items():
            if sha(ROOT/rel)!=want:raise ValueError('Frozen/prior file changed: '+rel)
        for path,want in lock['dependency_files'].items():
            if sha(path)!=want:raise ValueError('Dependency changed: '+path)
    unchanged();spec=json.loads((OUT/'AL25_readout_spec.json').read_text(encoding='utf-8'))
    data=json.loads((OUT/'AL25_inputs.json').read_text(encoding='utf-8'))
    if np.__version__!=lock['numpy_version']:raise ValueError('NumPy version changed')
    kernel_checks={name:([list(row) for row in readout.NUMERATORS[name]]==spec['kernels'][name]['numerator']
        and readout.DENOMINATORS[name]==spec['kernels'][name]['denominator']) for name in readout.NUMERATORS}
    kernel_checks['filter_order']=list(readout.FILTERS)==spec['filter_order']
    started=time.perf_counter();cpu_start=time.process_time();blas=thread_audit()
    failures=[] if all(kernel_checks.values()) else ['kernel_spec_mismatch'];rows=[];metrics_rows=[]
    tolerance=F(str(spec['normal_absolute_tolerance']))
    for case in data['records']:
        metrics={};row=dict(id=case['id'],mode=case['mode'],checks={},reference=case['reference'])
        try:
            fields={name:np.asarray(value,dtype=np.float64) for name,value in case['fields'].items()}
            for array in fields.values():array.setflags(write=False)
            result=readout.compute(fields,metrics);row['result']=result
            row['checks']['support_shape']=result['common_support_shape']==data['expected_common_support_shape']
            row['checks']['support_count']=result['common_support_elements']==data['expected_support_elements']
            row['checks']['q4_z12_layout']=len(result['q4_direct'])==4 and len(result['z12'])==12
            row['checks']['eta_unchanged']=result['eta_float']==spec['eta_float_literal']
            row['checks']['twenty_synthetic_filters']=metrics['filter_applications']==20
            comparisons=[]
            for actual,reference in zip(result['filters'],case['reference']):
                comp=dict(filter=actual['filter'],checks={})
                errors={key:error(actual[key],reference[key]) for key in ('N','E_a','E_b','D','A','B','C')}
                errors['q_direct']=error(actual['q_direct'],reference['q'])
                errors['q_compact_raw']=error(actual['q_compact_raw'],reference['q'])
                comp['exact_float_minus_fraction_reference']=errors
                comp['z_errors']=[error(x,y) for x,y in zip(actual['z'],reference['z'])]
                field_errors={key:max((abs(error(x,y)) for x,y in zip(flat(actual['filtered_fields'][key]),flat(reference['filtered_fields'][key]))),default=F(0)) for key in actual['filtered_fields']}
                comp['max_signed_filtered_field_errors']=field_errors
                comp['checks']['signed_field_reference']=all(x<=tolerance for x in field_errors.values())
                comp['checks']['common_filter_support']=actual['support_elements']==54 and actual['support_shape']==[2,3,3,3]
                comp['checks']['inner_sign_preserved']=(actual['C']<0)==(F(reference['C'])<0)
                comp['checks']['raw_compact_formula_retained']=actual['q_compact_raw']==actual['z'][0]+actual['z'][1]-2*actual['z'][2]
                comp['checks']['AE_bound_stays_unknown']=actual['AE_error_bound_status']=='unknown' and actual['source_decision'] is None
                if case['mode']=='normal':
                    comp['checks']['normal_absolute_tolerance']=all(abs(x)<=tolerance for x in list(errors.values())+comp['z_errors'])
                    comp['checks']['normal_path_reconstruction_tolerance']=abs(actual['q_compact_minus_direct'])<=float(tolerance)
                else:
                    # Report every cancellation result; never demand a particular rounded compact value.
                    comp['cancellation']=dict(exact_q=reference['q'],exact_q_binary_eta=reference['q_binary_eta'],
                        exact_N=reference['N'],direct_float=actual['q_direct'],compact_raw_float=actual['q_compact_raw'],
                        direct_minus_exact_binary_eta=error(actual['q_direct'],reference['q_binary_eta']),
                        raw_compact_minus_direct=actual['q_compact_minus_direct'],compact_numerator_raw=actual['compact_numerator_raw'],
                        numerator_first_diagnostic=actual['q_compact_numerator_first_diagnostic'],
                        operation_order='direct: subtract fields, correlate, square, mean, divide; compact: square/inner means, divide three terms, then A+B-2C',
                        not_a_source_information_gain=True,platform_specific_compact_value_not_required=True)
                    if actual['filter']=='identity':
                        comp['checks']['exact_reference_positive']=F(reference['q'])>0
                        comp['checks']['direct_float_retains_nonzero_toy_difference']=actual['N']>0 and actual['q_direct']>0
                comparisons.append(comp)
                if not all(comp['checks'].values()):failures.append(case['id']+'/'+actual['filter'])
            row['comparisons']=comparisons
        except Exception as exc:
            row['unexpected_error']=repr(exc);failures.append(case['id'])
        if not all(row['checks'].values()):failures.append(case['id']+'/case_checks')
        rows.append(row);metrics_rows.append(metrics)
    invalid_rows=[]
    for case in data['invalid_inputs']:
        metrics={};observed='returned';detail=None
        try:
            fields={name:np.asarray(decode(value),dtype=np.float64) for name,value in case['fields'].items()}
            readout.compute(fields,metrics)
        except readout.ReadoutInputError as exc:observed=exc.code;detail=str(exc)
        except Exception as exc:observed=type(exc).__name__;detail=str(exc)
        passed=observed==case['expected_code'] and metrics.get('filter_applications',0)==0
        invalid_rows.append(dict(id=case['id'],expected_code=case['expected_code'],observed_code=observed,detail=detail,
            filter_applications=metrics.get('filter_applications',0),passed=passed))
        metrics_rows.append(metrics)
        if not passed:failures.append(case['id'])
    filters=sum(m.get('filter_applications',0) for m in metrics_rows)
    means=sum(m.get('mean_products',0) for m in metrics_rows)
    if filters!=140 or means!=168:failures.append('operation_accounting')
    if any(name in sys.modules for name in ('torch','scipy','threadpoolctl')):failures.append('forbidden_import')
    unchanged()
    output=dict(task_id='AL25',dispatch_id=spec['dispatch_id'],readout_version=spec['version'],observed_at=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),freeze_sha256=sha(lock_path),
        files=lock['files'],dependency_files=lock['dependency_files'],old_artifacts_unchanged=True,
        status='pass_filtered_tensor_readout_reference' if not failures else 'failure_preserved',failures=failures,
        kernel_spec_checks=kernel_checks,cases=rows,invalid_inputs=invalid_rows,
        calls=dict(readout_attempts=10,successful_readouts=7,rejected_inputs=3,synthetic_field_filter_applications=filters,
            mean_products=means,actual_AE_or_probe_calls=0,AL15_core_calls=0),
        resources=dict(wall_seconds=time.perf_counter()-started,process_cpu_seconds=time.process_time()-cpu_start,
            python_worker_count=1,native_thread_cap=2,blas_runtime=blas,numpy=np.__version__,python=sys.version,
            max_array_bytes=max(m.get('max_array_bytes',0) for m in metrics_rows),max_raw_elements_per_array=150,
            process_peak_RSS='not_measured',models=False,weights=False,media=False,server=False,GPU=False,classifier_fitting=False),
        scope='Seven fixed synthetic fields and three invalid inputs only; exact toy errors do not certify real AE precision',
        future_pending=['real media normalization','BCTHW/17-frame wrapper','AE/model error bounds','source discrimination and innovation gate'],
        classification_metrics_computed=False,scientific_breakthrough=False)
    save(args.output,output)
    cancellation=next(r for r in rows if r['id']=='near_cancellation')
    print(json.dumps(dict(status=output['status'],failures=failures,calls=output['calls'],
        near_cancellation_q_direct=cancellation.get('result',{}).get('q4_direct'),
        near_cancellation_q_compact_raw=cancellation.get('result',{}).get('q4_compact_raw'),
        wall_seconds=output['resources']['wall_seconds']),indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
