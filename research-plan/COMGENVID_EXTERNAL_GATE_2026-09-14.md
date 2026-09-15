# ComGenVid external-source route

> 2026-09-14 update: local videos and 150 feature records now exist. These exposed videos are external-development data, not an unopened confirmation set. The replay uses the legacy 4-fps/8-frame/128-pixel pipeline; the 8-fps protocol below remains prospective. See [phase-2 audit](../research-runs/phase2_evidence_audit_20260914/report.md) for paired baselines, known-parent bootstrap and unresolved licence/ancestry/precision checks.

The official STALL repository documents ComGenVid as a balanced benchmark with
1700 real MSVD clips, 1700 Sora clips, and 1700 VEO3 clips. The Hugging Face
dataset provides per-video metadata and pre-computed DINOv3 embeddings. This is
the best current route to an independent fake-labeled source without renting a
GPU server.

Important boundary: pre-computed DINOv3 embeddings cannot be fed directly into
our frozen Farneback correspondence pipeline. The video files (or a compatible
frame-level representation) must be acquired and audited before claiming an
external AUROC. Metadata-only scoring is prohibited.

Primary references:

- https://github.com/OmerBenHayun/STALL
- https://huggingface.co/datasets/OmerXYZ/comgenvid

Acceptance plan: acquire a balanced, licence-documented subset; verify native
timestamps and fixed 2-second/8-fps sampling; exclude overlap with all existing
real-source IDs; generate float32 correct/fractional features; run the frozen
fusion head and parameter-matched controls; report source-stratified AUROC and
confidence intervals.
