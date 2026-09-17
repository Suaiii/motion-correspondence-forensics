# Sampling diagnostics and Pair2 transfer

These scripts use the existing server workspace `/root/autodl-tmp/cvpr27`.
They require the frozen caches, manifests and model weights referenced in the
saved protocol JSON files. Do not move videos or features to the local PC.
Use distinct output directories; protocols and successful records are immutable.

## Frozen paired-time replay

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
environment/venv/bin/python verify_paired_time.py \
  --root runs/paired_dino_time_v1 --time-cache runs/time_matched_dino_v1 \
  --output runs/paired_time_verification_v2
```

This reconstructs frozen-head inputs, checks saved predictions and runs
cluster bootstrap plus timing-only controls. It does not refit the main heads.

## Six-arm GPU development pilot

```bash
CUBLAS_WORKSPACE_CONFIG=:4096:8 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
environment/venv/bin/python sampling_consistency_pilot.py \
  --base /root/autodl-tmp/cvpr27 --output runs/sampling_consistency_pilot_v1
environment/venv/bin/python verify_sampling_consistency.py \
  --base /root/autodl-tmp/cvpr27 --root runs/sampling_consistency_pilot_v1
```

The complete 60-fit schedule has no walltime cap. Completed fits are reusable
only after their hashes pass. Calibration BCE selects epochs. The candidate
failed the frozen criterion; do not tune against exposed audit outcomes.

## Pair2 acquisition, origin join and frozen transfer

`stream_hdvg_prefix.py` streams only a bounded archive prefix, not the entire
80 GB archive. It requires the previously CRC-checked 7z headers and outer
metadata under `runs/overnight_20260911/hdvg_header_probe_v1`, pinned author
label files and `unrar`. Set HTTP(S) proxy variables only for the command when
needed. Never put credentials in code, manifests or this repository.

The recorded v2 extraction reuses verified chunks from the initial attempt:

```bash
environment/venv/bin/python stream_hdvg_prefix.py \
  --base /root/autodl-tmp/cvpr27 --output data/hdvg_prefix100_v2 \
  --labels Pair2_labels.txt --range-cache data/hdvg_prefix100_v1/ranges
environment/venv/bin/python audit_pair2_origins.py \
  --base /root/autodl-tmp/cvpr27 --hdvg data/hdvg_prefix100_v2 \
  --output runs/pair2_origin_audit_v1
```

For a fresh acquisition, omit `--range-cache`. The origin audit additionally
requires pinned `HDVG_14k_classes.txt` and `Pair1_labels.txt`. It checks the
metadata Git blob and joins origin IDs and prompt text, then excludes overlap
with all known Pair1 Vript IDs. Author metadata is not independent content proof.

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
environment/venv/bin/python evaluate_pair2_frozen.py \
  --base /root/autodl-tmp/cvpr27 --audit runs/pair2_origin_audit_v1 \
  --output runs/pair2_frozen_transfer_v2 \
  --reuse-cache runs/pair2_frozen_transfer_v1 --probe-timeout 0
environment/venv/bin/python verify_pair2_transfer.py \
  --base /root/autodl-tmp/cvpr27 --root runs/pair2_frozen_transfer_v2
```

The first pass has one operational ffprobe timeout. The retry reuses successful
features and removes that per-probe deadline for the pending clip, preserving
sampling and pixels. For a fresh transfer, omit `--reuse-cache`. No detector
fitting, recalibration, new-source checkpoint selection or final-set access is
performed. Keep the initial result alongside the completed retry.

Before a requested shutdown: complete verification, copy only compact evidence,
compare its hashes and push the reviewed paths to GitHub. Check that no research
process is active before calling the provider shutdown command. SSH disconnection
alone is not proof of provider billing status.
