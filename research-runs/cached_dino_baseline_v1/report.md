# Full available DINO-cache baseline: timing is a major confound

The server completed all six baseline arms and 18 calibration-selected LR fits
in 38.90 seconds. The existing DINO backbone caches were reused; this run used
CPU only and downloaded no data. It is an exploratory analysis, not a formal
mechanism acceptance or an algorithmic novelty result.

## Dataset and protocol

The two input caches share the DINOv2 ViT-B/14 checkpoint hash, repository
revision and native16 decoder hash. The retained pool contains 28,674 videos:
13,499 ModelScope, 13,501 VideoCrafter2, and 1,674 Vript. Historical exact-byte
exclusions were applied; no duplicate bytes remained. Raw input videos for all
27,000 generated and 1,727 originally available real feature records were
confirmed still present on the server, making resampling feasible.

Groups are original Vript video-prefix candidates or shared fake UUIDs.
SHA256(group + fixed seed) allocates fit/calibration/audit at 60/20/20.
For each of two experiments, one generator is entirely absent from fitting and
calibration. Evaluation uses that generator's audit groups and real audit
groups; shared fake UUIDs do not cross roles. Known group disjointness was
checked again by the verifier. Unknown ancestry is not certified by this rule.

Frames are unit-normalized before summarization. Arms are: mean embedding;
mean plus mean absolute adjacent-frame difference; mean plus the corresponding
difference divided by observed time intervals. The last two arms both have
1,536 features; the mean-only arm has 768. Standardization is fit-only; C is
chosen from [0.1, 1, 10] by calibration BCE. Training weights balance class and
within-class ancestor multiplicity. All selected fits converged.

## Held-generator results

Each audit comparison uses 326 real and 2,686 fake videos. Labels are fake=1.

| Held generator | Mean only | Mean + frame delta | Mean + delta/time |
|---|---:|---:|---:|
| ModelScope | 0.84348 | 0.92599 | 0.86808 |
| VideoCrafter2 | 0.85222 | 0.90196 | 0.89007 |

Ancestor-cluster, source-stratified paired bootstrap, 2,000 replicates:

| Held generator | Frame-delta gain, 95% CI | Delta/time gain, 95% CI |
|---|---|---|
| ModelScope | +0.08251 [0.06658, 0.09918] | +0.02460 [0.01468, 0.03430] |
| VideoCrafter2 | +0.04974 [0.03377, 0.06557] | +0.03785 [0.02400, 0.05106] |

These intervals condition on fitted models and source/ancestor proxies. They
do not establish new-real-source generalization or account for all model
selection uncertainty. Parameter/feature-capacity controls remain incomplete.

## Decisive negative control

A separate one-dimensional LR using only log(median frame interval), with the
same grouped split and fit/calibration rules, achieves AUROC **1.0 in both
held-generator audits**. Median intervals are approximately 0.033367 s for
Vript, 0.125 s for ModelScope and 0.1 s for VideoCrafter2.

The temporal feature gains cannot yet be attributed to generation forensics:
sampling time exposes class/source identity. This control shows that nuisance
information is available; it does not prove the DINO classifier uses that
specific cue. Dividing by elapsed time is not sufficient evidence that the
confound has been removed.

Next experiment: freeze a common physical-time sampling protocol for all
sources, with matched frame count and preprocessing; reuse the same ancestor
allocation; compare native-frame and time-sampled baselines and re-run the
timing-only control. Preserve exclusions by source and keep all final
confirmation data closed. A second independent real source is still required
for the eventual research claim.

## Storage and reproducibility

Full manifest, model coefficients, per-video predictions, lock hashes and logs
remain at `/root/autodl-tmp/cvpr27/runs/cached_dino_baseline_v1` on the server.
Local Git contains only this report, code and four compact summary/protocol
files (~11 KB JSON). `verify_cached_dino_baseline.py` rehashed run artifacts,
recomputed AUROC, checked group separation and generated the intervals and
timing probe. This is mechanical verification by the implementer, not an
independent scientific reproduction.
