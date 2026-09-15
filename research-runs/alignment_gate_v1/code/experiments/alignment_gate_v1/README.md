# Alignment mechanism diagnostic v1

Bounded local research run on the retained 595-video development manifest. Five identical 49,601-parameter bag networks, seeds 17/29/43, twenty epochs each. Checkpoints and thresholds use clean calibration only. No SNN is tested.

The two primary comparisons are correct correspondence against wrong integer correspondence and fractional-only displacement. Flow is quantized to OpenCV's 1/32-pixel interpolation-table resolution before constructing controls. All three use one bilinear remap with identical per-pixel fractional weights and the intersection of valid pixels. The unwarped anchor shares this mask. The fifth input is the signed channelwise reduction in absolute residual error from fractional-only to correct alignment.

These interventions do not make every nuisance identical: sampled texture and displacement smoothness change, fractional flow still contains subpixel motion, and the common mask may reveal source. A positive result would still require independent-source replication. The old development audit is explicitly reused; this run is not a new held-out confirmation cohort.

Run each stage through the existing E-drive runtime, in this order:

```powershell
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/tests.py
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py freeze
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py cache
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py train
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py evaluate
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py probes
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/run_alignment.py report
& research-runtime/enter.ps1 -Script experiments/alignment_gate_v1/verify_results.py
```

Do not rerun mutation stages over existing artifacts. The fixed run directory is `research-runs/alignment_gate_v1`. A new fit requires a new versioned experiment/run and a new pretraining lock. Read-only `verify_results.py` reloads all checkpoints and recomputes saved predictions, calibration thresholds, AUROC (also by explicit pairwise comparison), and probe predictions. It writes a verification receipt; this is mechanical checking by the implementer, not independent review.

`run_alignment.py` reuses the previous training engine and model without editing them. The complete imported source set is hashed and copied under the run's `code` tree. The source videos remain read-only at their original manifest paths. This package requires the recorded local environment and original assets; it is not a standalone public reproduction bundle.

Tests cover backward-warp direction, OpenCV interpolation-table equality, common valid support, output shapes, finite values, model parameter count, and compensation arithmetic. A pre-freeze exact-equality test initially failed because separately rounded float16 residuals do not preserve exact subtraction; the check now allows 0.001 absolute quantization error, and all four tests passed before training. The production formula remains evaluated in float32 before cache conversion.

Verification history: all 30 neural groups passed on the first replay. The first probe replay failed its strict probability check because the verifier standardized saved float32 residual features in float64. Replaying the original StandardScaler dtype and both rounding points resolved the discrepancy without changing training, features, models, or predictions. The final verifier also reproduced all eight bootstrap intervals with an explicit pairwise AUROC implementation.
