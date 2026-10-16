# RoboVid-SM v0.2 Evaluation Protocol (Benchmark Core)

Date: 2026-03-24

## Data Scope
- Manifest: `E:\AAGenvid\Dataset\RoboVid-SM\manifests\real_manifest_v02_random.jsonl`
- Pairs: 2000 (real/fake) -> 4000 videos
- Split: train 1600 / val 200 / test 200 pairs
- Split root: `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits`

## Degradation Settings
- L1: crop-only (design spec; not executed here).
- L2: crop + resize/re-encode (FFmpeg).
- L3: OSN social-media simulation (Wechat/Whatsapp).
- FFmpeg profiles: `E:\AAGenvid\main\scripts\ffmpeg_profiles.json`
- FFmpeg output root: `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_ffmpeg`
- OSN output roots:
  - `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_osn_wechat`
  - `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_osn_whatsapp`
  - Note: OSN/FFmpeg currently generated for **test split only**.

## Baselines
- D3 (AP evaluation) on test split.
- ReStraV (Acc/Recall/F1/AUC) on test split.
- Robustness eval: train on clean, test on L3 (OSN).

## Metrics
- Acc / Recall / F1 (ReStraV)
- AP (D3)
- Clean vs Degraded drop (primary table)

## Artifacts
- FFmpeg manifest: `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_ffmpeg\ffmpeg_manifest_clean.csv`
- OSN manifests:
  - `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_osn_wechat\osn_manifest.csv`
  - `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_osn_whatsapp\osn_manifest.csv`
- Baseline table: `E:\AAGenvid\main\reports\robovid_sm_v02\baseline_results.csv`
- Degraded manifest: `E:\AAGenvid\main\reports\robovid_sm_v02\degraded_manifest.csv`
