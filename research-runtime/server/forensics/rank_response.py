"""Reference primitive for local, interpolation-matched operator rank response.

This is an unvalidated research component, not a detector. Rank/census methods
have prior art. D4 transforms preserve the INTEGER displacement norm and each
operator's fractional interpolation weights, not total flow magnitude. Do not
describe the latter as exactly motion-matched; diagnostics expose its mismatch.
"""
from __future__ import annotations

import numpy as np


def displacement_orbit(flow: np.ndarray) -> np.ndarray:
    """Eight D4 actions on floor(flow), plus the unchanged fractional component.

    Coordinates are (dx,dy). Include identity. Stabilizer duplicates have equal
    multiplicity, so their tie contribution has a well-defined neutral value.
    """
    flow=np.asarray(flow,dtype=np.float64)
    if flow.ndim!=3 or flow.shape[-1]!=2 or not np.isfinite(flow).all():
        raise ValueError('Expected finite [H,W,2] flow')
    integer=np.floor(flow);frac=flow-integer
    x,y=integer[...,0],integer[...,1]
    transformed=np.stack([np.stack(pair,-1) for pair in
        [(x,y),(-y,x),(-x,-y),(y,-x),(-x,y),(x,-y),(y,x),(-y,-x)]])
    return transformed+frac[None]


def bilinear_target(target: np.ndarray, displacement: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    target=np.asarray(target,dtype=np.float64); displacement=np.asarray(displacement,dtype=np.float64)
    if target.ndim!=3 or displacement.shape!=target.shape[:2]+(2,):
        raise ValueError('Expected target [H,W,C] and displacement [H,W,2]')
    if not np.isfinite(target).all() or not np.isfinite(displacement).all():
        raise ValueError('Nonfinite image or displacement')
    h,w=target.shape[:2]
    if min(h,w)<2 or target.shape[2]<1:
        raise ValueError('Image grid must be at least 2x2 with a channel')
    yy,xx=np.mgrid[:h,:w]; sx=xx+displacement[...,0];sy=yy+displacement[...,1]
    # Require the full 2x2 interpolation footprint for every operator.
    valid=(sx>=0)&(sx<w-1)&(sy>=0)&(sy<h-1)
    safe_x=np.clip(sx,0,w-1);safe_y=np.clip(sy,0,h-1)
    ix=np.floor(safe_x).astype(int);iy=np.floor(safe_y).astype(int)
    jx=np.minimum(ix+1,w-1);jy=np.minimum(iy+1,h-1)
    fx=(safe_x-ix)[...,None];fy=(safe_y-iy)[...,None]
    value=(1-fx)*(1-fy)*target[iy,ix]+fx*(1-fy)*target[iy,jx]+(1-fx)*fy*target[jy,ix]+fx*fy*target[jy,jx]
    return value,valid


def orbit_rank(errors: np.ndarray, anchor: int=0) -> np.ndarray:
    """Midrank goodness: fraction with larger error plus half of exact ties.

    Invariant to a common strictly increasing transformation of all errors at
    one pixel. This is not invariance to arbitrary transformations of images.
    """
    errors=np.asarray(errors,dtype=np.float64)
    if errors.ndim<2 or errors.shape[0]<2 or not 0<=anchor<errors.shape[0]:
        raise ValueError('Expected an operator axis and a valid anchor')
    if not np.isfinite(errors).all() or (errors<0).any():
        raise ValueError('Errors must be finite and nonnegative')
    correct=errors[anchor]
    return ((errors>correct).sum(0)+.5*(errors==correct).sum(0))/errors.shape[0]


def local_response(reference: np.ndarray,target: np.ndarray,flow: np.ndarray,
                   integer_only: bool=False) -> dict:
    reference=np.asarray(reference,dtype=np.float64);target=np.asarray(target,dtype=np.float64)
    if reference.shape!=target.shape or reference.ndim!=3 or not np.isfinite(reference).all():
        raise ValueError('Expected matching finite reference/target [H,W,C]')
    original=np.asarray(flow,dtype=np.float64)
    applied=np.rint(original) if integer_only else original
    operators=displacement_orbit(applied)
    errors=[]; masks=[]
    for displacement in operators:
        warped,valid=bilinear_target(target,displacement)
        errors.append(np.square(reference-warped).mean(-1));masks.append(valid)
    errors=np.stack(errors);support=np.logical_and.reduce(masks)
    response=orbit_rank(errors)
    response=np.where(support,response,.5)
    norms=np.linalg.norm(operators,axis=-1)
    nontrivial=np.max(np.abs(operators-operators[:1]),axis=(0,3))>0
    # Preserve raw maps for later same-capacity controls. The caller must not
    # silently drop unsupported videos or interpret the support as authenticity.
    return dict(rank=response,support=support,errors=errors,
        diagnostics=dict(common_support_fraction=float(support.mean()),
            nontrivial_orbit_fraction=float(nontrivial[support].mean()) if support.any() else 0.,
            max_total_displacement_norm_change=float(np.max(np.abs(norms-norms[:1]))),
            applied_operator_magnitude_matched=bool(integer_only),
            integer_only=bool(integer_only),
            quantization_l2_error_max=float(np.linalg.norm(applied-original,axis=-1).max())))


def local_histograms(rank: np.ndarray,support: np.ndarray,cell_size: int=4,bins: int=8) -> tuple[np.ndarray,np.ndarray]:
    rank=np.asarray(rank,dtype=np.float64);support=np.asarray(support,dtype=bool)
    if rank.ndim!=2 or support.shape!=rank.shape or cell_size<1 or bins<2:
        raise ValueError('Invalid local histogram shape or resolution')
    if not np.isfinite(rank).all() or (rank<0).any() or (rank>1).any():
        raise ValueError('Ranks must lie in [0,1]')
    h,w=rank.shape
    if h%cell_size or w%cell_size:
        raise ValueError('Grid must divide into complete cells; no hidden cropping')
    hist=np.zeros((h//cell_size,w//cell_size,bins),dtype=np.float64)
    coverage=np.zeros(hist.shape[:2],dtype=np.float64)
    for y in range(hist.shape[0]):
        for x in range(hist.shape[1]):
            part=np.s_[y*cell_size:(y+1)*cell_size,x*cell_size:(x+1)*cell_size]
            mask=support[part];coverage[y,x]=mask.mean()
            if mask.any():
                ids=np.minimum((rank[part][mask]*bins).astype(int),bins-1)
                hist[y,x]=np.bincount(ids,minlength=bins)/mask.sum()
    return hist,coverage
