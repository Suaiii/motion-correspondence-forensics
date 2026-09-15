# Baseline and novelty status (2026-09-14)

## Phase-2 correction

The new [paired baseline audit](../../../research-runs/phase2_evidence_audit_20260914/report.md) reproduces frozen external fusion AUROC 0.6056, but correct-only is 0.6022 and fractional-only is 0.6434. Fusion-minus-correct is +0.0034 with source/known-parent clustered 95% CI [-0.05731, 0.06471]. Above-chance detection does not establish an incremental method contribution. These 150 exposed samples are external-development, with 50 real and 100 fake, and use 4 fps / 8 frames / 128 pixels. The independent source acceptance gate and native public-baseline reproduction remain incomplete. STALL has been added to the reproduction plan; its official precomputed embeddings are a native-protocol reference, not our correspondence features.

## STALL native reference (2026-09-15)

The pinned STALL implementation completed scoring 5,098 ComGenVid records from its official DINOv3 embedding route. Overall AUROC with real-as-positive direction is 0.85245. On the 150 IDs also present in our external feature cache, its AUROC is 0.82280, compared with 0.60560 for our frozen correspondence fusion. This is a strong diagnosis of a cross-source representation gap, not a fair same-backbone ranking: STALL uses the official DINOv3 precomputed representation, whereas our score uses native-video Farneback features and a different sampling/aggregation path. Full provenance and the matched-ID calculation are in [the comparison artifact](../../../research-runs/stall_comgenvid_20260915_comparison.json); D3 reproduction remains pending.

## Reproduced evidence

The locked `order_gate_v1`/`alignment_gate_v1` development protocol contains equal-parameter video baselines (49,601 parameters) with raw, aligned, wrong-integer and fractional controls. The alignment arm reaches clean audit AUROC 0.8327 versus 0.7594 for wrong-integer and 0.7658 for fractional. These are matched internal diagnostics, not external benchmark scores.

## Reproduction status

| Family | Current status | Evidence boundary |
|---|---|---|
| DINOv2 + LR/MLP | feature cache and lightweight probes available | no independent-source test yet |
| D3 / ReStraV / WaveRep / RIFT | planned integration | native reproduction not completed |
| G2VD / DCPT | novelty and protocol comparison pending | URLs alone are not reproduction |
| alignment-aware temporal consistency | mechanism diagnostic reproduced across 3 seeds and JPEG70 | historical development pool only |

## Gate decision

B01 remains incomplete. The alignment mechanism is the only current lead with a positive paired confidence interval, but no method is promoted to a paper claim until the external real-source protocol, source licensing, and matched strong-baseline table are complete.

The Kinetics-400 bounded external probe now has 64 float32 correspondence-feature records with finite-value QC and frozen-model directionality scores. These records are deliberately not treated as labelled test data: the probe has no matched fake set, full archive checksum, or completed licence review.

ComGenVid now supplies a balanced labelled external pilot (50 MSVD real, 50
Sora generated, 50 VEO3 generated). The frozen clean fusion reaches AUROC
0.6056 with source-stratified bootstrap 95% CI [0.5120, 0.6948]. Pairwise
AUROC is 0.5888 for MSVD--Sora and 0.6224 for MSVD--VEO3. This is supportive
but modest evidence; it does not replace larger-scale replication or native
strong-baseline comparisons.
