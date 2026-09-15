"""Nominal-CFR audit sampler. VFR streams require explicit decoded PTS handling."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SamplePlan:
    indices: tuple[int, ...]
    requested_times: tuple[float, ...]
    frame_times: tuple[float, ...]
    delta_times: tuple[float, ...]


def fixed_rate_plan(frame_count: int, source_fps: float, target_fps: float = 4.0,
                    window_sec: float = 2.0) -> SamplePlan:
    """Sample [start, start+window) without upsampling or repeat-last padding.

    This validates a metadata-level plan, not decoded-frame equality or VFR timing.
    Low frame rate and too-short clips are explicitly rejected, never relabeled.
    """
    if frame_count <= 0 or any(not math.isfinite(x) or x <= 0 for x in (source_fps, target_fps, window_sec)):
        raise ValueError("invalid frame count, frame rate or window")
    if source_fps < target_fps - 1e-8:
        raise ValueError("source frame rate below target; no synthetic upsampling allowed")
    duration = frame_count / source_fps
    if duration + 1e-8 < window_sec:
        raise ValueError("clip shorter than requested window; no repeat-last padding allowed")
    sample_count_float = target_fps * window_sec
    if abs(sample_count_float - round(sample_count_float)) > 1e-8:
        raise ValueError("target rate times window must be an integer for this audit sampler")
    count = round(sample_count_float)
    if count < 2:
        raise ValueError("at least two frames required")
    start = (duration - window_sec) / 2
    targets = tuple(start + k / target_fps for k in range(count))
    indices = tuple(int(math.floor(t * source_fps + 1e-8)) for t in targets)
    if len(set(indices)) != count or min(indices) < 0 or max(indices) >= frame_count:
        raise ValueError("invalid or repeated sample indices")
    actual = tuple(i / source_fps for i in indices)
    return SamplePlan(indices, targets, actual, tuple(b - a for a, b in zip(actual, actual[1:])))
