"""AL18 fixed exact-rational CPU run; no AL15 replay and no external numerical package."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from fractions import Fraction as F
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import bounds

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'research-runs/algorithm_search_20260918'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [pack(x) for x in v]
    return v
def decode(v):
    if isinstance(v,dict):
        if set(v)=={'nonfinite'}:return float(v['nonfinite'])
        return {k:decode(x) for k,x in v.items()}
    if isinstance(v,list):return [decode(x) for x in v]
    return v
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(pack(data),f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def as_vector(v):return tuple(F(x) for x in v)
def within(value,interval):return interval[0]<=value<=interval[1]
def norm_sq(v):return sum((x*x for x in v),F(0))
def bnd(value):return dict(value=value,basis='analytic_mock')
def displays(result):
    output={}
    for key in ('B_K','B_N','B_q','q_hat','denominator_lower'):
        if isinstance(result.get(key),F):
            try:output[key]=float(result[key])
            except OverflowError:output[key]=None
    return dict(values=output,role='Nearest-float display only, never used in coverage verification or as a certified upper bound')


def evaluate_record(record):
    row=dict(id=record['id'],family=record['family'],nominal_h=record['nominal_h'],
        worker=threading.current_thread().name,checks={},mock_probe_ledger=[],repeat_endpoint_ledger=[],public_contract_queries=0)
    expected=record['expected'];payload=decode(copy.deepcopy(record['payload']));h=decode(record['h']);eta=decode(record['eta'])
    def query(kind,p):
        row['public_contract_queries']+=1
        return bounds.evaluate(kind,p,h,eta)
    try:
        if record['family']==3:
            hf=F(h);epsilon=F(record['epsilon']);signs=record['signs'];x=(F(1,2),F(1,4))
            def call(value,sign,name,parent):
                error=(sign*epsilon,F(0));output=tuple(a+b for a,b in zip(value,error))
                row['mock_probe_ledger'].append(dict(name=name,parent=parent,input=value,output=output,
                    ideal_identity_output=value,additive_error=error,error_norm=epsilon,
                    bound=epsilon,L=F(1),basis='Defined identity plus fixed signed first-coordinate error'))
                return output
            def mix(left,right):return tuple((1-hf)*a+hf*b for a,b in zip(left,right))
            ra=call(x,signs[0],'a0','x');rb=call(x,signs[1],'b0','x')
            pa=mix(x,ra);pb=mix(x,rb)
            rab=call(pb,signs[2],'ab','pb');rba=call(pa,signs[3],'ba','pa')
            actual=dict(x=x,ra0=ra,rb0=rb,pa=pa,pb=pb,rab=rab,rba=rba,uab=mix(pb,rab),uba=mix(pa,rba))
            row['checks']['actual_trace_matches_precomputed_input']=all(actual[k]==as_vector(record['payload']['observations'][k]) for k in actual)
            payload['observations']=actual
            row['observations']=actual
        if record['kind']=='N4_then_N5':
            n4=query('N4',payload);row['N4']=n4
            den=F(record['ratio_denominator'])
            ratio_payload=dict(hat_n=n4['hat_n'],hat_d=den,
                bounds=dict(B_N=bnd(n4['B_N']),B_D=bnd(F(0)),rho_q=bnd(F(0)),rho_s=bnd(F(0))))
            result=query('N5',ratio_payload)
            row['checks']['N4_bound_exact']=n4['B_N']==F(expected['B_N'])
            row['checks']['N4_interval_exact']=n4['numerator_interval']==as_vector(expected['numerator_interval'])
            row['checks']['N4_covers_true_zero']=within(F(0),n4['numerator_interval'])
            row['checks']['N5_covers_true_zero']=within(F(0),result['ratio_interval'])
            row['checks']['ratio_bounds_exact']=result['B_q']==F(expected['B_q']) and result['ratio_interval']==as_vector(expected['ratio_interval'])
            row['checks']['no_source_decision']=result['origin_decision'] is None and result['score']['origin_decision'] is None
        elif record['kind']=='repeat_then_N1':
            readings=[]
            for i,value in enumerate(record['repeat_readouts']):
                truth=F(record['exact_endpoint'])
                # Actual controlled readout, independently compared with the frozen expected observation.
                observation=truth+F(record['analytic_bias_bound']);readings.append(observation)
                if observation!=F(value):raise AssertionError('Repeat mock differs from frozen input')
                row['repeat_endpoint_ledger'].append(dict(call=i+1,exact_endpoint=truth,observed_endpoint=observation,
                    actual_bias=observation-truth,basis='Controlled constant endpoint bias; not an AE measurement'))
            repeat_gap=abs(readings[0]-readings[1]);row['repeat_gap']=repeat_gap
            payload['hat_ab']=(readings[0],F(0))
            result=query('N1',payload)
            known=copy.deepcopy(payload);known['bounds']['delta_ab']=bnd(F(record['analytic_bias_bound']))
            known_result=query('N1',known);row['known_bias_contract']=known_result
            row['checks']['repeat_gap_zero']=repeat_gap==F(expected['repeat_gap'])
            row['checks']['unknown_not_filled_zero']=result['status']=='uncertified_bound' and 'B_K' not in result
            row['checks']['known_bias_bound_exact']=known_result['B_K']==F(expected['known_B_K'])
            row['checks']['known_bias_covers_zero']=within(F(0),known_result['coordinate_intervals'][0])
            row['checks']['known_state_matches']=known_result['status']==expected['known_status']
        else:result=query(record['kind'],payload)
        row['result']=result
        row['checks']['state_matches']=result['status']==expected['status']
        if record['family'] in (1,2,3):
            truth=as_vector(expected['truth_K']);observed=result['K_hat'];bk=result['B_K']
            error_sq=norm_sq(tuple(a-b for a,b in zip(observed,truth)))
            row['actual_error_squared']=error_sq;row['bound_attained']=error_sq==bk*bk
            row['checks']['K_observation_exact']=observed==as_vector(expected['K_hat'])
            row['checks']['N1_or_N2_bound_exact']=bk==F(expected['B_K'])
            row['checks']['euclidean_coverage']=error_sq<=bk*bk
            row['checks']['coordinate_coverage']=all(within(x,i) for x,i in zip(truth,result['coordinate_intervals']))
            row['checks']['tight_corner_recorded']=row['bound_attained']==expected['tight']
            if record['family']==3:
                row['checks']['endpoint_propagation_exact']=all(result['propagation'][k]==F(expected[k]) for k in ('delta_ab','delta_ba'))
                row['checks']['exactly_four_mock_calls']=len(row['mock_probe_ledger'])==4
                row['checks']['each_mock_call_respects_bound']=all(norm_sq(r['additive_error'])<=r['bound']**2 for r in row['mock_probe_ledger'])
        if record['family']==5:
            truth=F(expected['truth_q']);error=abs(result['q_hat']-truth)
            row['ratio_corner']=dict(n=F(expected['truth_n']),d=F(expected['truth_d']),q=truth,actual_error=error)
            row['checks']['N5_bound_exact']=result['B_q']==F(expected['B_q'])
            row['checks']['N5_interval_exact']=result['ratio_interval']==as_vector(expected['ratio_interval'])
            row['checks']['ratio_error_covered']=error<=result['B_q'] and within(truth,result['ratio_interval'])
            row['checks']['fixed_weight_score_bound']=result['score']['B_score']==result['B_q']
            row['checks']['numerical_sign_stable']=result['score']['sign_stability']==expected['sign_stability']
        if record['family']==6:
            if 'denominator_lower' in expected:
                row['checks']['nonpositive_prescribed_lower']=result['denominator_lower']==F(expected['denominator_lower']) and not result['interval_valid']
                row['checks']['no_ratio_fabricated']='ratio_interval' not in result
            else:
                row['checks']['zero_interval_recorded']=result['ratio_interval']==as_vector(expected['ratio_interval'])
                row['checks']['residual_lower_zero']=result['denominator_residual_energy_lower']==0
                row['checks']['boundary_not_origin_label']=result['score']['sign_stability']=='boundary_or_uncertain' and result['origin_decision'] is None
        if record['family']==7:
            row['checks']['uncertified_or_invalid_has_no_safe_interval']=not result['interval_valid']
            if expected['status']=='uncertified_bound':row['checks']['no_bound_zero_substitution']='B_K' not in result and bool(result['unknown_fields'])
        row['checks']['no_origin_label']=result['origin_decision'] is None
        row['display_only']=displays(result)
        row['passed']=all(row['checks'].values())
    except Exception as exc:
        row.update(passed=False,unexpected_error=repr(exc))
    return row


def container_stats(value):
    maximum=0;length=0
    if isinstance(value,(list,tuple)):
        if value and all(isinstance(x,(int,float,F)) and not isinstance(x,bool) for x in value):
            size=sys.getsizeof(value)+sum(sys.getsizeof(x)+(sys.getsizeof(x.numerator)+sys.getsizeof(x.denominator) if isinstance(x,F) else 0) for x in value)
            maximum=size;length=len(value)
        children=value
    elif isinstance(value,dict):children=value.values()
    else:children=()
    for child in children:
        child_size,child_length=container_stats(child);maximum=max(maximum,child_size);length=max(length,child_length)
    return maximum,length


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT/'AL18_evidence.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    freeze_path=OUT/'AL18_freeze.json';lock=json.loads(freeze_path.read_text(encoding='utf-8'))
    def unchanged():
        for name,want in dict(lock['files'],**lock['preserved']).items():
            if sha(ROOT/name)!=want:raise ValueError('Frozen/prior file changed: '+name)
        for name,want in lock['dependencies'].items():
            if sha(name)!=want:raise ValueError('Runtime dependency changed: '+name)
    unchanged();data=json.loads((OUT/'AL18_inputs.json').read_text(encoding='utf-8'))
    if cfg['numeric_workers']!=2 or cfg['score_weights']!=['1'] or cfg['score_threshold']!='0':
        raise ValueError('Frozen work-order contract changed')
    started=time.perf_counter();cpu_start=time.process_time()
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='AL18') as pool:
        rows=list(pool.map(evaluate_record,data['records']))
    failures=[r['id'] for r in rows if not r['passed']]
    calls=sum(len(r['mock_probe_ledger']) for r in rows);readouts=sum(len(r['repeat_endpoint_ledger']) for r in rows)
    queries=sum(r['public_contract_queries'] for r in rows)
    if (calls,readouts,queries)!=(192,6,156):failures.append('call_accounting')
    if any(name in sys.modules for name in ('numpy','scipy','torch','threadpoolctl')):failures.append('forbidden_numeric_import')
    container_bytes,container_length=container_stats(rows)
    if container_bytes>cfg['max_array_bytes'] or container_length>cfg['maximum_dimension']:failures.append('numeric_container_cap')
    unchanged()
    result=dict(task_id='AL18',dispatch_id=cfg['dispatch_id'],observed_at=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),command=sys.argv,
        freeze_sha256=sha(freeze_path),frozen_files=lock['files'],dependencies=lock['dependencies'],old_artifacts_unchanged=True,
        status='pass_conditional_numerical_contract_software' if not failures else 'failure_preserved',failures=failures,
        records=rows,state_counts=dict(Counter(r.get('result',{}).get('status','unhandled') for r in rows)),
        family_counts=dict(Counter(str(r['family']) for r in rows)),
        calls=dict(bounded_identity_mock_probes=calls,repeat_endpoint_readouts=readouts,public_contract_queries=queries,
            AL15_core_calls=0,real_AE_calls=0,meaning='N2 has four R mocks per corner; other supplied endpoints are inputs, not hidden probe calls'),
        numeric_convention=dict(norm='Euclidean; squared energies are sums',
            safety_arithmetic='Exact Fraction throughout; nonsquare norms have rational dyadic enclosure checked by exact squaring',
            rational_serialization='numerator/denominator strings',display_only='Nearest float; not an upper rounding or certification',
            assumptions='Bounds only conditionally valid under supplied analytic mock definitions; unknown/empirical-only stays uncertified',
            nonsquare_norm_path_exercised=False),
        resources=dict(wall_seconds=time.perf_counter()-started,process_cpu_seconds=time.process_time()-cpu_start,
            numeric_worker_cap=2,observed_worker_names=sorted({r['worker'] for r in rows}),
            implementation='Python stdlib only',python=sys.version,max_vector_dimension=2,numpy_arrays_allocated=0,
            max_observed_numeric_container_bytes=container_bytes,max_observed_numeric_container_length=container_length,
            container_measurement='sys.getsizeof of each numeric tuple/list plus scalar objects and Fraction integers; not process RSS',
            process_peak_RSS='not_measured',server_access=False,media_read=False,
            gpu_used=False,training_steps=0,classifier_fitting=False,cumulative_project_usage='unknown; unchanged'),
        scope='Conditional arithmetic contract on fixed controlled mocks only; no novelty, origin accuracy, real AE precision or paid-stage admission',
        AL19_executed=False,AL15_replayed=False,scientific_breakthrough=False)
    save(args.output,result)
    print(json.dumps(dict(status=result['status'],records=len(rows),state_counts=result['state_counts'],calls=result['calls'],
        failures=failures,workers=result['resources']['observed_worker_names'],wall_seconds=result['resources']['wall_seconds']),indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        path=OUT/'AL18_startup_or_unhandled_failure.json'
        if not path.exists():save(path,dict(status='unhandled_failure_preserved',error=repr(exc),script_sha256=sha(Path(__file__))))
        raise
