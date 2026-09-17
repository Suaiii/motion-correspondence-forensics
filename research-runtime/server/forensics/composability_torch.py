"""Batched torch implementation of the shared correspondence-response primitive."""
import torch
from .composability import branch_triplets,shift_permutation


@torch.no_grad()
def six_frame_response(tokens,grid=(16,16),temperature=.1,scales=(1,2,4),interior_control=False,branch_mode='temporal'):
    if tokens.ndim!=4 or tokens.shape[1]!=6 or tokens.shape[2]!=grid[0]*grid[1]:
        raise ValueError('Expected [batch,6,patch,channel] on the declared grid')
    if not torch.isfinite(tokens).all() or temperature<=0 or not torch.isfinite(torch.tensor(temperature)):
        raise ValueError('Finite tokens and positive finite temperature required')
    h,w=grid
    if not scales or len(set(scales))!=len(scales) or any(not isinstance(r,int) or not 0<r<min(h,w) for r in scales):
        raise ValueError('Invalid perturbation scales')
    if tokens.dtype not in (torch.float32,torch.float64):tokens=tokens.float()
    z=torch.nn.functional.normalize(tokens,dim=-1,eps=1e-12)
    permutations=[];wrap=[]
    for r in scales:
        for dy,dx in ((0,r),(0,-r),(r,0),(-r,0)):
            p,m=shift_permutation(grid,dy,dx)
            permutations.append(torch.tensor(p,device=z.device));wrap.append(torch.tensor(m,device=z.device))
    keep=~torch.stack(wrap).any(0) if interior_control else torch.ones(h*w,device=z.device,dtype=torch.bool)
    if not keep.any():raise ValueError('Empty common middle support')
    matrices={};tiny=torch.finfo(z.dtype).tiny
    def p(a,b):
        if (a,b) not in matrices:matrices[a,b]=torch.softmax((z[:,a]@z[:,b].transpose(-1,-2))/temperature,dim=-1)
        return matrices[a,b]
    def js(a,b):
        middle=(a+b)/2;lm=middle.clamp_min(tiny).log()
        return .5*((a*(a.clamp_min(tiny).log()-lm)).sum(-1)+(b*(b.clamp_min(tiny).log()-lm)).sum(-1))
    triplets=branch_triplets(branch_mode)
    responses=[];direct=[];entropies=[];support=[];masses=[]
    for a,b,c in triplets:
        ab,bc,ac=p(a,b),p(b,c),p(a,c)
        mass=ab[:,:,keep].sum(-1);valid=mass>1e-12
        weights=ab[:,:,keep]/mass.clamp_min(1e-12).unsqueeze(-1)
        d0=js(ac,weights@bc[:,keep,:])
        values=torch.stack([js(ac,weights@bc[:,perm[keep],:])-d0 for perm in permutations],dim=1)
        values=values.reshape(z.shape[0],len(scales),4,h,w).mean(2)
        values=values.masked_fill(~valid[:,None].reshape(z.shape[0],1,h,w),float('nan'))
        responses.append(values);direct.append(d0.masked_fill(~valid,float('nan')).reshape(-1,h,w))
        entropies.append(torch.stack([-(x*x.clamp_min(tiny).log()).sum(-1) for x in (ab,bc,ac)],dim=1).reshape(-1,3,h,w))
        support.append(valid.reshape(-1,h,w));masses.append(mass.reshape(-1,h,w))
    return dict(responses=torch.stack(responses,dim=1),direct_js=torch.stack(direct,dim=1),
        correspondence_entropies=torch.stack(entropies,dim=1),support=torch.stack(support,dim=1),
        middle_probability_mass=torch.stack(masses,dim=1),
        wrapped_middle_fraction=torch.stack(wrap).double().mean(-1).reshape(len(scales),4),
        middle_support_fraction=float(keep.double().mean()),branch_mode=branch_mode,
        triplets=triplets,unique_affinity_matrices=len(matrices))
