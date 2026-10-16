# AL146 causal predictive-residual two-timescale signed-event SNN

The candidate is fixed before training. Each normalized DINO sequence has a
causal one-step predictor (`z[t-1]` for the first transition and a linear
extrapolation thereafter). Residuals feed fixed fast and slow traces with
`alpha_fast=0.65` and `alpha_slow=0.95`. Signed events are emitted when the
fast-minus-slow residual exceeds `median + 3*MAD`, with the sign preserved.
The SNN readout is a 768-to-64 tanh layer followed by a scalar head. Five seeds
are fixed to `[11,23,37,53,71]`.

```powershell
$py = 'C:\Users\ZHUyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -X utf8 research-runs\VIDEO_EVIDENCE_V1_20261004\AL146_predictive_residual_two_timescale_snn.py `
  --selection research-runs\VIDEO_EVIDENCE_V1_20261004\selection_dense_holdout_v1_8frame_clean.json `
  --manifest research-runs\VIDEO_EVIDENCE_V1_20261004\v1_manifest.jsonl `
  --features /srv/video_evidence_v1/runs/dino_features `
  --run-dir /srv/video_evidence_v1/runs/AL146_predictive_residual_two_timescale_snn
```

The script fits only AAGenvid `fit`, uses AAGenvid `calibration` for dense
baseline C selection, and leaves AEGIS untouched until evaluation. It
recomputes the same dense native-velocity baseline and candidate events for
normal, static, shuffle, and reverse controls. The report contains each
seed's AUROC and candidate-minus-dense delta for in-domain, descriptive
OpenAI-Sora, and AEGIS external cohorts, plus the five-seed mean, descriptive
95% t interval, and positive-seed count.

The dense baseline uses the same three arms as AL145 (semantic mean, absolute
native-frame delta mean, and native-PTS velocity mean); the velocity arm uses
the locked per-sample native PTS intervals. This keeps the AL146 comparison
matched to the accepted AL145 implementation.

Release gate: mean external delta >= 0.03, paired 95% lower bound > 0, at
least four of five external deltas positive, and all static/shuffle/reverse
controls below the normal result. Any hash, role, PTS, or untouched-holdout
violation is an immediate no-go. A pass still requires an independent review
and further source-balanced confirmation before a CCF-A claim.
