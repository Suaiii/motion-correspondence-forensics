# RS04/RS05 canonical composability prototype

Plan version: cvpr27-20260917-v1. This implements the shared main candidate;
the earlier `rank_response.py` remains a separate diagnostic.

## Implementation and interface

- `composability.py`: independent NumPy reference for normalized patch
  affinities at temperature 0.1, direct/two-step JS and one-sided middle-index
  perturbations at 1/2/4 patches in four directions.
- `composability_torch.py`: batched CUDA implementation of the same operators.
- `local_composability.py`: frozen-feature interface accepting
  `[B,6,256,768]` patch tokens and `[B,6,768]` global tokens. It returns one
  logit per video, six sets of three 16x16 response maps, absolute JS and
  separate diagnostics. A shared spatial encoder pools each triplet and then
  averages triplet representations without sequence order. The default head
  has **217,057 trainable parameters**. Backbone inputs are detached.
- The calibrated candidate consumes the three response channels, not absolute
  JS or source metadata. Absolute JS is retained for explicit ablations.
- Empty local support has a defined semantic-input fallback. Support patterns
  can still be implicit cues; support-only controls remain necessary.
- `mechanism_sampling.py`: 1.5-second eligibility window, six unique native
  frames at target 4 Hz, 1.25-second target span. It retains all actual PTS and
  the two intervals for every one of the six specified triplets. No padding.

## Evidence actually executed

`composability_invariants.json` contains eleven NumPy tests and CUDA replay
against the independent NumPy implementation, including the internal-middle
control. Response-map absolute discrepancies are below 1e-7; entropy
discrepancy is below 2.1e-6. Additional CUDA checks confirm output shape,
finite classifier gradients, frozen feature inputs, unordered triplet
aggregation, diagnostic-only absolute JS and semantic fallback.

The checked source hashes match the local implementation. Transferred evidence
SHA256: `41b78470d980bca7fd50619bcaa1b93b78d1292a869c47ddcef658e8a0c0225a`.
Runtime was 3.71 seconds for the numerical/interface check. It excludes real
video decoding, DINO extraction and training. The initial CUDA event contains
warm-up/validation overhead; do not interpret its timing as a production
latency comparison between the two support modes.

## Scientific pitfalls exposed before training

1. A consistent reindexing of both middle connections cancels. A one-sided
   permutation does not. Under arbitrary reindexing, the perturbation must
   also be conjugated to describe the same intervention; tests cover this.
2. Cropping anchor rows alone cannot eliminate cyclic middle-node wrapping.
   The explicit interior control conditions all compared paths on the same
   unwrapped middle-node set, and records retained probability mass. For a
   16x16 grid and maximum radius 4, this retains 64/256 middle nodes.
3. **A perfectly static sequence can produce nonzero composition error and
   calibrated response.** Soft matching generally has `P @ P != P`. A
   repeated-feature toy sequence produced mean JS 0.02669 and mean response
   0.38257, with no temporal change. This is an algebraic counterexample, not
   a real-video metric or a rejection of the method. See
   `static_sequence_counterexample.json`. Recommend a repeated-frame/static
   patch control to planagent before attributing a gain to temporal structure.

## Gate recommendation

The numerical primitive and classifier interface are ready for software review.
No classifier was fitted and no real-data efficacy was measured. The
real-video caching and 100-video full-pipeline profile remain pending. The
old pairwise timing census does not validate the new six-frame joint support.
Formal data acceptance, method effect and novelty therefore remain unpassed.
Do not move scientific gates merely because the software replay passes.

## Existing-backbone integration check

`backbones.py` now returns both 16x16 patch tokens and global tokens. On the
server, the existing SHA-verified DINOv2 ViT-B/14 and pinned source revision
were run on six identical synthetic 224x224 frames, then connected to the new
head. Patch shape `[6,256,768]`, global shape `[6,768]`, response shape
`[1,6,3,16,16]` and a finite scalar logit passed. Backbone trainable parameters
are zero, head parameters 217,057, and optimizer steps zero. This check took
3.96 seconds with 0.366 GiB peak tensor allocation; it is not video throughput.

The actual frozen DINO also gives nonzero responses on the static synthetic
sequence: mean absolute response 0.09492 and mean JS 0.03408. These remain
synthetic diagnostics, reinforcing the repeated-frame-control recommendation.
`backbone_integration.json` records all source and model hashes; its transferred
SHA256 is `c94dbc65977123bd3539c02b4cdea8298e1b053d043de6f25fd3b2a0a637807b`.
