# AL78 CPU RGB reducer protocol

This bounded software package consumes already-computed four RGB fields and never creates reconstructor calls, reads media, fits a classifier, or contacts a server. It accepts explicit `BTHWC` or `BCTHW` layout and never infers layout through reshape.

`K=d_a-d_b`, `S=d_a+d_b`, and four fixed spatial correlation filters are reduced per sample. The denominator is `sum(v_a^2)+sum(v_b^2)+N*eta`, with `eta=1e-12` and N the reduced scalar count. This preserves the full-sample ratio across unequal temporal blocks; averaging block ratios is rejected. `r_K` is the direct K numerator and shares q exactly. No clipping, absolute value, or learned readout is used.

The C1--C6 cases in config are software-contract checks only. They do not authorize real reconstructors, media, model calls, training, GPU, or an innovation claim.
