# AL145 dense DINO baseline gate

AL145 establishes the strongest matched dense temporal baseline on the new
source/generator-holdout selection. It does not claim a mechanism or a
breakthrough. Inputs are the fixed eight-native-frame selection
`selection_dense_holdout_v1_8frame_clean.json` and the hash-locked DINO cache.

```powershell
$py = 'C:\Users\ZHUyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -X utf8 research-runs\VIDEO_EVIDENCE_V1_20261004\AL145_dense_dino_baseline.py `
  --selection research-runs\VIDEO_EVIDENCE_V1_20261004\selection_dense_holdout_v1_8frame_clean.json `
  --manifest research-runs\VIDEO_EVIDENCE_V1_20261004\v1_manifest.jsonl `
  --features /srv/video_evidence_v1/runs/dino_features `
  --output /srv/video_evidence_v1/runs/AL145_dense_baseline
```

The adapter verifies feature hashes, selects logistic-regression C on the
AAGenvid calibration cohort, and reports semantic, semantic-delta, and
native-time velocity arms on AAGenvid test, the seven descriptive OpenAI-Sora
rows, and the untouched AEGIS holdout. AEGIS must not enter fitting or C
selection. A complete dense result is required before AL146 is released.

Failure conditions: any selection/manifest/feature hash mismatch, incomplete
feature record, source or role overlap, nonmonotonic PTS, or missing external
metrics aborts the gate. `formal_gate_passed` remains false.
