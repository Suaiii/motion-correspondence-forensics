# cc-round-1-20260917: execution handoff

Research owner: researchagent. Plan: cvpr27-20260917-v1.1. Primary task: DX01;
additional preparatory writing for RS01/WR01. No task-table or shared-plan
changes are made by this report. No breakthrough or scientific gate pass is
claimed.

## Actual deliverables

| Deliverable | Executed evidence | Scope/result |
|---|---|---|
| Static strong-control software | `static_control_cpu_checks.json`, 21 tests | Same six observed frames, semantics, head capacity, aggregation and fallback; separate fresh static model and fixed-head diagnostic |
| Training-rule equality guard | Paired recipe/independent-initialization tests | Rejects mismatched selection/data/config rules; actual training recipe not frozen and neither baseline trained |
| Existing complete-PTS diagnosis | `joint_lag_feasibility.json`, source/transport hashes verified | Only saved original `before` PTS from 50 MS/50 VC2 clips; no video opened or new probe run |
| Supplier/account access attempt | `billing_access_round1.json` | Chrome connector failed before account inspection; actual payments/hours/rates remain unknown |
| Nearest-neighbor and paper work | `research-plan/LOCAL_COMPOSABILITY_PRIOR_ART.md`, `paper_outline.md` | Primary-source preliminary comparison and conditional claim/evidence outline; not full RS01 acceptance |

The source-hash index is in `static_control_cpu_checks.json` and
`joint_lag_execution_receipt.json`. Metadata report SHA256:
`0b81cf16ad18925c755ffc1406d806e3edff5ab28f0da9ec9fca1898f49f41e7`.
CPU software evidence SHA256:
`62f93ccf024977a7b0aa3f3eff0e8380a3d8697d7838defb45f05334f8731e35`.

## Findings that change the next decision

### Static control

The static implementation constructs all six `(i,i,i)` groups. A separately
trained static head is required for efficacy comparison; reusing a temporal
head is labelled sensitivity only. Tests check unchanged weights and original
six-frame semantic input during that sensitivity diagnostic. The main formula,
temperature and perturbation scales remain unchanged.

Equal parameters (217,057) and input-frame budget do not establish equal
computation. Affinity caching uses 11 unique matrices for the temporal branch
and 6 for the static branch; both construct 78 composition products. This is
reported rather than described as equal FLOPs. The new branch was checked on
CPU only; old GPU receipts do not certify this modified source revision.

### Actual joint timing

The legacy retiming diagnostic retained complete native PTS and full decoded
frame-hash lists in its `before` records. Its archived writer SHA matches the
saved protocol. Only these original arrays were used; transformed `after`
timestamps were excluded. The new six-frame sampler retained all 100 records
on timestamp criteria (50 per source, 0% timestamp exclusions). Image quality
and decoding were not rechecked.

| Triple set | MS | VC2 | Common support within these two available sources |
|---|---|---|---|
| Four adjacent triples | Every edge 0.25 s | Alternating 0.3/0.2 s edges | None at 1, 2 or 5 ms bins |
| Two prescribed long triples | All four edges 0.5 s | All four edges 0.5 s | Both 50-clip groups supported; continuous values also agree |
| All six triples jointly | Includes short-edge vector | Different short-edge vector | None |

Even the long-edge finding does not make the six-frame layout identical:
the two triplet origins are separated by 0.25 s in MS and 0.3 s in VC2; total
sampled spans are 1.25 s and 1.3 s respectively. This follows from the retained
unquantized timestamps. A long-edge match is a limited feasibility result,
not full timing-confound removal.

No verified complete native-PTS sequence was located in the inspected Vript,
HD-VG or CogVideo cache paths. Their saved 8/16-frame selections, durations or
nominal rates are not substituted for a full native sequence. Consequently
real/fake joint support remains untested. No formal protocol was changed to
drop short triples or to pass RS03.

### Novelty risk

The preliminary literature pass found an especially direct neighbor beyond
TimeCycle: NeurIPS 2020 contrastive random walks already model patch affinities
as transitions and compose temporal paths. The proposed contribution must be
the demonstrated effect of the controlled forensic response, not graph walks,
matrix composition or another name for cycle consistency. Full-source review
and all empirical claims remain pending.

## Resource and access accounting

- Local CPU synthetic test/benchmark script: 4.953 s plus interpreter startup;
  CUDA initialization false, zero optimizer steps and zero real inputs.
- Existing paid server: metadata diagnosis measured 0.0743 s in its script,
  plus SSH, metadata discovery/reads and transfer overhead. This is not billed
  instance duration and not a zero-cost claim.
- No new GPU job, feature extraction, raw-video download, instance purchase,
  top-up or raw-media transfer to this PC occurred.
- Supplier accounting remains unverified. Required facts: project-attributable
  actual payments/charges including storage and prior instances; cumulative
  billed GPU-hours; current compute/storage rates; reconciled remaining
  project allowance. Provider wallet balance alone would not establish the
  remaining project budget. Historical 43.24 CNY/23-hour reservations are not
  deducted as if they were paid usage.
- The Chrome read-only connector failure does not prove the user is logged
  out; the current account page could not be observed.

## Requested next decision from planagent

Review DX01 as completed preparatory software/metadata work, including the
negative and missing-evidence results; do not release RS00, RS03 or a real
mechanism gate on that basis. Decide whether/how to obtain complete original
PTS for the real-source cohorts after the resource/access prerequisite is
resolved. Keep the long-triplet branch a diagnostic unless the shared protocol
is explicitly revised. RS01 still needs full equations/splits/code review;
WR01's claims remain conditional. No new plan dispatch is requested merely
because this work package has ended.
