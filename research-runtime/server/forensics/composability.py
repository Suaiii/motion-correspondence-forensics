"""Numerical reference for WORK_PLAN cvpr27-20260917-v1.

Frozen local correspondences, direct/two-step JS, and one-sided middle-node
permutation responses. No detector, novelty claim or physical-law claim.
"""
from __future__ import annotations
import numpy as np
from .composability_config import A,frame_count,triplets as configured_triplets

TRIPLETS=((0,1,2),(1,2,3),(2,3,4),(3,4,5),(0,2,4),(1,3,5))
STATIC_TRIPLETS=tuple((i,i,i) for i in range(6))


def branch_triplets(branch_mode,candidate_id=A):
    return configured_triplets(candidate_id,branch_mode)


def correspondence(a,b,temperature=.1):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.ndim!=2 or b.ndim!=2 or a.shape[1]!=b.shape[1] or min(a.shape+b.shape)<1:
        raise ValueError('Features must be nonempty [patch,channel] with shared channels')
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not np.isfinite(temperature) or temperature<=0:
        raise ValueError('Finite features and positive finite temperature required')
    a=a/np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-12)
    b=b/np.maximum(np.linalg.norm(b,axis=1,keepdims=True),1e-12)
    scores=(a@b.T)/temperature;scores-=scores.max(axis=1,keepdims=True)
    p=np.exp(scores);return p/p.sum(axis=1,keepdims=True)


def stochastic(p):
    p=np.asarray(p,dtype=np.float64)
    if p.ndim!=2 or min(p.shape)<1 or not np.isfinite(p).all() or (p<0).any():
        raise ValueError('Expected finite nonnegative probability matrix')
    if not np.allclose(p.sum(1),1,atol=1e-10,rtol=1e-8):
        raise ValueError('Rows must sum to one; no silent renormalization')
    return p


def js_rows(p,q):
    p=stochastic(p);q=stochastic(q)
    if p.shape!=q.shape:raise ValueError('JS distributions must have the same shape')
    middle=(p+q)/2
    def kl(x):
        ratio=np.divide(x,middle,out=np.ones_like(x),where=x>0)
        return (x*np.log(ratio)).sum(-1)
    return .5*(kl(p)+kl(q))


def shift_permutation(grid,dy,dx):
    h,w=grid
    if h<1 or w<1 or not isinstance(dy,int) or not isinstance(dx,int):
        raise ValueError('Positive grid and integer shift required')
    yy,xx=np.mgrid[:h,:w]
    perm=(((yy+dy)%h)*w+(xx+dx)%w).ravel()
    wrap=(yy+dy<0)|(yy+dy>=h)|(xx+dx<0)|(xx+dx>=w)
    return perm,wrap.ravel()


def response_from_matrices(ab,bc,ac,permutations,middle_support=None):
    ab=stochastic(ab);bc=stochastic(bc);ac=stochastic(ac)
    if ab.shape[1]!=bc.shape[0] or ac.shape!=(ab.shape[0],bc.shape[1]):
        raise ValueError('Incompatible correspondence dimensions')
    n=bc.shape[0];permutations=[np.asarray(p) for p in permutations]
    if not permutations:raise ValueError('At least one permutation required')
    for p in permutations:
        if p.shape!=(n,) or not np.issubdtype(p.dtype,np.integer) or not np.array_equal(np.sort(p),np.arange(n)):
            raise ValueError('Middle-node perturbation must be a bijection')
    keep=np.ones(n,dtype=bool) if middle_support is None else np.asarray(middle_support,dtype=bool)
    if keep.shape!=(n,) or not keep.any():raise ValueError('Nonempty middle support required')
    restricted=ab[:,keep];mass=restricted.sum(1);valid=mass>1e-12
    weights=restricted[valid]/mass[valid,None]
    direct=np.full(ab.shape[0],np.nan);perturbed=np.full((len(permutations),ab.shape[0]),np.nan)
    if valid.any():
        direct[valid]=js_rows(ac[valid],weights@bc[keep])
        for i,perm in enumerate(permutations):
            perturbed[i,valid]=js_rows(ac[valid],weights@bc[perm[keep]])
    return dict(direct_js=direct,perturbed_js=perturbed,response=perturbed-direct[None],
                support=valid,middle_probability_mass=mass)


def six_frame_response(tokens,grid=(16,16),temperature=.1,scales=(1,2,4),interior_control=False,branch_mode='temporal'):
    return correspondence_response(tokens,grid,temperature,scales,interior_control,branch_mode,A)


def correspondence_response(tokens,grid=(16,16),temperature=.1,scales=(1,2,4),interior_control=False,branch_mode='temporal',candidate_id=A):
    tokens=np.asarray(tokens,dtype=np.float64);h,w=grid
    frames=frame_count(candidate_id)
    if tokens.ndim!=3 or tokens.shape[0]!=frames or tokens.shape[1]!=h*w:
        raise ValueError('Expected candidate frame count on the declared patch grid')
    if not scales or len(set(scales))!=len(scales) or any(not isinstance(r,int) or not 0<r<min(h,w) for r in scales):
        raise ValueError('Invalid distinct perturbation scales')
    permutations=[];wrap=[]
    for r in scales:
        for dy,dx in ((0,r),(0,-r),(r,0),(-r,0)):
            p,m=shift_permutation(grid,dy,dx);permutations.append(p);wrap.append(m)
    keep=None
    if interior_control:
        # Cropping anchor rows alone would not remove wrapping, because ab
        # may attend to border middle nodes. Restrict middle probability mass.
        keep=~np.logical_or.reduce(wrap)
        if not keep.any():raise ValueError('No shared non-wrapping middle support')
    pairs={}
    def p(a,b):
        if (a,b) not in pairs:pairs[a,b]=correspondence(tokens[a],tokens[b],temperature)
        return pairs[a,b]
    triplets=branch_triplets(branch_mode,candidate_id)
    results=[];entropy=[]
    for a,b,c in triplets:
        ab,bc,ac=p(a,b),p(b,c),p(a,c)
        results.append(response_from_matrices(ab,bc,ac,permutations,keep))
        entropy.append(np.stack([-(x*np.log(np.maximum(x,np.finfo(float).tiny))).sum(1) for x in (ab,bc,ac)]))
    responses=np.stack([r['response'].reshape(len(scales),4,h*w).mean(1).reshape(len(scales),h,w) for r in results])
    return dict(responses=responses,direct_js=np.stack([r['direct_js'].reshape(h,w) for r in results]),
        correspondence_entropies=np.stack(entropy).reshape(len(triplets),3,h,w),
        support=np.stack([r['support'].reshape(h,w) for r in results]),
        middle_probability_mass=np.stack([r['middle_probability_mass'].reshape(h,w) for r in results]),
        wrapped_middle_fraction=np.array([m.mean() for m in wrap]).reshape(len(scales),4),
        middle_support_fraction=float(keep.mean()) if keep is not None else 1.,
        branch_mode=branch_mode,triplets=triplets,unique_affinity_matrices=len(pairs),candidate_id=candidate_id,frame_count=frames,
        operator=dict(temperature=temperature,scales=list(scales),grid=list(grid),interior_control=interior_control))
