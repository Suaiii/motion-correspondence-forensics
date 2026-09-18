"""CPU reference and falsification fixtures for H-J; no media or model training."""
import os
os.environ['OMP_NUM_THREADS']='2'
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['MKL_NUM_THREADS']='2'
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import time
import numpy as np
import scipy
from scipy.optimize import linprog

PAIRS=((0,1),(1,2),(0,2))


def joint_distance(couplings):
    """Average pair-marginal L1 distance, constrained to uniform one-way marginals."""
    q=np.asarray(couplings,dtype=float)
    if q.ndim!=3 or q.shape[0]!=3 or q.shape[1]!=q.shape[2]:
        raise ValueError('Expected three square pair marginals')
    m=q.shape[1]
    if not 2<=m<=8 or not np.isfinite(q).all() or (q<0).any():
        raise ValueError('Invalid finite nonnegative small coupling')
    if max(np.max(np.abs(q.sum(1)-1/m)),np.max(np.abs(q.sum(2)-1/m)))>1e-8:
        raise ValueError('Pair marginals do not have the declared common uniform masses')
    triples=list(itertools.product(range(m),repeat=3));n=len(triples);k=3*m*m
    projections=np.zeros((k,n));singles=np.zeros((3*m,n))
    for col,idx in enumerate(triples):
        for frame in range(3):singles[frame*m+idx[frame],col]=1
        for pair,(a,b) in enumerate(PAIRS):projections[pair*m*m+idx[a]*m+idx[b],col]=1
    a_ub=np.block([[projections,-np.eye(k)],[-projections,-np.eye(k)]])
    b_ub=np.concatenate([q.ravel(),-q.ravel()])
    a_eq=np.concatenate([singles,np.zeros((3*m,k))],axis=1)
    cost=np.concatenate([np.zeros(n),np.full(k,1/3)])
    fit=linprog(cost,A_ub=a_ub,b_ub=b_ub,A_eq=a_eq,b_eq=np.full(3*m,1/m),
        bounds=(0,None),method='highs-ds',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
    if not fit.success:raise RuntimeError(fit.message)
    gamma=fit.x[:n].reshape((m,m,m))
    marg=np.stack([gamma.sum(2),gamma.sum(0),gamma.sum(1)])
    actual=float(np.abs(marg-q).sum()/3)
    residual=float(np.max(np.abs(singles@fit.x[:n]-1/m)))
    assert residual<1e-8 and float(gamma.min())>=-1e-8
    assert abs(actual-fit.fun)<1e-7
    return dict(distance=float(fit.fun),recomputed_distance=actual,single_marginal_error=residual,
        variables=n+k,largest_matrix_bytes=a_ub.nbytes,gamma=gamma)


def q_binary(r):
    return np.array([[1+r,1-r],[1-r,1+r]])/4


def binary_witness(r):
    vertices=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])
    deficits=1+vertices@np.asarray(r)
    return float(max(0.,-deficits.min())/3)


def cycle_js(q):
    m=q.shape[-1];p=m*q[2];other=(m*q[0])@(m*q[1]);mean=(p+other)/2
    a=np.zeros_like(p);b=np.zeros_like(p)
    mask=p>0;a[mask]=p[mask]*np.log(p[mask]/mean[mask])
    mask=other>0;b[mask]=other[mask]*np.log(other[mask]/mean[mask])
    return float(.5*(a+b).sum(1).mean())


def symmetric_kernel_coupling(z,tau=.1):
    z=np.asarray(z,dtype=float);z=z/np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)
    kernel=np.exp((z@z.T-1)/tau);m=len(z);d=np.ones(m)
    for _ in range(20000):
        mass=d*(kernel@d)
        if np.max(np.abs(mass-1/m))<1e-13:break
        d*=np.sqrt((1/m)/mass)
    q=d[:,None]*kernel*d[None,:]
    assert np.max(np.abs(q.sum(1)-1/m))<1e-11
    return q


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Keep prior evidence; use a new output')
    start=time.perf_counter();rows=[];errors=[];max_bytes=0
    # Entire fixed grid; no search for favorable examples or parameter selection.
    for r in itertools.product([-1.,-.5,0.,.5,1.],repeat=3):
        q=np.stack([q_binary(x) for x in r]);fit=joint_distance(q);expected=binary_witness(r)
        errors.append(abs(fit['distance']-expected));max_bytes=max(max_bytes,fit['largest_matrix_bytes'])
    assert max(errors)<1e-8
    examples={}
    for name,r in [('compatible_ambiguous',[.5,.5,.5]),('incompatible',[-.5,-.5,-.5])]:
        q=np.stack([q_binary(x) for x in r]);fit=joint_distance(q)
        examples[name]=dict(correlations=r,joint_distance=fit['distance'],multiplicative_js=cycle_js(q),
            gamma=fit['gamma'].tolist(),marginal_error=fit['single_marginal_error'])
    assert abs(examples['compatible_ambiguous']['joint_distance'])<1e-8
    assert examples['compatible_ambiguous']['multiplicative_js']>1e-5
    assert abs(examples['incompatible']['joint_distance']-1/6)<1e-8
    for seed in (17,29,43,59,71):
        rng=np.random.default_rng(seed)
        for m in (2,4,8):
            q=symmetric_kernel_coupling(rng.normal(size=(m,8)))
            perms=[rng.permutation(m) for _ in range(3)]
            cases={'static':np.stack([q,q,q]),'consistent_permutation':np.stack([q[np.ix_(perms[a],perms[b])] for a,b in PAIRS])}
            for kind,qs in cases.items():
                fit=joint_distance(qs);max_bytes=max(max_bytes,fit['largest_matrix_bytes'])
                assert abs(fit['distance'])<1e-8,(seed,m,kind,fit['distance'])
                rows.append(dict(seed=seed,m=m,case=kind,joint_distance=fit['distance'],multiplicative_js=cycle_js(qs),single_marginal_error=fit['single_marginal_error']))
    malformed=np.stack([q_binary(0)]*3);malformed[0,0,0]+=.01
    try:joint_distance(malformed)
    except ValueError:rejected=True
    else:rejected=False
    assert rejected
    result=dict(candidate='H-J',implementation='CPU small LP reference',status='pass_limited_structural_checks',
        observed_utc=datetime.now(timezone.utc).isoformat(),binary_grid_cases=len(errors),binary_formula_max_error=max(errors),
        examples=examples,static_and_permutation_cases=rows,max_numpy_constraint_matrix_bytes=max_bytes,
        mismatched_mass_rejected=rejected,scipy_version=scipy.__version__,numpy_version=np.__version__,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),elapsed_seconds=time.perf_counter()-start,
        gpu_used=False,media_read=False,training_steps=0,scientific_breakthrough=False,independent_review_completed=False,
        limitations=['Classical marginal compatibility foundation, not a novelty proof','Uniform complete support only; rejecting malformed mass is not occlusion robustness','No detector, real feature extraction, trained baseline or generalization evidence'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['static_and_permutation_cases','examples']},indent=2))
    print(json.dumps(examples,indent=2))


if __name__=='__main__':main()
