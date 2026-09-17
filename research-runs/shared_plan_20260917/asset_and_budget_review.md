# RS00 asset, access and accounting review

Plan: cvpr27-20260917-v1. Owner: researchagent. Execution status: delivered for
planagent review. Suggested gate: access/assets verified; accounting remains
explicitly unresolved. This report does not change project.json.

## Live access and retained assets

The user-provided SSH endpoint authenticated successfully in this turn.
The live instance is Ubuntu 22.04 with RTX 4090 D (24 GB class), 16 CPU cores,
80 GB RAM and about 14 GiB free on the 50 GiB data mount. Observed at
2026-09-17T10:45:39Z and rechecked during the operator validation at
2026-09-17T10:55:48Z. The prior SSH-refused/unauthenticated-browser notes are
historical and no longer describe SSH access.

Existing server inputs were reused:

| Asset | Current evidence/use |
|---|---|
| Paired native/time DINO manifest | 28,672 retained development records; existing checksums validated by the timing census |
| HD-VG/CogVideo transfer cohort | 196 accepted development records, author-origin overlap excluded; original classifier scores not rerun |
| Time-grid feature records | Actual saved PTS read for the completed 28,868-record descriptive census |
| DINO/RAFT weights and raw videos | Retained on server; no new download to the PC or new model purchase |
| New shared-plan primitive | NumPy reference, CUDA operator and small response/semantic head; synthetic verification only |

No training, model selection, final-data access or new instance rental was
performed in this handoff. Small source archives and compact reports were
transferred; raw videos, checkpoints and feature arrays stay server-side.

## Accounting: known reservations are not actual spending

Three server ledgers were read: `incoming/budget.json`, `metadata/budget.json`
and `runs/budget_20260914.json`. After deduplicating reservation IDs there are
eight historical reservations, totaling 43.24 CNY and 23 GPU hours. Every entry
is still labelled `reserved`; some ledgers duplicate the same reservation.
Hashes and exact totals are in `budget_snapshot.json`.

These files are incomplete admission bookkeeping. They do not prove paid
consumption, instance uptime, storage bills or current rate. Their old 3000-CNY
caps and 1.88-CNY/hour quote references must not override the newly confirmed
6000-CNY / 180-GPU-hour cumulative limits or be treated as a fresh provider
quote. I did not reset these historical ledgers or manufacture a remaining
balance.

| Quantity | Verified status |
|---|---|
| User-approved cumulative ceiling | 6000 CNY; initial cumulative 180 GPU hours, from shared plan |
| Historical provider payments | Unknown |
| Historical paid GPU hours | Unknown |
| Current instance and storage rates | Not verified against the provider |
| Remaining allocatable budget | Not derivable from reservation totals alone |

The latest synthetic primitive/interface check took 3.71 seconds in its own
script. This is not the billed duration of the instance. The old timing-census
script did not save an end-to-end elapsed-time field; no runtime is invented.
Reconcile provider bills and actual cumulative usage before allocating a new
large training stage. Existing source archives, code and data are not recreated
merely to obtain a clean ledger.

## Next deliverable and restrictions

The new 1.5-second/six-frame protocol still needs raw-PTS and joint-triplet
support checks. The existing half-second result concerns one pair inside the
old eight-frame cache and cannot validate all six new triplets. Main-method
training, the 100-video end-to-end profile, accepted source quotas and formal
scientific review remain pending the respective task gates.
