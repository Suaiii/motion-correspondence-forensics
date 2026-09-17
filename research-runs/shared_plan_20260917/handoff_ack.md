# researchagent acknowledgement

Plan version: **cvpr27-20260917-v1**. Research task: 科研冲击
(`01a09db1-3c10-7710-b866-130d4cc44d9e`). Planning task: Plan9.16
(`01a0aea6-38cb-77e1-8f1f-aba2a8dce36b`).

## 1. Files actually read

Read the root `AGENTS.md`, both role files, the complete `WORK_PLAN.md`, the
updated `project.json` (25 tasks, 11 milestones), latest DEVLOG and relevant
experimental reports. The canonical plan is now `WORK_PLAN.md`; historical
9/14 and local-rank plans do not supersede it. Plan/role versions agree.
Observed WORK_PLAN SHA256: `25ccf8777e288015c146d43dd542c7b8d1c043b29e9f8271dd088d08975b8d48`.
Research role SHA256: `06441a457727feea79ecb4474f715bb64af1abf9c50bf69c7c3f476f6374fb3a`.

## 2. Current work and new task IDs

- **RS00:** access and asset reconciliation in progress. User-provided SSH
  credentials now work. Live RTX 4090 D and retained server manifests were
  checked. Billing reconciliation is incomplete; no assumption of zero prior
  spending or a verified current hourly rate.
- **RS03, partial input:** the existing eight-frame timing census has now
  actually run on 28,868 records. This is the old protocol, not the new
  six-frame/triplet acceptance. At 2 ms bins, adjacent intervals have no common
  support across all five sources. A single half-second pair supports 998
  Vript, 83 HD-VG, 13,499 MS, 13,501 VC2 and 98 CogVideo clips. Continuous
  within-bin differences remain, and are explicitly recorded.
- **RS04, prototype preparation:** implemented canonical soft patch matching,
  direct/two-step JS, twelve one-sided index perturbations and three response
  scales. The candidate head reads response maps and global semantics; local
  rank remains a separate diagnostic. No real-data detector is trained.
- **RS05, partial software evidence:** eleven NumPy invariants pass. A CUDA
  operator replay against NumPy also passed; the classifier-interface and
  frozen-input gradient checks are being finalized as part of work already
  underway before this coordination message.

These are delivered/prepared assets, not unilateral changes to task states or
requires_pass gates. Please retain formal task acceptance with planagent.

## 3. Inputs and evidence already available

- Existing server data and DINO weights/caches remain under
  `/root/autodl-tmp/cvpr27`; no large media copied locally.
- Old paired cache: 28,672 successful clips; external development: 196 clips
  after author-origin overlap exclusion and successful slow-video retry.
- `research-runs/pair2_frozen_transfer_v2_evidence.json` records the frozen
  model transfer and timing controls. Its 0.93367 timing-only result is not
  a new-method effect.
- New census: `research-runs/actual_lag_support_v1_report.json`, transferred
  from server with matching SHA256
  `b50e090b7bf7efc9d5bc10e9ff9c593f9dc2b0e4da0fe94d64cf2aae27113c2a`.
- Canonical prototype sources are under `research-runtime/server/forensics/`:
  `composability.py`, `composability_torch.py`, `local_composability.py`, and
  `mechanism_sampling.py`. The latter implements 1.5 s / 4 Hz / 6 native frames
  and retains all six prescribed joint triplet interval vectors.

## 4. Remaining dependencies

- Actual cumulative cost, paid GPU hours and current provider pricing still
  need reconciliation against the 6000 CNY / 180 GPU-hour cumulative limits.
- The 196-clip second-source cohort is exposed, non-random development data,
  with author-metadata ancestry rather than independent content confirmation.
  Two accepted real families/four generators and the 2000-clip mechanism
  manifest have not been accepted.
- New six-frame joint timing support, metadata probes and per-source retention
  must be measured; the previous two-frame result cannot release that gate.
- Real-video decoding/caching integration and the 100-video end-to-end profile
  remain pending. Synthetic CUDA/backbone checks do not substitute for them.
- Formal method effect, propagation robustness and independent scientific
  review remain unestablished.

## 5. Next concrete delivery

Finish and transfer the software/GPU interface evidence to
`research-runs/shared_plan_20260917/composability_invariants.json`, with source
hashes and explicit limits. Then provide an asset/budget review and a sampler
handoff for the new six-frame joint-support census, subject to the updated
task dependencies. Do not repeat the 196-clip old classifier evaluation.

## 6. Plan/interface issues

- The DAG briefly still pointed to 9/14 while the role files were being
  written; a subsequent read confirms the new version and all 25 tasks.
- RS04's requested `local_composability.py` interface now exists. Numerical
  reference and GPU kernels are separate files rather than duplicated models.
- A crop of anchor rows alone cannot remove cyclic wrapping through middle
  nodes. The fixed-interior control restricts the middle-node support for all
  compared operators and records retained probability mass. This strengthens
  the intended boundary control without changing the main circular-permutation
  candidate.
- SSH access is now restored. Last live hardware/process check at
  2026-09-17T10:45:39Z showed no research training process; subsequent work is
  only a small already-authorized synthetic CUDA/software check. No purchase,
  restart or new training was initiated by this coordination message.
- I will not modify WORK_PLAN.md, project.json or reminder configuration.
  Research code, evidence and DEVLOG remain my responsibility. Please keep
  these current research edits out of the coordination commit to avoid
  capturing unfinished code.

Scientific status: **not evaluated / no new algorithm efficacy claim**.

## Completed evidence added after the initial acknowledgement

The final response/semantic head interface check now passes on CUDA. The
default head has 217,057 parameters; frozen-input, gradient, triplet-order,
absolute-JS isolation and semantic-fallback checks are recorded in
`composability_invariants.json`. Its source hashes match the current code.
`asset_and_budget_review.md` and `budget_snapshot.json` now document actual
ledger inspection: eight deduplicated historical reservations totaling
43.24 CNY/23 GPU hours, with all actual-payment/remaining-budget fields unknown.

An additional repeated-frame toy counterexample demonstrates that soft
composition and perturbation responses can be nonzero without temporal change.
`composability_report.md` recommends a static/repeated-frame control; it does
not modify the shared plan or assert real-video mechanism failure. These
deliveries are submitted for planagent review, without editing task states.

Frozen DINO integration has also passed on six synthetic images, using the
existing checkpoint and pinned model revision. Patch/global interfaces and
the 217,057-parameter head run together with zero optimizer steps. Evidence:
`backbone_integration.json`. Actual video decoding, new joint-PTS acceptance,
100-video profiling and efficacy remain pending. This does not start a new
training task or release the later mechanism gate.
