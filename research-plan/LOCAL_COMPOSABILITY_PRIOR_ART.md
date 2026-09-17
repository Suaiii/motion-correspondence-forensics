# Local composability: formula, code and protocol review

RS01; cc-round-2-offline-20260917; plan cvpr27-20260917-v1.1.
Review conducted September 17–18, 2026. This is a bounded primary-source review,
not exhaustive novelty clearance, independent scientific acceptance or replication.
Eight papers were inspected and seven public repositories pinned. The 38 selected
source/config files were inspected as text only; no author code, weights or data
executed. Full commits, Git blob hashes and SHA256 receipts are in
[the inventory](../research-runs/shared_plan_20260917/round2_author_sources.json);
[the selection](../research-runs/shared_plan_20260917/round2_source_selection.json)
identifies the inspected paths.

## 1. CRW: direct mathematical inheritance

[CRW v2](https://arxiv.org/html/2006.14613v2), Section 2, Eq. (1), defines row softmax
of normalized patch similarities divided by temperature. Eq. (2) multiplies
transition matrices along a path. These directly precede our P_ab and P_ab P_bc;
neither is a novel contribution here. Eq. (4) optimizes return-to-origin likelihood
on forward/backward walks. Edge dropout suppresses edges before normalization.
Appendix C discusses positional/boundary shortcuts; Appendix D includes repeated-
image sequences to distinguish spatial augmentation from temporal learning. It
trains on unlabeled Kinetics and transfers to correspondence tasks including
DAVIS, JHMDB and VIP, rather than our forensic split.

Pinned [model.py](https://github.com/ajabri/videowalk/blob/047f3f40135a4b1be2f837793b89c3dbfe7a6683/code/model.py):
stoch_mat drops affinity entries then softmaxes. Forward/reverse transitions are
separately normalized: reverse is not the transpose of an already normalized
stochastic matrix. Palindrome products are trained against identity targets using
logged transition probabilities. Our single-sided permutation differs from this
edge-dropout training, but the distinction still needs useful empirical evidence.

[train.py](https://github.com/ajabri/videowalk/blob/047f3f40135a4b1be2f837793b89c3dbfe7a6683/code/train.py)
dispatches Kinetics to torchvision video clips with frame_rate/frame_skip;
the separate [VideoList](https://github.com/ajabri/videowalk/blob/047f3f40135a4b1be2f837793b89c3dbfe7a6683/code/data/video.py)
uses JPEG indices and may reduce frame_gap. Do not describe every loader as
JPEG-only or import these as our native-PTS gate. The public argument default
clip length is 8, whereas the paper discusses 10: specify a recipe explicitly.
Checkpoint identity was not verified.

Project proposal: pre-freeze simple probes using diag(P_ab P_ba) and
diag(P_ab P_bc P_ca). These are CRW-inspired diagnostics, not reproduction of its
learned representation. Their aggregation and role require protocol review.

## 2. TimeCycle: learned localization and cycle supervision

[TimeCycle v2](https://arxiv.org/html/1903.07593v2), Section 3, learns a differentiable
tracker: patch/image affinity, localization network, then bilinear sampling.
The cycle objective compares recovered and starting patch coordinate grids,
with skip-cycle and feature terms. It learns representations on unlabeled video
and transfers to correspondence tasks. This differs from our frozen backbone
and JS between direct/composed row distributions; cycle supervision is prior art.

Pinned [model_simple.py](https://github.com/xiaolonw/TimeCycle/blob/16d33ac0fb0a08105a9ca781c7b1b36898e3b601/models/videos/model_simple.py)
contains normalized correlations, image-position softmax, a three-output transform
predictor, recurrent crops and multiple cycle lengths.
[TransformedGridLoss](https://github.com/xiaolonw/TimeCycle/blob/16d33ac0fb0a08105a9ca781c7b1b36898e3b601/geotnf/loss.py)
computes grid-coordinate MSE, not JS on path distributions.
[DATASET.md](https://github.com/xiaolonw/TimeCycle/blob/16d33ac0fb0a08105a9ca781c7b1b36898e3b601/DATASET.md)
specifies VLOG training, DAVIS-2017 validation preparation and 12-fps JPEG
preprocessing. vlog_train.py uses frame_gap/index selection, adjusted for short
sequences. These do not certify our actual PTS or ancestor separation.
No model was downloaded or verified. Correspondence transfer and a forensic
adaptation must be reported separately.

## 3. RIFT: relational modeling and implementation caveats

[RIFT v1](https://arxiv.org/html/2609.00742v1) combines macro/micro features,
conditional Gaussian NLL and MI estimation. Eq. (1) uses squared cosine
orthogonality; Eq. (12) scores conditional Gaussian residuals and Eq. (13) compares
joint and shuffled samples. Section 3.1 describes stratified 50/50 train/test,
with 10% of training for validation; held-generator experiments are separate.
Mixed-generator scores cannot stand in for our grouped unseen-generator protocol.

At commit 5c36debef9c7f5f20c655078414b87340514f1df:

- [scripts/train.py](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/scripts/train.py)
  uses seeded 80/20 random_split over cached files and saves validation filenames.
  This entrypoint has no ancestor grouping. Its discrepancy with the paper needs
  an explicit recipe decision, not an assumption about every paper run.
- [conditional_dependency.py](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/models/conditional/conditional_dependency.py)
  clamps log variance to [-10,10], aggregates NLL mean/max/standard deviation,
  and shuffles time within videos for MI marginals. The auxiliary loss averages
  all samples' NLL, then multiplies by the real-sample fraction. This is not
  sample-wise real-only masking: fake NLL still contributes in mixed batches.
  The [trainer](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/training/trainer.py)
  passes the mixed batch to that module. This is static code reasoning, not a
  measured performance effect; label any corrected variant separately.
- [orthogonal_decomp.py](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/models/decoupling/orthogonal_decomp.py)
  removes projection onto a QR basis of macro projection weights. Orthogonality
  does not imply independence: (X,0) and (0,X) are orthogonal yet share X. This
  logical limitation does not refute empirical detection performance.
- [default.yaml](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/configs/default.yaml)
  specifies 32 frames, 224 pixels, one training/three evaluation segments and
  fps_target null. Actual-lag matching is not established. trainer.train() runs
  stages 1 and 2; a legacy class name or extra config cannot establish stage 3.
- [Checkpoint README](https://github.com/Litsay/RIFT/blob/5c36debef9c7f5f20c655078414b87340514f1df/checkpoints/README.md)
  says pretrained weights await acceptance. Expected filenames are not verified
  downloadable checkpoints. No training or checkpoint evaluation occurred.

Our difference must exceed semantic/residual fusion or generic relational
discrepancy. Future comparison needs grouped inputs, a declared NLL-mask choice,
deterministic evaluation randomness and separate native/matched reports.

## 4. Additional forensic neighbors

### MAST

[MAST v2](https://arxiv.org/html/2605.05895v2), Sections 4–5, combines sigmoid-thresholded
pixel residuals and frozen X-CLIP patch displacement/curvature with channel-wise
LIF integration. Its objective adds auxiliary BCE and supervised contrastive loss.
GenVideo training uses Kinetics/Pika and tests ten unseen generators; IvyFake uses
three training and nine unseen test generators. Appendix E.3 explicitly identifies
SEINE 8-fps versus Youku 24-fps shortcut risk. We cannot claim earlier work
universally ignores FPS confounds. No author repository/version was verified in
this pass; availability remains unresolved, not proven absent.

Project implication: SNN, temporal differences and semantic fusion alone are
insufficient differentiation. Replacing X-CLIP with framewise DINO changes temporal
context and is an adaptation. Paper tables mixing cited and author-run results
are not our matched comparison.

### WaveRep

[Paper](https://arxiv.org/html/2506.16802), Section 3.2, combines VAE-reconstructed
real videos with wavelet replacement while preserving diagnostic diagonal bands.
It provides an augmentation alternative to our local mechanism. Its single-
training-generator transfer protocol differs from our grouped setting.

Pinned [augmentation](https://github.com/grip-unina/WaveRep-SyntheticVideoDetection/blob/0fd6010759c14b572b7842a28fa9f85fe1ddd2fd/augmentation/pytorch_wt.py)
defaults to separable Haar, three levels, independent probability tests for
replacing baseband and axis-aligned bands from paired real input. Unrelated
replacement inputs would change the method.
The [demo](https://github.com/grip-unina/WaveRep-SyntheticVideoDetection/blob/0fd6010759c14b572b7842a28fa9f85fe1ddd2fd/demo/main_avideo.py)
uses DINOv2 with registers and 504-pixel cropping, averaging frame logits before
sigmoid; this differs from our 224-pixel patch head. Augmentation/demo/test-data
instructions do not certify complete training reproduction or checkpoint integrity.
Matched augmentation precedes feature extraction and may invalidate old caches.

### G2VD

[G2VD v2](https://arxiv.org/html/2607.04607v2), Eq. (15–16), combines a two-branch
objective with HSIC, and VAE reconstruction with frequency/pixel alignment.
Its causal interpretation depends on assumptions; an intervention name or small
dependence penalty does not establish identification.

Pinned [HSIC code](https://github.com/DMOSCAR-98/G2VD/blob/ffddba72de900c10d3b40648ad3ed5b2fd340818/loss_functions/independence_loss.py)
uses RBF kernels, median bandwidths, zero diagonals and the unbiased-estimator
formula, then clamps negative values to zero; batches <=3 return zero. The
clipped finite-sample output should not be called strictly unbiased.
The [training template](https://github.com/DMOSCAR-98/G2VD/blob/ffddba72de900c10d3b40648ad3ed5b2fd340818/configs/templates/train_g2vd_clip.yaml)
sets 8 frames/2-second clips with placeholder train/validation metadata paths.
The loader uses RandomClipSampler and UniformTemporalSubsample.
[DATA.md](https://github.com/DMOSCAR-98/G2VD/blob/ffddba72de900c10d3b40648ad3ed5b2fd340818/DATA.md)
lists GenVidBench, GenVideo, GVD and GVF metadata families; exact paper split
manifests and ancestry remain unverified. No VAE/model downloaded or equivalence
to our frozen-backbone compute budget established.

### STALL

[STALL](https://arxiv.org/html/2603.15026), Algorithm 1/Section 4, fits spatial and
normalized-transition whitening on real videos, then combines percentile scores
of maximum spatial and minimum temporal likelihood. Real calibration is required
despite no synthetic supervision. A DINOv2 adaptation differs from native DINOv3.

Pinned [stall.py](https://github.com/OmerBenHayun/STALL/blob/bfcc603ae83b4e609681277b9b5e80e7a9497e15/src/stall.py)
uses DINOv3 ViT-L/16 at 224 pixels, higher-is-real scores, and +infinity for zero
transitions before temporal min. For all-zero transitions and finite calibration
scores, final_score=(spatial_percentile+1)/2: ranking becomes spatial-only but the
number is not the raw spatial percentile.
[create_params.py](https://github.com/OmerBenHayun/STALL/blob/bfcc603ae83b4e609681277b9b5e80e7a9497e15/src/create_params.py)
fits spatial whitening on one random frame per real video and temporal whitening
on all normalized differences. That builder does not filter zeros as inference
does. Its directory workflow downsamples to 8 fps and selects a window. Native
PTS and calibration/test ancestor isolation still need project checks.
Calibration reuse does not authorize overlap with test videos.

### VidAudit

[VidAudit](https://arxiv.org/html/2606.31004) frames controls around canonical
processing, leakage, real-vs-real separation, matched evaluation, uncertainty and
cross-dataset transfer. This audit precedent does not imply our gates passed.

Pinned [canonical.py](https://github.com/KurbanIntelligenceLab/vidaudit/blob/9c8775f4a94529405db271e18d383381128ad294/vidaudit/data/canonical.py)
defaults to H.264, CRF23, GOP12, 8 fps and 512x512 bilinear scaling. Canonical output
FPS does not certify original timestamp equivalence.
[protocol.py](https://github.com/KurbanIntelligenceLab/vidaudit/blob/9c8775f4a94529405db271e18d383381128ad294/vidaudit/audit/protocol.py)
uses seeded 80/20 per-generator splits and a shared real split, excluding the
held generator from OOD fitting; these functions do not implement our ancestor
grouping. Generator-AUC bootstrap and held-out ROC operating points differ from
our ancestor-paired intervals and thresholds frozen on separate calibration.
Supply explicit feature allowlists: its metadata exclusion list need not cover
our new numeric metadata fields. No leaderboard scores are imported here.

## 5. Distinctive hypothesis and remaining gates

The hypothesis is transferable incremental information in
mean_k JS(P_ac, P_ab Pi_rk P_bc) - JS(P_ac, P_ab P_bc) on frozen local features,
after matched sampling, static, capacity, augmentation and support controls.
This is neither an established novelty claim nor demonstrated temporal mechanism.
Graph transitions, products, JS, cycles, static controls and fusion are inherited
tools. Our own static input already yields nonzero response.

Prioritize direct error, simple cycles, static responses (uniform and proposed
graph-weighted), ordinary patch pooling, entropy/support probes and matched
WaveRep augmentation. Do not choose the weakest comparator after results.
Response maps alone do not validate forgery localization.

Formulas and selected code/protocol paths now have traceable evidence. MAST code,
exact G2VD paper split manifests, checkpoint identities and execution-based
reproductions remain unresolved. Ask the planner to review this bounded literature
deliverable separately from reproduction and mechanism gates. No gate is self-
approved; no CCF-A readiness or breakthrough follows from this review.
