"""Single fixed AL24 run. Exact small matching plus ordinary-float scalar optimization."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='2'
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from fractions import Fraction as F
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time
import matching
import objective

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'research-runs/algorithm_search_20260918'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):
    if isinstance(v,F):return str(v)
    if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [pack(x) for x in v]
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
def pair_tuple(pairs):return tuple(tuple(x) for x in pairs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT/'AL24_evidence.json');args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'));freeze_path=OUT/'AL24_freeze.json';lock=json.loads(freeze_path.read_text(encoding='utf-8'))
    def unchanged():
        for path,want in dict(lock['files'],**lock['preserved']).items():
            if sha(ROOT/path)!=want:raise ValueError('Frozen/prior file changed: '+path)
        for path,want in lock['dependencies'].items():
            if sha(path)!=want:raise ValueError('Runtime dependency changed')
    unchanged();data=json.loads((OUT/'AL24_inputs.json').read_text(encoding='utf-8'));start=time.perf_counter();cpu_start=time.process_time()
    if cfg['numeric_worker_cap']!=2 or cfg['lambda_target']!='1/1000' or cfg['caliper']!='1/2':raise ValueError('Frozen scope changed')
    def graph_run(record):
        row=dict(id=record['id'],worker=threading.current_thread().name,checks={})
        try:
            result=matching.exact_match(decode(record['left']),decode(record['right']))
            row['result']=result
            expected=record['expected']
            if 'exception' in expected:row['checks']['expected_input_rejection']=False
            else:
                row['checks']=dict(status=result['status']==expected['status'],
                    selected_pairs=result['selected_pairs']==pair_tuple(expected['selected']),
                    cardinality=result['cardinality']==expected['cardinality'],
                    exact_cost=result['total_squared_RMS_cost']==F(expected['cost']),
                    complete_tie_set=result['all_max_cardinality_min_cost_ties']==[pair_tuple(x) for x in expected['ties']],
                    q_not_used=result['q_accessed'] is False)
        except Exception as exc:
            row['error']=type(exc).__name__+': '+str(exc)
            row['checks']['expected_input_rejection']=type(exc).__name__==record['expected'].get('exception')
        row['passed']=all(row['checks'].values());return row
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='AL24match') as pool:
        graph_rows=list(pool.map(graph_run,data['graphs']+data['invalid_graphs']))
    q={key:tuple(F(x) for x in value) for key,value in data['q_values'].items()}
    def objective_run(record):
        row=dict(id=record['id'],worker=threading.current_thread().name,checks={})
        try:
            if record['pairs'] is not None:
                differences=[tuple(x-y for x,y in zip(q[pid],q[nid])) for pid,nid in record['pairs']]
                row['checks']['prespecified_pair_differences']=differences==[tuple(F(x) for x in d) for d in record['differences']]
            else:differences=[tuple(F(x) for x in d) for d in record['differences']]
            obj=objective.FixedObjective(differences,float(F(cfg['lambda_target'])))
            at_one=obj.evaluate(cfg['gradient_sign_check_at'])
            solved=objective.solve_first_coordinate(obj,tuple(cfg['initial_bracket']),cfg['bracket_width_tolerance'],cfg['maximum_iterations'])
            row.update(pairs=record['pairs'],differences=differences,at_w1=at_one,solver=solved,objective_evaluations_total=obj.calls,
                lambda_used=obj.lam,lambda_binary_hex=obj.lam.hex())
            sign='negative' if at_one['gradient'][0]<0 else 'positive' if at_one['gradient'][0]>0 else 'zero'
            row['checks']['gradient_at_one_sign']=sign==record['expected']['gradient_at_one_sign']
            solution=solved.get('solution')
            if solution is None:row['checks']['solution_exists_in_reference']=False
            else:
                t=solution['w'][0]
                if 'solution_open_interval' in record['expected']:
                    lo,hi=record['expected']['solution_open_interval'];row['checks']['analytic_coarse_solution_range']=lo<t<hi
                else:row['checks']['nonempty_zero_difference_solution']=t==record['expected']['solution_exact']
                row['checks']['other_three_weights_fixed']=all(x==0 for x in solution['w'][1:])
                row['checks']['observed_positive_hessian']=solution['hessian'][0][0]>=2*obj.lam
                row['checks']['numeric_gradient_residual']=abs(solution['gradient'][0])<=1e-10
                row['checks']['no_strict_numeric_certificate']=solved.get('rigorous_parameter_error_bound') is None
        except Exception as exc:row['error']=repr(exc);row['checks']['unexpected_error']=False
        row['passed']=all(row['checks'].values());return row
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='AL24objective') as pool:
        objective_rows=list(pool.map(objective_run,data['objectives']))
    g3=next(r for r in graph_rows if r['id']=='G3').get('result')
    pair_binding=dict(M1_is_G3_selected=g3 is not None and g3['selected_pairs']==pair_tuple(data['objectives'][0]['pairs']),
        M2_is_predeclared_unchosen_optimal_tie=g3 is not None and pair_tuple(data['objectives'][1]['pairs']) in g3['all_max_cardinality_min_cost_ties'] and g3['selected_pairs']!=pair_tuple(data['objectives'][1]['pairs']))
    empty_obj=objective.FixedObjective([]);empty_result=objective.solve_first_coordinate(empty_obj)
    g4=next(r for r in graph_rows if r['id']=='G4').get('result')
    empty_pass=g4 is not None and g4['cardinality']==0 and empty_result['status']=='no_training_support' and empty_result['w'] is None and empty_obj.calls==0
    failures=[r['id'] for r in graph_rows+objective_rows if not r['passed']]
    if not all(pair_binding.values()):failures.append('G3_pair_binding')
    if not empty_pass:failures.append('G4_empty_not_zero_difference')
    unchanged()
    result=dict(task_id='AL24',dispatch_id=cfg['dispatch_id'],observed_at=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),freeze_sha256=sha(freeze_path),
        files=lock['files'],dependencies=lock['dependencies'],prior_artifacts_unchanged=True,
        status='pass_matching_and_scalar_objective_reference' if not failures else 'failure_preserved',failures=failures,
        graphs=graph_rows,objectives=objective_rows,G3_pair_binding=pair_binding,
        empty_support_control=dict(result=empty_result,passed=empty_pass,objective_evaluations=empty_obj.calls),
        calls=dict(matching_queries=len(graph_rows),scalar_solver_queries=4,
            value_gradient_hessian_evaluations=sum(r.get('objective_evaluations_total',0) for r in objective_rows),probe=0,model=0),
        resources=dict(wall_seconds=time.perf_counter()-start,process_cpu_seconds=time.process_time()-cpu_start,worker_cap=2,
            worker_pools='Matching pool completes before objective pool starts; at most two numeric workers concurrently',
            workers=sorted({r['worker'] for r in graph_rows+objective_rows}),stdlib_only=True,
            max_actual_items_per_side=2,hard_limit_per_side=4,b_dimension=12,q_dimension=4,
            max_descriptor_container_bytes=max((r.get('result',{}).get('max_descriptor_container_bytes',0) for r in graph_rows),default=0),
            process_peak_RSS='not_measured',server=False,media=False,GPU=False,weights_or_models=False),
        scope='Exact small matching and ordinary-float first-coordinate mathematical objectives only; not a detector or generic four-dimensional optimizer',
        real_source_labels_used=False,classification_probabilities_produced=False,classification_metrics_computed=False,scientific_breakthrough=False)
    save(args.output,result)
    print(json.dumps(dict(status=result['status'],failures=failures,calls=result['calls'],
        solutions=[dict(id=r['id'],w=r.get('solver',{}).get('solution',{}).get('w'),
            gradient=r.get('solver',{}).get('solution',{}).get('gradient'),iterations=r.get('solver',{}).get('iterations')) for r in objective_rows],
        wall_seconds=result['resources']['wall_seconds']),indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
