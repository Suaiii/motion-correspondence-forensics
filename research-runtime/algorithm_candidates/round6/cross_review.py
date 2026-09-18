"""Independent H-J checks: alternate LP, analytic witnesses, adversarial inputs."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import time
import warnings
from unittest.mock import patch
import numpy as np
from scipy.optimize import linprog,OptimizeWarning
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[3]
PAIRS=((0,1),(1,2),(0,2))
V=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def arraysha(x):return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()


def capped_lp(*args,**kwargs):
    kwargs['options']=dict(kwargs.get('options',{}),threads=2)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',OptimizeWarning)
        return linprog(*args,**kwargs)


def independent_lp(q):
    """Equality slack LP; separately assembles marginals by tensor basis sums."""
    m=q.shape[1];n=m**3;k=3*m*m
    basis=np.eye(n).reshape(n,m,m,m)
    pair=np.concatenate([basis.sum(3).reshape(n,-1),basis.sum(1).reshape(n,-1),basis.sum(2).reshape(n,-1)],axis=1).T
    single=np.concatenate([basis.sum((2,3)),basis.sum((1,3)),basis.sum((1,2))],axis=1).T
    # pair(gamma)-positive_slack+negative_slack=q, all variables nonnegative.
    eq=np.block([[pair,-np.eye(k),np.eye(k)],[single,np.zeros((3*m,2*k))]])
    rhs=np.r_[q.ravel(),np.full(3*m,1/m)]
    cost=np.r_[np.zeros(n),np.full(2*k,1/3)]
    fit=capped_lp(cost,A_eq=eq,b_eq=rhs,bounds=(0,None),method='highs-ds',
        options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    if not fit.success:raise RuntimeError(fit.message)
    dual=fit.eqlin.marginals
    return dict(distance=float(fit.fun),recomputed=float(abs(pair@fit.x[:n]-q.ravel()).sum()/3),
        primal_residual=float(abs(eq@fit.x-rhs).max()),
        dual_constraint_violation=float(max(0,(eq.T@dual-cost).max())),
        duality_gap=float(abs(rhs@dual-fit.fun)),matrix_bytes=eq.nbytes)


def binary_projection(r):
    deficits=1+V@r;i=int(np.argmin(deficits));delta=max(0.,-float(deficits[i]))
    projected=r+delta*V[i]/3
    atoms=np.array(list(itertools.product([-1,1],repeat=3)))
    mass=(1+projected[0]*atoms[:,0]*atoms[:,1]+projected[1]*atoms[:,1]*atoms[:,2]+projected[2]*atoms[:,0]*atoms[:,2])/8
    return projected,mass,delta/3


def uniform_gamma(rng,m):
    g=rng.random((m,m,m))+.05
    for _ in range(1000):
        for axis in range(3):
            marginal=g.sum(tuple(i for i in range(3) if i!=axis))
            shape=[1,1,1];shape[axis]=m;g*=((1/m)/marginal).reshape(shape)
        if max(abs(g.sum(tuple(i for i in range(3) if i!=axis))-1/m).max() for axis in range(3))<1e-13:break
    return g


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    start=time.perf_counter();cfg_path=Path(__file__).with_name('config.json');cfg=json.loads(cfg_path.read_text())
    reference=ROOT/'research-plan/fallback-runtime/joint_marginal_reference.py'
    digest=sha(reference);assert digest==cfg['reviewed_reference_sha256']
    spec=importlib.util.spec_from_file_location('readonly_joint_reference',reference)
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    rng=np.random.default_rng(cfg['al03_seed']);binary=[];cases=[]
    with threadpool_limits(limits=2),patch.object(ref,'linprog',capped_lp):
        correlations=list(rng.uniform(-1,1,(cfg['al03_continuous_binary_cases'],3)))
        for eps in cfg['al03_boundary_epsilons']:
            correlations.extend([np.full(3,-1/3-eps),np.full(3,-1/3+eps)])
        for r in correlations:
            projected,mass,expected=binary_projection(r)
            q=np.stack([ref.q_binary(v) for v in r]);fit=ref.joint_distance(q);own=independent_lp(q)
            assert mass.min()>-1e-12 and abs(mass.sum()-1)<1e-12
            assert abs(fit['distance']-expected)<1e-8 and abs(own['distance']-expected)<1e-8
            assert own['primal_residual']<1e-8 and own['dual_constraint_violation']<1e-8 and own['duality_gap']<1e-8
            binary.append(dict(r=r.tolist(),projection=projected.tolist(),witness_masses=mass.tolist(),
                analytic_distance=expected,reviewed_distance=fit['distance'],independent=own))
        for m in cfg['sizes']:
            g=uniform_gamma(rng,m);qs=np.stack([g.sum(2),g.sum(0),g.sum(1)])
            hard=np.stack([np.eye(m)/m,np.eye(m)/m,np.roll(np.eye(m),1,axis=1)/m])
            for name,q,expected in [('general_compatible_joint',qs,0.),('inconsistent_hard_cycle',hard,2/3)]:
                fit=ref.joint_distance(q);own=independent_lp(q)
                assert abs(fit['distance']-expected)<1e-8 and abs(own['distance']-expected)<1e-8
                cases.append(dict(m=m,name=name,q=q.tolist(),input_sha256=arraysha(q),expected=expected,
                    reviewed_distance=fit['distance'],independent=own,multiplicative_js_same_q=ref.cycle_js(q)))
        q=np.stack([ref.q_binary(-1)]*3);static_outside=ref.joint_distance(q)['distance']
        assert abs(static_outside-2/3)<1e-8
        negative_tau_q=ref.symmetric_kernel_coupling(np.array([[1.,0.],[-1.,0.]]),tau=-.1)
        negative_tau=dict(accepted=True,q=negative_tau_q.tolist(),distance=ref.joint_distance(np.stack([negative_tau_q]*3))['distance'])
        bad={};base=np.stack([ref.q_binary(0)]*3)
        variants={}
        for name,value in [('negative',-1e-5),('nan',float('nan')),('infinity',float('inf'))]:
            x=base.copy();x[0,0,0]=value;variants[name]=x
        x=base.copy();x[0,0,0]+=.01;variants['mass_mismatch']=x
        x=base.copy();x[0,0,:]*=.5;variants['occlusion_lost_mass']=x
        for name,x in variants.items():
            try:ref.joint_distance(x)
            except ValueError:bad[name]='rejected'
            else:bad[name]='accepted'
        near=base.copy();near[0,0,0]+=5e-9
        tolerance_band=ref.joint_distance(near)
    assert sha(reference)==digest
    out=dict(dispatch_id=cfg['dispatch_id'],task_id='AL03',plan_version=cfg['plan_version'],
        status='qualified_mathematical_pass_with_helper_validation_issue',
        observed_utc=datetime.now(timezone.utc).isoformat(),binary_cases=binary,general_cases=cases,
        static_non_gaussian_identical_q_distance=static_outside,negative_temperature_helper=negative_tau,
        invalid_inputs=bad,near_tolerance_input=dict(mass_error=5e-9,accepted=True,distance=tolerance_band['distance']),
        gaussian_integrability_review='u_i*u_j*u_k/S <= u_i*u_j and E[u_i*u_j]=Q_ij finite; Tonelli applies',
        gaussian_proof_status='valid under finite features, tau>0, positive symmetric scaling, complete support',
        geometry_limitation='All independently relabelled copies of one feature set remain jointly realizable',
        reference_sha256=digest,config_sha256=sha(cfg_path),script_sha256=sha(Path(__file__)),
        elapsed_seconds=time.perf_counter()-start,threads=2,
        solver_note='Only runtime linprog threads option added to reviewed calls; reference file unchanged',
        media_read=False,server_accessed=False,gpu_used=False,training_steps=0,
        novelty_established=False,real_detection_evidence=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
    print(json.dumps({k:out[k] for k in ['status','static_non_gaussian_identical_q_distance','negative_temperature_helper','invalid_inputs','near_tolerance_input','elapsed_seconds']},indent=2))


if __name__=='__main__':main()
