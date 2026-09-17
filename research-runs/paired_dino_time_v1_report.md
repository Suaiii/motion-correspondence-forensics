# Paired DINO time-grid comparison

The server completed the time-grid extraction before shutdown: 28,674 requested
records, 28,672 successful and two excluded. The extraction used a centered
one-second physical-time window with eight nearest native frames at 8 Hz. The
previous native control used the middle eight frames from the frozen native16
cache. Both paths used the same DINOv2 ViT-B/14 checkpoint, decoder revision,
spatial crop and normalization.

The paired cached baseline completed six LR arms for two generator holdouts.
Scores were printed and observed in the live server session before shutdown:

| Holdout | Native semantic | Native delta | Time semantic | Time delta |
|---|---:|---:|---:|---:|
| ModelScope | 0.8397 | 0.9183 | 0.8441 | 0.8445 |
| VideoCrafter2 | 0.8478 | 0.8992 | 0.8556 | 0.8628 |

The native-frame delta gain is reduced substantially by the nearest-frame
time grid. Sampling sensitivity is established, but the change also alters
temporal coverage and does not isolate a causal effect of timing alone.
The compact server JSON has now been retrieved. Frozen-head replay passes;
the time-delta gain intervals cross zero on both holdouts: ModelScope
[-0.011488, 0.011573], VideoCrafter2 [-0.004446, 0.018758].
Actual interval-only probes still obtain AUROC 0.78395 and 1.0 respectively.
The grid therefore does not eliminate source timing cues. There is one real
source, ancestry is only proxied and all sources were exposed during development.
The original server output is preserved on the server data
disk at `/root/autodl-tmp/cvpr27/runs/paired_dino_time_v1/`.

Decision: keep time delta as a baseline; its incremental mechanism gate has
not passed. See `paired_time_verification_v2_report.json`. Do not claim the
native-frame gain, and do not open final confirmation data from this run.
