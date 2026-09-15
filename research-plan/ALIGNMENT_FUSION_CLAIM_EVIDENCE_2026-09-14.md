# Learned correspondence fusion: claim–evidence checkpoint

## Supported claim

On the locked 595-video development protocol, concatenating the `correct` and
`fractional` intermediate alignment features and fitting a calibration-selected
linear head improves audit AUROC over the correct-only arm under both clean and
JPEG70 conditions.

| condition | fusion gain | paired bootstrap 95% CI | positive fraction |
|---|---:|---|---:|
| clean | +0.05292 | [0.00557, 0.10888] | 0.988 |
| JPEG70 | +0.05760 | [0.00323, 0.11696] | 0.982 |

The regularization constant is selected on calibration only (clean C=30,
JPEG70 C=100). No audit-based hyperparameter choice is used in the primary
records.

## Not yet supported

- independent real-source generalization;
- comparison against native D3/ReStraV/WaveRep/RIFT implementations;
- causal attribution to motion rather than residual source nuisance;
- final CCF-A-level performance claim.

## Next gate

Freeze the fusion feature definition and evaluate it on the accepted external
real source and unseen generators. Preserve the current development results as
the pre-registered reference, including all negative nuisance-adversarial and
probability-contrast pilots.
