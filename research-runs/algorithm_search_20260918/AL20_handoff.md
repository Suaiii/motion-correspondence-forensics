# AL20交接：有限响应紧凑基线合同成立

包cc-al20-al24-baseline-matching-20260919；子任务AL20；researchagent_next。
独立工作树 `D:/SUAI/codex/worktree/662f/脉冲神经网络`，分支 `codex/al20-al24-baseline-matching`。
输入/公式/三个trace ID在bef69a4提交前冻结，随后仅作归档读后审查；未调用core/probe或拟合。
工作单摘要7784b52940d94799926f867ea47ed01f5801be88455c7c6628a5fbb56dcfa3d3已核对。

## 结论与范围

有限h精确有K=d_a−d_b；同固定线性H、相同支持/mean尺度/分母下，q_l=A_l/D_l+B_l/D_l−2C_l/D_l。
四组三元组组成12维紧凑强基线，能精确包含候选四维读出。
它不是用于匹配的12维b，也不允许据此重新选择配对或修改旧方法。
不需要C²或h趋零；有限精度不同运算顺序不被说成bitwise相同。

独立核对T的block=(1,1,−2)^T，T^TT=6I。
同字面lambda时，指定beta=Tw嵌入的惩罚为候选6倍。新自由基线若事前用lambda/6=1/6000，
在该子空间与候选lambda=1/1000目标相同，故相同数据/配对/权重下最优训练目标不高于候选。
这不是测试泛化排序，也不说明所有相同训练预测参数均有该范数；原lambda未改、没有执行新lambda拟合。
固定重构0参数、约束读出4自由度、自由读出12自由度与完整端点模型都要明列，不能零padding假称等容量。

## 三条预定trace的实际精确核查

均为development_base/sample_0/h=0.125，完整ID在协议/回执：

| 族 | d_a | d_b | identity下mean(A,B,C) |
|---|---|---|---|
| linear_exact | (1/2,0) | (0,1/4) | (1/8,1/32,0) |
| nonlinear_remainder | (0,33/128) | (1/4,0) | (1089/32768,1/32,0) |
| noncommuting_but_redundant | (1/2,0) | (0,1/4) | (1/8,1/32,0) |

K、端点关系、能量与同分母重构全部精确一致。原q标量浮点舍入路径也复核一致。
归档float q减去确切binary输入所定义的有理表达约为8.35e-18、−9.37e-17、8.35e-18；
这些仅是显示差，没有被写成严格等于0或一般浮点误差认证。
第一与第三数值设置相同，三条内积C均为0；本次没有检验实际非零C trace，且没有另搜一条来补结果。
一般C项的必要性来自线性代数推导，不包装为这三条trace上的实测发现。

## 交付与下一步

AL20_method_baseline.md、AL20_protocol.md、AL20_freeze.json、AL20_trace_audit.json、本报告与artifact manifest；
分析脚本在or1_baseline_audit。原归档SHA256保持076ae934e740d72943ca2e9f1b9c5cda27ffd8ecc2611a7ca8b386e88646c3ec。
审查回执SHA256：994b7cb164b82a8e7fc6b80d9a498d37aa89bf50345d00b993a37d874a270fe2。
单线程stdlib/Fraction，约.1192771秒，低于2线程上限；真实四滤波未运行。
没有模型/媒体/服务器/GPU或训练；主DAG和旧产物不变，无未预期失败。

建议将固定/约束/自由紧凑基线及其正则度量纳入后续同数据对照合同，再判断OR1剩余贡献是否有实际价值。
不能仅凭函数包含就自动否定所有有限样本归纳作用，也不能再把弱单步压缩遗漏当新观察信息。
通过范围仅finite_response_baseline_contract；真实创新、数据/资源与最终集门槛不释放。
