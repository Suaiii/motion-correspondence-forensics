# AL27 frozen original-z convex objective reference

Scope: only `multidimensional_objective_reference_software`. Three prescribed
abstract Gram panels, no probe/readout import, classifier, media, model, labels,
probabilities, AUROC, source/ancestor fitting, server, GPU, or hyperparameter search.
AL29 is not read or incorporated by this implementation; z coordinates stay original.
All actual inputs, exact expectations, source and dependency hashes are committed
before the first objective or optimizer execution. One batch; preserve every failure.

## Definitions and exact controls

Each z is 12-dimensional, four (A/D,B/D,C/D) triplets. T is 12 by 4 with disjoint
columns (1,1,-2), hence T^T T=6I and q=T^T z. For a fixed uniform pair list:

L_c(w)=mean softplus(-Delta-q dot w)+(1/1000)||w||^2.
L_f(beta)=mean softplus(-Delta-z dot beta)+(1/6000)||beta||^2.

The free head has 12 parameters against 4. L_f(Tw)=L_c(w), including regularization.
The free optimum cannot exceed the candidate optimum on this identical synthetic
training objective. This does not order test risk or detection performance.

Every negative row is z0=(1,1,0) repeated four times. All actual plus/minus rows are
frozen as rational strings. Each pair has weight 1/n; no pooled panels.

1. aligned: four plus rows z0+T[:,j]/8, j=0..3. Delta-z and Delta-q ranks 4 and 4.
   Candidate initial gradient (-3/32)*4; free initial gradient
   (-1/64,-1/64,1/32)*4. Any component of beta perpendicular to range(T) changes
   only the positive regularizer, so beta*=Tw*. By permutation symmetry and strict
   convexity, w*=t*ones. Independent scalar objective is
   log(1+exp(-3t/4))+t^2/250; derivative is -0.75/(1+exp(0.75t))+t/125.
2. full_rank: twelve plus rows z0+e_j/4, j=0..11. Ranks 12 and 4. Sum Delta-q=0,
   so unique candidate optimum is zero, objective log(2). Free initial gradient
   (-1/96)*12; unique optimum beta=b*ones has b>0. Scalar objective is
   log(1+exp(-b/4))+b^2/500; derivative is -0.25/(1+exp(0.25b))+b/250.
   Fixed beta=ones is a separate feasible check, never an initialization change:
   log(1+exp(-1/4))+1/500 < log(2). For example exp(1/4)>5/4 implies
   log(1+exp(-1/4))<log(9/5), and log(10/9)>1/10>1/500.
3. symmetric: eight plus rows z0 +/- T[:,j]/8, j=0..3, plus sign then minus sign.
   Ranks 4 and 4. Both initial gradients exactly zero. Positive regularizers make
   both zero optima unique. This valid balanced support differs from empty input.

Fraction elimination independently checks ranks and g(0)=-sum Delta/(2n) from the
actual frozen rows. Each A>=0, B>=0, AB-C^2>=0 is checked exactly. These are
individual abstract Gram constraints only; no simultaneous realizability by one
video or four filters is claimed.

## Numerical contract

Stable softplus(-m)=max(-m,0)+log1p(exp(-abs(m))). With e=exp(-abs(m)), the negative
logistic derivative factor is e/(1+e) for m>=0 and 1/(1+e) otherwise; curvature
e/(1+e)^2. Gradient=-D^T factor/n+2lambda*x, Hessian=D^T diag(curvature)D/n+2lambda*I.
No predicted probabilities are reported.

Float64 damped Newton starts at zero. Euclidean gradient norm <=1e-10 stops.
Maximum 200 accepted iterations, solve H*p=-g directly, no jitter or fallback.
Armijo c=1e-4, alpha=1 halved at most 40 times, including 2^-40; preserve failure
if no trial accepted. No line-search tolerance relaxation. Each full evaluation
saves x, data/reg/total objective, gradient and Hessian; each solve saves RHS,
direction, residual, g dot p, all trial IDs/steps/bounds and stopping reason.
Diagnostic free evaluations at beta=Tw (three) and beta=ones (full_rank only) are
logged separately and do not change optimizer terminal_evaluation_id.

Independent stdlib bisection uses analytic scalar derivatives, fixed bracket
[0,64], width <=1e-13, at most 128 iterations. Bracket signs and strict monotonicity
provide the mathematical reference; floating computations are not a rigorous
error certificate. All derivative evaluations are recorded. Prespecified maximum
absolute coordinate and objective agreement tolerance is 1e-9. No rerun or retuning.

Only two extra boundaries: empty pair arrays return no_training_support with
parameters=null, no objective evaluations; one NaN in a frozen z row rejects
before projection or solver for each representation. A valid optimum at zero
remains distinguishable from no support and rejection.

## Resources and immutable evidence

NumPy/stdlib only; sequential solves, native BLAS threads explicitly set and
verified at 2. No Torch or SciPy Python import. NumPy's vendored OpenBLAS DLL name
can contain scipy; that does not import SciPy. Dimension <=12, pairs <=12 and
feature rows <=24 per panel, each numerical ndarray <=1MiB (largest possible
solver Hessian 12x12 float64=1152 bytes). No claim about peak RSS, which is not
measured. Stored JSON ledgers are not ndarrays. Pre/post checks hash historical
AL01/04/06/09/12/15/18/20/24/25 artifacts and source files without executing them.
Dependency receipt hashes executable, NumPy core and BLAS plus metadata; it is
a selected dependency receipt, not a claim of hashing every loaded system DLL.

Expected attempts: six supported solves, two empty solves, two rejected inputs;
two independent scalar references. Record actual counts including line-search
trials and four diagnostic free-objective evaluations. Timing includes imports,
hash verification after run and all checks; GPU/project historical spend remains
unknown and is not overwritten. Software pass releases no scientific, real-data,
novelty, budget, resource or final-confirmation gate.
