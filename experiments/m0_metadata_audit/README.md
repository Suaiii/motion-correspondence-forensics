# M0 元信息捷径实验

运行结果见 `E:\aNB\TECH\脉冲神经网络\research-runs\m0_metadata_v2`。当前脚本是 v2，拒绝覆盖已有选择/预测结果；重跑须使用新的 run-dir。

```powershell
$entry = 'E:\aNB\TECH\脉冲神经网络\research-runtime\enter.ps1'
$script = 'E:\aNB\TECH\脉冲神经网络\experiments\m0_metadata_audit\run.py'
$run = 'E:\aNB\TECH\脉冲神经网络\research-runs\m0_metadata_reproduction'
& $entry -Script $script prepare --run-dir $run
& $entry -Script $script probe --run-dir $run
```

若有平均哈希候选，先运行 review_candidates.py 导出证据并逐项复核，形成 candidate_decisions.json；判为重复或未复核则不运行 evaluate。具体字段可参照已运行版本；绝不复制 verdict 而忽略文件哈希变化。

```powershell
& $entry -Script $script evaluate --run-dir $run
& $entry -Script 'E:\aNB\TECH\脉冲神经网络\experiments\m0_metadata_audit\verify_outputs.py' --run-dir $run
```

模型只用元信息，读画面仅作质量检查。采样索引和直轨迹 null 是补充诊断，命令 sampling_probe.py 与 check_sampling_control.py 接受相同 --run-dir。它们不运行 DINOv2 或视频分类器。

测试：通过统一 E 盘入口运行 test_run.py（4项）与 research-code/test_sampling.py（6项）。
