# Video Evidence v1

冻结日期：2026-10-04（Asia/Shanghai）

## Package contents

- `v1_manifest.jsonl`: 9,236 rows with file SHA-256, stream metadata, full probed PTS arrays, best-effort timestamp arrays, time base, frame count, and status.
- `summary.json`: counts, input hashes, manifest hash, and generator-label repair receipt.
- `build_v1_manifest.py`: reproducible builder for the current local bundle.

## Sources

### AAGenvid RoboVid-SM v0.2

- 8,800 rows: clean v0.2 splits, `splits_osn`, WeChat and WhatsApp variants.
- 4,400 real rows from Vript candidates.
- 4,400 fake rows: OpenSora, T2V-Zero, and a small OpenAI-Sora-named subset.
- Random pair records are retained as `pair_record` with `content_pairing=random_pair`.
  They are not ancestor evidence.

### AEGIS Hard Test

- 436 clean external holdout videos:
  - 111 Kling fake;
  - 107 Sora fake;
  - 109 DVF real;
  - 109 YouTube real.
- Raw tar, mapping CSV and README are stored under `E:\\AAGenvid\\external_datasets\\AEGIS`.
- Usage remains subject to AEGIS's Custom Academic Use License and upstream dataset terms.

## Verification result

- Rows: 9,236.
- Hash/probe success: 9,236/9,236.
- Native PTS complete: 9,236/9,236.
- Native PTS monotonic: 9,236/9,236.
- Formal mechanism gate: **not evaluated**.

## Interpretation

This is a stable benchmark candidate and propagation evidence inventory. It is suitable for:

- clean vs derived propagation evaluation;
- cross-generator external holdout evaluation;
- source/codec/OSN response analysis;
- later baseline replay.

It does not yet establish ancestor-level causal pairing, license closure for every AAGenvid source, or an accepted unknown-generator mechanism result.

