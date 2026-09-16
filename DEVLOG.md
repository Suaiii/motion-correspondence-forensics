# Research handoff

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
