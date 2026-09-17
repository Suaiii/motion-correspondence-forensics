# Research handoff

## 2026-09-17 physical-time decision

The full cached DINO comparison completed with 28,672 successful time-grid
records out of 28,674. Native delta AUROC was 0.9183/0.8992 on the two held
generator audits; physical-time delta was 0.8445/0.8628, with semantic-only
time-grid scores 0.8441/0.8556. Retain time-delta as a mechanism candidate,
reject native-frame delta as a standalone claim. Formal release still needs
two accepted real families, four generators including CogVideo, timing and
estimator controls, five seeds, and a fresh group-disjoint cohort. See
`research-plan/TIME_MATCHED_DECISION_2026-09-17.md`.

## Full-cache experiment completed on server

`cached_dino_baseline_v1` used all 28,674 retained DINO-feature records and
completed 18 LR fits (six arms across two generator holdouts). New code and
compact results live under the corresponding server scripts / research-runs
directory. Full predictions and features remain server-side.
Frame-delta features improve held-generator AUROC by +0.08251 (ModelScope)
and +0.04974 (VideoCrafter2), but the timing-only negative control scores 1.0
on both. This prevents a forensic mechanism claim. See the run's report.
Next action: matched physical-time sampling with fixed frame count, then
repeat the same group allocation and timing probe. All 28,727 originally
cached raw videos are still present server-side; do not redownload them.
Do not call this a passed formal gate or an innovative algorithm. This
completed server CPU experiment reused GPU features; it did not train a GPU
backbone. Source independence and rights qualification remain separately open.

## Latest provenance checkpoint

## Paired physical-time baseline checkpoint

The server completed 28,674 matched-time DINO extractions (28,672 successful,
2 excluded) and the paired baseline before the requested shutdown. Observed
AUROCs: ModelScope native semantic 0.8397, native delta 0.9183, time-grid
semantic 0.8441, time-grid delta 0.8445; VideoCrafter2 native semantic 0.8478,
native delta 0.8992, time-grid semantic 0.8556, time-grid delta 0.8628.
This is an exposed one-real-source diagnostic. The timing-only confound was
identified at AUROC 1.0 in the preceding run; the time-grid delta remains a
candidate but not a method claim. Compact JSON was not retrieved before the
server shutdown; preserve the server path and the local report
`research-runs/paired_dino_time_v1_report.md`.

See `research-plan/PROVENANCE_DECISION_2026-09-16.md` and
`research-runs/source_lineage_correction_v1.json`.
The server audit rehashed 263 files: videoOSN maps back to Vript/Sora by the
original source metadata; corrected candidate counts are 90 Vript real,
80 OpenSora, 80 T2VZ and 13 Sora, with seven shared ancestor candidate groups.
Do not count videoOSN as an independent real source or generator.
The author paper supports CogVideo T2V identity and shared HD-VG ancestry;
sample-level ancestor mapping remains open. Official GenVidBench declares
CC BY-NC 4.0, with upstream rights qualifications recorded in the decision.
Server DINOv2 ViT-B weights and early feature caches were found live and can be
reused after their configuration/hash audit; do not redownload them blindly.
No training was launched by this provenance audit.

## Current storage policy and transfer

User requested server-first processing because local disk is limited. Downloads,
extraction, feature caches and training belong on the server; local storage is
for code and necessary compact evidence. The instance was rechecked live and
was online (RTX 4090 D, 0% utilization, 1 MiB allocated, ~16 GB data space free).
CogVideo recovery data now reside at
`/root/autodl-tmp/cvpr27/data/cogvideo_cached_recovery_v1`.
All 202 manifest-listed artifacts were rehashed there; all 100 video copies
were subsequently rehashed and removed locally, reclaiming 27,655,068 bytes.
See the run's `server_transfer.json`. No training was launched in this transfer.
The shutdown note below is historical; it must not be treated as current power
state. Use live evidence for future server status.

## CogVideo recovery checkpoint (2026-09-16)

- Actual result: 100 frozen CogVideo members recovered from existing local
  RAR5 caches; all member CRC/size/SHA checks pass, all 4/8 fps decoded-PTS
  checks pass. No server restart, network download or GPU run in this step.
- Evidence: `research-runs/cogvideo_cached_recovery_v1/{summary,verification}.json`
  and per-member `records/`; procedure and limitations in that run's report.
- Next owner/action: data provenance audit for task type, licence and ancestor
  mapping. Binary author labels do not prove the inherited `T2V` field.
- Full training and an independently demonstrated method contribution remain
  incomplete. No patentability or CCF-A readiness claim is established.
- Server: last shutdown was user-requested; not queried or restarted in this
  checkpoint. Do not infer billing status from local completion.

## Interpretation corrections for subsequent work

- An unchanged hash is a byte-identity check, not proof of unseen ancestry.
- videoOSN is a transformation collection; its folder names do not establish
  an independent real acquisition source or a new generator.
- Repo-to-space CC0 metadata does not itself prove camera-captured real labels
  or per-file upstream rights. Prior `verified` labels need source evidence.
- The ResponseBag pilot's code evaluates the last epoch despite the stored
  protocol saying minimum calibration BCE. Its saved numbers are exploratory
  final-epoch results; they cannot validate that claimed selection procedure.
- GPU idleness does not imply absence of instance or storage billing.

## 2026-09-17 live resume: timing replay and GPU consistency candidate

The user booted the instance; SSH, RTX 4090 D and the existing server caches
were verified live. No videos, weights or feature arrays were downloaded to
the local machine. The earlier "compact JSON not retrieved" note is historical:
those files have been retrieved and the interpretation is corrected below.

