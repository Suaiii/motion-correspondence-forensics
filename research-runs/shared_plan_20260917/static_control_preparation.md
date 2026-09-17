# DX01: six-frame static control preparation

Work package: cc-round-1-20260917. Plan: cvpr27-20260917-v1.1.
Result: software preparation passed; no static baseline has been trained and
no detection effect has been measured.

## Implemented comparisons

The temporal branch retains the six prescribed triples. The static branch
uses `(0,0,0)` through `(5,5,5)`, one for each of the original six frames.
Both retain the same six global semantic vectors, temperature, perturbation
scales, spatial encoder, unordered aggregation and semantic fallback. The
default head has 217,057 parameters in either mode.

`make_matched_control_models` produces fresh independent heads with identical
initial parameter values. Static-baseline training must use its own optimizer
and training run; it must not be relabelled from a fitted temporal checkpoint.
The matched-recipe helper rejects differences in the common data, split,
seeds, augmentation, optimizer, capacity or checkpoint-selection settings.
It validates software configuration equality; the actual experiment recipe is
not frozen or executed. Save branch mode with checkpoint configuration because
the raw weight tensors alone do not identify which branch was trained.

`fixed_branch_sensitivity` uses one unchanged eval-mode temporal head twice,
replacing only the response branch. It preserves all six semantic inputs,
does not change weights and labels its output as sensitivity only. It rejects
training mode to avoid comparing different dropout draws.

## Verification actually run

`static_control_cpu_checks.json` records **21 passing tests**: the original 11
mathematical tests and 10 new static-control tests. They cover each frame's
individual `(i,i,i)` response against NumPy, frame permutation, identical-frame
equivalence, equal parameter counts and initialization, independent storage,
semantic-input identity, fixed-weight replacement, gradient boundaries,
fallback and mismatched selection-rule rejection.

All work used small local CPU synthetic tensors. CUDA was not initialized;
no backbone inference, real-video read, optimizer step or new feature
extraction occurred. The measured script runtime was 4.953 seconds, excluding
Python/PyTorch startup. The previous GPU certificates apply to their archived
source version; the new static mode has only CPU verification in this round.

## Equality and differences that must remain visible

The arms see the same six input frames and have equal trainable capacity.
This does not assert equal information-theoretic content: temporal connections
are deliberately removed in the control. Frame-role occurrence counts also
differ: temporal `[2,3,4,4,3,2]`, static `[3,3,3,3,3,3]`; the shared six-frame
semantic mean remains identical. No weighting rule was changed to hide this.

The implementation caches 11 unique affinity matrices for temporal input and
6 for static input, while both perform 78 composition products and produce
six response groups. Thus computation is not exactly matched. A tiny CPU
operator benchmark on `[1,6,256,32]` synthetic tokens gave median 0.131 s
temporal and 0.145 s static over three alternating-order measurements. This
small measurement cannot predict GPU/video throughput or establish a speed
advantage. Full-pipeline cost remains a future measurement.

The static control uses the original JS/perturbation formula. No temperature
change, forced subtraction or zero-static-response correction was introduced.
Software success does not pass the temporal-mechanism gate.
