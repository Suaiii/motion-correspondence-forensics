# AL32 frozen stable-coordinate integration reference

Dispatch cc-al32-stable-baseline-integration-20260919. Gate scope only
`stable_readout_metric_integration_reference`. New directory, frozen code and
selected inputs committed before one arithmetic batch. No old runtime import,
optimizer, filtering, probe, AE, model, media, real training or classification.
AL27 remains fail; AL30 known-regression identity is retained. AL33 is separate
planner work and is not executed or awaited here.

## Part A: three archived synthetic response fields

Select exactly positive_inner, negative_inner, near_cancellation from AL25_evidence,
in that order; source SHA256 is frozen. Filter order identity, laplacian, sobel_x,
sobel_y, each already-filtered array has common THWC shape(2,3,3,3),54 scalars.
Only stored Hda,Hdb,HK arrays are processed. Stored per-filter D, q_direct,
A/B/C, raw z, compact q and other scalar diagnostics retain their original values.
No new eta, denominator, padding, filter support or input-field computation.

Per filter use this specific float64 path:

    s_H = stored Hda + stored Hdb
    r_S = mean(s_H*s_H)/stored D
    r_K = stored q_direct                 # literal reuse; check float.hex
    r_J = mean(s_H*stored HK)/stored D

The 12 r_K values must match the frozen source hex values. Do not reconstruct
r_K from z's three terms, recompute K energy, refilter a sum field, clip negatives
or alter source metadata. Store full s_H, raw scalars, stable values/hex/signs,
all field signs, source array values in frozen input, and every reconstruction
difference. The existing negative C and near-cancellation compact=0/direct-q>0
records stay intact. No claim that adding stored filtered arrays is bitwise
identical to filtering a newly computed sum field.

Independent stdlib Fraction references treat stored binary floats as exact inputs
and calculate r_S and r_J using rational sums/products and the exact binary value
of stored D. r_K remains the exact binary value of the stored q. Compare numeric
r to float(reference) with fixed absolute tolerance1e-12; this arithmetic reference
is not an error certificate for a real AE. Record M*z and M_inverse*r, their
signed differences from stable r / original z, without requiring identity after
archival rounding or interpreting loss of a small term as a scientific feature.

Fixed w=(1,-2,1/2,0), embedded gamma=(0,w_l,0) in each block. Both candidate q4
and stable r_K4 pass through the SAME function: four ordered scalar products and
four accumulator additions starting at0.0. Require the two scores' float.hex
to match. Record products and partial sums. Separately calculate generic
12-dimensional gamma dot r, record its value/hex and signed difference from the
shared four-term score. No unconditional bitwise requirement on the generic dot.
These predetermined weights are a mathematical control, not source predictions.

## Part B: three abstract known regressions, two fixed points only

Select aligned, full_rank, symmetric from frozen AL30_inputs, retaining exact
rational rows and known_regression identity; verify selection against source
bytes. Exclude full_rank_scale. These panels are not paired with or derived from
the archived response fields in Part A; do not pool either evidence type.

M=[[1,1,2],[1,1,-2],[1,-1,0]], with inverse
[[1/4,1/4,1/2],[1/4,1/4,-1/2],[1/4,-1/4,0]]. B=diag(M,M,M,M).
G3=MM^T=[[6,-2,0],[-2,6,0],[0,0,2]], G=BB^T. All exact inverse and metric
identities are checked with Fraction; matrices and exact expected G are frozen.

For each rational row r=Bz. Compute positive and negative r separately, then
Delta-r; check against B*Delta-z and independent Fraction rows. There are exactly
two gamma values per panel: all-zero and four blocks(0,w_l,0). The corresponding
beta=B^T gamma has blocks(w_l,w_l,-2w_l). Fraction verifies both fixed margins and
penalties exactly. Exact penalties are0 and21/4000, with lambda=1/1000 unchanged.

At the six points evaluate each representation ONCE, without an optimization loop:

    L_beta = mean softplus(-Delta-z dot beta) + (lambda/6)||beta||²
    L_gamma = mean softplus(-Delta-r dot gamma) + (lambda/6)gamma^T G gamma

Preserve uniform within-panel weights. Stable softplus uses max(-m,0)+log1p(exp(-abs(m))).
The usual logistic derivative/curvature evaluate the gradient/Hessian; regularizer
derivatives are2(lambda/6)G gamma and2(lambda/6)G (identity metric for beta).
Store parameters, margins, total/data/penalty values, all gradient/Hessian data
and penalty components. Compare fixed absolute maximum errors <=1e-12:

    L_gamma == L_beta; grad_gamma == B grad_beta;
    Hess_gamma == B Hess_beta B^T;
    penalty_gamma == penalty_beta == exact expected penalty.

The embedded penalty21/4000 must also equal lambda||w||². Do not substitute an
isotropic gamma penalty, tune parameters, search weights or evaluate new points.
The same new fixed-evaluation helper serves both coordinates; Fraction algebra is
a separate implementation, not a claim of independent scientific review.

## Counting, archival preservation and resource limits

Record complete high-level arithmetic counts; these are algorithm/API operations,
not disassembly-based scalar hardware instruction counts. In Part A expected
12 field array additions,24 elementwise products,24 mean reductions,24 scalar
normalizations and12 literal q reuses;6 four-term scores (24 scalar products,
24 accumulator additions),3 generic dots,24 3x3 reconstruction products.
Independent exact field references:12, each contains two rational mean products;
they are listed separately from the24 float means and cause no AE/filter calls.

Part B:3 independent exact panel references,6 parameter maps,6 gradient maps,
12 Hessian-map matrix multiplications,9 float panel transforms (positive,
negative and difference check per panel),1 float metric product. Exactly12 fixed
objective evaluations, each with5 matrix/dot products and1 data mean. Objective
elementwise exp/logistic/derivative operations belong to those evaluation calls;
full values/derivatives are saved. Candidate embedded penalty uses4 squares,
4 sum additions and1 scalar lambda multiplication. Exact matrix identity checks,
data differences, signs, comparisons and hashing are diagnostics, not new samples
or objective evaluations. No optimization, readout, filtering, probe or AE calls.

Only NumPy/stdlib, sequential two-native-thread execution, maximum parameter
dimension12, pairs<=12 per abstract panel, each ndarray<=1MiB. Archived arrays
have54 elements; largest matrix/Hessian is12x12 float64=1152B. Log array sizes,
wall/process CPU time; peak RSS is not measured. NumPy-vendored OpenBLAS library
names may contain scipy, but the SciPy Python package is not imported. No Torch,
downloads, server/SSH/GPU, weights/media, real data/classifier, probabilities/AUROC.

Frozen source/input/dependency and protected historical hashes checked before and
after one run; require clean committed Git blobs before exclusive started receipt.
On failure preserve all available evidence, do not change inputs/weights/tolerance
or rerun. Save AL32_protocol/inputs/config/freeze/started/evidence/report/handoff
and manifest. Main DAG is read-only; AL27 failure, AL25 cancellation receipt and all
real-science/resource gates remain intact. Real AE error stays unknown/null.
