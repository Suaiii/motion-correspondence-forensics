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

## 2026-09-17 shared researchagent plan accepted; live SSH and canonical prototype

Read the actual root/role files, shared WORK_PLAN cvpr27-20260917-v1 and the
updated 25-task/11-milestone DAG. Main work now follows the matched-perturbation
local composability candidate; local-rank stays a diagnostic. Researchagent
does not edit the plan, task states or reminders. Written acknowledgement and
asset/accounting review are under `research-runs/shared_plan_20260917/`.

The latest user-provided SSH command authenticated. RTX 4090 D, retained
manifests and about 14 GiB free data space were checked live. The old access
block is resolved. Ran the old eight-frame actual-lag census on 28,868 records:
at 2 ms bins no adjacent-gap signature supports all five sources, while one
half-second pair supports 998 Vript, 83 HD-VG, 13,499 MS, 13,501 VC2 and 98
CogVideo. Continuous timing differences remain. This is partial input to RS03,
not validation of the new six-frame or joint-triplet protocol.

Implemented canonical NumPy/CUDA composability, the six-frame sampler and a
217,057-parameter response/semantic head. Eleven numerical tests and CUDA
reference replay pass; response discrepancies are below 1e-7. The head checks
verify frozen inputs, finite gradients, unordered triplet pooling, diagnostic
absolute JS and explicit semantic fallback. No real-data classifier was fitted.
GPU/software evidence and current source hashes are verified in
`shared_plan_20260917/composability_invariants.json`.

Two interpretation safeguards are now explicit. Anchor-only cropping cannot
remove wrapping through middle nodes, so the interior control conditions all
paths on a common non-wrapping middle support. Also, a six-identical-frame toy
sequence gives nonzero JS and perturbation response because soft P need not
obey P squared = P. Recommend a static/repeated-frame control before attributing
a future gain to temporal structure; the toy result does not reject the method.

Historical ledger inspection found eight unique reservations totaling 43.24
CNY/23 GPU hours, all still marked reserved. These are not actual payments or
remaining budget. Current provider rate and cumulative spending/hours remain
unverified against the shared 6000 CNY/180-hour ceiling. Larger stages and the
100-video end-to-end profile remain subject to the shared task gates.

The patch/global adapter was integrated with the existing pinned DINOv2
checkpoint on six static synthetic images. Shapes and the new head pass,
with zero backbone gradients/optimizer steps; runtime 3.96 s and peak tensor
allocation 0.366 GiB. Frozen DINO's static synthetic response is also nonzero
(mean absolute response 0.09492, mean JS 0.03408), reinforcing the need for a
repeated-frame control. This is not a real-video detection result or the
100-video profile. See shared-plan `backbone_integration.json`.

## 2026-09-17 cc-round-1: static control and existing-PTS feasibility

Executed DX01 within its CPU/read-existing-metadata scope. Added a static mode
using every original frame's (i,i,i) triple, with identical six-frame semantic
input and 217,057-parameter heads. Fresh matched models and equal-recipe guards
are separate from a fixed-eval-model branch replacement diagnostic. The latter
does not stand in for retraining the static strong baseline. All 21 CPU checks
pass, CUDA remained uninitialized, and no optimizer step was taken.

The comparison uses the same frame budget and head capacity but not identical
cached computation: temporal requires 11 affinity matrices, static 6; both
construct 78 composition products. Synthetic CPU timing is recorded, without
extrapolating to video/GPU performance. New static-source changes have CPU-only
evidence this round; earlier GPU reports remain tied to their older hashes.

Found complete original timestamps in the archived retiming diagnostic: 50 MS
and 50 VC2 before records, with complete decoded-frame hash counts and a matching
archived writer hash. Reused those arrays only. All 100 pass new six-frame
timestamp selection. Short triples have no joint support across these two
sources at 1/2/5 ms bins; long triples' four edges are all 0.5 s in both sources.
Between-triplet offsets and total six-frame spans still differ. Complete native
PTS for Vript/HD-VG/CogVideo were not found in the inspected caches; selected
8/16-frame PTS were not promoted to full sequences. No raw video read, new probe,
feature extraction, classifier fitting or old eight-frame census rerun occurred.

Supplier billing could not be inspected because the Chrome connector failed.
Actual spending, billed GPU-hours, current rates and remaining allowance stay
unknown; historical reserved amounts do not resolve RS00. Existing-instance
CPU/SSH work can still incur charges. The report includes required missing facts.

Added a preliminary primary-source neighbor map and conditional paper outline.
Contrastive random walks (NeurIPS 2020) are an additional close precedent for
patch-transition/path composition. No exhaustive novelty review or scientific
breakthrough is claimed. Deliverables: shared-plan static_control_preparation.md,
joint_lag_feasibility.json and collaboration_round_1.md. Formal gates unchanged.

Round-1 evidence and research source were pushed as 44a0c2b and remote HEAD
verified. With all package jobs terminal and no research/GPU process observed,
the provider shutdown command was executed under the earlier user instruction.
SSH disconnected and the TCP port was unreachable at 2026-09-17T12:07:50Z.
No arbitrary time cap or active-job interruption was involved. Billing status
is unverified; the overall innovation objective and formal gates are incomplete.

