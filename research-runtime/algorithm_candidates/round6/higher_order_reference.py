"""Observable-key toy H-T prototype and counterexamples; no trained model."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse
from datetime import datetime,timezone
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'research-runtime/server'))
from forensics.composability import correspondence,response_from_matrices
PAIRS=((0,1),(1,2),(0,2))
STATES=np.array(list(itertools.product([-1.,1.],repeat=3)))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ah(x):return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()


def pair_marginals(p):return (p.sum(2),p.sum(0),p.sum(1))


def binary_maxent(p):
    """Exact feasible affine family for binary all-pair marginals; entropy root.

    All such 2x2x2 arrays differ by eta*(-1)^(i+j+k). This fixes the objective
    and constraints of the initial IPF, including its near-boundary failure.
    """
    sign=np.fromfunction(lambda i,j,k:(-1.)**(i+j+k),(2,2,2))
    lo=-float(p[sign>0].min());hi=float(p[sign<0].min())
    for iteration in range(80):
        mid=(lo+hi)/2;mass=p+mid*sign
        derivative=float(np.sum(sign*np.log(np.maximum(mass,np.finfo(float).tiny))))
        if derivative>0:hi=mid
        else:lo=mid
    out=p+((lo+hi)/2)*sign
    if out.min() < -1e-14:raise ValueError('Negative reference mass')
    out=np.maximum(out,0)
    assert max(abs(a-b).max() for a,b in zip(pair_marginals(out),pair_marginals(p)))<1e-12
    return out,iteration+1


def weighted_tensor(w,z):
    means=[np.einsum('ijk,id->d',w,z[0]),np.einsum('ijk,jd->d',w,z[1]),np.einsum('ijk,kd->d',w,z[2])]
    return np.einsum('ijk,ip,jq,kr->pqr',w,z[0]-means[0],z[1]-means[1],z[2]-means[2],optimize=True)


def infer(keys,z,tau=.1,override_w=None):
    """No labels/true correspondences accepted. Binary payload support only."""
    m=z.shape[1]
    if m>8 or z.shape[0]!=3 or not np.isfinite(z).all() or not np.isfinite(keys).all():raise ValueError('Small finite three-frame inputs required')
    pp=np.stack([correspondence(keys[a],keys[b],tau) for a,b in PAIRS])
    w=np.einsum('ij,jk->ijk',pp[0],pp[1])/m if override_w is None else override_w
    if abs(w.sum()-1)>1e-10 or (w<0).any():raise ValueError('Invalid tuple weights')
    # Value groups inferred from observed vectors, not from parity labels.
    values=[];indices=[]
    for frame in z:
        vals,idx=np.unique(frame,axis=0,return_inverse=True)
        if len(vals)!=2:raise ValueError('This first prototype requires two observed payload values per frame')
        values.append(vals);indices.append(idx)
    p=np.zeros((2,2,2))
    for i,j,k in itertools.product(range(m),repeat=3):p[indices[0][i],indices[1][j],indices[2][k]]+=w[i,j,k]
    pref,iters=binary_maxent(p)
    t=weighted_tensor(w,z);tref=weighted_tensor(pref,np.asarray(values));delta=t-tref
    qab,qbc,qac=pair_marginals(w);pi=qab.sum(0)
    markov=qab[:,:,None]*qbc[None,:,:]/pi[None,:,None]
    full_reference_delta=float(np.linalg.norm(t-weighted_tensor(markov,z)))
    diagonal=np.zeros_like(w);diagonal[np.arange(m),np.arange(m),np.arange(m)]=1/m
    flat=z.reshape(-1,z.shape[-1]);center=flat-flat.mean(0)
    full=np.concatenate([keys,z],axis=-1);pooled=full.reshape(-1,full.shape[-1])
    q_full=np.stack([correspondence(full[a],full[b],tau) for a,b in PAIRS])
    shifts=[np.roll(np.arange(m),sign*r) for r in (1,2,4) for sign in (1,-1)]
    c=response_from_matrices(q_full[0],q_full[1],q_full[2],shifts)
    entropy=-sum(np.sum(np.where(p0>0,p0*np.log(np.maximum(p0,1e-300)),0)) for p0 in pp)/(3*m)
    return dict(tensor=t,delta=delta,reference_tensor=tref,scalar_signed=float(delta[0,0,0]),
        score=float(np.linalg.norm(delta)),ordinary_aligned_score=float(np.linalg.norm(t)),
        unaligned_score=float(np.linalg.norm(weighted_tensor(diagonal,z))),
        static_payload_mean=flat.mean(0),static_payload_cov=center.T@center/len(flat),
        static_payload_third=np.einsum('ip,iq,ir->pqr',center,center,center)/len(flat),
        static_full_second=pooled.T@pooled/len(pooled),
        temporal_coordinate_third=((z-z.mean(0))**3).mean((0,1)),
        q_full=q_full,payload_pair_tables=np.stack(pair_marginals(p)),w=w,p=p,reference=pref,
        reference_solver_iterations=iters,full_index_reference_delta=full_reference_delta,
        entropy=float(entropy),C_direct=float(np.mean(c['direct_js'])),C_response=c['response'].mean(1))


def fixture(m,kind):
    if m==4:
        ab=np.array(list(itertools.product([-1.,1.],repeat=2)))
        data=np.c_[ab,ab[:,0]*ab[:,1]*(1 if kind=='even' else -1)]
    elif kind=='independent':data=STATES.copy()
    else:
        ab=np.repeat(np.array(list(itertools.product([-1.,1.],repeat=2))),2,axis=0)
        data=np.c_[ab,ab[:,0]*ab[:,1]*(1 if kind=='even' else -1)]
    z=np.zeros((3,m,2));z[:,:,0]=data.T
    return np.repeat(np.eye(m)[None],3,axis=0),z


def compact(r):
    keys=('score','scalar_signed','ordinary_aligned_score','unaligned_score','full_index_reference_delta',
          'entropy','C_direct','C_response','temporal_coordinate_third','static_payload_mean','static_payload_cov',
          'static_payload_third','payload_pair_tables','reference_solver_iterations')
    return {k:r[k].tolist() if isinstance(r[k],np.ndarray) else r[k] for k in keys}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    start=time.perf_counter();config_path=Path(__file__).with_name('ht_config.json');cfg=json.loads(config_path.read_text())
    cases={};comparisons={};checks=[]
    with threadpool_limits(limits=2):
        for m,kinds in [(4,('even','odd')),(8,('even','independent'))]:
            for kind in kinds:
                key,z=fixture(m,kind);r=infer(key,z,cfg['temperature'])
                cases[f'{m}_{kind}']=dict(inputs=dict(keys=key.tolist(),payload=z.tolist(),keys_sha256=ah(key),payload_sha256=ah(z)),outputs=compact(r))
        keys,even=fixture(4,'even');_,odd=fixture(4,'odd')
        re,ro=infer(keys,even),infer(keys,odd)
        comparisons['equal_pair_histograms_not_equal_observation_tuple']=dict(
            pair_histogram_gap=float(abs(re['payload_pair_tables']-ro['payload_pair_tables']).max()),
            entire_Q_tuple_gap=float(abs(re['q_full']-ro['q_full']).max()),
            signed_scores=[re['scalar_signed'],ro['scalar_signed']],norm_scores=[re['score'],ro['score']])
        flipped=infer(keys,-even)
        comparisons['same_entire_Q_common_sign_flip']=dict(Q_tuple_gap=float(abs(re['q_full']-flipped['q_full']).max()),
            signed_scores=[re['scalar_signed'],flipped['scalar_signed']],norm_scores=[re['score'],flipped['score']],
            C_response_gap=float(abs(re['C_response']-flipped['C_response']).max()))
        k8,z8=fixture(8,'even');_,zi=fixture(8,'independent');r8,ri=infer(k8,z8),infer(k8,zi)
        comparisons['parity_vs_independent']=dict(scores=[r8['score'],ri['score']],
            ordinary_aligned_scores=[r8['ordinary_aligned_score'],ri['ordinary_aligned_score']],
            payload_pair_gap=float(abs(r8['payload_pair_tables']-ri['payload_pair_tables']).max()),
            static_full_second_gap=float(abs(r8['static_full_second']-ri['static_full_second']).max()),
            Q_tuple_gap=float(abs(r8['q_full']-ri['q_full']).max()))
        for seed in cfg['seeds']:
            rng=np.random.default_rng(seed);rotation=np.linalg.qr(rng.normal(size=(2,2)))[0]
            perms=[rng.permutation(8) for _ in range(3)]
            kp=np.stack([k8[t,perms[t]] for t in range(3)])
            zp=np.stack([z8[t,perms[t]] for t in range(3)])
            base=infer(kp,zp);rot=infer(kp,zp@rotation)
            erased=infer(np.ones_like(kp),zp)
            row=dict(seed=seed,aligned_observed_score=base['score'],same_index_unaligned_score=base['unaligned_score'],
                patch_reindex_score_error=abs(base['score']-r8['score']),
                common_payload_rotation_score_error=abs(rot['score']-base['score']),
                signed_coordinate_before_after=[base['scalar_signed'],rot['scalar_signed']],
                no_keys=dict(score=erased['score'],entropy=erased['entropy']),
                amplitude=[],time_reorders=[],wrong_keys=[])
            for scale in cfg['scales']:
                rs=infer(kp,zp*scale)
                row['amplitude'].append(dict(scale=scale,score=rs['score'],score_div_scale_cubed=rs['score']/scale**3))
            for order in cfg['time_orders']:
                rt=infer(kp[order],zp[order]);row['time_reorders'].append(dict(order=order,score=rt['score']))
            for fraction in cfg['wrong_key_fractions']:
                wrong=kp.copy();wrong[2]=(1-fraction)*kp[2]+fraction*np.roll(kp[2],1,axis=0)
                rw=infer(wrong,zp);row['wrong_keys'].append(dict(fraction=fraction,score=rw['score'],entropy=rw['entropy']))
            assert row['patch_reindex_score_error']<1e-10 and row['common_payload_rotation_score_error']<1e-10
            checks.append(row)
        assert comparisons['equal_pair_histograms_not_equal_observation_tuple']['pair_histogram_gap']<1e-10
        assert comparisons['equal_pair_histograms_not_equal_observation_tuple']['entire_Q_tuple_gap']>1e-5
        assert comparisons['same_entire_Q_common_sign_flip']['Q_tuple_gap']==0
        assert max(abs(v['outputs']['score']-v['outputs']['ordinary_aligned_score']) for v in cases.values())<1e-10
    output=dict(dispatch_id=cfg['dispatch_id'],task_id='AL02',plan_version='cvpr27-20260918-v1.4',
        observed_utc=datetime.now(timezone.utc).isoformat(),cases=cases,comparisons=comparisons,stress_checks=checks,
        hypothesis_result='refuted_for_current_independent_increment_claim',
        supported_scope='Known third-order information beyond separate coarse payload pair marginals, given observable matching keys',
        failure='Current conditional residual equals ordinary aligned third statistic on these fixtures; full-index Markov reference is tautologically zero',
        reference_solver='Binary feasible affine line, 80 fixed bisection steps on entropy derivative; initial IPF failure archived',
        real_mechanism='unknown',real_key_extractor='not_provided',
        input_fairness='Every baseline receives identical observed (key,payload) arrays; no ground-truth trajectory passed to infer',
        scientific_breakthrough=False,training_steps=0,server_accessed=False,media_read=False,gpu_used=False,
        threads=2,elapsed_seconds=time.perf_counter()-start,
        config_sha256=sha(config_path),script_sha256=sha(Path(__file__)),
        frozen_C_primitive_sha256=sha(ROOT/'research-runtime/server/forensics/composability.py'),
        complexity='W O(m^3) memory; full tensor O(d^3); toy only m<=8 d=2, not a scalable DINO implementation')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(output,f,indent=2,allow_nan=False)
    print(json.dumps(dict(hypothesis_result=output['hypothesis_result'],comparisons=comparisons,
        cases={k:v['outputs']['score'] for k,v in cases.items()},elapsed_seconds=output['elapsed_seconds']),indent=2))


if __name__=='__main__':main()
