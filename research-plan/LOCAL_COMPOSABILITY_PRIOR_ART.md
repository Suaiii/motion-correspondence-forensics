# Local composability: preliminary nearest-neighbor map

RS01 work-in-progress, checked 2026-09-17 for cc-round-1-20260917.
This pass verifies primary abstracts and author repositories. Full equations,
dataset ancestry, evaluation splits, code revisions and independent execution
still require review; RS01 is not submitted as a completed reproduction.

| Neighbor | Verified mechanism and protocol direction | Specific overlap/risk for our candidate | Source and code status |
|---|---|---|---|
| TimeCycle | Learns correspondences from unlabeled video using temporal cycle supervision, then transfers the representation to correspondence tasks. | Temporal composition/cycle consistency is established prior art. Our frozen-feature perturbation response needs evidence beyond a renamed consistency error. | [Paper](https://arxiv.org/abs/1903.07593), [author code](https://github.com/xiaolonw/TimeCycle). Training/testing code and a model link are advertised; not executed here. |
| RIFT | Combines semantic trajectory analysis, residual analysis and a cross-scale dependency component; its repository describes frozen DINO/RAFT precomputation and two-stage training. | DINO plus motion/residual fusion is insufficient differentiation. Compare against its relational modeling under controlled inputs; do not equate orthogonality with statistical independence. | [Paper](https://arxiv.org/abs/2609.00742), [author repository](https://github.com/Litsay/RIFT). Code paths inspected at README level; no checkpoint integrity or execution verified. |
| MAST | Uses multiple temporal residual channels with a spiking temporal branch and a frozen semantic encoder; abstract discusses cross-generator evaluation. | Temporal residuals, SNN integration and semantic fusion are already covered. Our distinguishing hypothesis must concern the controlled local correspondence response. | [Primary preprint v2](https://arxiv.org/abs/2605.05895v2). Repository not verified in this pass; no reproduction claim. |
| WaveRep | Uses wavelet-based forensic augmentation and evaluates transfer from a single training generator to other generators. | A gain caused by stronger augmentation would not establish the proposed correspondence mechanism. Use its augmentation as a matched-backbone control, separately from its author-native method. | [Author repository](https://github.com/grip-unina/WaveRep-SyntheticVideoDetection) exposes augmentation/demo/test-set entries; augmentation release is documented. No weights downloaded or results rerun here. |
| G2VD | Applies VAE reconstruction with frequency/pixel alignment and an HSIC-constrained two-branch classifier for domain robustness. | Calling an intervention causal is not differentiation or identification. Our permutation intervention must isolate a measurable local mechanism and survive simpler controls. | [Paper](https://arxiv.org/abs/2607.04607v2), [author code](https://github.com/DMOSCAR-98/G2VD). README describes three training stages and metadata/config templates; checkpoints are not stored in that repository. Not reproduced. |
| VidAudit | Audits preprocessing, duration leakage, real-vs-real separation, matched training, uncertainty and cross-dataset transfer, plus operational FPR metrics. | Shortcut discovery and a high AUC are insufficient contributions. Preserve source controls and calibrated operating points, not only generator-averaged AUC. | [Paper](https://arxiv.org/abs/2606.31004), [author toolkit](https://github.com/KurbanIntelligenceLab/vidaudit). Documentation inspected; its leaderboard is not our replication or a same-cohort comparison. |

## Current candidate difference is a hypothesis

An additional direct mathematical neighbor is
[Space-Time Correspondence as a Contrastive Random Walk, NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/e2ef524fbf3d9fe611d5a8e90fefdc9c-Abstract.html).
It treats patches as graph nodes, feature similarities as transition
probabilities and long-range correspondence as graph walks, with cycle-based
learning. Soft transition graphs and multi-step composition are therefore
already established. The overlap with `P_ab P_bc` is structural; exact
equation/code equivalence still needs review. The proposed forensic
perturbation response must earn an effect beyond this foundation.

Our proposed statistic compares `P_ac` with `P_ab P_bc`, then measures how
one-sided middle-index permutations change that discrepancy. The backbone is
frozen and the small head receives local responses plus global semantics.
The unresolved contribution would be an incremental, transferable temporal
signal beyond the same six frames processed as independent static triples,
ordinary patch aggregation, entropy and uncalibrated matching errors.

Two observations already limit the interpretation. Soft `P` need not satisfy
`P²=P`, so a static sequence can have nonzero response. Also, the existing
complete MS/VC2 PTS show incompatible short-triplet timing even under the
nominal six-frame/4-Hz recipe. Neither observation proves the candidate cannot
work; both prevent a mechanism claim without the corresponding controls.

## Review still required

Before RS01 acceptance, inspect the exact TimeCycle tracking operator, RIFT
dependency estimator and each method's split/sampling definitions; pin code
commits and audit checkpoint availability. Quantitative rankings in the
papers use different cohorts and estimands and are intentionally not copied
into a project comparison table. The project has not established an exhaustive
novelty search or a patentability conclusion.
