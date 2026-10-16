# 2026-10-16 元数据捷径与 real-vs-real 对照（CPU，只读输入）

执行：Claude 会话，2026-10-16 22:50—23:30 北京时间。服务器 `connect.westc.seetacloud.com:53135`
（vGPU-48GB；13340 现拒绝现有 key，22647/43641 拒绝连接）。仅读 catalog/manifest/既有 DINO 特征；
输出只写入服务器新目录 `cvpr27/runs/claude_meta_probe_20261016/`（位于 `/root/autodl-tmp` 下）。无 GPU、无模型前向、无下载。

| 文件 | SHA-256 |
|---|---|
| `probe.py` | `eff8b0139509f600c248c2f9fb10574c0fc4d0859ddca3f9750ab1ab0309af82` |
| `real_vs_real.py` | `4546b1bc923693e94f411f267e37f1b223a186946c46c7c7fe53403b87a9b408` |
| `out/results.json` | `346058f7bd6955af8d3ed96a75fdec214b119065ed5d56408da867d5aa94abec` |
| `out/real_vs_real.json` | `377f85578ee4d4a2ed6b42c3d5d0af4efa11ebdc7cc74fc0281cd56471218cf0` |

## E1 仅元数据可分性

特征：fps、帧数、时长、宽、高、宽高比、像素数、文件大小、码率、time_base 分母。
HistGradientBoosting，5 折 StratifiedGroupKFold（组=clean_identity_group 或候选源视频 ID）。

| 数据池 | n (fake) | 全元数据 AUROC | 最强单特征 |
|---|---:|---:|---|
| RoboVid-SM clean（现训练池） | 4000 (2000) | 0.9996 | width 0.998，fps 0.997，frames 0.996 |
| AEGIS Hard Test（现外部测试） | 436 (218) | 0.9998 | duration 0.854 |
| AIGVDBench 扩展（Luma/Pika/Vidu vs OpenVid-HD） | 2999 (1500) | 1.0000 | width 0.992，pixels 0.984 |

## E2 冻结 DINOv2 特征上的 real-vs-real / fake-vs-fake 对照

既有 8×768 特征（224 resize 后）→ [帧均值, 帧间绝对差均值]，标准化 + LR(C=0.1)，
5 折 StratifiedGroupKFold（组=YouTube 前缀），3 个划分种子。

| 对照 | n | AUROC (mean±sd) |
|---|---:|---:|
| RoboVid 真实：原生 720p vs 其他 | 1989 | 0.538 ± 0.045 |
| RoboVid 真实：≥29 fps vs ≤25.5 fps | 1980 | 0.612 ± 0.002 |
| **AEGIS 真实：DVF vs YouTube** | 218 | **0.985 ± 0.001** |
| AEGIS 假：Kling vs Sora | 218 | 0.753 ± 0.014 |
| AEGIS 真 vs 假（池内 CV） | 436 | 0.958 ± 0.002 |

## 解释边界

- 元数据可分性说明这些池**允许**捷径，不证明某个像素检测器**使用了**捷径。
- 两个真实来源比真假更可分，说明 AEGIS 上的真假 AUROC 无法与“来源识别”区分；
  任何结论须报告分真实来源的 AUROC 与 real-vs-real 下限（VidAudit C3）。
- 帧率经 8 帧 DINO 特征有中等泄漏（0.61），分辨率经 224 resize 后在 Vript 内泄漏较弱（0.54，负类仅 53 条）。
- 已暴露开发数据上的描述性诊断，不是正式门结果。
