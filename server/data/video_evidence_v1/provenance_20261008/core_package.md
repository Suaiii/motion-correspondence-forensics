# RoboVid-SM v0.2 Core Package

## Data & Manifests
- v0.2 split root: `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits`
- OSN degraded: `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_osn`
- FFmpeg degraded (test split): `E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_ffmpeg`
- Degraded manifest: `E:\AAGenvid\main\reports\robovid_sm_v02\degraded_manifest.csv`

## Baseline Results
- Baseline CSV: `E:\AAGenvid\main\reports\robovid_sm_v02\baseline_results.csv`
- D3 sample table: `E:\AAGenvid\main\reports\robovid_sm_v02\baseline_table.md`
- ReStraV table: `E:\AAGenvid\main\reports\robovid_sm_v02\baseline_table_restrav.md`
- ReStraV cross-domain table: `E:\AAGenvid\main\reports\robovid_sm_v02\baseline_table_restrav_cross.md`
- Figure: `E:\AAGenvid\main\reports\robovid_sm_v02\figures\d3_ap_drop.png`

## Protocol & Outline
- Protocol: `E:\AAGenvid\main\reports\robovid_sm_v02\protocol.md`
- Degradation matrix: `E:\AAGenvid\main\reports\robovid_sm_v02\degradation_matrix.md`
- Paper outline: `E:\AAGenvid\main\reports\robovid_sm_v02\paper_outline.md`

## Repro Commands (Key)
```powershell
# FFmpeg degrade (test split)
python E:\AAGenvid\main\scripts\apply_ffmpeg_degrade.py `
  --input-root E:\AAGenvid\Dataset\RoboVid-SM\v02\splits `
  --output-root E:\AAGenvid\Dataset\RoboVid-SM\v02\splits_ffmpeg `
  --config E:\AAGenvid\main\scripts\ffmpeg_profiles.json `
  --profiles wechat_l2,douyin_l2,douyin_l3 `
  --splits test

# D3 frame prep (2s)
E:\AAGenvid\.conda_envs\d3_cuda\python.exe E:\AAGenvid\main\baselines\prepare_d3_dataset.py `
  --input-root E:\AAGenvid\Dataset\RoboVid-SM\v02\splits `
  --output-root E:\AAGenvid\Dataset\RoboVid-SM\v02\d3_clean_2s `
  --split test --duration 2.0 --fps 8

# D3 sample eval
E:\AAGenvid\.conda_envs\d3_cuda\python.exe E:\AAGenvid\main\baselines\run_d3_eval.py `
  --d3-root E:\AAGenvid\external_repos\D3 `
  --python E:\AAGenvid\.conda_envs\d3_cuda\python.exe `
  --real-csv E:\AAGenvid\main\reports\robovid_sm_v02\d3_samples\clean\csv\real.csv `
  --fake-csv E:\AAGenvid\main\reports\robovid_sm_v02\d3_samples\clean\csv\fake.csv `
  --out-dir E:\AAGenvid\main\reports\robovid_sm_v02\d3_samples\clean
```
