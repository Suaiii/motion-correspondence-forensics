"""H-J v2: checked domain and certificates, unchanged classical marginal LP."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import itertools
import warnings
import numpy as np
from scipy.optimize import linprog, OptimizeWarning

PAIRS=((0,1),(1,2),(0,2))
MASS_TOL=1e-10
ZERO_TOL=1e-8

class InputDomainError(ValueError):
    pass

class NumericalDomainError(RuntimeError):
    pass


def positive_temperature(tau):
    if isinstance(tau,(bool,str,bytes)) or np.ndim(tau)!=0 or np.iscomplexobj(tau):
        raise InputDomainError('Temperature must be a real scalar, not bool/string/array')
    try:
        value=float(tau)
    except (TypeError,ValueError) as exc:
        raise InputDomainError('Temperature must be a positive finite real scalar') from exc
    if not np.isfinite(value) or value<=0:
        raise InputDomainError('Temperature must be positive and finite')
    return value


def features(z):
    if np.iscomplexobj(z):
        raise InputDomainError('Real features required')
    try:
        z=np.asarray(z,dtype=float)
    except (TypeError,ValueError) as exc:
        raise InputDomainError('Numeric features required') from exc
    if z.ndim!=2 or not 2<=z.shape[0]<=8 or not 1<=z.shape[1]<=32 or not np.isfinite(z).all():
        raise InputDomainError('Finite [m,d] features with 2<=m<=8, 1<=d<=32 required')
    scales=abs(z).max(1,keepdims=True)
    if (scales==0).any():
        raise InputDomainError('Zero feature rows have no declared unit-vector meaning')
    # Stable for very small/large finite magnitudes without squaring original z.
    scaled=z/scales
    return scaled/np.linalg.norm(scaled,axis=1,keepdims=True)


def kernel(a,b,tau):
    tau=positive_temperature(tau)
    a=features(a);b=features(b)
    if a.shape!=b.shape:
        raise InputDomainError('Shared patch count and channel dimension required')
    # Clamp only roundoff outside mathematical cosine bounds, no adaptive tau.
    gram=np.clip(a@b.T,-1,1)
    with np.errstate(over='ignore',invalid='ignore'):
        logits=(gram-1)/tau
    if not np.isfinite(logits).all() or logits.min() < -700:
        raise NumericalDomainError('Positive kernel outside supported float64 exponential range')
    return np.exp(logits)


def symmetric_kernel_coupling(z,tau=.1):
    k=kernel(z,z,tau);m=len(k);d=np.ones(m)
    for iteration in range(20000):
        mass=d*(k@d)
        if np.max(abs(mass-1/m))<1e-13:
            break
        d*=np.sqrt((1/m)/mass)
    else:
        raise NumericalDomainError('Symmetric scaling did not converge at fixed tolerance')
    q=d[:,None]*k*d[None,:]
    if not np.isfinite(q).all() or np.max(abs(q.sum(1)-1/m))>1e-11:
        raise NumericalDomainError('Symmetric scaling certificate failed')
    return q


def normalization_pair(a,b,tau=.1):
    k=kernel(a,b,tau);m=len(k)
    raw=k/k.sum(1,keepdims=True)/m
    u=np.ones(m);v=np.ones(m)
    for iteration in range(20000):
        u=(1/m)/(k@v);v=(1/m)/(k.T@u)
        q=u[:,None]*k*v[None,:]
        if max(abs(q.sum(0)-1/m).max(),abs(q.sum(1)-1/m).max())<1e-12:
            break
    else:
        raise NumericalDomainError('Pair Sinkhorn did not converge')
    return dict(row_only_joint=raw,balanced_joint=q,iterations=iteration+1)


def validate_couplings(couplings,full_support=(True,True,True)):
    if np.iscomplexobj(couplings):
        raise InputDomainError('Real coupling required')
    try:q=np.asarray(couplings,dtype=float)
    except (TypeError,ValueError) as exc:raise InputDomainError('Numeric coupling required') from exc
    if q.ndim!=3 or q.shape[0]!=3 or q.shape[1]!=q.shape[2] or not 2<=q.shape[1]<=8:
        raise InputDomainError('Three square couplings with 2<=m<=8 required')
    if not np.isfinite(q).all() or (q<0).any():
        raise InputDomainError('Finite nonnegative couplings required')
    if len(full_support)!=3 or any(value is not True for value in full_support):
        raise InputDomainError('Missing/partial support is outside this complete-support model')
    m=q.shape[1]
    error=float(max(abs(q.sum(1)-1/m).max(),abs(q.sum(2)-1/m).max()))
    if error>MASS_TOL:
        raise InputDomainError('Nonuniform/inconsistent masses; never silently renormalized')
    return q,error


def project(g):return np.stack([g.sum(2),g.sum(0),g.sum(1)])


def joint_distance(couplings,full_support=(True,True,True)):
    q,input_error=validate_couplings(couplings,full_support);m=q.shape[1]
    triples=list(itertools.product(range(m),repeat=3));n=m**3;k=3*m*m
    projections=np.zeros((k,n));singles=np.zeros((3*m,n))
    for col,idx in enumerate(triples):
        for t in range(3):singles[t*m+idx[t],col]=1
        for t,(a,b) in enumerate(PAIRS):projections[t*m*m+idx[a]*m+idx[b],col]=1
    aub=np.block([[projections,-np.eye(k)],[-projections,-np.eye(k)]])
    bub=np.r_[q.ravel(),-q.ravel()]
    aeq=np.c_[singles,np.zeros((3*m,k))];beq=np.full(3*m,1/m)
    cost=np.r_[np.zeros(n),np.full(k,1/3)]
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=OptimizeWarning,message='Unrecognized options detected.*')
        fit=linprog(cost,A_ub=aub,b_ub=bub,A_eq=aeq,b_eq=beq,bounds=(0,None),method='highs-ds',
            options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9,threads=2,parallel=False))
    if not fit.success:raise NumericalDomainError(fit.message)
    gamma=fit.x[:n].reshape(m,m,m)
    recomputed=float(abs(project(gamma)-q).sum()/3)
    y=fit.ineqlin.marginals;lam=fit.eqlin.marginals
    dual=float(bub@y+beq@lam)
    primal=max(float(np.max(aub@fit.x-bub)),float(np.max(abs(aeq@fit.x-beq))),float(-fit.x.min()),0.)
    dual_violation=max(float(np.max(aub.T@y+aeq.T@lam-cost)),float(y.max()),0.)
    gap=abs(float(fit.fun)-dual)
    if max(primal,dual_violation,gap)>1e-8 or abs(recomputed-fit.fun)>1e-7:
        raise NumericalDomainError('Primal/dual/objective certificate exceeds frozen tolerance')
    return dict(distance=float(fit.fun),recomputed_distance=recomputed,input_mass_error=input_error,
        numerical_status='near_zero_not_exact_compatibility' if fit.fun<=ZERO_TOL else 'positive_above_tolerance',
        gamma=gamma,dual_inequality=y,dual_equality=lam,primal_residual=primal,
        dual_violation=dual_violation,duality_gap=gap,max_matrix_bytes=aub.nbytes)


def summaries(q):
    q=np.asarray(q);m=q.shape[1];p=m*q
    lhs=[p[2],p[0],p[1]]
    rhs=[p[0]@p[1],p[2]@p[1].T,p[0].T@p[2]]
    def js(a,b):
        center=(a+b)/2;total=0.
        for v in (a,b):
            mask=v>0;total+=np.sum(v[mask]*np.log(v[mask]/center[mask]))
        return float(total/(2*m))
    residuals=[float(abs(a-b).sum()/m) for a,b in zip(lhs,rhs)]
    mass_error=float(max(abs(q.sum(1)-1/m).max(),abs(q.sum(2)-1/m).max()))
    uniform=mass_error<=MASS_TOL
    # Transposes of row-only conditionals need not be reverse conditionals.
    # Do not label their residuals as three valid probabilistic cycle controls.
    return dict(forward_js=js(lhs[0],rhs[0]),cycle_l1=residuals if uniform else [residuals[0],None,None],
        mean_cycle_l1=float(np.mean(residuals)) if uniform else None,
        cycle_scope='all_three_uniform_mass_cycles' if uniform else 'forward_row_stochastic_cycle_only',
        pair_entropy=[float(-np.sum(v[v>0]*np.log(v[v>0]))) for v in q],
        mass_error=mass_error)


def binary_q(r):return np.array([[1+r,1-r],[1-r,1+r]],dtype=float)/4


def binary_facet_distance(q):
    if q.shape!=(3,2,2):raise ValueError('Only binary uniform marginals')
    r=q[:,0,0]+q[:,1,1]-q[:,0,1]-q[:,1,0]
    v=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])
    return float(max(0,-np.min(1+v@r))/3)