## 2026-09-18 cc-round-2: offline sampling proposals and pinned prior-art review

Continued cc-round-2-offline-20260917 under plan v1.1 after reading the research
role and shared dispatch. Delivered A/B/C sampling comparison, graph-derived
static readout weights, a disabled future PTS acquisition contract, and expanded
CRW/TimeCycle/RIFT plus five-neighbor formula/code/protocol review. No runtime
algorithm, WORK_PLAN, project task table or reminder state was edited.

Only two long triples still leave a source-dependent phase offset. Proposed one
centered .5+.5-second triple for review, retaining the 1.5-second eligibility
window initially. The proposed static weights [2,3,4,4,3,2]/18 address total role
exposure only; keep uniform-static and independent training if adopted. Neither
proposal replaces v1.1 or establishes real-source timing support.

Pinned seven public author repositories and verified 38 source/config files
(277,174 bytes). Downloaded text was never imported or executed. Found direct
CRW inheritance, RIFT paper/entrypoint split discrepancy and whole-batch NLL
scaling despite real-only intent, plus protocol distinctions in other neighbors.
These are static review findings, not reproduced detector performance. No source
leaderboard is presented as our result and no novelty clearance is claimed.

Offline arithmetic, permission fields and evidence hashes passed validation.
See research-runs/shared_plan_20260917/collaboration_round_2.md and
round2_validation.json for scope and artifact hashes. No SSH, server probe,
ffprobe, media read, feature extraction, training or new GPU job occurred.
The previous shutdown observation is historical; billing remains unverified.
DX02/RS01 are submitted for scoped review, without releasing formal gates.

## 2026-09-18 translation-null identifiability diagnostic

Using unchanged v1.1 NumPy formulas, established a restricted algebraic null:
when all frames are toroidal translations of one fixed patch-token field and
middle support is full, each temporal triple response equals its anchor-frame
static response. Three synthetic seeds verify map equality below 8e-16. Thus
the temporal pooled readout equals static pooling with anchor counts
[2,2,1,1,0,0]/6, not general total-role weights [2,3,4,4,3,2]/18.

A fixed random spatial encoder gives nonzero uniform/degree-weighted readout
differences even in this null. These are vector distances, not detector gains.
Arbitrary reindexing and fixed interior support break the commuting-permutation
condition; no general motion failure or DINO equivariance is claimed. Proposed
anchor-matched static as an additional diagnostic, not replacement for the
required all-frame static strong baseline. See translation_null_review.md and
translation_null_diagnostic.json under shared_plan_20260917.

Ran 6.69 seconds on local CPU only, no training, backbone, raw media or server
access. No protocol or planner state changed. Formal innovation remains unproven.

## 2026-09-18 original-PTS collector preparation

Implemented a stdlib server collector with metadata-only planning by default,
explicit adopted-contract/code/manifest bindings for execution, native integer
PTS preservation without best-effort substitution, original-file checks,
hash-verified resume and separate acquisition/resource failure receipts.
Fee/hour exposure continues from a fixed contract billing start; unknown actual
payments remain unknown. No startup, SSH, training or shutdown is built into it.

Sixteen mocked local tests pass (final run 0.341 s), including unauthorized
execution refusal, missing/duplicate/nonmonotone PTS, >2^53 precision, corrupted
resume artifacts, source changes, subprocess resource interruption and fast
over-cap output. No real ffprobe process or media was run. The future Linux
ffprobe integration still needs the authorized server pilot. Current PTS contract
remains disabled; WORK_PLAN/project and existing scientific gates are unchanged.
Details: shared_plan_20260917/native_pts_collector_preparation.md.

## 2026-09-18 DX03: explicit centered-three-frame candidate

Implemented cc-round-3-c-software-20260918 under plan v1.2. Candidate C samples
three unique native frames around the center at -.5/0/+.5 s; A's six-frame
sampler/default wrapper remain. Generalized NumPy/Torch responses and the head
to explicit candidate/group identities. C uses one temporal group, three static
groups and one anchor-only diagnostic group; all retain identical three-frame
semantics and 217,057-parameter heads, with separate parameter storage.

Added configuration, cache provenance, matched-recipe and compatible-checkpoint
interfaces. Unlabelled/other-candidate/other-control checkpoints and corrupted
parameter shapes/values are rejected before loading. Raw state_dict copying is
only used for fresh matched initialization, not scientific checkpoint reuse.

Final CPU validation passes 33 tests: old 21 A tests plus 12 C tests with boundary
subcases. No optimizer step or backbone executed; CUDA remained uninitialized.
Exact translated-feature null matches anchor-static maps at 4.44e-16 and matched
head logits within tolerance. Fixed interior/noncommuting cases break this
response equality and are separately recorded. These are software diagnostics,
not real DINO equivariance, detection performance or innovation acceptance.

Evidence and source hashes: shared_plan_20260917/candidate_c_cpu_validation.json;
scope/limitations: candidate_c_software_report.md and collaboration_round_3.md.
No server, ffprobe, media, GPU, model download or actual training this package.
Shared planner files and historical scientific receipts were not changed.

