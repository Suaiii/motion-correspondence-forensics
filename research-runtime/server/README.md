# Portable CVPR 2027 research runtime

2026-09-10 deployment update: a user-rented RTX 4090 D instance is connected, with cgroup-verified 16 CPU cores and 62 GiB memory, 550 GB data disk and user-confirmed CNY 1.88/hour instance price. The initial software/GPU resume checks and 100-video historical performance profile have completed. The paragraphs below describe the reusable workflow; server rental is no longer pending. Full research data and strong-baseline experiments remain pending.

Capacity tuning on this instance: the original serial 100-video profile took 312.2 s (269.8 s decoding, 42.0 s flow/control computation, 0.43 s GPU inference). The source-identical 12-process preprocessing test took 50.1 s. A synthetic training-tensor benchmark of the small bag network selected batch 64 (about 1637 clips/s; 3.64 GiB allocated), not 128/256, which were slower. These are separate measurements, not an end-to-end training rate, and do not set the batch size for a large backbone.

`configs/mechanism_expanded.json` is a prospective larger experiment: 18k target clips, five seeds, 40 epochs, batch64, 8 loading workers, 12 materialization workers, 320 GiB cache ceiling and 5000 bootstrap replicates. Four of five seeds must agree. `configs/study_scale.json` records larger data targets, not acquired sample counts. New monetary limits are pending; no extra rental is implied.

For larger runs, use `materialize --arm correct --workers 12` after extraction and before fitting that arm. It renders immutable float32 NPY inputs in parallel; training reads them instead of recomputing all warps each epoch. After all fits/evaluations for that arm, `purge-materialized --arm correct` verifies hashes and removes only generated files under the materialized subtree; source videos and RGB/flow caches stay available. It refuses active training. Do not purge during evaluation. Render one arm at a time to stay within disk capacity. Resume reuses per-shard receipts. Cached and computed input tensors are both made contiguous; the v4 test caught a CPU layout-dependent training difference, and this normalization fixes the source of that discrepancy.

This package implements the server execution foundation and mechanism experiment. It does not mean a server has been selected, rented, connected, or benchmarked. Public dataset metadata is pinned locally; new research video samples have not yet been acquired or accepted. Native D3/ReStraV/WaveRep/RIFT reproductions and the final paper remain downstream tasks.

## Server setup

Select the SSH host and verify its data mount, GPU, persistent-disk retention and actual stop/billing action. Fill `configs/server.example.json` into a private deployment configuration; do not put credentials or private keys in it. No remote command is dispatched by this template.

Copy this directory to the selected server, use Python 3.11, ensure `ffmpeg` and `ffprobe` are present, and run `bash scripts/bootstrap.sh`. The bootstrap creates a project-local venv and installs a pinned CUDA 12.1 Torch stack. It requires a compatible driver. It does not install system packages, start cloud resources, or stop billing. Execute `doctor` first:

```bash
.venv/bin/python run.py doctor --data-root /data/videos --cache-root /data/cache --output /data/doctor.json
```

The paths above are examples, not discovered server mounts. `doctor` reports the process's actual hardware and tools, not cloud-provider status. All new manifests use root-relative POSIX paths; the existing Windows experiment files remain untouched.

## Dataset acquisition and identity

`catalog` pins the two public Hugging Face repositories to commits and records file sizes/objects. `download-plan` accepts exact file names only; `fetch` checks size and Git/LFS identity and supports byte-range resume. No command implicitly downloads the entire dataset.

```bash
.venv/bin/python run.py catalog --output /data/catalog.json
.venv/bin/python run.py zip-index --catalog /data/catalog.json --repo AIGVDBench/AIGVDBench --archive AIGVDBench/OpenSource/T2V/Wan2.1.zip --output /data/wan-index.json
.venv/bin/python run.py zip-fetch --catalog /data/catalog.json --repo AIGVDBench/AIGVDBench --archive AIGVDBench/OpenSource/T2V/Wan2.1.zip --members /data/selected-members.json --data-root /data/videos/wan21 --max-gib 20
```

`selected-members.json` is a JSON array of exact archive member names chosen from the pinned index before examining detector scores. ZIP reads require HTTP range support; the client refuses full-body fallback. Completed members are hash-checked on resume; an interrupted compressed member restarts and preserves the partial file. ZIP CRC plus downloaded-member SHA256 does not constitute verification of the entire remote archive; receipts explicitly distinguish these. RAR/solid archives require explicit whole-archive acquisition and separately checked extraction; the runtime does not pretend they support selective ZIP reads.

Every canonical JSONL row must contain:

```json
{"sample_id":"dataset:video-id","path":"source/video.mp4","sha256":"64_lowercase_hex_characters","label_fake":1,"source":"ModelScope","generator":"ModelScope-version","task":"T2V","source_group":"namespaced:original-id","reference_group":null,"prompt_group":null,"ancestry_status":"verified","role":"fit","scope":"development","dataset_revision":"immutable_release","license":"recorded-source-license"}
```