`verify_paired_time.py` validated artifact hashes, reconstructed all six frozen
heads' inputs and replayed both audit cohorts for both held generators. Main
models were not refitted. Time-delta gains over semantic LR are +0.000425
(95% paired ancestor-proxy CI [-0.011488, 0.011573]) and +0.007175
([-0.004446, 0.018758]); no incremental temporal effect has passed. Actual
time-grid median-interval probes still reach 0.78395/1.0 AUROC. Withdraw the
earlier claim that a genuine temporal signal was confirmed by time matching.

Developed and executed `sampling_consistency_pilot.py`: six equal-parameter
MLP arms, five seeds, two generator holdouts, full 40-epoch schedules with
minimum calibration BCE selection, no walltime cap. All 60 fits finished in
131.81 seconds including loading and bootstrap. The paired-consistency
candidate loses to ordinary two-view ERM on ModelScope in all five seeds,
while improving VideoCrafter2. Shuffled pairing matches or exceeds its
ensemble performance. Reject the candidate under its predeclared criterion;
do not present the improved MLP baseline as algorithm novelty.

`verify_sampling_consistency.py` independently reconstructed audit features
and replayed all 60 saved checkpoints without training. Hashes, metrics,
checkpoint epoch selection and parameter counts passed. Large artifacts stay
on the server. See the compact paired-time and sampling-consistency reports
under `research-runs/` and the frozen pilot plan under `research-plan/`.
These are development diagnostics; the overall innovation goal is incomplete.

## 2026-09-17 second-source access and frozen external transfer

Implemented streaming recovery for the nested HD-VG 7z/RAR release. Read
552 MiB of pinned compressed prefix and recovered 100 original videos
(579,425,559 bytes), checking RAR header CRC, member CRC/size and SHA256.
The first attempt stopped at the 128 MiB per-member guard; v2 safely permits
512 MiB per member, reuses hash-verified range chunks and completes all 100.
The whole 80 GB archive was not fetched or hashed. All media remain on server.
The user's local Clash proxy was forwarded only to server loopback to bypass
a direct network timeout; this was a transport fix, not a local media download.

Fetched pinned author metadata and verified its Git blob against the release
catalog. All 100 HD-VG origin IDs and 100 CogVideo prompts join to author
indices. Excluding two origins shared with Pair1 removes four candidates;
one additional real video hits the 60-second ffprobe deadline (an operational
timeout, not established video-quality failure). The initial transfer cohort has 195 clips,
100 origin groups and 95 groups spanning both real/generated labels.

Evaluated all 60 old checkpoints without refitting or recalibration. Ordinary
two-view ERM ensemble AUROC is 0.86324/0.91058 for models trained with
VideoCrafter2/ModelScope fake videos respectively. Paired consistency remains
unpreferred relative to shuffled pairing. Frozen interval-only controls reach
0.93299, so high neural scores still do not establish a forensic mechanism.
Replayed all 60 external predictions and verified raw/features/checkpoint
hashes. Details: `research-runs/pair2_frozen_transfer_v1_report.md`.

The GPU extraction path now prefetches with 12 decode workers and batches of
32 videos. This small run completed in 92.51 seconds with 2.10 GiB peak GPU
allocation; no claim of sustained high utilization or provider cost is made.
The second-source access issue is reduced, but formal source acceptance and
the algorithm-innovation goal remain incomplete. No final set was opened.

The timed-out HD-VG sample is a 497-second 1080p video. A separate v2 pass
removed the operational probe deadline, reused the 195 successful feature
records, and recovered the clip with unchanged sampling. The complete
98-real/98-generated cohort passes extraction, with 100 origin groups and
96 containing both labels. Ordinary two-view ERM ensemble AUROC becomes
0.86172/0.90848; the candidate rejection remains unchanged. The v2 process
took 111.21 additional seconds. Preserve both versions; the first exclusion
was an operational timeout, not evidence of bad video quality.

The complete-cohort verifier passed all 60 frozen-head replays and artifact
hash checks. Timing-only transfer AUROC is 0.93367 in both configurations.
Compact evidence is retrieved locally; the 196 videos/features and detailed
predictions remain server-side. The temporary loopback proxy tunnel is closed.

## 2026-09-17 continued goal: actual-lag support and local-response reference

The previous goal turn made concrete progress, but the innovation objective
remains unmet. A completed batch is not completion of the full objective.
The instance was shut down after that batch. This continuation verified SSH
unreachable and used the browser to reach the AutoDL console, which redirected
to an unauthenticated login form. The user was asked to boot the original
instance or sign in. No cloud power-on operation succeeded or was claimed.

Continued code preparation without local media downloads or local GPU work:

- `lag_support.py` and `audit_actual_lag_support.py` measure source/class
  overlap in actual timestamp intervals, including a prespecified 0.5-second
  pair available inside the existing cache. They retain continuous within-bin
  timing differences rather than treating quantization as removal of cues.
- `rank_response.py` retains local operator-response maps and cell histograms.
  It exposes a fractional-flow counterexample: equal interpolation weights
  and equal integer displacement lengths do not imply equal full lengths.
  An integer-only mode matches the applied lengths exactly while explicitly
  recording quantization error and neutral uninformative motion.
- Six actual-lag tests and ten rank-response tests check analytic translated
  scenes, interpolation, support, ties, common monotone error transforms,
  quantization, and the motion-length counterexample. No classifier is trained.

The next-step plan records rank/census and DINO-trajectory prior art. These
components are unvalidated research primitives, not a novel detector result.
Real-data support census and any mechanism evaluation remain pending server
access. See `research-plan/ACTUAL_LAG_AND_LOCAL_RANK_2026-09-17.md`.