## 2026-09-18 DX04: one-pass C audit on existing original-time metadata

Executed cc-round-4-c-metadata-20260918 against the frozen original 50 MS/50 VC2
selection. Verified all record/protocol/writer/sampler/config/analysis-plan
digests before sampling, reconstructed the matching DX01 input-index digest,
and rechecked input bytes after analysis. C was called exactly 100 times;
all 100 were eligible and matched A positions 1/3/5 in indices and targets.

Both recorded gaps are .5 s, spans 1 s and center errors zero for both sources.
All predetermined 1/2/5 ms joint-gap and gap-plus-center views have one common
bin containing all 50 records from each source. Original durations still differ
(2.0 vs 1.6 s), as do absolute selection times and indices. No detection metric,
classifier, parameter change or source-exchangeability conclusion was produced.

The archived writer obtains best_effort_timestamp_time, not independently saved
native integer PTS. before.pts counts match complete decoded-frame hash counts;
that historical provenance is explicitly retained, with no fresh media/hash
verification and no after.pts analysis. Real-source original timestamps and
verified ancestry remain missing. This is retrospective exposed-development
metadata evidence, not real/fake support acceptance or a mechanism result.

Local CPU analysis took 0.121 s. No server, probe, media, backbone, GPU, training
or additional batch. Four requested artifacts are in shared_plan_20260917 with
candidate_c_existing_pts prefixes and collaboration_round_4.md; the new audit
script preserves old inputs and refuses to overwrite its outputs.

## 2026-09-19 round6: independent H-J review and H-T falsification

Executed cc-round-6-crossreview-ht-20260918 (AL03/AL02) after ordinary-model
recovery; did not repeat or modify planagent's AL01 primary implementation.
Independently assembled an equality/slack LP, proved the binary tetrahedron
average-L1 distance by a feasible projection/witness, and checked 45 continuous
or near-facet cases plus compatible/hard-cycle m=2/4/8 examples. The Gaussian
static-zero construction is integrable under its positive-temperature and
complete-support assumptions. Arbitrary consistent relabeling remains invisible.
Reported a helper input-validation defect: negative temperature is accepted;
the default positive-temperature theorem and old results are not thereby refuted.

H-T now has an executable observable-key binary-payload prototype and explicit
negative results. Full-index Markov maximum-entropy conditioning is tautological;
coarse symmetric binary-payload conditioning reduces to ordinary aligned third
moments. Equal pair histograms did not imply equal indexed Q observations.
An exact common-sign-flip example preserves all Q/C inputs but only changes a
coordinate-sensitive signed statistic; the invariant norm remains unchanged.
Complete-input static second moments, amplitude, time permutation and confidently
wrong correspondences explain or defeat the apparent toy gain.

Initial IPF reference failed to converge in a fixed stress case. Preserved its
source and failure; solved the same binary all-pair entropy problem on its exact
one-dimensional affine feasible family. Fourteen independent probability-table
checks against scalar optimization agree within 4.45e-16 entropy. No case or
temperature was selected based on outcomes. Main evidence and decisions are in
research-runs/algorithm_search_20260918, with a round6 artifact manifest/handoff.
No server, media, backbone, GPU, classifier fitting or formal innovation claim.

## 2026-09-19 AL27: multidimensional objective batch completed, gate failed

Original-coordinate 4D/12D synthetic convex reference frozen at dc78269 before
the only numerical batch. All three prescribed Gram panels and two boundary
types executed. 68/69 checks pass; full-rank free-head coordinate agreement
fails (3.158438133255004e-8 versus 1e-9), despite its gradient L2 meeting the
fixed 1e-10 stop and objective agreement near floating precision. No rerun,
extra Newton step or tolerance change. Execution done does not release a pass
dependency. Complete vectors/derivatives/solver calls, failure explanation and
handoff: research-runs/algorithm_search_20260918/AL27_report.md and AL27_evidence.json.
Only NumPy/stdlib, 2 native threads, 26 objective evaluations, 16 linear solves,
two scalar references. No real classifier/model/probe/readout/media/server/GPU.
All 92 protected historical files unchanged. No scientific or data gate passed.

## 2026-09-19 AL30: accuracy-budgeted stopping software reference

Frozen new batch at 1fa8bb8; only solver threshold changes by the uniform
mu/parameter-error-budget rule. Original objective module byte-identical;
three known regressions plus one prespecified delta=1/8 scale control pass
94 archived software checks. Full-rank regression naturally reaches step5
with coordinate difference5.3291e-15; original AL27 remains done/fail with
all source, inputs and failed evidence preserved. Gradient rounding bound
unknown/null, no rigorous parameter certificate or scientific efficacy claim.
One batch only:35 objective evaluations,21 solves,159 scalar derivative calls,
2 native threads, largest array1152B. Protected105 historical files and5
dependencies unchanged. No probe/readout/model/media/real training/server/GPU.
Evidence/report/handoff: research-runs/algorithm_search_20260918/AL30_*.