Real rows have `generator: null` and `task: "real"`. Allowed roles: `fit`, `calibration`, `dev_audit`, `ood_dev`, `final_audit`, `profile`. Allowed scopes: `development`, `final`, `historical`, `synthetic`. Historical data are profile-only. Unknown ancestry is reported and blocked from confirmation-grade manifests until evidence is reconciled; do not change it to verified merely to pass validation. A source ID and a reference ID referring to the same original must use the same namespaced value.

`audit` validates identity, cross-role ancestry, source/generator holdouts and optional file hashes. `split` deterministically assigns connected development groups at 60/20/20; it never invents generator holdouts or changes reserved OOD/final data. Targets are approximate when components span many samples. A data custodian must first reconcile native metadata and actual files; native path-label lists alone are insufficient.

## Budget admission

```bash
.venv/bin/python run.py budget-init --ledger /data/budget.json
.venv/bin/python run.py budget-reserve --ledger /data/budget.json --reservation mechanism-001 --category mechanism --hours 4 --hourly-rate ACTUAL_QUOTED_RATE --quote PROVIDER_QUOTE_REFERENCE
```

Reservations enforce CNY 3000, the five category caps and 180 GPU hours; both actual charges and outstanding reservations count. Use `budget-settle --actual-cny ... --hours ... --receipt ...` after obtaining the provider bill. Overspend is recorded, not hidden. GPU training checks reservation wall time and fit deadlines, saving prior committed epochs.

**The ledger is admission accounting, not a provider billing cap.** Stopping Python does not necessarily stop VM billing. Storage, network, idle time and GPU-instance lifecycle must be checked at the provider. `billing_stop_action` remains unset until this is verified; no invented automatic cloud shutdown is claimed.

## Mechanism execution

First profile 100 source-balanced eligible videos with `profile`; it measures decode, flow/control construction and inference separately. It does not measure training throughput or produce an actual bill. Then prepare a fresh run:

```bash
.venv/bin/python run.py audit --manifest /data/mechanism.jsonl --data-root /data/videos --check-files --output /data/manifest-audit.json
.venv/bin/python run.py prepare --config configs/mechanism.json --manifest /data/mechanism.jsonl --run-dir /data/runs/mechanism-interior-v1
.venv/bin/python run.py extract --run-dir /data/runs/mechanism-interior-v1 --data-root /data/videos --cache-root /data/cache
.venv/bin/python run.py train --run-dir /data/runs/mechanism-interior-v1 --cache-root /data/cache --device cuda:0 --arm correct --seed 17 --ledger /data/budget.json --reservation mechanism-001
```

Run all five frozen arms and seeds 17/29/43. Each arm has its own checkpoint/optimizer/RNG history. Repeating a completed fit is refused; repeating an unfinished fit resumes committed epochs. `--epochs-this-call` provides deliberate epoch-boundary pauses. Incomplete checkpoint commits or changed cache files are blocked for review; they are not silently accepted. Stale `.lock` files after process termination must be reconciled with the server process list before removal.

Inputs cache sampled RGB plus backward flow, not every dense residual arm. Full-video FFmpeg transformations precede PTS-based sampling; no repeated-frame padding is allowed. Qualifying short/black clips are removed across all conditions without replacement; unexpected decode failures stop extraction. Cached arrays are never loaded with pickle. The same cohort must be frozen for common-mask and interior comparisons. Any cross-run QC mismatch invalidates direct paired comparison.

The interior config uses a 16-pixel margin and a 12-pixel flow bound. Quantization is at 1/32 pixel. Correct, wrong and fractional controls share OpenCV interpolation weights. Four integer-field shifts preserve the original fractional part. Nuisance fields are recorded but not directly passed to the classifier. The 15-channel concatenation method has extra input parameters and must not be mislabeled parameter-matched.

After all fits, run `evaluate --role dev_audit`, `evaluate --role ood_dev`, `probes`, `verify`, then `decide`, always supplying the run/cache roots. `verify` recomputes saved-probability metrics and explicit pairwise AUROC; it does not independently replay all checkpoints. The end-to-end resume test checks inference equivalence separately. Independent scientific reproduction remains required.

`decide` applies paired, ancestry-cluster bootstrap to macro generator AUROC across the frozen conditions, with the same real pool reused coherently. It requires interior support and OOD evidence. Method configs are refused without a passing mechanism evidence file. The fixed top-half `selective_consistency` loss is only a tested building block, not a completed fallback experiment.

Final records are excluded by default. `freeze-final --review ...` requires completed fits and a recorded development review; it binds the manifest, config and checkpoints. Only then may `extract --role final_audit` and `evaluate --role final_audit` run. A review file is an accountable research handoff, not cryptographic proof of scientific validity.

## Validation and currently pending integrations

```bash
.venv/bin/python tests/test_runtime.py
.venv/bin/python tests/smoke.py /data/validation/fresh-unique-directory
```

The smoke experiment uses generated synthetic videos solely to check the software. It covers full-video H.264, sampling, extraction, training, prediction verification and bitwise epoch-resume equality. No synthetic test score is research evidence.

`forensics.backbones` contains explicit local-weight DINOv2 and RAFT-small adapters; these are not yet wired into the default Farneback experiment or validated on server hardware. `configs/baselines.json` records native reproduction status honestly. No public model is auto-downloaded or treated as reproduced because its URL exists.
