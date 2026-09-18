"""One AL32 frozen arithmetic batch. No optimizer or old runtime module imports."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='2'
import ctypes
from datetime import datetime,timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'research-runs/algorithm_search_20260918'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT/('AL32_'+name+'.json')).read_text(encoding='utf-8'))


def save(name,data):
    with (OUT/('AL32_'+name+'.json')).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')


def main():
    assert not (OUT/'AL32_started.json').exists() and not (OUT/'AL32_evidence.json').exists(),'batch already started'
    frozen=load('freeze')
    for category in ['inputs','dependencies','historical']:
        for p,digest in frozen[category].items(): assert sha(ROOT/p)==digest,(category,p)
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'commit first'
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for path in [*frozen['inputs'],'research-runs/algorithm_search_20260918/AL32_freeze.json']:
        assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)).hexdigest()==sha(ROOT/path)
    save('started',dict(started_at=datetime.now(timezone.utc).isoformat(),commit=revision,
                        freeze_sha256=sha(OUT/'AL32_freeze.json'),single_batch=True))
    wall,cpu=time.perf_counter(),time.process_time()
    evidence=dict(commit=revision,freeze_sha256=sha(OUT/'AL32_freeze.json'),checks=[],failures=[],
        archived_field_processing=[],abstract_fixed_point_processing=[],resources={},
        calls={k:0 for k in ['field_cases','field_filters','field_array_additions','field_elementwise_products',
          'field_mean_reductions','field_scalar_normalizations','literal_q_reuses','four_term_score_calls',
          'score_scalar_multiplications','score_accumulator_additions','generic_12_dot_calls',
          'field_matrix_reconstructions','metric_matrix_products','panel_coordinate_products',
          'parameter_map_products','gradient_transform_products','hessian_transform_products',
          'fixed_objective_evaluations','objective_matrix_products','objective_data_mean_reductions',
          'independent_exact_field_references','independent_exact_panel_references',
          'candidate_penalty_scalar_multiplications','candidate_penalty_sum_additions',
          'optimizer_calls','old_readout_calls','probe_calls','AE_calls','filtering_calls']})
    try:
        import numpy as np
        from exact import transpose,multiply,vector,strings,field_reference,panel_reference
        from kernels import stable_filter,four_term_score,fixed_objective
        config,inputs=load('config'),load('inputs'); calls=evidence['calls']; tol=config['tolerance']
        libs=list((Path(np.__file__).parent.parent/'numpy.libs').glob('*openblas*.dll'))
        assert len(libs)==1
        library=ctypes.CDLL(str(libs[0])); setter=library.scipy_openblas_set_num_threads64_
        getter=library.scipy_openblas_get_num_threads64_; setter.argtypes=[ctypes.c_int]; getter.restype=ctypes.c_int
        setter(2); assert getter()==2
        evidence['resources'].update(native_threads_before=getter(),numpy_version=np.__version__,
            native_library=str(libs[0]),max_array_bytes=0,arrays=[],peak_rss_bytes=None,
            peak_rss_note='not measured; single-array bound is not an RSS bound',
            sequential_execution=True,server_calls=0,gpu_calls=0,real_classifier_training_calls=0)
        def check(name,passed,**details):
            evidence['checks'].append(dict(name=name,passed=bool(passed),**details))
            if not passed: evidence['failures'].append(dict(check=name,details=details))
        def array(name,values):
            result=np.array(values,dtype=np.float64)
            assert result.nbytes<=config['max_array_bytes'] and np.isfinite(result).all()
            evidence['resources']['max_array_bytes']=max(result.nbytes,evidence['resources']['max_array_bytes'])
            evidence['resources']['arrays'].append(dict(name=name,shape=list(result.shape),bytes=result.nbytes))
            return result
        def product(kind,left,right):
            calls[kind]+=1
            return left@right
        def error(actual,expected):
            return float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
        for source in ['field_source','panel_source']:
            check(source+'/source_bytes',sha(ROOT/inputs[source]['path'])==inputs[source]['sha256'])
        evidence['old_gates']={name:json.loads((OUT/(name+'_evidence.json')).read_text(encoding='utf-8'))['gate_result']
                               for name in ['AL27','AL30']}
        check('preserved_old_gates',evidence['old_gates']==config['expected_old_gate'])
        m_exact=[[F(v) for v in row] for row in config['M']]
        inv_exact=[[F(v) for v in row] for row in config['M_inverse']]
        b_exact=[[F(v) for v in row] for row in config['B']]
        identity=[[F(int(i==j)) for j in range(3)] for i in range(3)]
        metric_exact=multiply(b_exact,transpose(b_exact))
        exact_matrices=dict(M_inverse_left=multiply(inv_exact,m_exact),M_inverse_right=multiply(m_exact,inv_exact),
                            MMt=multiply(m_exact,transpose(m_exact)),BBt=metric_exact)
        evidence['exact_matrices']={k:strings(v) for k,v in exact_matrices.items()}
        check('exact_inverse_both_sides',exact_matrices['M_inverse_left']==identity and exact_matrices['M_inverse_right']==identity)
        check('exact_metrics',exact_matrices['MMt']==config['expected_MMt'] and metric_exact==config['expected_BBt'])
        m=array('M',config['M']); inverse=array('M_inverse',[[float(v) for v in row] for row in inv_exact])
        block=array('B',config['B']); metric=product('metric_matrix_products',block,block.T)
        check('float_metric',np.array_equal(metric,np.array(config['expected_BBt'])))
        weights=[float(F(v)) for v in config['weights']]
        embedded=array('embedded_gamma',[float(F(v)) for v in config['points'][1]['gamma']])
        candidate_penalty=float(F(config['candidate_lambda']))*sum(v*v for v in weights)
        calls['candidate_penalty_scalar_multiplications']=5  # four squares, lambda scaling
        calls['candidate_penalty_sum_additions']=4
        check('candidate_embedded_penalty',abs(candidate_penalty-float(F(config['points'][1]['expected_penalty'])))<=tol)
        evidence['candidate_embedded_penalty']=candidate_penalty
        # Part A: archived response fields; never used as samples in Part B.
        assert [c['id'] for c in inputs['archived_fields']]==inputs['field_source']['case_ids']
        for case in inputs['archived_fields']:
            calls['field_cases']+=1
            entry=dict(id=case['id'],evidence_role=case['evidence_role'],filters=[])
            evidence['archived_field_processing'].append(entry)
            assert [f['filter'] for f in case['filters']]==config['filter_order']
            features=[]
            for source in case['filters']:
                calls['field_filters']+=1
                stable=stable_filter(source,calls)
                r=array(case['id']+'/'+source['filter']+'/r',stable['r'])
                z=array(case['id']+'/'+source['filter']+'/raw_z',source['z'])
                predicted=product('field_matrix_reconstructions',m,z)
                reconstructed=product('field_matrix_reconstructions',inverse,r)
                reference=field_reference(source); calls['independent_exact_field_references']+=1
                item=dict(filter=source['filter'],support_shape=source['support_shape'],D=source['D'],
                    D_hex=source['D'].hex(),raw={k:v for k,v in source.items() if k not in ['filtered_fields','expected_q_hex']},
                    raw_z_hex=[v.hex() for v in source['z']],raw_z_signs=np.sign(z).astype(int).tolist(),
                    raw_compact_hex=source['q_compact_raw'].hex(),raw_compact_sign=int(np.sign(source['q_compact_raw'])),
                    stable=stable,exact_from_archived_binary_fields=strings(reference),
                    M_times_stored_z=predicted.tolist(),stable_minus_Mz=(r-predicted).tolist(),
                    inverse_times_stable_r=reconstructed.tolist(),reconstructed_z_minus_raw=(reconstructed-z).tolist(),
                    rK_minus_raw_compact=stable['r'][1]-source['q_compact_raw'])
                entry['filters'].append(item); features.extend(stable['r'])
                evidence['resources']['max_array_bytes']=max(stable['max_array_bytes'],evidence['resources']['max_array_bytes'])
                check(case['id']+'/'+source['filter']+'/literal_q_hex',stable['r_hex'][1]==source['expected_q_hex'])
                diff=error(r,[float(v) for v in reference])
                check(case['id']+'/'+source['filter']+'/exact_field_arithmetic_reference',diff<=tol,max_abs_error=diff)
            r12=array(case['id']+'/r12',features)
            entry['r12']=features; entry['raw_z12']=case['z12']; entry['raw_compact_q4']=case['q4_compact_raw']
            entry['candidate_four_score']=four_term_score(weights,case['q4_direct'],calls)
            entry['stable_four_score']=four_term_score(weights,features[1::3],calls)
            generic=float(product('generic_12_dot_calls',embedded,r12))
            entry['generic_12_score']=dict(value=generic,hex=generic.hex(),
                minus_shared_four_score=generic-entry['candidate_four_score']['value'])
            check(case['id']+'/same_four_term_score_hex',entry['candidate_four_score']['hex']==entry['stable_four_score']['hex'])
        # Part B: AL30's three known abstract regressions at precisely two points.
        original_panel_source=json.loads((ROOT/inputs['panel_source']['path']).read_text(encoding='utf-8'))
        selected=[p for p in original_panel_source['panels'] if p['name'] in inputs['panel_source']['names']]
        check('exact_known_regression_selection',selected==inputs['abstract_panels'] and
              [p['name'] for p in selected]==['aligned','full_rank','symmetric'])
        reg=float(F(config['free_lambda']))
        for panel in inputs['abstract_panels']:
            entry=dict(name=panel['name'],evidence_role='known_abstract_regression_fixed_points',points=[])
            evidence['abstract_fixed_point_processing'].append(entry)
            reference=panel_reference(panel,b_exact,config['points'],F(config['free_lambda']))
            calls['independent_exact_panel_references']+=1; entry['exact']=reference
            check(panel['name']+'/exact_difference_transform',reference['difference_transform_exact'])
            plus=array(panel['name']+'/plus_z',[[float(F(v)) for v in row] for row in panel['plus']])
            minus=array(panel['name']+'/minus_z',[[float(F(v)) for v in row] for row in panel['minus']])
            rplus=product('panel_coordinate_products',plus,block.T)
            rminus=product('panel_coordinate_products',minus,block.T)
            dz=plus-minus; dr=rplus-rminus
            direct_dr=product('panel_coordinate_products',dz,block.T)
            entry.update(plus_r=rplus.tolist(),minus_r=rminus.tolist(),delta_z=dz.tolist(),delta_r=dr.tolist())
            exact_input_error=max(error(actual,[[float(F(v)) for v in row] for row in reference[key]])
                                  for actual,key in [(rplus,'plus_r'),(rminus,'minus_r'),(dz,'delta_z'),(dr,'delta_r')])
            check(panel['name']+'/fraction_input_reference',exact_input_error<=tol,max_abs_error=exact_input_error)
            check(panel['name']+'/float_input_transform',error(dr,direct_dr)<=tol,
                  max_abs_error=error(dr,direct_dr))
            for point,exact_point in zip(config['points'],reference['points']):
                gamma=array(panel['name']+'/'+point['name']+'/gamma',[float(F(v)) for v in point['gamma']])
                beta=product('parameter_map_products',block.T,gamma)
                check(panel['name']+'/'+point['name']+'/exact_parameter_and_penalty',exact_point['exact_equal'] and
                      exact_point['beta']==point['expected_beta'] and exact_point['penalty_beta']==point['expected_penalty'])
                beta_eval=fixed_objective(dz,beta,np.eye(12),reg,calls)
                gamma_eval=fixed_objective(dr,gamma,metric,reg,calls)
                transformed_g=product('gradient_transform_products',block,np.array(beta_eval['gradient']))
                transformed_h=product('hessian_transform_products',
                    product('hessian_transform_products',block,np.array(beta_eval['hessian'])),block.T)
                differences=dict(objective=abs(gamma_eval['objective']-beta_eval['objective']),
                    gradient=error(gamma_eval['gradient'],transformed_g),hessian=error(gamma_eval['hessian'],transformed_h),
                    penalty=abs(gamma_eval['penalty']-beta_eval['penalty']),
                    expected_penalty=abs(gamma_eval['penalty']-float(F(point['expected_penalty']))))
                entry['points'].append(dict(name=point['name'],beta=beta.tolist(),gamma=gamma.tolist(),
                    beta_evaluation=beta_eval,gamma_evaluation=gamma_eval,
                    B_grad_beta=transformed_g.tolist(),B_Hess_beta_Bt=transformed_h.tolist(),errors=differences))
                for kind,value in differences.items():
                    check(panel['name']+'/'+point['name']+'/'+kind,value<=tol,max_abs_error=value)
        evidence['resources']['native_threads_after']=getter(); check('native_threads',getter()==2)
        check('single_array_cap',evidence['resources']['max_array_bytes']<=config['max_array_bytes'])
        for category in ['inputs','dependencies','historical']:
            changed=[p for p,digest in frozen[category].items() if sha(ROOT/p)!=digest]
            check(category+'/unchanged_after',not changed,changed=changed)
        evidence['gate_result']='pass' if not evidence['failures'] else 'fail'
    except Exception as exc:
        evidence['failures'].append(dict(exception=repr(exc),traceback=traceback.format_exc()))
        evidence['gate_result']='fail'
    finally:
        evidence['resources']['wall_seconds']=time.perf_counter()-wall
        evidence['resources']['process_cpu_seconds']=time.process_time()-cpu
        evidence['completed_at']=datetime.now(timezone.utc).isoformat()
        evidence['scope']='stable_readout_metric_integration_reference'
        evidence['real_AE_error_bound']=None
        evidence['scientific_innovation_gate_passed']=False
        evidence['strict_numeric_certificate']=False
        save('evidence',evidence)
    print(json.dumps(dict(gate_result=evidence['gate_result'],failures=evidence['failures'],calls=evidence['calls'],
                         resources={k:v for k,v in evidence['resources'].items() if k!='arrays'}),ensure_ascii=False))
    return 0 if evidence['gate_result']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
