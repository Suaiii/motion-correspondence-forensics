# Physical-time matching decision

The full cached DINO comparison is complete. It used 28,674 development
records, with 28,672 successful time-grid extractions and two exclusions. The
native middle-eight-frame arm and the new one-second eight-frame arm shared the
same DINOv2 ViT-B/14 weights, grouped split, calibration rule, and generator
holdouts.

The native delta arm was strong: AUROC 0.9183 on the held ModelScope audit and
0.8992 on the held VideoCrafter2 audit. After physical-time matching, the
delta arm became 0.8445 and 0.8628. Semantic-only time-grid scores were 0.8441
and 0.8556. This confirms a real temporal representation signal is worth
further study, while showing that a large fraction of the native-frame gain
was a timing/source confound.

## Decision

Retain `time_delta` as a mechanism candidate. Reject the native-frame delta
gain as a standalone contribution. Do not describe the current result as
unknown-generator generalization or a patent effect.

The next accepted-cohort experiment must add:

1. at least two accepted real-source families;
2. at least four independently identified generators, including CogVideo;
3. identical physical-time windows and frame count for every source;
4. a timing-only control, an equal-FLOP semantic baseline, and an estimator
   control;
5. group-disjoint fit/calibration/audit allocation with a fresh source family;
6. five stochastic seeds and source-grouped confidence intervals.

The candidate passes a mechanism gate only if its gain over the matched
semantic baseline has a positive interval on both held-generator groups and
does not disappear under the timing-only control. The current experiment is an
exposed development diagnostic and cannot satisfy that gate.
