# AL67：样本级数据权威性、时间与祖先合同审查

- 审查者：planagent；实际开始：2026-09-22T00:56:56+08:00
- 范围：只审查已有本地文献审查、计划合同、哈希记录，并对服务器已有 manifest 做只读字段盘点；未读取媒体帧、未下载新媒体、未运行模型/分类器/GPU。
- 目标：回答“文献综述、云服务器和算力是否已经足以支撑权威有效数据集”。

## 分级定义

- **verified**：当前材料绑定到样本级字段或可复算清单，另一复核者可以从记录重建判断。
- **partial**：论文/协议层面有总体说明，但缺少样本级映射、版本、哈希或证据链。
- **missing**：当前没有能支持正式实验的证据。
- `formal_data_gate` 只有在所有关键项 verified、祖先级 split 固定并完成独立复核后才可 pass。

## 当前证据矩阵

| 门槛 | 状态 | 当前能支持什么 | 仍缺什么 |
|---|---|---|---|
| 数据身份与发布 revision | partial | OpenVid-1M/OpenVidHD 论文身份、版本和规模可定位；AIGVDBench协议可定位 | AIGVDBench实际下载 revision、样本 manifest、项目使用的精确子集 |
| 上游来源与真实/生成标签 | partial | 多上游名单、AIGVDBench开放/闭源划分及同 prompt 描述 | 每条样本的原始来源、标签凭据、人工/作者标签与变更记录 |
| 祖先链与切段关系 | missing | 文献说明存在切镜头/多上游筛选 | 父文件/父片段 hash、切分区间、同祖先闭包和跨集合排除证明 |
| 原生时间字段 | missing | 论文的平均时长和训练抽帧配置可见 | 每个文件原生整数 PTS、time_base、解码顺序、切段映射；best-effort 或名义 FPS 不足 |
| 解码器、codec 与处理版本 | partial | AIGVDBench提到统一 H.264，OpenVid描述HD筛选 | 每条文件的 codec tag、decoder build、解码参数、处理脚本/版本 hash |
| 生成器与生成配置 | partial | 部分生成器和模型家族可从协议识别 | checkpoint/VAE/decoder hash、prompt、seed、条件、生成时间和失败/重生成记录 |
| 同祖先反事实/配对 | partial | 同 prompt 配对可作为协议线索 | 是否同内容、同 decoder、同 ancestor、传播前后链的样本级关系 |
| 传播链 | partial | 统一 H.264 与部分处理设置有总体描述 | 每条样本实际 codec/resize/crop/再编码顺序、参数与输出 hash |
| 许可和使用条件 | missing | 论文公开许可文字可定位 | 上游视频、caption、生成结果的训练/再分发授权，逐来源与版本的证据 |
| 祖先级 train/val/test split | missing | 论文给出总体划分比例/数量 | ancestor_id 不交集证明、共享 decoder/caption/prompt 的泄漏审计 |
| 选择/覆盖记录 | partial | OpenVid 的运动、相邻帧、清晰度、切镜头筛选已知 | 各上游保留率、过滤参数版本、缺失值规则和类条件选择比/共同支持 |
| 开发池与最终集隔离 | partial | 计划规定开发池冻结、最终集封存 | 当前库存和 hash ledger 尚未逐样本证明没有交叉或重命名 |

## 为什么现有“权威性”还不够

文献综述解决的是身份、方法和公开管线的可定位问题，服务器解决的是核验与运行能力；两者都不能替代样本级的来源、时间、祖先和许可证据。OpenVid正文说明多个上游，以及对相邻帧、光流、清晰度和运动范围的筛选；这些变量与局部时序候选的输入相关，构成需要测量的选择机制。AIGVDBench引用的 HD 小时数与 OpenVid 原文的统计口径不一致，且实际 revision/样本映射未知。仅凭“规模大、论文明确、算力足”不能把候选池称为正式权威集。

AL66已证明：即使按可见 $Z$ 匹配，若选择比 $a_1(q,z)/a_0(q,z)$ 随候选特征 $Q$ 变化，来源排序仍可被选择机制改变；零支持时总体甚至不可恢复。这里的结论约束实验合同，不能直接断言当前公开数据确实有该偏差。当前数据审计没有样本级选择率、共同支持或祖先闭包，所以正式机制结果仍不能解释为来源因果效应。

