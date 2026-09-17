# Paired sampling consistency: exposed development screen

The paired frozen-head replay found no positive lower confidence bound for
time-grid delta over semantics on either generator holdout. The nearest-frame
grid also retains source-dependent timing. This invalidates the earlier wording
that a genuine temporal contribution was already confirmed.

## Hypothesis and fixed experiment

A classifier trained to agree on two samplings of the same video may suppress
sampling-sensitive shortcuts. This is a hypothesis, not a new-algorithm claim.
The existing native8 and time8 caches permit a low-cost screen without another
download or feature extraction. Their temporal coverage differs, so they are
not a clean intervention on frame rate alone.

Freeze before viewing this pilot's outcomes:

- Holdouts and fit/calibration/audit groups: reuse the paired baseline split.
- Seeds: 17, 29, 43, 59, 71; 40 epochs, batch 1024; AdamW 0.001/0.01.
- Every head: 1536 inputs, 256 GELU units, dropout 0.1, scalar logit.
- Select the earliest minimum time-view calibration BCE checkpoint.
- Six arms: duplicated semantic mean, mean+unordered standard deviation,
  mean+temporal delta, ordinary two-view ERM, paired consistency, and
  within-source/label shuffled-pair consistency.
- Consistency adds squared paired logit difference with coefficient 1.
  Both two-view branches retain supervised BCE. This deliberately conservative
  coefficient is fixed, not optimized against audit scores.
- Report all seeds and both holdouts; store checkpoints, per-video logits,
  calibration histories, hashes and source-group bootstrap intervals.
- Same parameter count is not equal training compute. Two-view ERM is the
  compute-matched primary comparator to the consistency arm.
- No time cutoff. Resume completed fits after hash verification. Large
  artifacts remain server-side.

Reject this candidate if it fails to beat ordinary two-view ERM, shuffled
pairing or unordered statistics in either holdout, or if at least four of five
seed differences are not positive. A positive result would still require
independent real sources, timing controls and accepted ancestry before formal
training or a publication-level claim.

## Closest prior work and limits

[ReStraV (NeurIPS 2025)](https://github.com/ChristianInterno/ReStraV) already
uses DINO trajectory geometry.
[SPLIT (ECCV 2026)](https://split-eccv2026.github.io/) uses spatial incoherence
and temporal roughness. Merely replacing delta with curvature or chord ratios
would not establish novelty relative to these methods.
[Causal Matching (ICML 2021)](https://proceedings.mlr.press/v139/mahajan21b.html)
already motivates matching representations of the same object across domains.
Consequently, this pilot tests whether a sampling-specific instantiation is
useful; consistency loss itself is not an original contribution. These primary
sources were checked on 2026-09-17. This targeted search is not an exhaustive
novelty review.
