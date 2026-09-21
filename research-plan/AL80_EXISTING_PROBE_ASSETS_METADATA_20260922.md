# AL80：现有服务器重建探针资产清单

planagent只读资产审查，独立于AL79的软件结果及AL36的算法准入。用户2026-09-22已恢复工作并明确计费由其负责；不反复索要账单，未知用量不写零，不另租/充值/扩容。

## 要解决的唯一依赖

AL35/AL75指出尚未绑定R_a/R_b。以现有13340实例为唯一目标，只确认项目是否已经存在可识别的自动编码器配置/权重缓存和wrapper源码，以决定下一次模型兼容性工作需要补什么，避免再次写“wrapper pending”泛化清单。

## 读取边界

- 从server_connection.json读取端点与现有密钥路径。仅公开project/cache/release目录；不读凭据、环境变量、token或其他用户项目。
- 一个只读SSH包，10分钟以内，目录深度<=6；列出cvpr27/cache、releases、environment下与vae/autoencoder/Wan/CogVideo有关的文件路径/大小和最多10个公开模型config JSON（每个<=64KiB，合计<=256KiB）。若目标目录缺失记录，不改目录；不遍历其他用户目录。
- 权重仅stat路径和字节大小，不加载、不遍读大型权重哈希、不下载；repo/revision/LFS标识若已有小型公开索引可记录，并明确它不等于本次权重字节校验。
- wrapper只查看已有文本至多5份、每份<=64KiB；记录身份、shape/缩放/缓存接口，既有DINO权重不能当成AE权重。字段不足记unknown，不依据文件名假定可运行。
- 输出仅路径、size、config/schema/文本SHA、缺口和适用性结论。禁止读取媒体、运行ffprobe、import torch/模型、启动GPU、安装依赖、网络下载或更改服务器文件。

交付reviews/AL80_EXISTING_PROBE_ASSETS_REVIEW_20260922.md与AL80_ASSET_RECEIPT_20260922.json。该资产表不释放真实模型或机制实验；后续须另冻结探针身份、wrapper、具体输入和profile范围。与AL68的媒体时间核验、AL36的不同执行者审查分别推进，不重复派发失败窗口。
