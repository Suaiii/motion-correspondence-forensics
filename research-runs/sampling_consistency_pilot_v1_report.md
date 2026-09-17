# Sampling consistency pilot: reject the current candidate

On 2026-09-17, the server completed six heads × five seeds × two held-generator
splits: 60 fits on the existing 28,672-record paired DINO development manifest.
Every head has 393,729 parameters. Checkpoint selection uses calibration BCE;
held-generator audit scores never select epochs. The model is a small MLP on
frozen features, not a fine-tuned video backbone or SNN.

| Arm | ModelScope mean AUROC | VideoCrafter2 mean AUROC |
|---|---:|---:|
| Semantic mean, duplicated input | 0.88476 | 0.90917 |
| Mean + unordered standard deviation | 0.88986 | 0.90142 |
| Mean + temporal delta | 0.89390 | 0.90572 |
| Ordinary two-view ERM | 0.90153 | 0.90975 |
| Same-video paired consistency | 0.89373 | 0.91745 |
| Within-source shuffled consistency | 0.89574 | 0.91478 |

These are means of five individual seed AUROCs, not ensemble scores. The
separate paired bootstrap averages the five models' probabilities first and
resamples source/label-stratified ancestor-proxy groups 2,000 times.

For that ensemble estimand, paired consistency minus ordinary two-view ERM is
-0.00710 (95% CI [-0.01331, -0.00103]) on ModelScope and +0.00799
([0.00280, 0.01335]) on VideoCrafter2. Individual-seed differences agree:
0/5 positive on ModelScope, 5/5 on VideoCrafter2. Paired versus shuffled
consistency is -0.00796 ([-0.01515, -0.00068]) and -0.00055
([-0.00541, 0.00487]). Thus the required same-video pairing benefit is absent.

## Decision

Reject this fixed consistency-loss candidate under the predeclared criterion.
Do not tune its coefficient against these audit scores to manufacture a pass.
Keep ordinary two-view ERM as a stronger development comparator. The improved
MLP scores relative to the prior LR are an estimator change, not a new forensic
mechanism. The supervised shuffled control uses labels only within the fit
set; it is an ablation of pairing necessity, not a deployment procedure.

The physical-time verification is also negative for the earlier claim: time
delta versus semantic LR confidence intervals cross zero on both holdouts.
Nearest-frame grids retain timing-only AUROC 0.78395/1.0. All current neural
heads share this residual nuisance and one real source, so none establishes
independent generalization or a CCF-A/patent-ready method.

## Execution and verification

- Complete run: 131.81 seconds, including feature reads, training and bootstrap;
  not the total billed instance uptime. No arbitrary walltime limit was set.
- RTX 4090 D executed the heads. These cached-feature heads need little GPU
  memory; low utilization is not a reason to repeat unnecessary extraction.
- A separate inference script reloaded all 60 saved checkpoints, re-extracted
  audit inputs from hash-verified caches and reproduced stored logits/metrics.
  It verified epoch selection against all 40 recorded calibration losses and
  the identical parameter count. All checks passed without refitting models.
- This is mechanical replay by the same research workflow, not an independent
  replication. The bootstrap conditions on these fitted models; five-seed
  variability is separately reported and intervals are not multiplicity-adjusted.
- Checkpoints, histories and per-video predictions remain under server path
  `/root/autodl-tmp/cvpr27/runs/sampling_consistency_pilot_v1/`. Only code and
  compact report/protocol/verification evidence are copied locally and to GitHub.

## Next research gate

The two negative controls now point away from another global-delta head.
Before another method claim, complete a second real-source cohort and
sample-level ancestry joins, then compare the spatially localized controlled
correspondence response from the phase-2 plan against this stronger baseline.
Keep a timing-only diagnostic on every sampling protocol; a nominal target
FPS is insufficient. Any resampling/interpolation remedy needs its own
estimator control rather than being assumed harmless. No new final set was
opened in this pilot.
