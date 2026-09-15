# 传播退化下的 AIGC 视频取证：研究方案与任务框架

> **2026-09-14 当前入口：[第二阶段计划](PHASE2_PLAN_2026-09-14.md)。** 启动审计已重算：内部融合增益 +0.05292；已查看外部池增益仅 +0.00340，区间跨零。类别/来源内训练与评估独立打乱仍有高分，原“同视频配对必要性”解释须降级。实际旧协议为 4 fps/8 帧/128 像素；新协议另轨验收。任务依赖已同步至 `task-hermes/project.json`，详见[审计报告](../research-runs/phase2_evidence_audit_20260914/report.md)。下方时间线保留历史，不代表当前完成状态。

> 2026-09-10 收尾：两份11.19 GB归档已于04:42下载并由下载器验收。六点关机没有实现；本次执行于10:38开始，约10:40执行关机，后续SSH复连被拒绝。新1000条QC与正式训练均未运行。详见[收尾报告](../research-runs/overnight_closeout_20260910/report.md)，此前“下载运行中”的记录保留为历史。

> 2026-09-10 最新：服务器已部署，用户要求提高资源使用和实验规模。实测12路预处理约为原串行预处理的6.2倍；小型残差网络采用batch64。机制集目标1.8万、训练目标4.8万、独立确认目标2万，五种子。详见[升级记录](CVPR2027_UPSCALE_20260910.md)。这些是新目标，正式数据仍在下载与验收阶段。

> 2026-09-10 当前执行入口：[CVPR 2027 服务器总计划](CVPR2027_MASTER_PLAN.md)与[可部署执行代码](../research-runtime/server/README.md)。已完成软件底座、合成端到端/续训验证、公开数据版本与清单审计；11项当前任务见`task-hermes/project.json`，原14项任务作为历史保留。用户已决定另租服务器，租用浏览器等待登录，远程profile和正式实验尚未开始。

> 2026-09-09：已完成595条视频、15次等参数训练及机械复核。正确对齐通过两项本地排假门槛，但mask探针AUROC=0.8035，独立来源复现仍未完成；新增局部补偿收益未证明更优。详见 [最新研究判定](ALIGNMENT_DECISION_2026-09-09.md)、[实验报告](../research-runs/alignment_gate_v1/report.md)、[复核结果](../research-runs/alignment_gate_v1/verification.json)。SNN继续低优先级。相关先例见 [检索记录](ALIGNMENT_PRIOR_ART_2026-09-09.md)。

> 2026-09-08 最新决定：[转向记录](PIVOT_DECISION_2026-09-08.md)。595条开发样本、12次等参数训练未通过顺序记忆门槛，已降低SNN/膜状态输运优先级；下一步检查对齐表示、插值/mask混杂与独立来源泛化。证据见 [门槛报告](../research-runs/order_gate_v1/gate_report.md)。旧SNN路线不再是默认实施方案。

> 2026-09-08：两版本地神经训练pilot已完成，共18次fit；发生过拟合后做了一次训练配方调整，未获得稳定改善。记录见 [神经训练检查点](../research-runs/neural_pilot_summary_2026-09-08.md)。这是开发训练结果，不表示强基线、SNN或最终泛化门槛完成。

> 首轮实际运行已完成：[M0 研究检查点](../research-runs/m0_metadata_v2/research_checkpoint.md)。研究全部使用 E 盘入口 `research-runtime/enter.ps1`；120条小样本揭示了帧率/尺寸捷径和重复抽帧混杂，尚未运行新SNN检测器训练。

> 当前入口：2026-09-07 [反方审查与修订研究计划](ADVERSARIAL_REVIEW_2026-09-07.md)。研究以本对话推进，`task-hermes/project.json` 是当前任务 DAG；`project_ccfa.json` 和旧版路线、图仅作设计历史。新增原视频来源前缀审计见 `artifacts/source_group_audit.json`。

