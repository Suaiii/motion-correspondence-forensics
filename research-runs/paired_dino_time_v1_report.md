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

The native-frame delta gain is reduced substantially by matched physical-time
sampling. This confirms that the earlier 0.92-scale results were partly driven
by source-dependent timing. The time-matched delta remains above the semantic
baseline in this exposed development diagnostic, but this is not a CCF-A or
patent result: there is one real source, ancestry is only proxied, all sources
were exposed during development, and the compact server JSON was not retrieved
before shutdown. The original server output is preserved on the server data
disk at `/root/autodl-tmp/cvpr27/runs/paired_dino_time_v1/`.

Decision: keep the time-matched delta as a mechanism candidate for a fresh
accepted cohort. Do not claim the native-frame gain, and do not open final
confirmation data from this run.
