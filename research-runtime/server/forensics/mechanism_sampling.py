"""Actual-PTS six-frame sampler for the shared 1.5 s / 4 Hz protocol."""
import numpy as np
from .composability import TRIPLETS
from .composability_config import C


def choose_six(pts):
    pts=np.asarray(pts,dtype=np.float64)
    if pts.ndim!=1 or len(pts)<6 or not np.isfinite(pts).all() or not (np.diff(pts)>0).all():
        raise ValueError('Invalid or insufficient native timestamps')
    duration=float(pts[-1]-pts[0]+np.median(np.diff(pts)))
    if duration<1.5-1e-6:raise ValueError('Native duration shorter than 1.5 s window')
    targets=pts[0]+(duration-1.5)/2+np.arange(6)/4
    hi=np.clip(np.searchsorted(pts,targets),0,len(pts)-1);lo=np.maximum(hi-1,0)
    # Resolve mathematical ties despite sub-nanosecond float representation.
    index=np.where(np.abs(pts[lo]-targets)<=np.abs(pts[hi]-targets)+1e-9,lo,hi)
    if len(set(index))!=6:raise ValueError('Repeated native frames; no duplication allowed')
    actual=pts[index];error=actual-targets
    if np.max(np.abs(error))>.125+1e-6:raise ValueError('Nearest-frame error exceeds half a target step')
    joint=np.array([[actual[b]-actual[a],actual[c]-actual[b]] for a,b,c in TRIPLETS])
    return index,dict(indices=index.tolist(),pts=actual.tolist(),targets=targets.tolist(),
        timing_error=error.tolist(),native_duration=duration,window_seconds=1.5,
        target_span_seconds=1.25,actual_span_seconds=float(actual[-1]-actual[0]),
        triplets=[list(t) for t in TRIPLETS],joint_triplet_intervals=joint.tolist(),tie_tolerance_seconds=1e-9)


def choose_centered_three(pts):
    """Candidate C only: software eligibility is not cross-source lag support."""
    pts=np.asarray(pts,dtype=np.float64)
    if pts.ndim!=1 or len(pts)<3 or not np.isfinite(pts).all() or not (np.diff(pts)>0).all():
        raise ValueError('Invalid or insufficient native timestamps')
    duration=float(pts[-1]-pts[0]+np.median(np.diff(pts)))
    if duration<1.5-1e-6:raise ValueError('Native duration shorter than 1.5 s window')
    center=pts[0]+duration/2
    targets=center+np.array([-.5,0.,.5])
    hi=np.clip(np.searchsorted(pts,targets),0,len(pts)-1);lo=np.maximum(hi-1,0)
    index=np.where(np.abs(pts[lo]-targets)<=np.abs(pts[hi]-targets)+1e-9,lo,hi)
    if len(set(index))!=3:raise ValueError('Repeated native frames; no duplication allowed')
    actual=pts[index];error=actual-targets
    if np.max(np.abs(error))>.125+1e-6:raise ValueError('Nearest-frame error exceeds permitted bound')
    return index,dict(candidate_id=C,indices=index.tolist(),pts=actual.tolist(),targets=targets.tolist(),
        timing_error=error.tolist(),native_duration=duration,window_seconds=1.5,target_span_seconds=1.,
        actual_span_seconds=float(actual[-1]-actual[0]),center_target_seconds=float(center),
        center_error_seconds=float(actual[1]-center),triplets=[[0,1,2]],
        joint_triplet_intervals=[[float(actual[1]-actual[0]),float(actual[2]-actual[1])]],
        tie_tolerance_seconds=1e-9,selection_error_limit_seconds=.125,numerical_tolerance_seconds=1e-6,
        real_source_joint_support_established=False)
