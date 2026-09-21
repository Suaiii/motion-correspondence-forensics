from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from reducer import FILTERS, compare, reduce_fields, sha

HERE=Path(__file__).resolve().parent; OUT=HERE/'run_v1'; CONFIG=HERE/'config.json'

def make_case(seed,B,T,H,W,layout):
    a=np.zeros((B,T,H,W,3),dtype=np.float64); b=np.zeros_like(a); va=np.zeros_like(a); vb=np.zeros_like(a)
    for bi in range(B):
      for t in range(T):
       for h in range(H):
        for w in range(W):
         for c in range(3):
          a[bi,t,h,w,c]=((seed+3*bi+5*t+7*h+11*w+13*c)%23-11)/7
          b[bi,t,h,w,c]=((seed+2*bi+3*t+5*h+7*w+17*c)%19-9)/9
          va[bi,t,h,w,c]=((seed+bi+t+h+2*w+c)%13-6)/8
          vb[bi,t,h,w,c]=((seed+2*bi+2*t+3*h+w+2*c)%17-8)/10
    if seed==3: a.fill(0);b.fill(0);va.fill(0);vb.fill(0)
    if seed==4: b=a+1e-8;va.fill(1);vb.fill(-1)
    f={'d_a':a,'d_b':b,'v_a':va,'v_b':vb}
    return ({k:np.transpose(v,(0,4,1,2,3)) for k,v in f.items()} if layout=='BCTHW' else f)

def main():
    if OUT.exists(): raise RuntimeError('run_v1 already exists')
    OUT.mkdir(); cfg=json.loads(CONFIG.read_text(encoding='utf-8')); start=time.perf_counter(); cpu=time.process_time(); checks=[]; failures=[]; rows=[]
    specs=[('C1_non_square',4,3,7,8,'BTHWC',[(0,3)]),('C2_unequal_temporal_blocks',1,7,9,7,'BTHWC',[(0,2),(2,7)]),('C3_zero_fields',3,2,5,5,'BTHWC',[(0,2)]),('C4_near_cancellation',4,3,5,5,'BTHWC',[(0,3)]),('C5_large_interface',1,17,32,48,'BCTHW',[(0,5),(5,17)]),('C6_signed_cross_term',1,4,7,7,'BTHWC',[(0,1),(1,4)])]
    for name,seed,T,H,W,layout,blocks in specs:
        fields=make_case(seed,B=4 if name=='C1_non_square' else 1,T=T,H=H,W=W,layout=layout); r=reduce_fields(fields,layout,blocks)
        canonical={k:(np.transpose(v,(0,2,3,4,1)) if layout=='BCTHW' else v) for k,v in fields.items()}; alt=reduce_fields(canonical,'BTHWC',blocks); ok,err=compare(r['filters'],alt['filters'],cfg['float_abs_tol'],cfg['float_rel_tol']); checks.append({'name':name+'/explicit_layout', 'passed':ok,'max_error':err}); rows.append({'name':name,'shape':list(next(iter(fields.values())).shape),'layout':layout,'blocks':blocks,'filters':r['filters'],'batch_count':len(r['batch'])})
        if not ok: failures.append(name+'/explicit_layout')
        # Analytic/contract checks independent from reducer: zero fields yield zero q/rK and eta-only denominator.
        if name=='C3_zero_fields':
            ok2=all(x['q_direct']==0.0 and x['r_k']==0.0 and x['denominator']>0 for x in r['filters']);checks.append({'name':name+'/zero_eta', 'passed':ok2});
            if not ok2:failures.append(name+'/zero_eta')
    for name,fields,layout,blocks in [('missing',{'d_a':np.zeros((1,2,3,3,3),dtype=np.float64)},'BTHWC',[(0,2)]),('bad_layout',make_case(9,1,2,5,5,'BTHWC'),'BAD',[(0,2)])]:
        try: reduce_fields(fields,layout,blocks); checks.append({'name':'reject_'+name,'passed':False});failures.append('reject_'+name)
        except Exception as e: checks.append({'name':'reject_'+name,'passed':True,'error_type':type(e).__name__})
    evidence={'task_id':'AL78','version':cfg['version'],'started_at':start,'finished_at':time.perf_counter(),'process_cpu_seconds':time.process_time()-cpu,'python':sys.version,'numpy':np.__version__,'config_sha256':sha(CONFIG),'source_sha256':sha(HERE/'reducer.py'),'checks':checks,'failures':failures,'cases':rows,'software_pass':not failures,'scope':'CPU reducer only; no media/model/server/GPU/classifier'}
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'software_pass':evidence['software_pass'],'checks':len(checks),'failures':failures},ensure_ascii=False))
if __name__=='__main__':main()