> 2026-09-07 更新：已定位 `E:\AAGenvid` 的 RoboVid-SM 资产并完成协议审计。面向 CCF-A 的最新版路线见 [CCFA_VIDEO_ALGORITHM_ROADMAP.md](CCFA_VIDEO_ALGORITHM_ROADMAP.md)，审计证据见 [ROBOVID_AUDIT.md](ROBOVID_AUDIT.md)。下文保留第一轮方案作为设计演化记录。

检索日期：2026-09-06。这里交付的是文献地图、可检验的研究方案、实现接口与任务工具；没有运行视频模型训练，所有增益目标均为预注册候选标准。

## 研究判断

建议主线：**传播退化下的取证证据可靠性建模与自适应脉冲视频检测**。

你们的 Beyond Clean Pixels 提供 G/C/N 因子实验与“假视频被判为真”的失效现象；综述明确跨生成器泛化、传播鲁棒性、可解释性和效率目标。新研究应先判断哪些时间证据在退化后仍然可靠，再研究 SNN 是否比同条件 ANN 更适合保留这些证据。边界分支是待验证的候选机制。

本次检索最重要的变化是：DeMamba 已包含 degraded-video task；RA-Bench 已研究社交传播模拟；WaveRep 已用取证导向增强提升泛化。因此，不能将“首次考虑传播退化”“首次增强视频检测”作为贡献。可争取的贡献是**受控退化干预、证据可靠性估计与神经元动态调整之间的可验证联系**。本次并非系统综述，不能据此保证不存在相同方法。

## 1. 已有工作与相关论文

以下优先使用作者论文、会议官网和作者仓库。表中结果不做跨协议排名；预印本状态以本次核验为准，仓库公开不等于权重、数据或全量训练代码齐备。

