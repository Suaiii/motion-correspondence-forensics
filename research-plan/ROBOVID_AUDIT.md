# RoboVid-SM v02 可复用性审计

审计日期：2026-09-06。资产根目录：`E:\AAGenvid`。本审计为只读检查，没有改动数据、旧代码与旧结果。

## 可以复用的资产

- `Dataset/RoboVid-SM/v02/splits`：1600/200/200 对 train/val/test，真假文件均存在。
- `splits_ffmpeg*`：单因素、复合因素和多阶段 FFmpeg 版本，可作为受控干预素材。
- `splits_osn_wechat`、`splits_osn_whatsapp`：各 400 条 test-only 代理输出。
- `main/reports/robovid_sm_v02`：ReStraV、D3、DeepfakeBench、PwTF 的逐视频预测和汇总。
- `main/OSN`：图像 OSN 模型、视频封装、3D U-Net 去噪原型与若干权重。
- DINOv2 与 X-CLIP 本地缓存，以及 ReStraV、D3、PwTF 等外部仓库。

这些资产适合做 pilot、复现和退化机制研究。它们不适合作为 CCF-A 算法论文的唯一训练或主测试证据。

## 不能继承的结论

### 1. v02 不支持严格跨生成器结论

清单有 2000 对唯一真假视频，但全部为随机配对；`semantic_score` 被统一写为 1.0，不能解释为语义匹配分数。假视频分布为：

| Split | t2vz | OpenSora | OpenAI Sora |
|---|---:|---:|---:|
| train | 800 | 794 | 6 |
| val | 104 | 95 | 1 |
| test | 99 | 101 | 0 |

测试集只有 t2vz 与 OpenSora，且两者也出现在训练集；真实视频仅来自 Vript。现有划分只能研究同源分类及同视频退化，不能证明未知生成器或跨真实来源泛化。

### 2. ReStraV 评测存在视频身份重叠

`restrav_features_clean.npz` 来自 clean test 目录的 400 条视频。`restrav_train.py` 在这 400 条上再做 50/50 切分：200 条训练，200 条内部测试。后续 cross-domain 脚本却对退化 test 目录的全部 400 条视频评测，因此其中 200 条与 clean 训练视频具有相同身份。

用保存的 clean held-out 身份筛选退化预测，得到以下阈值无关 AUROC：

| 条件 | 原 400 条 AUROC | 仅身份 held-out 200 条 AUROC |
|---|---:|---:|
| OSN Proxy WeChat | 0.9894 | 0.9850 |
| OSN Proxy WhatsApp | 0.9901 | 0.9846 |
| Light Re-encode / wechat_l2 | 0.8304 | 0.8077 |
| Codec Pure | 0.9889 | 0.9795 |
| Geo Only | 0.5442 | 0.5319 |
| Geometric Reformat | 0.1687 | 0.1854 |

这些数值仍有机制参考价值，但不能替代从 train 训练、val 定阈值、test 一次评测的协议。

### 3. 汇总数值与预测文件不能完全闭合

当前 `restrav_clean/best_tau.npy` 为 0.46。用它重算 `codec_only` 预测文件得到 Accuracy 0.605，而对应 summary 和 baseline 表为 0.675。说明模型、阈值或产物在不同运行间被覆盖，汇总文件没有完整绑定 checkpoint hash、threshold、feature hash 与代码版本。

因此，本审计只把逐视频概率用于 AUROC 复核；阈值指标需重新运行统一协议。

### 4. 退化命名混合了多个因素

- `wechat_l2` 同时包含缩放、fps=25、Gaussian noise alls=6 和 H.264 1000k，不能称 Codec-Only。
- `geo_only` 仍包含 fps 变化、light noise 和重新编码，不能称几何单因素。
- 真正接近 codec 单因素的是 `codec_pure`。
- `noise=...:allf=t` 产生逐时间变化的合成噪声。它适合压力测试，但不能直接代表平台转码噪声。

`ablation_2x2x2` 的单因素定义更清楚，应优先于旧 condition 名称；仍需补充变换顺序和连续强度扫描。

### 5. OSN Proxy 的溯源信息不足

WeChat 与 WhatsApp 配置文件除平台字符串外参数相同，`weights_path` 均为 null；磁盘上存在不同平台权重，两个输出集合也不相同，但 `osn_manifest.csv` 没有记录实际权重路径、权重 SHA256、代码版本和完整命令。因此现有视频可以用于探索，正式实验应重新生成或补齐可验证 provenance。

当前实际平台样本目录只有：WeChat real=10/fake=9，WhatsApp real=10/fake=9；配对表中真实平台有效配对各为 9。它们只适合小规模外部核验，不能支撑“200 对真实平台传输”的表述。

## 处理决定

2026-09-07 补充：按 `vript_clip_id` 去除 `-Scene-NNN` 后缀得到原视频前缀代理，train/test 共享 113 个前缀，test real 中 140/200 条片段具有 train 中出现过的前缀。独立文件并不保证独立源视频；这属于待原始元数据与内容检查确认的来源重叠。脚本及输入哈希记录见 `scripts/audit_source_groups.py` 与 `artifacts/source_group_audit.json`。

此前“说明产物被覆盖”的措辞过强：目前证实的是保存阈值、预测和汇总不能闭合，具体原因尚未确认。此前平台样本数量仅是已检查目录中的存量，不足以断言历史上从未有其他传输样本。

1. 旧论文只保留三个研究线索：传播退化值得研究、几何重排可能制造捷径、逐时间变化噪声会显著改变时序特征。
2. RoboVid-SM v02 降级为 pilot 和退化干预库。
3. 新算法必须在重新构建的 v03 / 公共 benchmark 上训练和评测。
4. 旧汇总表不进入新论文主表；需要时仅作为历史记录，并明确原协议缺陷。
5. 审计脚本位于 `scripts/audit_robovid.py`，可重复输出数据分布和 held-out AUROC。
