"""Classical balanced binary projection certificates, not a novel detector."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import itertools
import numpy as np

PAIRS=((0,1),(1,2),(0,2))
V=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]],dtype=int)


def validate(q,tol=1e-10):
    if np.iscomplexobj(q):raise ValueError('Real couplings required')
    q=np.asarray(q,dtype=float)
    if q.ndim!=3 or q.shape[0]!=3 or q.shape[1]!=q.shape[2] or q.shape[1] not in (2,4,8):
        raise ValueError('Three square even-sized couplings, m=2/4/8')
    m=q.shape[1]
    if not np.isfinite(q).all() or q.min()<0:raise ValueError('Finite nonnegative Q required')
    error=float(max(abs(q.sum(1)-1/m).max(),abs(q.sum(2)-1/m).max()))
    if error>tol:raise ValueError('Uniform mass domain required; no silent balancing')
    return q,error


def partitions(m,representatives=True):
    if m not in (2,4,8):raise ValueError('Small even m only')
    rows=[]
    for positive in itertools.combinations(range(m),m//2):
        if representatives and 0 not in positive:continue
        h=-np.ones(m,dtype=int);h[list(positive)]=1;rows.append(h)
    return np.stack(rows)


def tables(q,h):return [h@matrix@h.T for matrix in q]


def search_tables(corr):
    ab,bc,ac=corr
    best_value=np.inf;best_indices=None;best_v=None;max_array=0
    for v in V:
        facets=1+v[0]*ab[:,:,None]+v[1]*bc[None,:,:]+v[2]*ac[:,None,:]
        max_array=max(max_array,facets.nbytes)
        idx=np.unravel_index(np.argmin(facets),facets.shape)
        value=float(facets[idx])
        if value<best_value:
            best_value=value;best_indices=idx;best_v=v
    return dict(lower_bound=max(0.,-best_value)/3,min_facet=best_value,
        witness_indices=list(best_indices),facet_signs=best_v,max_facet_array_bytes=max_array)


def coarse_tables(q,hs):
    maps=[np.stack([h==-1,h==1]).astype(float) for h in hs]
    return np.stack([maps[a]@q[k]@maps[b].T for k,(a,b) in enumerate(PAIRS)])


def certificate(q):
    q,error=validate(q);m=q.shape[1];h=partitions(m)
    corr=tables(q,h);result=search_tables(corr)
    hs=np.stack([h[i] for i in result['witness_indices']])
    r=np.array([hs[a]@q[k]@hs[b] for k,(a,b) in enumerate(PAIRS)])
    result.update(partition_count=len(h),tested_partition_triples=len(h)**3,
        input_mass_error=error,representative_partitions=h,correlation_tables=np.stack(corr),
        witness_partitions=hs,witness_correlations=r,witness_coarse_Q=coarse_tables(q,hs),
        witness_all_facets=1+V@r)
    # This is a lower bound even for positive input errors within tolerance;
    # equality at the threshold is interpreted only numerically by the harness.
    return result


def simple_controls(q):
    q,_=validate(q);m=q.shape[1];p=m*q
    pairs=[(p[2],p[0]@p[1]),(p[0],p[2]@p[1].T),(p[1],p[0].T@p[2])]
    l1=[];js=[]
    for a,b in pairs:
        mid=(a+b)/2;total=0.
        for x in (a,b):
            nz=x>0;total+=float(np.sum(x[nz]*np.log(x[nz]/mid[nz])))
        js.append(total/(2*m));l1.append(float(abs(a-b).sum()/m))
    return dict(cycle_L1=l1,multiplicative_JS=js,
        pair_entropy=[float(-np.sum(x[x>0]*np.log(x[x>0]))) for x in q])


def direct_pair_checks(q,cert):
    hs=np.asarray(cert['witness_partitions']);r=np.asarray(cert['witness_correlations'])
    coarse=coarse_tables(q,hs)
    recovered=coarse[:,0,0]+coarse[:,1,1]-coarse[:,0,1]-coarse[:,1,0]
    sign_rows=[]
    for epsilon in itertools.product((-1,1),repeat=3):
        changed=hs*np.asarray(epsilon)[:,None]
        rr=np.array([changed[a]@q[k]@changed[b] for k,(a,b) in enumerate(PAIRS)])
        sign_rows.append(dict(vertex_signs=epsilon,all_facets=1+V@rr,
            bound=float(max(0,-np.min(1+V@rr))/3)))
    # Loop enumeration is deliberately separate from matrix multiplication;
    # it checks ab/bc/ac order, signed coarse correlations and contraction input.
    direct=np.zeros((3,2,2))
    for edge,(a,b) in enumerate(PAIRS):
        for i in range(q.shape[1]):
            for j in range(q.shape[2]):
                direct[edge,int(hs[a,i]>0),int(hs[b,j]>0)]+=q[edge,i,j]
    return dict(coarse_loop_max_error=float(abs(direct-coarse).max()),
        correlation_max_error=float(abs(recovered-r).max()),sign_representative_checks=sign_rows)
