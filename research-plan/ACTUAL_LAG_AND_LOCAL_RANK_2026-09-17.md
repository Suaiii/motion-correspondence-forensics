# Next mechanism step: actual-lag support and local operator ranks

Status: numerical reference components implemented; real-data execution
pending server access. This is not a successful new detector or a novelty claim.
It follows the negative paired-consistency experiment and the 0.93367 timing-only
score on the 196-clip HD-VG/CogVideo development cohort.

## 1. Establish what can be compared

`audit_actual_lag_support.py` reads the saved actual timestamps, without video
download, feature recomputation or classifier fitting. It audits:

- All seven adjacent intervals of the nominal eight-frame grid.
- The existing frame pair at indices 0 and 4, targeting an actual 0.5-second
  interval with a prespecified 0.002-second tolerance.
- Quantization sensitivities of 1, 2 and 5 milliseconds, fixed before outcomes.
- Pairwise real-source/fake-source support and intersection across all sources.
- Raw within-bin timing differences; rounded overlap must not be described as
  removal of continuous timing information.

The support census uses labels to describe overlap, not to choose frames or
fit a detector. Its cohorts are exposed development data. If support is absent,
do not invent matched samples or interpolate scores to obtain a positive gate.
Keep the full-cohort result and report support exclusions explicitly.

Synthetic 30-fps real and 8-fps fake timelines demonstrate the distinction:
their nearest-frame nominal 8-Hz grids have different adjacent intervals,
while a selected half-second pair can share a true lag. Whether enough actual
videos share such support remains to be measured on the server.

## 2. Local operator-response primitive

For a reference location and an estimated displacement, form the eight square
symmetry transforms of its integer displacement. Compare squared residuals on
the intersection of every operator's valid sampling footprint. The identity
operator's midrank among these residuals produces a local response map.
Exact ties contribute one half; uninformative zero-displacement orbits remain
neutral. Preserve spatial cells instead of immediately reducing everything to
twelve whole-video statistics. Unsupported pixels and videos remain explicit.

This midrank is invariant to a common strictly increasing transformation of
the residual errors at a pixel. It is not invariant to arbitrary image
compression, arbitrary photometric transformations, changing flow estimators,
or changes to the estimated correspondence itself.

### A constraint discovered during implementation

For displacement `q + f`, where q is integer and f its fractional component,
preserving interpolation phase fixes f. Exact total-length matching requires:

`||q'||^2 - ||q||^2 + 2 f dot (q' - q) = 0`.

Rotating q preserves the first two norm terms but generally not the final
fractional cross-term. Therefore an integer-length-matched null is not an
exact full-motion-length-matched null. The code exposes this discrepancy and
tests a concrete subpixel counterexample; it must not be hidden in a method
description or inferred away from a shared interpolation kernel.

The `integer_only` diagnostic mode instead rounds the estimated displacement
before constructing the orbit. All applied operators then have identical
lengths and integer sampling. This guarantee applies to the quantized flow,
not to the original estimate. The maximum quantization error is recorded;
subpixel-only motion may become uninformative. That is an estimator tradeoff,
not a free invariance improvement.

## 3. Comparisons required before accepting a detector

No real-data model has been fitted from this primitive. A mechanism experiment
must compare continuous correct-only residual, integer correct-only residual,
integer-orbit raw residual concatenation, local ranks, shuffled local ranks,
ordinary DINO/two-view ERM and support-only controls. Every mechanism arm must
use the same frames, applied-flow estimator and common support where compared.
The integer correct-only baseline isolates rounding cost; concatenation tests
whether rank normalization adds value beyond receiving multiple residuals.

Keep all videos, define a semantic fallback for absent support before training,
and report its coverage. Not passing a mask to a head does not remove implicit
mask/coverage information from a neutral-filled response map. A mask-only arm
is mandatory. Verify a second flow estimator and at least two genuine source
families before an attribution claim. Neither the support audit nor these
synthetic tests release the formal training gate.

## 4. Prior art and novelty boundary

[Zabih and Woodfill, ECCV 1994](https://www.cs.cornell.edu/~rdz/Papers/ZW-ECCV94.pdf)
already introduced rank/census-style correspondence transforms.
[UnFlow](https://arxiv.org/abs/1711.07837) uses a robust census loss for optical
flow. [ReStraV, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/1d9a43752c2819e03967c5c1b708169c-Abstract-Conference.html)
already uses DINO trajectory geometry for generated-video detection.
These primary sources were checked on 2026-09-17. Ranking, optical flow,
temporal geometry, and nearest-neighbor sampling alone are not new claims.
The unresolved question is whether an explicitly controlled local response
offers an effect beyond these baselines under source and timing controls.

## 5. Current operational state

The preceding goal turn made progress, but its batch completion did not complete
the full research objective. The instance was shut down then. On this
continuation SSH is unreachable and the AutoDL UI redirects the console to a
login form. No cloud account credentials or authenticated control session are
available. The user has been asked to start the original instance or sign in.
Only small CPU synthetic tests and code preparation run locally; no research
videos, model weights or feature caches are downloaded locally.
