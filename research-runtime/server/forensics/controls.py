"""Nearest-integer matched-sampler controls. No learned mask input."""
import cv2
import numpy as np

MECHANISM_ARMS=('raw','correct','wrong','fractional','self_warp')
METHOD_ARMS=('single_contrast','multi_contrast','concat')


def fields(flow,bound=None):
    f=np.asarray(flow,dtype=np.float32)
    clipped=float(np.mean(np.any(np.abs(f)>bound,axis=-1))) if bound is not None else 0.
    if bound is not None:f=np.clip(f,-bound,bound)
    f=(np.rint(f*32)/32).astype(np.float32)
    integer=np.rint(f);fraction=f-integer
    h,w=f.shape[:2]
    shifts=[(h//2,0),(0,w//2),(h//2,w//2),(h//4,w//4)]
    nulls=[np.roll(integer,shift,axis=(0,1))+fraction for shift in shifts]
    return f,fraction,nulls,clipped


def warp(frame,flow,kernel='linear'):
    h,w=frame.shape[:2];yy,xx=np.mgrid[:h,:w].astype(np.float32)
    mx,my=xx+flow[...,0],yy+flow[...,1]
    radius=2 if kernel=='cubic' else 0
    valid=(mx>=radius)&(mx<=w-1-radius)&(my>=radius)&(my<=h-1-radius)
    interpolation={'linear':cv2.INTER_LINEAR,'cubic':cv2.INTER_CUBIC}[kernel]
    return cv2.remap(frame,mx,my,interpolation,borderMode=cv2.BORDER_CONSTANT),valid


def pair(previous,current,flow,support='interior',margin=16,bound=12,kernel='linear'):
    if support not in ('interior','common'):raise ValueError('support')
    if support=='interior' and (bound is None or margin<bound+3):raise ValueError('Interior margin must exceed flow bound and kernel support')
    f,frac,nulls,clipped=fields(flow,bound if support=='interior' else None)
    sampled=[warp(previous,g,kernel) for g in [f,frac]+nulls]
    self_sample,self_valid=warp(current,f,kernel)
    valid=np.logical_and.reduce([v for _,v in sampled]+[self_valid])
    residual=[current-s for s,_ in sampled]
    actual,phase,*wrong=residual
    result={'raw':current-previous,'correct':actual,'wrong':wrong[0],
            'fractional':phase,'self_warp':current-self_sample,
            'single_contrast':np.abs(wrong[0])-np.abs(actual),
            'multi_contrast':np.mean(np.abs(np.stack(wrong)),axis=0)-np.abs(actual),
            'concat':np.concatenate([actual]+wrong,axis=-1)}
    if support=='interior':
        if min(previous.shape[:2])<=2*margin:raise ValueError('Empty interior')
        sl=(slice(margin,-margin),slice(margin,-margin))
        if not valid[sl].all():raise ValueError('Interior control has invalid samples')
        result={k:v[sl] for k,v in result.items()}
    else:result={k:v*valid[...,None] for k,v in result.items()}
    q={'common_coverage':float(valid.mean()),'clipped_fraction':clipped,
       'flow_magnitude':float(np.linalg.norm(f,axis=-1).mean()),
       'fractional_magnitude':float(np.linalg.norm(frac,axis=-1).mean()),
       'texture_std':float(previous.std()),
       'wrong_changed_fraction':float(np.any(nulls[0]!=f,axis=-1).mean())}
    return {k:v.transpose(2,0,1).astype(np.float32) for k,v in result.items()},q


def represent(bgr,cfg,flow_provider=None):
    rgb=bgr[...,::-1].astype(np.float32)/255
    gray=[cv2.cvtColor(x,cv2.COLOR_BGR2GRAY) for x in bgr]
    output={k:[] for k in MECHANISM_ARMS+METHOD_ARMS};quality=[]
    for t in range(1,len(bgr)):
        flow=(flow_provider(bgr[t],bgr[t-1]) if flow_provider else
              cv2.calcOpticalFlowFarneback(gray[t],gray[t-1],None,.5,3,15,3,5,1.2,0))
        values,q=pair(rgb[t-1],rgb[t],flow,cfg['support'],cfg['margin'],cfg['flow_bound'],cfg['kernel'])
        for k,v in values.items():output[k].append(v)
        quality.append(q)
    return {k:np.stack(v) for k,v in output.items()},quality
