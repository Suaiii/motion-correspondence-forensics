"""Run only normalization recovery and previously interrupted edge checks."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from threadpoolctl import threadpool_limits,threadpool_info
import joint_v2 as v2
import balance_newton
from run_package import HERE,ROOT,OUT,sha,save,now,git


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
    p.add_argument('--output',type=Path,default=OUT/'AL01_normalization_recovery.json');args=p.parse_args()
    lock=OUT/'AL01_normalization_freeze.json'
    if args.mode=='prepare':
        paths=[HERE/'balance_newton.py',Path(__file__),HERE/'joint_v2.py',HERE/'run_package.py',HERE/'config.json',
            OUT/'AL01_inputs.json',OUT/'AL01_evidence.json',OUT/'AL01_freeze.json',OUT/'AL01_normalization_note.md']
        save(lock,dict(frozen_at=now(),failure_commit='81e7087',
            files={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in paths},
            unchanged_problem='same inputs, tau=.1, KL scaling objective, target masses and 1e-12 residual',
            solver='fixed 100 Newton steps, 40 backtracks, last dual coordinate fixed to zero'))
        print('Frozen numerical recovery before execution');return
    if args.output.exists():raise FileExistsError(args.output)
    freeze=json.loads(lock.read_text(encoding='utf-8'))
    def unchanged():
        for name,digest in freeze['files'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Changed recovery source/input: '+name)
        oldfreeze=json.loads((OUT/'AL01_freeze.json').read_text(encoding='utf-8'))
        for name,digest in oldfreeze['preserved_AL04'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Changed AL04 artifact: '+name)
    unchanged();start=time.perf_counter();rows=[];errors=[]
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    cases=json.loads((OUT/'AL01_inputs.json').read_text(encoding='utf-8'))['cases']
    previous=json.loads((OUT/'AL01_evidence.json').read_text(encoding='utf-8'))
    with threadpool_limits(limits=2):
        pools=threadpool_info()
        for case in cases:
            if case['kind']!='features':continue
            row=dict(id=case['id'],split=case['split'],checks={})
            try:
                frames=np.asarray(case['frames']);z=np.asarray(case['z'])
                normalized=[balance_newton.normalization_pair(frames[a],frames[b],cfg['temperature']) for a,b in v2.PAIRS]
                raw=np.stack([x['row_only_joint'] for x in normalized]);balanced=np.stack([x['balanced_joint'] for x in normalized])
                fit=v2.joint_distance(balanced)
                try:v2.joint_distance(raw);raw_status='accepted'
                except v2.InputDomainError:raw_status='unsupported_uniform_masses'
                row.update(normalization_certificates=normalized,raw_status=raw_status,
                    raw_summaries=v2.summaries(raw),balanced_summaries=v2.summaries(balanced),balanced_fit=fit,
                    total_Q_l1_change=float(abs(raw-balanced).sum()))
                oldrow=next(r for r in previous['rows'] if r['id']==case['id'])
                row['prior_status']=oldrow.get('status','returned')
                if 'normalization' in oldrow:
                    prior=np.asarray(oldrow['normalization']['balanced_Q'])
                    row['previous_converged_max_gap']=float(abs(prior-balanced).max())
                    row['checks']['same_solution_as_previous_converged_case']=row['previous_converged_max_gap']<1e-10
                row['checks']['normalization_problem_certified']=all(x['max_mass_error']<1e-12 and x['log_scaling_stationarity_error']<1e-10 for x in normalized)
                row['checks']['raw_input_rejected']=raw_status=='unsupported_uniform_masses'
                original=v2.symmetric_kernel_coupling(z,cfg['temperature'])
                row['checks']['large_finite_normalization']=np.max(abs(v2.symmetric_kernel_coupling(z*1e250)-original))<1e-10
                row['checks']['small_finite_normalization']=np.max(abs(v2.symmetric_kernel_coupling(z*1e-250)-original))<1e-10
            except Exception as exc:
                row['error']=repr(exc);errors.append(case['id'])
            row['checks']={k:bool(v) for k,v in row['checks'].items()}
            if not all(row['checks'].values()):errors.append(case['id'])
            rows.append(row)
    unchanged()
    result=dict(task_id='AL01',scope='same-objective normalization recovery only',observed_at=now(),
        git_revision=git('rev-parse','HEAD').decode().strip(),command=vars(args)|{'output':str(args.output)},
        freeze_sha256=sha(lock),files=freeze['files'],initial_evidence_sha256=sha(OUT/'AL01_evidence.json'),
        initial_failure_preserved=True,AL04_unchanged=True,
        status='pass_same_problem_recovery' if not errors else 'failure_preserved',failures=errors,rows=rows,
        scientific_criteria_changed=False,independent_review='pending',scientific_breakthrough=False,
        elapsed_seconds=time.perf_counter()-start,threads=2,threadpools=pools,
        server_access=False,media_read=False,gpu_used=False,training_steps=0)
    save(args.output,result)
    print(json.dumps(dict(status=result['status'],failures=errors,elapsed_seconds=result['elapsed_seconds'],
        normalization=[dict(id=r['id'],raw_js=r.get('raw_summaries',{}).get('forward_js'),
            balanced_js=r.get('balanced_summaries',{}).get('forward_js'),DJ=r.get('balanced_fit',{}).get('distance'),
            iterations=[x['iterations'] for x in r.get('normalization_certificates',[])]) for r in rows]),indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
