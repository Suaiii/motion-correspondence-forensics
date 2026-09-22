# AL85 handoff — strict shared-ancestor point estimator

A new isolated software path replaced the invalid AL83 implementation. The estimator validates complete sample IDs, ancestor IDs, labels, shared negatives, fixed methods/tags/generators, finite scores and integer ancestor weights. It sorts score blocks and records `two_U` and `2*Wp*Wn`; an independent Fraction pairwise implementation checks the same deltas.

One frozen synthetic batch completed with 21 checks and `software_pass=true`: all-one tag-a delta `7/24`, tag-b delta `0`, mean `7/48`; ancestor-A doubled delta `11/48`, mean `11/96`; zero-class schemes returned invalid; order invariance and malformed inputs were checked. Evidence SHA256: `515146ee59bd4af853c36328c141c93d68d98530f9a2cce344e49c9c2f8f873e`.

This is a point-estimator/software contract only. It has no CI, bootstrap, real samples, models, media, server, network or GPU, and is not independent scientific review or a CCF-A contribution. AL81 and AL83 failures remain unchanged; this repair does not release any formal efficacy or innovation gate.
