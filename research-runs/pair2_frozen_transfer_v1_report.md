# Pair2 prefix transfer: second real-source candidates now available

## Acquisition and provenance

An incremental LZMA2 reader recovered the first 100 non-solid RAR5 MP4 members
from 578,813,952 compressed bytes (552 MiB), without storing the 80 GB nested
archive. Raw output totals 579,425,559 bytes. Original RAR headers, per-file
CRC/size and SHA256 were checked; the whole archive was not hashed. The initial
128 MiB member guard rejected the second file. The completed v2 run raised the
bounded member allowance to 512 MiB, reused range chunks and finished in
216.97 seconds. Both attempts are preserved server-side. No walltime cutoff
was set. All videos and compressed ranges remain on the server; no raw media
was copied locally or published to GitHub.

The pinned `HDVG_14k_classes.txt` has Git blob SHA1
`9ebfc67dbe27d2827a0b8cf37029e4a66708736c`, matching the frozen release catalog.
Its author index joins 100/100 HD-VG filenames to source-video IDs and
100/100 CogVideo filenames to normalized prompt text. This is an explicit
author-metadata join, not independent proof of camera capture or ancestry.

Source IDs shared with the full Pair1 Vript list excluded two real and two
generated candidates. One remaining real video hit a 60-second ffprobe timeout
in this initial pass; it was not established to be a low-quality video. The retained
external-development set has 97 HD-VG and 98 CogVideo clips, 100 source-ID
groups, including 95 containing both labels. Bootstrap draws preserve whole
groups jointly across real/generated labels.

HD-VG's [official repository](https://github.com/daooshee/HD-VG-130M) declares
academic-only use and restrictions on redistribution. The
[GenVidBench project](https://genvidbench.github.io/) declares CC BY-NC 4.0
and records upstream copyright qualifications. These pages were checked on
2026-09-17. Recording those terms does not assert cleared commercial rights
or release the formal training gate.

## Frozen model transfer

No head was fitted, recalibrated or selected using this cohort. All six arms,
five seeds and both old training configurations were evaluated. DINO weights,
decoder hash, crop, normalization and time grid match the old cache. Extraction
used 12 decode workers with prefetch and batches of 32 videos. The entire
extraction/evaluation/bootstrap run completed in 92.51 s; measured DINO CUDA
forward time was 1.22 s and peak allocated GPU memory 2.10 GiB.

The table shows five-model probability-ensemble AUROC. The saved configuration
called `ms` held out ModelScope and trained on VideoCrafter2; `vc2` trained on
ModelScope. Both used Vript real videos. Every row evaluates the same new
HD-VG/CogVideo cohort.

| Arm | Train fake: VideoCrafter2 | Train fake: ModelScope |
|---|---:|---:|
| Semantic mean | 0.78151 | 0.89017 |
| Mean + unordered standard deviation | 0.82622 | 0.86556 |
| Mean + temporal delta | 0.84736 | 0.89796 |
| Ordinary two-view ERM | 0.86324 | 0.91058 |
| Same-video paired consistency | 0.82127 | 0.91258 |
| Within-source shuffled consistency | 0.86019 | 0.93762 |

Ordinary two-view ERM beats semantics by +0.08174 (paired group 95% CI
[0.05277, 0.11588]) and +0.02041 ([0.00172, 0.04038]). These are conditional
development results, not a method novelty claim. The paired-consistency
candidate does not become the preferred method: shuffled pairing remains
competitive or better, consistent with its earlier rejection. Do not select
the best training source or seed after evaluation and present the selected
value as an unbiased result.

Crucially, frozen interval-only controls reach AUROC 0.93299 from both old
training configurations on these 195 samples. Jitter-inclusive controls invert
their ordering (0.02062 and 0.0); they are not flipped using the new labels.
Timing information remains available after the nominal time grid across this
second real-source collection. This does not prove the neural heads use it,
but prevents attributing their high scores to a specific forensic mechanism.

## Verification and decision

All 60 external predictions were reproduced from saved old checkpoints and
separately reconstructed cached inputs. Raw-video, feature and head hashes
passed; individual and ensemble metrics agree. The verifier performed no
training. Compact evidence is in `pair2_frozen_transfer_v1_evidence.json`;
full records, features, predictions and timing scores remain in server run
`/root/autodl-tmp/cvpr27/runs/pair2_frozen_transfer_v1/`.

The source-access blocker is reduced: second-source candidates, author
origin/prompt joins and an executable frozen-transfer protocol now exist.
Formal independent-source acceptance is incomplete. Archive-prefix selection
is non-random, author provenance is not content proof, and this cohort is now
exposed development data. No new final set was opened.

Next: use actual-lag support and estimator controls to distinguish motion
response from sampling shortcuts, then test localized controlled
correspondence against ordinary two-view ERM. Do not expand training merely
to push source-correlated AUROC higher. The overall innovation goal is unmet.

The initial 195-clip result is preserved. A separate v2 run retries the single
slow clip without a probe deadline and reuses only hash-verified successful
features. Its complete-cohort report supersedes this initial cohort for future
comparisons; the original code snapshot remains in the server v1 directory.
