# Research handoff

## Latest provenance checkpoint

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
