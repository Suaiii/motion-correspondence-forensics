# Domain-generalized correspondence hypothesis

> Historical hypothesis, superseded by [phase 2](PHASE2_PLAN_2026-09-14.md). The larger 150-video external pilot has AUROC 0.6056, but the newly computed gain over correct-only is +0.0034 with CI crossing zero. The initial 0.49 result below belongs to an earlier small subset. Unconditional source-adversarial training is no longer required: source and class are confounded, so source removal may also remove label information. Prioritize matched operator responses and balanced baselines first.

## Motivation from evidence

The correct+fractional fusion mechanism is strongly supported on the internal
development pool (source-stratified clean/JPEG70 intervals above zero and
correspondence permutation p=0.00498), but its first balanced external
MSVD–VEO3 pilot is negative (AUROC 0.49). Therefore the internal gain cannot be
treated as a source-invariant detector.

## New falsifiable hypothesis

A correspondence encoder should separate *within-video temporal consistency*
from source-specific appearance and codec statistics. The representation must
be trained with source-balanced batches and a source-adversarial nuisance head,
but the nuisance target should be source identity and codec metadata, not the
mask itself. The primary score is a temporal-consistency residual normalized by
within-video robust scale.

## Required experiment

Train on at least two labelled sources and hold out a third source entirely.
Compare (i) current fusion, (ii) source-balanced empirical-risk minimization,
and (iii) source-adversarial correspondence encoder. Freeze all thresholds on
calibration. Success requires positive AUROC gain over current fusion on both
held-out generator sources with a source-stratified paired interval above zero;
otherwise reject the hypothesis.

No paid run is authorized until the external video quota, licence, and source
manifest are accepted.
