"""Learned correct/fractional correspondence fusion head."""
from torch import nn
import torch

class CorrespondenceFusion(nn.Module):
    def __init__(self, feature_dim, hidden=128, dropout=0.0):
        super().__init__()
        self.norm=nn.LayerNorm(feature_dim*2)
        self.proj=nn.Sequential(nn.Linear(feature_dim*2,hidden),nn.GELU(),nn.Dropout(dropout))
        self.classifier=nn.Linear(hidden,1)
    def forward(self, correct, fractional):
        if correct.shape != fractional.shape: raise ValueError('correct/fractional shape mismatch')
        z=self.proj(self.norm(torch.cat([correct,fractional],dim=-1)))
        return self.classifier(z).squeeze(-1)
