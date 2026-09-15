# Alignment mechanism evidence checkpoint

## Evidence

The frozen `alignment_gate_v1` evaluation reports a consistent gain for temporal alignment over the matched wrong-integer control: clean ΔAUROC `0.14152`, 95% paired bootstrap interval `[0.07485, 0.21608]`; JPEG70 ΔAUROC `0.15526`, interval `[0.08743, 0.23043]`. All three seeds are positive in both conditions. Alignment also exceeds fractional-shift control (clean `0.10292`, interval `[0.03040, 0.18188]`; JPEG70 `0.10643`, interval `[0.03479, 0.18656]`).

## Interpretation

This is the strongest current algorithmic lead: temporal correspondence appears to expose a signal that survives JPEG perturbation and is not explained by the tested integer/fractional misalignment controls. It is not yet a CCF-A claim: the evaluation is on the historical development pool, the independent-source replication flag is false, and the mask-only probe (`AUROC 0.8035`) shows residual nuisance shortcuts.

The compensation branch is rejected as the primary contribution for now: its clean gain over alignment is only `0.01930` with interval `[-0.03977, 0.07895]`, and its JPEG70 difference is negative (`-0.01520`). The next method design should therefore center on alignment-aware temporal consistency, with nuisance controls and independent real-source replication as mandatory gates.

## Decision

Retain alignment as the mechanism hypothesis; do not spend paid GPU time on the compensation branch until an independent source reproduces a positive confidence interval. This checkpoint is evidence of a viable direction, not completion of the research goal.
