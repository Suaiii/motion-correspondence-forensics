"""Exact-parameter-matched 2x2 representation/readout baseline."""
from torch import nn


class FrameEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.Sequential(
            nn.Conv2d(3,16,5,stride=2,padding=2),nn.GroupNorm(4,16),nn.SiLU(),
            nn.Conv2d(16,32,3,stride=2,padding=1),nn.GroupNorm(4,32),nn.SiLU(),
            nn.Conv2d(32,64,3,stride=2,padding=1),nn.GroupNorm(8,64),nn.SiLU(),
            nn.AdaptiveAvgPool2d(1),nn.Flatten())

    def forward(self,x):return self.layers(x)


class VideoBaseline(nn.Module):
    def __init__(self,kind):
        super().__init__()
        if kind not in ('raw_temporal','aligned_temporal','raw_bag','aligned_bag'):raise ValueError(kind)
        self.kind=kind;self.encoder=FrameEncoder()
        if kind.endswith('_bag'):
            # 24,832 MLP parameters + 128 LayerNorm parameters = 24,960 GRU parameters.
            self.readout=nn.Sequential(nn.Linear(64,192),nn.SiLU(),nn.Linear(192,64),nn.LayerNorm(64),nn.SiLU())
        else:self.readout=nn.GRU(64,64,batch_first=True)
        self.head=nn.Linear(64,1)

    def forward(self,x):
        b,t,c,h,w=x.shape
        z=self.encoder(x.reshape(b*t,c,h,w)).reshape(b,t,64)
        if self.kind.endswith('_bag'):z=self.readout(z.mean(1))
        else:_,h=self.readout(z);z=h[-1]
        return self.head(z).squeeze(-1)
