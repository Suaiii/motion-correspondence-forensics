# AL30 frozen accuracy-budgeted stopping reference

Dispatch cc-al30-accuracy-budgeted-stop-20260919; scope only
`accuracy_budgeted_optimizer_reference`. AL27 execution is done and its failed
software gate is permanent. This is a new versioned recovery batch, not an AL27
continuation or a scientific success dependency. No AL31 work is executed.

## One numerical policy change

Retain original z=(A/D,B/D,C/D) in four blocks, q=T^T z, T^T T=6I. Candidate w has
dimension4, lambda=1/1000; free beta has dimension12, lambda_free=1/6000. Each head
uses identical uniform pairs within each panel, original stable pairwise logistic
and squared Euclidean regularizer. L_free(Tw)=L_candidate(w). The objective.py
is copied byte-identically from AL27, not imported from or written to the old module.
Its AL27 module docstring indicates provenance. All objective, gradient, Hessian,
linear solving and Armijo calculations are unchanged; only the threshold supplied
to the solver changes by this uniform rule:

    epsilon_x=1e-9; mu=2*lambda_head
    tau_stop=min(1e-10, mu*epsilon_x/2)

Candidate exact mu=1/500, exact tau=1e-12; free exact mu=1/3000, exact tau=1/(6e12).
Store exact rationals and actual float lambda/mu/epsilon/tau in frozen config and
each head result. Euclidean gradient norm is compared to the frozen float tau.
No special case adds a Newton step. In exact arithmetic strong convexity gives
||x-x*||_2 <= ||gradient(x)||_2/mu. To certify parameter error from a computed
gradient would additionally require a rounding error bound <=mu*epsilon_x/2.
That bound is unknown (`null`), not zero. `parameter_error_certified=false` for
all results, even when independent scalar comparisons pass.

Original float64 zero initialization, at most200 accepted steps, Armijo c=1e-4,
alpha=1 halved up to40 times including2^-40, direct H*p=-g, and no damping jitter
or fallback remain fixed. Original max-absolute parameter difference and absolute
objective difference tolerances remain1e-9. Never relax or rerun based on results.

## Fixed actual inputs and controls

AL27_inputs.json is referenced by raw-byte SHA256. Its original three panel rows
are copied without numerical modification into AL30_inputs.json and explicitly
labeled `known_regression`. Verify their equality and the old raw bytes before
running. AL27 remains fail; successful regression is not new independent evidence.

All negatives are z0=(1,1,0) repeated4 times. Four panel types only:

| Panel | Pairs | Positive rows | Exact rank z/q | Exact initial gradient candidate/free |
|---|---:|---|---|---|
| aligned, known regression |4|z0+T[:,j]/8|4/4|(-3/32)*4 ; (-1/64,-1/64,1/32)*4|
| full_rank, known regression |12|z0+e_j/4|12/4|0 ; (-1/96)*12|
| symmetric, known regression |8|z0 +/- T[:,j]/8|4/4|0 ; 0|
| full_rank_scale, new software control |12|z0+e_j/8|12/4|0 ; (-1/192)*12|

Indices and signs follow original AL27 order; the new scale panel uses j=0..11.
The new control changes only the predeclared full-rank positive displacement to
delta=1/8. No random inputs, labels, hyperparameter/scale search, or other scenarios.
Individual triplet Gram feasibility is checked exactly with Fraction: A>=0, B>=0,
AB-C²>=0. Exact rank and g(0)=-sum Delta/(2n) come from actual frozen rational rows.
No simultaneous real-video/four-filter realizability is assumed.

Aligned free optimum lies in range(T): perpendicular components affect only the
positive regularizer. Symmetry gives w=t*ones4, beta=Tw. Independent scalar
objective log(1+exp(-3t/4))+t²/250, derivative -0.75/(1+exp(0.75t))+t/125.
For either full-rank panel, candidate gradient is exactly zero at zero and its
positive regularizer makes zero the unique optimum. Free beta=b*ones12 has
objective log(1+exp(-delta*b))+b²/500 and derivative
-delta/(1+exp(delta*b))+b/250. Use delta=1/4 and1/8 respectively. Both roots are
positive. Fixed beta=ones provides a separate feasible objective below log2;
it is not an initialization. Symmetric panel unique optima remain zero.

Independent scalar code uses stdlib math, fixed bracket[0,64], width<=1e-13,
at most128 bisections. Three references (aligned, old full-rank, new scale);
save every derivative evaluation. No rigorous floating root certificate.
Record max coordinate and objective differences <=1e-9 without changing them.

Only empty pair and one-NaN boundaries are inherited, unchanged. Empty returns
no_training_support/parameters=null with no evaluations. NaN rejects before
projection or solver. Valid zero optima remain separate from both boundaries.

## Freeze, ledger and resources

Freeze all source/inputs/config/protocol, exact rank/zero expectations, upstream
work-order/reference hashes, selected runtime dependencies and historical AL27
plus its protected predecessors. Commit before any numeric objective/optimizer.
Run once; exclusive started/evidence creation prevents a silent second batch.
Hash inputs, dependencies and historical files both before and after execution.
Only main planning/DAG snapshots are mutable externally; record but do not own them.

Log full vectors, objective/data/reg terms, gradients/Hessians, g norms, all
linear directions/RHS/residuals, trial IDs/bounds/step lengths, stop reasons and
failures. Four beta=Tw diagnostics plus two fixed beta=ones checks are separately
logged free-objective calls; terminal optimizer IDs remain unchanged.
Expected input attempts12: eight supported heads, two empty returns and two
nonfinite rejections. Ten solver entries; three independent scalar references.
Record actual evaluation, solve, trial and derivative counts, not just expectations.

NumPy/stdlib only, two native threads, sequential head execution, dimension<=12,
each panel pairs<=12 and feature rows<=24, each ndarray<=1MiB (largest possible
Hessian12x12 float64=1152B). RSS not measured. No Torch/SciPy Python, model/weight,
readout/probe, media, true data/classifier fitting, source probabilities/AUROC,
SSH/server/GPU or downloads. NumPy's vendored BLAS name contains scipy without
importing the SciPy Python package. No AL29 coordinate rewrite or AL31 review.

Outputs AL30_protocol/inputs/config/freeze/started/evidence/report/handoff and
artifact manifest. The old AL27 gate and all scientific/resource/final-confirmation
boundaries stay unchanged regardless of this software batch's outcome.
