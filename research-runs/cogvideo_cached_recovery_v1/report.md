# CogVideo cached-member recovery

100/100 selected members were recovered locally using Windows bsdtar/libarchive,
with no network transfer, GPU computation or server restart. Total recovered
video bytes: 27,655,068. Acquisition plus decoded-PTS QC took 28.812 seconds.

All 100 mini archives match the frozen RAR5 headers. Unpacked length and CRC32
match the index; SHA256 was recomputed for every video. All hashes are unique,
and none matches the configured historical exact-byte exclusions. The 100
member names and fake labels also match the pinned author Pair2 label file.

The existing server decoder successfully produced eight frames at 4 fps and
16 frames at 8 fps from each video, using a two-second window and 224-pixel
spatial preprocessing. Selected indices are unique and PTS are increasing.
This establishes decoding eligibility, not detection performance.

## Corrections and limits

- The earlier claim that Windows cannot recover these members without UnRAR
  was incorrect. Windows tar.exe is bsdtar with RAR5 support on this machine.
- Original failed acquisitions and partial outputs remain untouched.
- Full archive SHA256 has not been verified; member integrity is verified.
- `task: T2V` is inherited from the earlier selection, **not verified** by this
  recovery. A separate upstream task-type check is still required. Do not use
  the inherited field to admit a T2V training cohort.
- Ancestor/reference/prompt relations and licence acceptance remain unresolved.
  The author labels alone do not resolve them.
- These are the original first 100 selected members, not a random or
  representative full-benchmark sample. No replacement or score selection was
  performed.
- No model was trained or evaluated; this is not an algorithmic contribution.

## Replay

Run `research-runtime/enter.ps1 -Script research-runtime/recover_cogvideo_cached.py
--output <fresh-run-directory>` with the original cached mini archives and
the frozen index/selection. Then run `verify_cogvideo_recovery.py <run-directory>`
through the same runtime. The latter recomputes all artifact digests, raw CRCs,
author-label joins and recorded sampling invariants. It is mechanical
verification by the implementer, not independent scientific reproduction.

Raw videos, RAR members and local-only archives remain outside Git. The index,
selection, recovery code, per-member receipts and verification are versioned.

Next decision: audit CogVideo task provenance and source relationships, then
combine accepted sources under a grouped development protocol. Server power
is not a prerequisite for this acquisition anymore. Respect the user's latest
shutdown request until a concrete paid experiment is ready to launch.
