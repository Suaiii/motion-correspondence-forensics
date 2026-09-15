# P2C operator response screen

- Protocol: `operator_response_v1`, legacy 4 fps / 8 frames / 128 px cache; fit-only calibration selection; no external tuning.
- Formula: `(median(|wrong_integer|, |fractional|) - |correct|) / (MAD + 1e-3)` with twelve pooled temporal/spatial features.
- Synthetic invariants: PASS.
- Legacy audit AUROC: 0.678947; selected C=100; baseline frozen fusion audit AUROC 0.886257.
- Decision: reject this first formula as the main method. Preserve as a valid negative result; do not tune it against audit.
- Next bounded variant: test signed residual response and four-control magnitude-matched permutations only after P2D protocol acceptance. If it cannot beat simple fusion on held-out source, close the operator-response branch and redirect to strong-baseline/generalization analysis.
