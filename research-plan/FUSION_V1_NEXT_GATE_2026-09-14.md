# Fusion v1 next gate

> Superseded by [phase 2](PHASE2_PLAN_2026-09-14.md). External data now exist, but the paired external increment is not supported. Five identical deterministic LR refits do not establish seed stability; apply the seed gate to stochastic training. The existing LR concatenation has more coefficients than correct-only and must not inherit the neural baseline's equal-parameter claim. The historical instructions below remain a record of the earlier candidate.

## Frozen candidate

Use the concatenation of the `correct` and `fractional` alignment feature
vectors as the only proposed method change. Keep the backbone and parameter
budget matched to alignment_gate_v1. Select C on calibration only; do not tune
on audit or external test.

## Existing evidence

The candidate improves audit AUROC by +0.05292 (clean) and +0.05760 (JPEG70).
Source-stratified paired bootstrap intervals are [0.00760, 0.10561] and
[0.00467, 0.11815], respectively.

## Release criteria

1. Re-run with at least five frozen seeds under the same split.
2. Evaluate an accepted independent real source and an unseen generator.
3. Compare parameter-matched correct-only, correct+wrong-integer, and
   correct+fractional arms.
4. Report source-stratified confidence intervals, calibration protocol,
   runtime, and all failures.

Until all four criteria pass, call this a development breakthrough candidate,
not a final CCF-A claim.
