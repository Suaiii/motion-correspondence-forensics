# Round 2 handoff: offline sampling and prior-art review

- dispatch_id: cc-round-2-offline-20260917
- task_ids: DX02, RS01
- plan_version: cvpr27-20260917-v1.1
- role: researchagent; prepared 2026-09-18, continuing the September 17 dispatch
- implementation baseline: 3707bf9b1ad3a904620302fee6bd41633fbf725b
- execution_status: bounded offline package completed; submitted for planner review
- suggested gate_scope: protocol_proposal_only_not_adopted / bounded_literature_review
- scientific_gate_result: not_evaluated; no breakthrough or CCF-A readiness claim

## Decisions proposed, not enacted

1. Keep A (six frames/six triples) as the current v1.1 protocol. B (same six frames,
   only two long triples) does not remove the observed inter-group phase difference.
   Prioritize review of C, one centered triple with .5+.5-second target gaps, as
   the smallest next mechanism diagnostic. C algebraically coincides with A's
   indices 1,3,5 under identical duration/selection rules; this is not measured
   real-source support. Retain initial 1.5-second eligibility and the existing
   nearest-frame error bound to avoid simultaneously changing short-video admission.
2. Retain uniform-static. Propose a secondary static readout weighted by the fixed
   graph degrees [2,3,4,4,3,2]/18, applied after spatial encoding/pooling. It matches
   normalized total frame-role exposure, not individual roles or nonlinear information.
   It must be independently trained if adopted. B/C degree weights become uniform.
3. Future raw-PTS acquisition has an explicit contract with execution_authorized=false.
   Initial proposal: five existing original videos per real source, ten total,
   sorted by frozen identity before timing outcomes; two CPU workers. A possible
   expansion to 100 requires review. Proposed 5 CNY is NOT approved spending.
   No server activation or probing happened in this package.

## Prior-art findings that change interpretation

CRW Eq. (1)/(2) directly cover the soft transition and matrix-product foundation;
Eq. (4) and Appendix C/D establish cycle training and static/position controls.
TimeCycle learns a localization/sampling operator with grid-cycle loss, not our
frozen-feature JS readout. Neither matrix multiplication nor cycle consistency nor
static controls should be promoted to standalone innovation.

RIFT's inspected public entrypoint splits cached files 80/20, unlike the paper's
50/50 stratified protocol with an inner validation set. Its conditional auxiliary
loss scales whole-batch NLL by real fraction instead of masking fake samples.
These are code-level findings, not executed reproductions or proof of an effect
on the paper's results. Declare the protocol and any corrected variant separately.
The checkpoint README describes a future release, so expected names do not certify
available weights. MAST itself discusses an FPS shortcut. WaveRep is a substantive
augmentation alternative. G2VD/STALL/VidAudit require native-versus-adapted protocol
distinctions; their published scores are not copied as matched project results.

## Deliverables and verification

- [Sampling proposal](../../research-plan/SAMPLING_REVISION_PROPOSAL_20260917.md)
- [Static fairness proposal](../../research-plan/STATIC_CONTROL_FAIRNESS_20260917.md)
- [PTS resource contract](pts_acquisition_contract_draft.json)
- [Formula/code/split review](../../research-plan/LOCAL_COMPOSABILITY_PRIOR_ART.md)
- [Pinned source receipts](round2_author_sources.json) and [file selection](round2_source_selection.json)
- [Validation receipt and artifact SHA256 values](round2_validation.json)
- [Read-only source collector](../../research-runtime/review_author_sources.py)
- [Offline validation program](../../research-runtime/verify_round2_proposals.py)

Validation passed: exact rational graph weights, role counts, A/B/C affinity and
composition counts, centered-target algebra, disabled contract execution, old PTS
evidence identity, and all 38 selected public file Git-blob/SHA256 digests.
The seven pinned repositories are preserved in metadata; third-party source snapshots
remain in the ignored temporary cache and are not published. This is a mechanical
evidence check, not independent scientific review, detector testing or a PTS probe.

No classifier fitted, no features extracted, no original video read, no final set
opened. No current runtime algorithm or v1.1 protocol was changed. Research outputs
are staged explicitly; concurrent planner-owned files are excluded from this commit.

## Resources and remaining dependencies

The inspected public source text totals 277,174 bytes; the repository inventory is
about 252 KB. Local additions are compact code/metadata/reports only. No weights,
videos or datasets downloaded, no new GPU job or third-party program executed.
This work used local CPU and public HTTP/Git access; provider spending was not measured.
Actual paid CNY, billed hours, current rate and remaining budget remain unknown;
43.24 CNY/23 hours of historical reservations cannot resolve those values.

Server state has not been refreshed in this offline package. The last observation
remains the prior shutdown receipt at 2026-09-17T12:07:50Z (SSH closed, TCP unreachable).
This is a historical observation, not a fresh provider status or billing confirmation.
No repeat billing access attempt and no repeated user usage question occurred.

Planner review may accept DX02 only as a proposal deliverable, without adopting B/C
or clearing RS03. RS01 now provides concrete overlap/code/split evidence for the
specified neighbors; MAST author code, exact G2VD paper split manifests, checkpoint
identities and actual replications remain unresolved. Request bounded literature
acceptance separately from reproduction. Scientific interpretation needs a reviewer
other than this implementer. RS00/RS02/RS03 and all formal experiment gates stay intact.

Next actionable decision: review C and static weights, then version any adopted
protocol and its comparison family. Only after resource allowance and source
manifest review may the separate PTS acquisition contract be activated. Sampling
metadata from ten or one hundred videos cannot itself authorize formal training.
