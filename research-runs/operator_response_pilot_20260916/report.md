# Operator response pilot v1

This is a historical-development exploratory pilot on the reused 595-video
pool. It is not external confirmation and cannot support a paper or patent
claim.

The response branch was compared against the same `correct-only` Bag training
recipe for seeds 17, 29, and 43. Audit AUROC deltas (response minus baseline)
were -0.06871, +0.00409, and -0.02047; the mean delta was negative. The
response branch is therefore rejected as a method candidate in this form.

Decision: do not release GPU budget for this branch. Preserve the encoder and
its tests as a reusable component, and redirect the next experiment to a
common DINO/native representation with source-balanced training.
