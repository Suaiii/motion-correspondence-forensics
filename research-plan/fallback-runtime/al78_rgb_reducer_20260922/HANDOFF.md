# AL78 handoff：RGB q/r reducer CPU software contract

- 完成：2026-09-22T05:59:40+08:00
- dispatch：cc-al77-al78-local-review-cpu-20260922
- executor：planagent fallback-runtime after recorded research-window provider failure; no researchagent artifact was overwritten.
- scope：precomputed four RGB fields only; no reconstructor, media, model, server, GPU, training, classifier or network.
- command: `C:/Users/ZHUyi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 run_batch.py`
- software result: `software_pass=True`, checks=9, failures=[], process CPU seconds=0.140625; this is interface/software evidence only.

## Fixed results

C1 non-square BTHWC, C2 unequal temporal blocks, C3 all-zero fields, C4 near-cancellation, C5 BCTHW large interface, C6 signed cross-term all passed explicit layout/contract checks. Batch reductions are per sample and aggregate sums before ratios, so unequal temporal blocks do not average block ratios. q and r_K are assigned from the same direct K sum; signed r_S/r_J and eta behavior remain visible. Rejection checks for missing fields and invalid layout passed.

No scientific efficacy, real wrapper compatibility, source provenance, or innovation claim follows. Actual probe output shapes and reconstructors remain unknown. Independent review is pending.

## Hashes

```json
{
  "reducer.py": "444852c59aef4af22968415d2809ae13aa7dcf9bf0025b23fb508fe36a896f05",
  "run_batch.py": "f0795c9ac00fa2b0ef9afde02ae2d76ad0cdeb2e07eacd31c393f816961dc592",
  "config.json": "ac47232dcae8d25d5ff8d276dd0edb3205a6ae9330ec9257796b96475e0255c9",
  "PROTOCOL.md": "964bd065067810f03e6e19739afb0f67f4fdac8e813b21df70402b208dca9480",
  "run_v1/evidence.json": "10a6eebd2d3cfb4001f7ad3307842995285f10aa2621d2137eb5925c36efc4e3"
}
```

## Follow-ups

1. After AL36/data gates, a separately authorized ProbeBatch adapter must bind R_a/R_b, h, four calls, shapes and failure codes.
2. A separately authorized same-output q-only versus r/full evaluator must freeze matching, calibration, regularization, seeds and controls. Neither follow-up is executed here.
