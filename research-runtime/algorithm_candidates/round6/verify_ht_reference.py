"""Independent entropy checks on new probability tables, no classifier fitting."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='2'
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.optimize import minimize_scalar
from threadpoolctl import threadpool_limits
from higher_order_reference import binary_maxent,pair_marginals


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    started=time.perf_counter();rng=np.random.default_rng(2909);checks=[]
    sign=np.fromfunction(lambda i,j,k:(-1.)**(i+j+k),(2,2,2))
    tables=[np.ones((2,2,2))/8,(1+sign)/8]
    tables += [rng.dirichlet(np.ones(8)).reshape(2,2,2) for _ in range(12)]
    def entropy(p):
        p=p[p>0];return float(-np.sum(p*np.log(p)))
    with threadpool_limits(limits=2):
        for p in tables:
            actual,_=binary_maxent(p);lo=-p[sign>0].min();hi=p[sign<0].min()
            fit=minimize_scalar(lambda eta:-entropy(p+eta*sign),bounds=(lo,hi),method='bounded',
                options={'xatol':1e-14}) if hi>lo else None
            gap=abs(entropy(actual)+fit.fun) if fit else 0.
            marginal=max(abs(a-b).max() for a,b in zip(pair_marginals(p),pair_marginals(actual)))
            assert gap<1e-10 and marginal<1e-12 and entropy(actual)>=entropy(p)-1e-12
            checks.append(dict(entropy_gap=gap,marginal_error=marginal,min_mass=float(actual.min())))
    result=dict(status='pass',scope='binary_reference_solver_only',cases=len(checks),checks=checks,
        prototype_sha256=hashlib.sha256(Path(__file__).with_name('higher_order_reference.py').read_bytes()).hexdigest(),
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        elapsed_seconds=time.perf_counter()-started,threads=2,training_steps=0,real_data=False)
    with args.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status='pass',cases=len(checks),max_entropy_gap=max(c['entropy_gap'] for c in checks))))


if __name__=='__main__':main()
