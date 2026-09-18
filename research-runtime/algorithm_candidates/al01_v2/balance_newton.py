"""Numerical recovery of the same positive-kernel uniform scaling problem.

The original Sinkhorn failure, candidate LP, tau and inputs remain unchanged.
"""
import numpy as np
from scipy.special import logsumexp
from joint_v2 import kernel,NumericalDomainError


def normalization_pair(a,b,tau=.1):
    k=kernel(a,b,tau);m=len(k);logk=np.log(k);beta=np.zeros(m)
    raw=k/k.sum(1,keepdims=True)/m
    def state(beta):
        logits=logk+beta[None,:];denom=logsumexp(logits,axis=1)
        p=np.exp(logits-denom[:,None]);q=p/m
        gradient=q.sum(0)-1/m
        objective=float(denom.mean()-beta.mean())
        return p,q,gradient,objective,denom
    history=[]
    for iteration in range(100):
        p,q,gradient,objective,denom=state(beta)
        error=float(abs(gradient).max());history.append(error)
        if error<1e-12:break
        hessian=(np.diag(p.sum(0))-p.T@p)/m
        try:direction=np.linalg.solve(hessian[:-1,:-1],-gradient[:-1])
        except np.linalg.LinAlgError as exc:raise NumericalDomainError('Scaling Hessian singular') from exc
        step=np.r_[direction,0.]
        descent=float(gradient@step)
        accepted=False
        for backtrack in range(40):
            alpha=2.**(-backtrack)
            next_beta=beta+alpha*step
            _,_,next_gradient,next_objective,_=state(next_beta)
            # Residual alternative avoids cancellation in a nearly flat dual.
            if next_objective<=objective+1e-4*alpha*descent or abs(next_gradient).max()<.9*error:
                beta=next_beta;accepted=True;break
        if not accepted:raise NumericalDomainError('Fixed Newton backtracking budget exhausted')
    else:raise NumericalDomainError('Fixed Newton iteration budget exhausted')
    logu=-np.log(m)-denom
    stationarity=float(abs(np.log(q/k)-(logu[:,None]+beta[None,:])).max())
    mass_error=float(max(abs(q.sum(0)-1/m).max(),abs(q.sum(1)-1/m).max()))
    if mass_error>=1e-12 or stationarity>1e-10 or q.min()<=0:
        raise NumericalDomainError('Uniform scaling/KKT certificate failed')
    return dict(row_only_joint=raw,balanced_joint=q,iterations=iteration+1,
        max_mass_error=mass_error,log_scaling_stationarity_error=stationarity,
        residual_history=history,log_row_scaling=logu,log_column_scaling=beta,
        objective='sum(Q*log(Q/K)-Q); same uniform row/column constraints as original Sinkhorn')
