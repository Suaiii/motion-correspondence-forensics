# Operator Response Encoder v1

## Intended contribution

For each video interval, the model receives one estimated correspondence
residual and at least two matched null-correspondence residuals. It encodes the
response of the same content to these operators rather than classifying the
absolute residual magnitude:

`R = (median_k |e_null,k| - |e_correct|) / (MAD_k |e_null,k| + tau)`.

The encoder emits pooled response statistics and a learned video-level logit.
The valid support, sampling, optical-flow implementation, and `tau` are fixed
outside the module. A mask is used to define support but is never supplied as a
classification feature.

## Why this is a candidate

The operator-response construction is content-matched: nulls are generated
from the same frame pair and the same fractional sampling weights. This makes
it possible to test whether a detector responds to a temporal correspondence
structure instead of a source-specific residual scale. The construction is
compatible with dense or spiking readouts, but it does not assume that SNN is
necessary.

## Required evidence before a paper or patent claim

1. A fresh development cohort with accepted source, licence, and ancestry
   records.
2. Comparison with correct-only, ordinary concatenation, matched parameter
   dense temporal models, and DINO/STALL native references.
3. Two unseen generators and one unseen real source with source-grouped
   intervals, five seeds, and frozen calibration.
4. Controls for interpolation kernel, flow implementation, support, motion
   magnitude, and mask-only prediction.
5. A claim that survives the external gate. The current internal and external
   exploratory results do not satisfy this requirement.

## Patent boundary

The mathematical form alone is insufficient for a patent claim. A potentially
protectable system claim would need a demonstrated technical effect tied to a
specific deployment pipeline, such as lower false-positive drift under a
defined re-encoding family at a measured latency budget. No such effect has
been established yet; this card is an invention candidate, not a patent
assertion.
