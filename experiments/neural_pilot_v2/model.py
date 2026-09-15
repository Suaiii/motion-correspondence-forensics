"""Small common-protocol neural baselines; no pretrained models or downloads."""
import torch
from torch import nn


class FrameEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(3, 16, 5, stride=2, padding=2), nn.GroupNorm(4, 16), nn.SiLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.GroupNorm(4, 32), nn.SiLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.GroupNorm(8, 64), nn.SiLU(),
            nn.AdaptiveAvgPool2d(1), nn.Flatten(),
        )

    def forward(self, x):
        return self.layers(x)


class VideoBaseline(nn.Module):
    def __init__(self, kind):
        super().__init__()
        if kind not in ("frame_mean", "raw_temporal", "aligned_temporal"):
            raise ValueError(kind)
        self.kind = kind
        self.encoder = FrameEncoder()
        self.temporal = None if kind == "frame_mean" else nn.GRU(64, 64, batch_first=True)
        self.head = nn.Linear(64, 1)

    def forward(self, x):
        b, t, c, h, w = x.shape
        z = self.encoder(x.reshape(b * t, c, h, w)).reshape(b, t, 64)
        if self.temporal is None:
            z = z.mean(1)
        else:
            _, hidden = self.temporal(z)
            z = hidden[-1]
        return self.head(z).squeeze(-1)