| 工作 | 已有贡献与迁移价值 | 本项目中的位置 | 来源 / 代码状态 |
|---|---|---|---|
| Beyond Clean Pixels，团队已有论文 | RoboVid-SM V02；G/C/N 因子实验；干净训练、退化测试；噪声与几何交互 | 问题来源与旧协议复现 | [本地正文](../..//IEEE+DLCV-2026-RegistrationFiles/report.tex)；本次目录未发现训练代码和逐视频预测 |
| AIGC 安全防御综述，团队已有稿件 | 被动检测与主动防护；泛化、鲁棒、解释和开销 | 确定研究目标，文献汇总不能当作自研模型结果 | [本地稿件](../../综述撰写/report.tex) |
| ReStraV，NeurIPS 2025 | DINOv2 表征的曲率与距离统计 | 复现旧结果；固定统计量基线 | [作者机构页面](https://deepmind.google/research/publications/160567/) |
| D3，ICCV 2025 | 免训练二阶特征差分 | 时间变化基线；核查旧 AP 接近随机的原因 | [论文](https://arxiv.org/abs/2508.00701)、[官方代码](https://github.com/Zig-HS/D3) |
| DeMamba / GenVideo，2024 预印本起 | 时序 Mamba；跨生成器与退化评测 | ANN 时序基线与公开数据协议 | [论文](https://arxiv.org/abs/2405.19707)、[代码](https://github.com/chenhaoxing/DeMamba) |
| MAST，2026-05 预印本 | 六通道伪事件、通道 LIF 与冻结 X-CLIP | 核心 SNN 基线；本次未确认作者检测代码与权重 | [论文及附录](https://arxiv.org/html/2605.05895v1) |
| Spike-BRGNet，TCSVT 稿件 | 事件语义分割；细节、上下文、边界分支与 SMSCA | 迁移空间结构建模；不迁移交通场景结论 | [官方仓库](https://github.com/longxianlei/Spike-BRGNet-v1.0)、本地 TCSVT_Final_Version.pdf |
| WaveRep，NeurIPS 2025 | 用小波频带替换引导模型学习可泛化取证线索 | 必须纳入的强增强基线，防止把增强收益归因给 SNN | [论文](https://arxiv.org/abs/2506.16802)、[代码](https://github.com/grip-unina/WaveRep-SyntheticVideoDetection/)；仓库公告已发布增强代码 |
| NSG-VD，NeurIPS 2025 | 物理驱动时空建模与分布比较 | 不依赖同一类语义曲率的比较对象 | [官方仓库](https://github.com/ZSHsh98/NSG-VD)；资源需求单独评估 |
| Native-Scale Detection，ICLR 2026 | 可变空间分辨率、时间长度，减少预处理破坏 | 检查缩放和裁剪是否先破坏了边界证据 | [会议页面](https://proceedings.iclr.cc/paper_files/paper/2026/hash/20e45668fefa793bd9f2edf19be12c4b-Abstract-Conference.html)、[项目](https://github.com/mgiant/Qwen2.5ViT-AIGVDetection) |
| GenVidBench，2025 预印本起 | 跨来源、跨生成器视频数据 | 固定版本与 split；不能混用不同版本规模 | [论文](https://arxiv.org/abs/2501.11340)、[项目](https://genvidbench.github.io) |
| RRDataset，ICCV 2025 | 真实图像传播与重新数字化评测 | 迁移平台传输记录和样本配对方法；它是图像工作 | [会议论文](https://openaccess.thecvf.com/content/ICCV2025/papers/Li_Bridging_the_Gap_Between_Ideal_and_Real-world_Evaluation_Benchmarking_AI-Generated_ICCV_2025_paper.pdf) |
| VidAudit，2026-06 预印本 | 编码、泄漏、真实源辨别、匹配评测、多种子、跨数据集审计 | 排除时长、数据来源等捷径；借鉴控制方法 | [论文](https://arxiv.org/abs/2606.31004)、[代码](https://github.com/KurbanIntelligenceLab/vidaudit) |
| Detect Early, Escalate Rarely，2026-07 预印本 | 从压缩码流做流式筛查与按需升级 | 后续效率方向；当前不把模型扩成级联系统 | [论文](https://arxiv.org/abs/2607.19476) |
| RA-Bench，2026-08 预印本 | 真实危机场景锚定生成与 LastMile 传播模拟 | 最新外部压力测试；明确区分模拟与真实平台传输 | [论文](https://arxiv.org/html/2608.14391v1)、[官方仓库](https://github.com/24029100313/RA-Bench) |

优先复现：ReStraV、D3、MAST（如代码不可得则标记重实现）、WaveRep；再加入 DeMamba 或匹配参数 ANN。NSG-VD 与 Native-Scale 视资源作为扩展。不要再以未适配且 clean 表现较弱的图像检测器作为唯一主要对照。

## 2. 必须先修正的研究前提

1. **MAST 是外部论文，并非我们的已有成果。** 前序讨论第一次把它误当作已有工作，现已纠正。
2. **结果核对先于方法设计。** 旧稿正文称两个 OSN-Proxy 的 Acc 都保持 0.965，但表中为 0.843 / 0.876；传输成功数与 fidelity 表样本数也需对齐。以逐视频预测和成功传输 ID 重算，不能直接选一个数。
3. **AUC 下降不能仅归因阈值漂移。** AUC 是排序指标；0.997 到 0.169 表明排序严重变化或评测链路存在问题。检查真假标签、分数方向、样本顺序、checkpoint、预处理和源分组。不得按测试结果翻转分数以提高指标。
4. **三种边界须分开。** MAST 附录 G 的 BF/IF 使用 14×14 patch 的固定外圈；另有 Sobel 边缘重合统计。二者不等同于 Spike-BRGNet 的语义类别边界。竖屏 padding 恰好会改变画面边界，容易形成捷径。
5. **噪声不是平台传播的通用物理模型。** FFmpeg 配置和实际输出统计需复核；高斯噪声、压缩残差、时间相关噪声分别测试。RA-Bench 的 LastMile 也是模拟，不能替代真实上传下载证据。
6. **注意时间与状态。** X-CLIP 含跨帧上下文，完整 clip 编码不能称严格因果流式；LIF 每个独立视频重置。原始时间戳、采样间隔和重复帧需记录。
7. **图像平滑不保证取证提升。** 降噪可能同时消除伪造痕迹，必须比较 raw、降噪、双路残差，而非假设“更清晰就更可检测”。

## 3. Idea 融合：先提出能够失败的假设

| 假设 | 操作 | 支持证据 | 否证后怎么做 |
|---|---|---|---|
| H1：退化改变了各通道的判别可靠性 | 对同一视频逐级改变 G/C/N，记录分布、脉冲率和真假间距 | 可靠性变化与漏检关联，在新生成器复现 | 若只是输入或标签 bug，修基线；不提出新机制 |
| H2：结构边缘附近存在可保留时间证据 | 比较物体边缘、固定外圈、内部与等面积随机区域；控制 padding 与运动 | 物体边缘效应在配对退化与跨生成器下保留 | 若外圈有效而物体边缘无效，放弃 BA，查 padding 捷径 |
| H3：样本条件化 LIF 比固定 LIF 更稳定 | 相同输入、增强、参数预算，对比固定/可学习/条件化 LIF 与 ANN 门控 | 未见路径中增益，clean 代价可接受 | 若 ANN 同样或更好，采用 ANN；SNN 不作为预设结论 |
| H4：同视频配对训练有助于保留取证证据 | 只对训练视频生成 clean/degraded 配对，加入表征一致性 | 超过普通增强和 WaveRep 增强对照 | 若仅记住已见路径，删除或缩小一致性损失 |

推荐第一版仅有：**原 MAST 式输入 + 通道可靠性门控 + 有界条件化 LIF + 配对训练**。BA/SMSCA 仅在 H2 获得支持后加入；EvAF 留到训练稳定性消融，避免同时堆叠过多因素。

融合来源：团队工作提供退化干预；MAST 提供时间积分；Spike-BRGNet 提供结构边缘建模候选；WaveRep 提供取证增强对照；VidAudit 提供混杂控制。主动防护与水印留在后续独立课题，目前输出是检测证据图，未经像素标签验证不能称真实伪造定位。

## 4. 具体实现架构

[模型方案（Draw.io 可编辑源文件）](figures/model.drawio)

**数据接口。** `manifest.jsonl` 每行包含 `video_id, source_group_id, label, generator, real_source, split, path, sha256, original_fps, duration, width, height, transform_chain, parent_video_id`。真假语义配对 ID 与同一视频退化 parent ID 是两个字段，不能混为一谈。所有派生版本跟随源视频分组，禁止跨 split。

**输入。** 初版 `frames: [B,8,3,224,224]`，记录 `timestamps: [B,8]` 与 `valid_mask`；先使用统一采样复现，再做 8/16/32 帧敏感性。保留等比例缩放的有效区域 mask，padding 不参与统计。另设高分辨率分支实验，不与基础复现混用。

**证据。** 从 RGB 构造 HF/Sobel/AbsDiff/Diff2：`[B,T,4,H,W]`；从冻结 X-CLIP patch token 得到位移和曲率：`[B,T,2,14,14]`。无有效差分的起始帧设 mask，零位移处曲率做 epsilon 和有效性处理。先复现论文归一化，再单独消融鲁棒尺度归一化；逐帧归一化可能抹掉待分析的噪声幅度。

**可靠性估计。** 测试时仅由待测视频和可见元数据预测 `q`，不能读取真实退化标签或 clean 对应视频。训练时可用已知 G/C/N 作辅助标签。为每个通道输出 `r: [B,6]`，初版 clip 内共享，后续再考虑逐帧调整。可靠性应同时考虑判别能力与稳定性，不能仅仅奖励低方差。

**脉冲积分。** 建议用 `a= sigmoid(MLP(q))` 表示有界泄漏系数，`v_t=a*v_(t-1)+r*E_t`；正阈值用 `softplus`。若引入实际时间间隔，改用 `a_t=exp(-dt/tau)` 且 `tau>0`，并做固定时间间隔对照。训练以替代梯度反传，每个独立 clip 重置膜电位。初版参数范围由训练集与验证集确定，不能根据 test 调整。

**可选边界机制。** 在下采样至 14×14 之前提取结构特征，保留约 28×28 的局部分支，并经多尺度池化对齐融合。Sobel 仅提供结构先验，不等于伪造 mask。分支输出称 `evidence_map`；通过等面积随机遮挡对照、边缘/内部/外圈对照和变换对齐一致性评价，不能用 Sobel 命中率宣称定位准确率。

**读出。** 语义视频向量、SNN 时间统计和可选结构特征分别投影到统一维度后融合。保留仅语义、仅时间、融合三组分类头。`forward` 返回 `logit [B]、evidence_map、channel_weight、spike_rate、quality_pred`。EMA clean teacher 仅训练使用，部署端只有 degraded 输入。骨干蒸馏为后续独立效率实验。

候选目标函数：`L = L_cls + λ_aux L_aux + λ_pair L_pair + λ_q L_quality + λ_rate L_rate`。

`L_cls` 同时监督 clean/degraded 真假分类；`L_pair` 约束同源视图的取证表示，teacher stop-gradient，以分类损失防止常量坍缩；严重不可恢复退化可降低一致性权重，不能强行制造“保真证据”；`L_quality` 仅训练阶段使用退化标签；`L_rate` 限制过密/全静默。每一项分别消融。

拟实现代码模块：`data/manifest.py、data/transforms.py、models/residuals.py、models/quality_gate.py、models/conditional_lif.py、models/structure_branch.py、models/detector.py、train.py、evaluate.py、audit.py`。这些是接口设计，本交付尚未实现视频模型。

## 5. 评测协议与资源顺序

设 P0 为仅 clean 训练，复现旧协议；P1 为训练源上做已知退化增强，测试未见强度与未见组合；P2 同时留出生成器和退化路径；P3 做跨数据集与真实平台外部测试。P0 与 P1 必须分表，不能把增强训练称为 clean-only。

数据控制保留两条轨道：原始视频轨道用于观察真实信号；统一编码、时长和格式的审计轨道用于排除捷径。统一重编码本身也会破坏取证痕迹，不能把它当成无损处理。退化因子实验从相同起点执行，另测先后顺序和重复转码。

主指标：按生成器×路径宏平均 AUROC、最差组 AUROC、固定验证阈值的 Fake Recall / Real Recall、BAcc、ECE；报告逐视频分数、混淆矩阵、5 个种子（探索阶段可 3 个）和按源视频分组的 paired bootstrap。仅 200 条真实测试视频不适合稳定评价 0.1% FPR；若保留极低 FPR 指标须扩充独立真实集并报告区间。

效率报告同硬件同精度下端到端 p50/p95 延迟、吞吐、显存；计入解码、残差与语义骨干。SOP 能耗是估计值，不能等同墙上功耗。MAST 附录的约 69 倍是 gate 分支估计；按其全链路数值 1294.85 对 1379.22 mJ，仅约 6.1% 降幅。

资源路线：先 100–200 条配对视频做输入/统计诊断；再用可获得的公开训练子集验证原型，冻结语义骨干并缓存对应变换版本特征；最后扩展多种子与完整留出集。缓存 key 含输入哈希、变换顺序、采样配置、骨干 checkpoint 和代码版本。真实 GPU 配置、数据存放位置与训练时长尚待资产审计确认。

## 6. Goal–Milestone

[Goal 与验收里程碑（Draw.io 可编辑源文件）](figures/milestones.drawio)

总 Goal G0：在排除数据捷径后，验证可靠性建模是否改善未知生成器与未见传播路径下的检测，并确定 SNN 的实际准确率—开销权衡。

| Milestone | 依赖 | 产物 | 验收 / 决策 |
|---|---|---|---|
| M0 证据与数据审计 | 无 | 结果勘误、数据清单、split、官方代码/版本记录 | 对齐 OSN 数值、标签与分数方向；找不到原始资产则记录阻塞，不假报复现 |
| M1 共同协议基线 | M0 | ReStraV/D3/MAST/WaveRep 逐视频结果 | 原协议可解释复现；强增强与参数匹配对照齐备 |
| M2 机制验证 | M1 | 通道可靠性、三类边界、噪声扫描 | H1/H2 有受控证据；H2 失败则删除 BA |
| M3 最小方法 | M2 | 门控+LIF 原型、配对训练消融 | 相比相同增强基线取得增益，排除仅参数量或阈值贡献 |
| M4 双重泛化 | M3 | P2/P3、组别统计、外部测试 | 候选门槛：最差组 AUROC +3 个百分点，clean AUROC 损失≤1 点，配对差值区间支持改善 |
| M5 复现与论文证据 | M4 | 代码、锁定配置、manifest、延迟、失败案例 | 独立重跑结论一致；所有主张可追溯至预测和配置 |

数值门槛是项目目标，必须在看最终 test 前冻结；不是现有结果或发表保证。M2 无机制证据时转向评测/失效分析，M3 若普通增强或 ANN 更强则如实采用该结论。进度按 gate 推进，不在未知硬件与数据资产条件下承诺周数。

## 7. 研究框架选型与 task-hermes 复用

用户已说明由我们选择框架。建议采用 **Agent Laboratory 式研究阶段 + Hermes Kanban 式任务持久化 + 项目自定义证据验收**。

| 框架 | 核验到的用途 | 本次取舍 |
|---|---|---|
| [Agent Laboratory](https://agentlaboratory.github.io/) / [论文](https://arxiv.org/abs/2501.04227) | 从人类 idea 出发，文献、实验、报告，支持阶段反馈 | 作为研究工作流参考；复用阶段结构 |
| [AI Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) / [论文](https://arxiv.org/abs/2504.08066) | 自动科学发现、实验树搜索 | 后续有明确算力预算时借鉴；当前优先受控实验 |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | 持久任务板、依赖、角色、复核与产物交接 | 作为可选执行后端；当前实现本地任务与 payload 导出 |

[研究任务执行框架（Draw.io 可编辑源文件）](figures/task-framework.drawio)

本目录 `task-hermes` 是**本项目适配层名称**，不是声称找到一个同名的官方科学研究框架。它包含目标、milestone、task DAG、验收产物和只读导出器。实际 Hermes 安装、模型配置及 dispatcher 尚未接入或启动；本次不触发付费实验。

后续架构、工作流、时序与数据流图统一在 Draw.io 中以可编辑图元绘制，并保留 `.drawio` 源文件。投稿与 Word 插图由同一源文件导出 PNG/PDF；不再以脚本生成的 SVG 静态图作为交付版本。

Hermes 官方 Kanban 支持父任务完成后放行，以及 review 和持久附件。我们的 `hypothesis、acceptance、seed、split_hash、budget` 是研究扩展字段，放入任务正文/元数据，不假定属于 Hermes 原生 schema。[官方规范](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/user-guide/features/kanban.md)

角色是执行职责，不表示本次已启动多个 agent：研究负责人锁定假设；文献角色维护来源；数据角色控制 split；实现角色改模型；实验角色提交有界作业；复核角色检查证据。每次交接附 source、配置、代码版本、逐视频预测、检查结果与未解决问题。

本地用法：`python task-hermes/board.py validate` 校验 DAG；`python task-hermes/board.py next` 查看依赖放行任务；`python task-hermes/board.py export` 输出 Hermes 调用计划。使用实际环境 Python 运行。导出的 parent 是本地 ID，接入时必须先映射为 Hermes 返回 ID；文档明确标记 placeholder，不能直接当作远程 ID 调用。

`done` 需要所有依赖 done、必需产物存在且 SHA256 匹配、复核者与 verdict。工具只做机械证据检查，科研结论仍需审阅；非空文件不代表实验正确。失败结果同样是有效研究产物，只要说明否证与后续决策。

下一项可执行工作是 M0：定位真实数据、原始预测和模型 checkpoint，修复旧结果口径，再冻结 P0/P1/P2。文献与规划交付完成不代表这些研究 milestone 已完成。
