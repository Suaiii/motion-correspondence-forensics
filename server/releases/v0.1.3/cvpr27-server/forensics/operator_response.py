"""Learnable operator-response features for phase-2 experiments.

The module compares one estimated correspondence against matched null
correspondences on the same video.  It is deliberately separate from the
frozen residual controls until an external development gate is accepted.
"""
from __future__ import annotations

import torch
from torch import nn


class OperatorResponseEncoder(nn.Module):
    """Encode relative correspondence response without using a mask as a feature.

    Args:
        channels: residual channels, normally three RGB channels.
        hidden: width of the small readout.
        tau: positive robust-scale floor, frozen from fit data in experiments.
    """

    def __init__(self, channels: int = 3, hidden: int = 32, tau: float = 1e-3):
        super().__init__()
        if channels < 1 or hidden < 1 or tau <= 0:
            raise ValueError("channels/hidden must be positive and tau must be > 0")
        self.channels = channels
        self.tau = float(tau)
        # Nine response summaries plus three absolute residual controls.
        self.readout = nn.Sequential(nn.LayerNorm(12), nn.Linear(12, hidden), nn.GELU(), nn.Linear(hidden, 1))

    def forward(self, correct: torch.Tensor, controls: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ``(logit, response_features)``.

        ``correct`` is ``[B,T,C,H,W]`` and ``controls`` is
        ``[B,K,T,C,H,W]``.  All tensors must share shape except for K.
        ``controls`` should use a common valid support prepared by the data
        pipeline; this module does not infer or consume a validity mask.
        """
        if correct.ndim != 5 or controls.ndim != 6:
            raise ValueError("expected correct [B,T,C,H,W] and controls [B,K,T,C,H,W]")
        if controls.shape[0] != correct.shape[0] or (controls.shape[0:1] + controls.shape[2:]) != correct.shape or controls.shape[1] < 2:
            raise ValueError("controls must be [B,K,T,C,H,W] with K >= 2")
        if correct.shape[2] != self.channels or not torch.isfinite(correct).all() or not torch.isfinite(controls).all():
            raise ValueError("channel mismatch or nonfinite residual")
        target = correct.abs()
        null = controls.abs()
        median = null.median(dim=1).values
        mad = (null - median.unsqueeze(1)).abs().median(dim=1).values
        response = (median - target) / (mad + self.tau)
        pooled = response.flatten(1)
        flat_response = response.flatten(1)
        flat_target = target.flatten(1)
        flat_null = null.flatten(1)
        temporal = response.mean(dim=(2, 3, 4))
        features = torch.cat((
            response.mean(dim=(1, 2, 3, 4), keepdim=False).unsqueeze(1),
            response.std(dim=(1, 2, 3, 4), unbiased=False).unsqueeze(1),
            torch.quantile(flat_response, torch.tensor([.05, .50, .95], device=response.device), dim=1).T,
            (response > 0).float().mean(dim=(1, 2, 3, 4)).unsqueeze(1),
            temporal.std(dim=1, unbiased=False).unsqueeze(1),
            response.abs().mean(dim=(1, 2, 3, 4)).unsqueeze(1),
            torch.quantile(flat_response.abs(), torch.tensor(.95, device=response.device), dim=1).reshape(-1, 1),
            target.mean(dim=(1, 2, 3, 4)).unsqueeze(1),
            target.std(dim=(1, 2, 3, 4), unbiased=False).unsqueeze(1),
            null.mean(dim=(1, 2, 3, 4, 5)).unsqueeze(1),
        ), dim=1)
        if features.shape[1] != 12:
            raise RuntimeError("response feature contract changed")
        return self.readout(features).squeeze(-1), features
