# Provenance decision: CogVideo and historical source aliases

This checkpoint supersedes source counts based on directory names in the
provisional manifests. It does not rewrite the original manifests or metrics.

## CogVideo task identity

The [GenVidBench paper v3](https://arxiv.org/html/2501.11340v3), section 3.1,
states that CogVideo and Mora were generated from HD-VG-130M prompts, whereas
SVD and MuseV use extracted HD-VG frames. This supports the CogVideo subset's
text-to-video task classification. It also establishes that Pair2 real videos
and several generated subsets share content ancestry; they cannot be assigned
independently to splits. The recovered member IDs still need a per-video join
to the HD-VG reference metadata.

The [official repository](https://github.com/genvidbench/GenVidBench) declares
CC BY-NC 4.0. The [project page](https://genvidbench.github.io/) also records
upstream copyright restrictions for Pair1 and points to Vript, HD-VG and
VidProM. Record the declared licence and preserve attribution; do not equate
this declaration with cleared third-party rights or commercial-use permission.
These primary sources were fetched live through the local proxy on 2026-09-16.

The paper mentions 4 fps for CogVideo; the 100 recovered files passed actual
8 fps decoded-PTS selection. Keep the concrete measurements and investigate
release/encoding differences; do not silently retime files to match prose.

## Server source-alias audit

The audit rehashed all 263 server videos and joined their names to the original
RoboVid source map. Candidate source identities after this join:

| Identity | Count |
|---|---:|
| Vript real | 90 |
| OpenSora | 80 |
| Text2Video-Zero | 80 |
| OpenAI Sora | 13 |

The videoOSN entries account for ten of the Vript and eight of the Sora rows.
They are a reuse/transport collection, not an independent real acquisition
source or generator. Seven ancestor candidate groups contain multiple rows.
The join uses local metadata plus names; it is deliberately not a claim that
all ancestry has been content-verified. All ancestry status remains unknown.

The 100 recovered CogVideo records provide an additional documented generator
candidate. Combining them with this pool gives four generator identities but
still only one established real-source family. Earlier claims that videoOSN
supplied a second real source are withdrawn.

## Next experiment prerequisite

Use the existing MSVD/ComGenVid pool as exposed development only after its
sample-level rights/provenance review, or acquire a genuinely independent
real-source pool. Do not count repo-to-space examples as confirmed real based
solely on a CC0 dataset card. Group source videos and generated references
before fit/calibration/audit allocation. New downloads and compute remain on
the server; local files are limited to code and evidence.

No new classifier was trained at this checkpoint. The overall research goal
remains incomplete. An upstream declared licence, successful decoding or
completed audit script is not evidence of an innovative algorithm.
