# Physical-time matching decision

The full cached DINO comparison is complete. It used 28,674 development
records, with 28,672 successful time-grid extractions and two exclusions. The
native middle-eight-frame arm and the new one-second eight-frame arm shared the
same DINOv2 ViT-B/14 weights, grouped split, calibration rule, and generator
holdouts.

The native delta arm was strong: AUROC 0.9183 on the held ModelScope audit and
0.8992 on the held VideoCrafter2 audit. After physical-time matching, the
delta arm became 0.8445 and 0.8628. Semantic-only time-grid scores were 0.8441
and 0.8556. Frozen-head replay and 2,000 paired ancestor-proxy bootstrap draws
now give time-delta gains of +0.000425 (95% CI [-0.011488, 0.011573]) and
+0.007175 ([-0.004446, 0.018758]). Both intervals cross zero. These results
do not establish an incremental temporal signal.

The native-to-time change reduces the delta-over-semantic gain by 0.078185
and 0.044166, with both reduction intervals below zero. This is evidence of
sampling sensitivity, not proof that timing alone caused the entire reduction:
the selected frames and temporal coverage also change.

Crucially, nearest-native-frame sampling has not removed timing information.
A log median-interval classifier still obtains held-out AUROC 0.78395 and
1.0. Adding interval jitter reverses its ranking on the held sources (0.0 and
0.00309); preserve this orientation rather than flipping scores after looking
at held-out labels. That reversal is another sign of source dependence, not
a useful general detector or evidence that timing is absent.

## Decision

Retain `time_delta` only as an experimental baseline. It has not passed the
mechanism gate below. Reject the native-frame delta gain as a standalone
contribution. Do not describe the current result as demonstrated
unknown-generator generalization or a patent effect. The earlier statement
that a real temporal signal had been confirmed is withdrawn.

The replay recomputed probabilities using the saved six heads for both audit
cohorts and both holdouts, without refitting those heads. This is mechanical
verification by the same workflow, not independent scientific replication.
Compact evidence: `research-runs/paired_time_verification_v2_report.json`.

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
