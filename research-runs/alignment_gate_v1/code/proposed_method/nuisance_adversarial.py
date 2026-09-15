"""Minimal alignment-aware nuisance-adversarial video head.

The nuisance head predicts observable mask statistics while gradient reversal
prevents the representation from retaining them.  This is a method prototype,
not yet a validated experiment.
"""
import torch
from torch import nn
from torch.autograd import Function

class _GR(Function):
    @staticmethod
    def forward(ctx, x, strength):
        ctx.strength=float(strength); return x.view_as(x)
    @staticmethod
    def backward(ctx, grad):
        return -ctx.strength*grad, None

def grad_reverse(x, strength=1.0):
    return _GR.apply(x, strength)

class AlignmentNuisanceAdversarial(nn.Module):
    def __init__(self, feature_dim, mask_dim=8, hidden=128, grl_strength=1.0):
        super().__init__(); self.grl_strength=grl_strength
        self.encoder=nn.Sequential(nn.LayerNorm(feature_dim),nn.Linear(feature_dim,hidden),nn.GELU())
        self.fake_head=nn.Linear(hidden,1)
        self.nuisance_head=nn.Sequential(nn.Linear(hidden,hidden//2),nn.GELU(),nn.Linear(hidden//2,mask_dim))
    def forward(self, aligned_features):
        z=self.encoder(aligned_features)
        return {'representation':z,'fake_logit':self.fake_head(z).squeeze(-1),'nuisance_pred':self.nuisance_head(grad_reverse(z,self.grl_strength))}

def adversarial_loss(outputs, fake_labels, mask_targets, nuisance_weight=1.0):
    fake=nn.functional.binary_cross_entropy_with_logits(outputs['fake_logit'],fake_labels.float())
    nuisance=nn.functional.mse_loss(outputs['nuisance_pred'],mask_targets.float())
    return fake+nuisance_weight*nuisance, {'fake':float(fake.detach()),'nuisance':float(nuisance.detach())}
