# Breakthrough summary: paired correspondence fusion

> Superseded interpretation: the [phase-2 audit](../research-runs/phase2_evidence_audit_20260914/report.md) reproduces the internal gain, but external fusion-minus-correct is only +0.0034 with a paired interval crossing zero. Source/label-conditional independent shuffling at both fit and audit retains high performance. The historical global-shuffle result below does not establish that within-video pairing is necessary. Preserve its numbers as exploratory evidence, not a causal mechanism claim.

## Finding

The correct and fractional alignment representations contain a paired,
video-specific signal. A calibration-selected linear fusion reaches audit
AUROC 0.88626 versus 0.83333 for correct-only. The gain is +0.05292 with
source-stratified 95% CI [0.00760, 0.10561]. Under JPEG70 it is +0.05760 with
source-stratified 95% CI [0.00467, 0.11815].

## Mechanism falsification

Shuffling fractional representations across videos while keeping dimensions,
labels, and classifier fixed reduces AUROC to 0.83626; 200 permutation trials
have mean 0.83561, SD 0.00700, maximum 0.85380, and upper-tail p=0.00498.
Therefore the gain is tied to correct within-video correspondence rather than
feature count alone.

## Research claim boundary

This is a statistically supported development-pool mechanism breakthrough. It
is not yet external-domain evidence: the independent real-source and unseen
generator gates remain open. The next experiment must freeze the feature order,
calibration protocol, and permutation control before any paid run.
