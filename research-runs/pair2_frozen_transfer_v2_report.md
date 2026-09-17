# Complete Pair2 development transfer

This supersedes the initial 195-clip transfer in
`pair2_frozen_transfer_v1_report.md`. The previously excluded HD-VG clip was a
497-second 1080p video whose full-frame timestamp probe exceeded 60 seconds.
It was retried without that operational deadline and passed the same decoder,
sampling, raw-hash and feature checks. No data-quality exclusion is warranted.
The retry reuses 195 hash-verified feature records and extracts only that clip;
the original timeout and initial metrics remain preserved.

The complete cohort contains **98 HD-VG real and 98 CogVideo generated clips**,
100 author-origin groups and 96 groups spanning both labels. Four of the 200
acquired candidates remain excluded due to two origins shared with Pair1.
All 196 eligible clips pass extraction. There is no new detector fitting,
checkpoint selection or recalibration on this external-development cohort.

## Results

These are five-model probability-ensemble AUROCs. The source column identifies
the fake generator used for the original fitting; both configurations used
Vript real videos. Every cell below evaluates the same HD-VG/CogVideo cohort.

| Arm | Train fake: VideoCrafter2 | Train fake: ModelScope |
|---|---:|---:|
| Semantic mean | 0.77593 | 0.88671 |
| Mean + unordered standard deviation | 0.82257 | 0.86058 |
| Mean + temporal delta | 0.84465 | 0.89484 |
| Ordinary two-view ERM | 0.86172 | 0.90848 |
| Same-video paired consistency | 0.81862 | 0.90848 |
| Within-source shuffled consistency | 0.85870 | 0.93367 |

Ordinary two-view ERM improves over semantics by +0.08580 (paired origin-group
95% CI [0.05686, 0.11990]) and +0.02176 ([0.00300, 0.04240]). The consistency
candidate still does not demonstrate a benefit from same-video pairing.
Bootstrap resamples entire origin groups jointly across labels; it conditions
on the frozen models and is not multiplicity-adjusted.

The frozen interval-only probes each reach **0.93367 AUROC** on this complete
cohort. Jitter-inclusive probes yield 0.02041/0.0 without post-hoc inversion.
These controls still show available sampling/source cues; they do not prove
the neural classifier's decisions are causally driven by timing alone.

The small second-source cohort is an engineering and evaluation advance, not
a new-algorithm result. Actual timing remains a strong available cue, and the
acquisition uses a non-random archive prefix. The author index/origin/prompt
join is explicit but does not independently prove pixel-level ancestry or
camera capture. Do not promote this now-exposed cohort to a final test set.

## Artifacts and execution

The completed retry took 111.21 seconds, including slow-clip recovery and
recomputed metrics/bootstrap, in addition to the 92.51-second initial pass.
These are process runtimes, not billed instance uptime. The old 60 classifiers
remain frozen. Verification evidence, timing-control transfer scores and code
hashes are included in `pair2_frozen_transfer_v2_evidence.json`; large feature
and per-video prediction files remain at
`/root/autodl-tmp/cvpr27/runs/pair2_frozen_transfer_v2/`.

The final verifier passed all 60 checkpoint replays, individual/ensemble
metric checks and raw/feature/checkpoint hash checks, with no model refitting.

The next methodological requirement is an actual-lag/estimator control and a
localized controlled-correspondence test against the stronger ordinary ERM
baseline. Formal source acceptance and algorithm novelty remain incomplete.
