# AL87 handoff — exact-byte trace identity repair

The targeted repair keeps AL84/AL86 bytes and failures intact. It replaces only cross-call identity comparisons with canonical float64 byte equality; arithmetic K consistency retains a declared floating tolerance.

The first frozen v1 batch accepted the one-ULP attack because the replacement missed the original `equal_nan=False` text; that evidence is preserved. v2 then applied exact comparison to arithmetic K and failed before evidence (`run_v2_failure.json`). v3 separated identity and arithmetic checks and completed one batch: the valid four-call trace matched the independent d/v/K reference, one bounded AL79 reducer call returned `rgb-reducer-v2`, and all nine malformed cases—including the ULP base-input attack—were rejected. v3 evidence SHA256: 6074aac7d8d3e534a457921485c9c6744fb359e06ef30111a6121b094cd9cc23.

This is an exact precomputed software contract only. It does not authenticate a real probe, decoder, pixel/time correspondence, source label or detection effect; network/media/server/models/GPU/CI were unused and no independent scientific review is claimed. AL84 and AL86 remain failed historical contracts; AL36/AL68 remain separate provider-blocked follow-ups.
