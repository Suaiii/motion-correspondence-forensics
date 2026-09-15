# 首轮本地神经训练 pilot

从历史120条开发样本开始，以预先固定的同一质量规则筛选；原有角色不变，不按预测结果替换样本。仅作工程训练与初步对照，不标记R03/E1或最终数据门槛完成。

三个从随机初始化训练的小模型：frame_mean（逐帧CNN均值）、raw_temporal（共同有效区域上的未对齐残差CNN+GRU）、aligned_temporal（对齐残差CNN+GRU）。两个时序模型参数相同，frame_mean容量不同。

严格顺序：tests → prepare → cache → train → evaluate → verify_results。prepare锁定代码、协议和输入清单；代码变化需使用新运行目录。缓存记录完整抽帧PTS和质量剔除；只有clean/fit参与优化，clean/calibration选择checkpoint与阈值。全部9个fit完成后才评估audit三种条件。遇到异常保留events.jsonl，不静默换样或更改分数方向。

入口均为 `E:\aNB\TECH\脉冲神经网络\research-runtime\enter.ps1`。每阶段示例：

```powershell
& '.\research-runtime\enter.ps1' -Script '.\experiments\neural_pilot_v1\run.py' train --run-dir 'E:\aNB\TECH\脉冲神经网络\research-runs\neural_pilot_v1'
```

CPU先生成3条件共同缓存，GPU训练20轮×3模型×3种子，训练预算30分钟。所有输出和缓存在E盘。无网络下载、无付费任务、未使用外部预训练骨干。检查点只保存state_dict，加载时weights_only=True。

若质量筛选后某角色某类不足5条，或解码PTS无效，则训练前失败并保留错误；若OOM/非有限损失则记录失败，调整后使用新的版本化运行目录。
