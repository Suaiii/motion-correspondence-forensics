# AL80：现有服务器重建探针资产元数据清单

- 实际只读核验：2026-09-22T07:25:27+08:00
- 端点：`connect.westc.seetacloud.com:13340`；服务器时间与本机相差约1秒，均保留原始回执。
- 回执：`AL80_ASSET_RECEIPT_20260922.json`，SHA256 `1f925be8d39c7e980bf243f71cc51b20cbd7896b4679f1bd55123d1bd15801fc`。
- 没有读取凭据、媒体帧或权重内容，没有加载模型、启动GPU、运行ffprobe或修改服务器。

## 发现

**没有找到可识别的 OR1 重建器资产。** 深度6的受限路径扫描没有发现命名为 `vae`、`autoencoder`、`recon`、`decoder`、CogVideo或Wan的AE配置/权重。唯一含Wan字符串的是一条已有MP4路径；它没有被打开。发现的权重仅包括 DINOv2 ViT-B/14、RAFT和旧 sampling pilot checkpoints，均不等于AE探针。

发布 v0.1.3 的小型配置说明的是传统/机制检测路径：

- `mechanism.json`：16帧、8 fps、2秒、3 seeds、机制bag arms；
- `mechanism_expanded.json`：5 seeds、同样16帧/8 fps、五个arms、目标库存和“无新数据结果”的前瞻说明；
- `baselines.json`：DINO、aligned residual bag，以及D3/ReStraV/WaveRep/RIFT的状态；没有 R_a/R_b 身份。

源码 `forensics/model.py` 定义 CNN `Bag` 与 `ResponseBag`；`operator_response.py` 的输入是 `[B,T,C,H,W]` 和 `[B,K,T,C,H,W]` 的 residual/correspondence controls。它是检测器/响应读出，不是 AL12 要求的两个固定公开自动编码器重建器。`pipeline.py` 是视频读取、抽取和训练流水线，不能由文件名推断有完整AE wrapper。

`source_manifest.json` 是代码/配置哈希表，不是探针权重或样本身份清单。

## 对 AL12/AL75 的裁决

AL12的真正合同要求固定两个公开重建器、h=1/8、四次完整E+D调用及完整中间结果。当前服务器资产只证明项目有DINO/RAFT/Bag/ResponseBag软件路径，不能填补 reconstructor identity、权重字节、encode/decode mode、缓存复位、颜色/范围/输出shape或四调用记录。AL75提出的 `ProbeBatch` adapter 仍是后续设计，不是现有资产。

因此：

- AL80：**done / pass（既有资产元数据范围）**；
- 正式数据门：保持 `not_evaluated`；
- OR1 innovation_admitted / real_experiments_authorized：保持 `false`；
- DINO/RAFT/Bag不能替代AE，也不能用历史机制配置声明OR1已经可运行。

## 需要的最小新增信息

要进入真正的兼容性批次，至少需另立任务冻结：R_a/R_b 的公开来源、commit/权重SHA、wrapper输入输出shape和dtype、缓存/随机状态重置、四次调用回执、失败码，以及授权样本的时间/祖先/label manifest。只有这些信息齐备，才可评估是否值得启动小型机制pilot；本清单不授权任何模型或GPU执行。
