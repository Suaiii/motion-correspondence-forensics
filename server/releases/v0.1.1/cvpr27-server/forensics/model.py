import torch
from torch import nn


class Bag(nn.Module):
    def __init__(self,channels=3):
        super().__init__()
        self.encoder=nn.Sequential(nn.Conv2d(channels,16,5,2,2),nn.GroupNorm(4,16),nn.SiLU(),
            nn.Conv2d(16,32,3,2,1),nn.GroupNorm(4,32),nn.SiLU(),
            nn.Conv2d(32,64,3,2,1),nn.GroupNorm(8,64),nn.SiLU(),nn.AdaptiveAvgPool2d(1),nn.Flatten())
        self.readout=nn.Sequential(nn.Linear(64,192),nn.SiLU(),nn.Linear(192,64),nn.LayerNorm(64),nn.SiLU(),nn.Linear(64,1))

    def forward(self,x):
        b,t,c,h,w=x.shape
        return self.readout(self.encoder(x.reshape(b*t,c,h,w)).reshape(b,t,64).mean(1)).squeeze(-1)


def selective_consistency(clean,degraded):
    """Fixed top-half stable tokens; an optional diagnostic, not enabled training."""
    if clean.shape!=degraded.shape or clean.ndim!=3:raise ValueError('Expected matched [batch,tokens,features]')
    similarity=torch.nn.functional.cosine_similarity(clean.detach(),degraded.detach(),dim=-1)
    k=max(1,clean.shape[1]//2)
    indices=similarity.topk(k,dim=1).indices
    loss=1-torch.nn.functional.cosine_similarity(clean.detach(),degraded,dim=-1)
    return loss.gather(1,indices).mean()
