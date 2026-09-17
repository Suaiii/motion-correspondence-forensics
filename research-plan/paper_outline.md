# Working research question and evidence outline

WR01 draft, cc-round-1-20260917; author decisions remain with the user and
supervisor. This is an outline for a possible new paper, not submission text
claiming a validated algorithm.

## Question

Does the response of local visual correspondences to a controlled middle-node
perturbation add identifiable temporal information beyond the same six frames
processed independently, under source and actual-time controls?

The new work must be distinguished from the earlier propagation/degradation
paper. Shared engineering and datasets do not automatically constitute new
scientific contribution; no old results are presented as this method's effect.

## Planned argument

1. Explain why local temporal correspondence is a plausible forensic signal,
   while acknowledging established cycle-consistency and residual methods.
2. Define the unchanged soft correspondence, composition discrepancy and
   calibrated perturbation response. State that these are statistical
   measurements, not direct tests of physical laws or forgery localization.
3. Establish support in actual joint timestamps and source/ancestor groups
   before evaluating a mechanism. Missing PTS are missing evidence, not
   automatically rejected videos.
4. Compare with a separately trained six-frame static branch, ordinary patch
   aggregation, uncalibrated matching, entropy/support probes and strong
   matched preprocessing/augmentation baselines.
5. Only after an accepted development effect, freeze the method and test
   genuinely held-out sources/generators and propagation conditions.

## Claim-evidence ledger

| Possible claim | Current evidence | What is still required |
|---|---|---|
| Implementation follows the specified operator | Numerical/reference checks and synthetic backbone integration | Independent real-input replay and full-pipeline profile |
| Static control preserves the observation budget and semantics | All six `(i,i,i)` groups; equal 217,057-parameter heads; CPU contract tests | Actual matched training and checkpoint-selection audit |
| Response identifies additional temporal information | Not established; static sequences also give nonzero responses | Gain over the retrained static strong baseline and mechanism interventions |
| Sampling confounds are controlled | MS/VC2 long-edge metadata match in a 100-clip historical subset | Full original PTS for real sources, joint support, between-triplet phase and continuous nuisance tests |
| Method generalizes beyond strong baselines | No evidence for the new candidate | Frozen data roles, five seeds, shared-ancestor uncertainty and new-source confirmation |
| A deployment advantage exists | Not established | Actual end-to-end cost and calibrated low-FPR evaluation |

## Figures/tables to earn

- Actual timestamp/joint-support table with missing-source counts and retention.
- Same-frame static-versus-temporal mechanism table; untrained diagnostic
  replacements kept separate from independently trained baselines.
- Source/generator/propagation main table with fixed thresholds and uncertainty.
- Response maps labelled as responses, with no unsupported localization claim.
- Failure groups and the measured compute/coverage tradeoffs.

Do not write a result-bearing abstract until these evidence slots are filled.
If the full method does not exceed the static strong baseline, withdraw the
temporal-mechanism claim rather than modifying the formula to force static
responses to zero. The overall innovation objective remains unmet.