既有 196 条 HD-VG/CogVideo 回放和 100 条 MS/VC2 归档记录可以继续作为暴露开发与软件/协议检查，但它们已经进入开发历史，且不含本合同要求的完整样本级链路。不能把它们扩充、重命名或追加调参后当成最终确认集。

## 最小释放合同

正式实验前，每条样本必须有机器可读记录：

```text
sample_id, ancestor_id, role, source_label, label_provenance,
raw_file_sha256, parent_file_sha256, segment_start/end,
pts_integer[], time_base_num/den, decode_order, missing_time_flags,
codec_name/tag, decoder_build_hash, preprocessing_code_hash,
generator_family, checkpoint_hash, vae_hash, decoder_hash,
prompt_hash, seed, condition_hash, generation_record,
propagation_chain[], pair_id, pair_relation, split,
upstream_source, filter_pipeline_hash, inclusion/exclusion_reason,
licence_evidence, permission_scope, audit_status
```

释放前必须机械检查：`ancestor_id` 在 split 间不相交；每个时间字段可以由原文件与工具版本复算；标签、生成器和处理链都有来源证据；配对关系区分“同祖先”“同 prompt”“同 decoder”和“仅统计匹配”；选择/过滤保留率按源类和上游单独报告；缺失关键字段的样本自动排除或只进入候选池。

## 服务器现有 manifest 的只读核验

2026-09-22 01:00（北京时间）对 `connect.westc.seetacloud.com:13340` 上已有小型 manifest 做了只读盘点，收据为 `research-plan/reviews/SERVER_DATA_MANIFEST_INVENTORY_20260922.json`，SHA256 `e437177ead211aae4c39c35ebcde1db963a25c1fe988285f0104226f9b5015f2`。没有读取媒体内容，也没有改动服务器文件。

这次核验把判断从“只有论文层面的候选”收紧为“已有历史/开发 manifest，但正式数据门仍未封口”：

- `candidate200` 200 行、`combined_candidate130` 230 行、`mech4fps_manifest_fixed` 267 行和 `profile100` 100 行有 `sample_id`、文件 SHA256、来源/任务、label、source/reference/prompt group、`ancestry_status`、数据 revision 和 license 字段；但很多记录仍是 `ancestry_status=unknown` 或 `license=upstream-terms-pending`，没有原生 PTS/time_base、codec/decoder、prompt/seed、处理链或 split。
- `pair2_origin_audit_v1` 200 行和 `pair2_frozen_transfer_v2` 196 行已经保存 `origin_id`、作者来源/提示匹配、metadata lineage join、抽帧 PTS 和 timing error 等开发审计字段；两者均明确 `ancestry_content_verified=false`、`formal_training_released=false`、`role=external_development_only`，所以它们支持开发审计，不能释放正式训练。
- `real_manifest.jsonl` 只有 51 条基于绝对路径的语义匹配记录，含 query/source/clip id，但没有样本 SHA、原生时间、ancestor、许可和 split 字段。
- `cvpr27-server/source_manifest.json` 是代码文件哈希表，不是样本 manifest；不能用代码可复现性替代数据来源可追溯性。

因此，当前本地/服务器资产已经具备“可盘点的历史候选 manifest”这一层证据，判断比纯文献综述更强；关键缺口仍集中在时间原生性、祖先内容真实性、生成配置、逐样本许可和祖先级划分。`candidate200` 等文件中的 license 字段存在仅代表记录了状态字符串，`upstream-terms-pending` 不能视为许可通过。

## 结论与可执行后续

- **AL67 审查交付：done / pass（仅合同审查范围）。**
- **正式数据 gate：not_evaluated，当前不放行训练、校准或最终确认。**
- 当前实验基底的判断是：**文献、服务器和历史 manifest 足够继续做样本级核验，数据集的正式权威性和有效性仍不足以放行训练。** 最关键的补强顺序是：
  1. 锁定一个有可追溯原始祖先与许可的真实来源，并形成逐样本 manifest；
  2. 对候选生成器保存 checkpoint/VAE/decoder、prompt/seed 和输出哈希；
  3. 在服务器上对原生 PTS/time_base、解码器/codec 和传播链做一次可复算审计；
  4. 完成祖先级 split、共同支持和选择率报告，再仅用约 2000 条机制集做受控 pilot；
  5. 只有 pilot 通过静态、容量、增强、来源、采样和未见生成器门槛，才打开正式训练。

AL36 的 OR1 反方准入审查仍需不同执行者，不能用 AL67 或 AL66 的计划端审查充当独立复核。没有新算法准入，也没有阶段突破结论。
