# AL74：上游文件身份与负类标签语义

- 实际完成：2026-09-22T03:37:46+08:00
- 执行者：planagent；公开主文/仓库/数据卡审查，没有读取test内容、媒体、模型、权重、服务器或GPU。
- 来源记录：`AL74_SOURCE_RECORD_20260922.json`，当前 SHA256 `c6040a09118c869ff94ca119a779c4e97957823a808d95fe727b3b30ab20d72b`。

## AIGVDBench的真实/生成定义

AIGVDBench v1（arXiv:2601.11035v1）在数据统计中区分生成方法与 real-video comparison pool。对每个开放生成模型，论文描述20,000条生成视频，按14,000/3,000/3,000划分；同时加入20,000条“real videos”，每条与生成视频基于同一 prompt 配对并采用相同划分。对闭源模型，论文描述每个2,000条生成测试视频，并从完整 real-video test set 的前2,000条形成匹配 real test set。

这一定义足以支持“公开基准中的生成视频与比较视频”的黑盒检测评测；`same prompt` 只说明条件内容配对，不能说明同一视觉祖先、同一拍摄设备或同一真实事件。公开文献没有把 AIGVDBench 的 real 标签定义为逐样本摄像来源证明。

论文还明确写到用 OpenVid-HD 作为 real-video source 来做 prompt 平衡。OpenVid-1M v3 的原文说明集合来自 ChronoMagic、CelebVHQ、Open-Sora-plan 与 Panda 子集，并进行美学、相邻帧一致性、光流、清晰度和切镜头筛选。它是多上游、经过选择的 in-the-wild 视频池；它的集合身份不能自动升级为逐条 camera-origin 证明。

## 许可与发布边界

AIGVDBench论文页标注 CC BY 4.0，Hugging Face 数据页也显示 cc-by-4.0；这些属于 benchmark/release 层信息。它们不能替代每个 OpenVid 上游视频、caption、切段和再分发范围的逐样本许可审计。OpenVid论文页的 arXiv perpetual non-exclusive license 是论文发布许可，不能直接作为视频媒体许可。

## 对本项目的影响

1. 公开基准轨道可以按作者 train/val/test 和 Video_id 组织黑盒评测，结果表述应写成“对 AIGVDBench 的 benchmark real/fake labels”。
2. 机制轨道若把负类称为 camera-origin 或把 real/fake 差异归因于生成器过程，必须补充祖先、来源、原生时间、标签凭据、处理链和许可证据。
3. `same prompt`、OpenVid-HD 名称、文件名 root 或作者的 real 字样都不能单独承担摄像来源标签；AL72 的446个候选root风险仍未被作者公开映射解释。
4. 闭源模型的 checkpoint/VAE/seed未知不必然阻止黑盒评测，但必须在限制中保留；若主张 decoder机制，则该内部信息是机制合同的一部分。

## 结论

AL74：**done / pass（上游身份与标签语义审查范围）**。公开基准的 label 语义可以支持受限可比评测，不能支持当前 OR1 的摄像来源因果解释或最终确认。AL68 的原生 PTS 核验、AL36 的不同执行者反方审查以及正式数据 gate 保持独立。
