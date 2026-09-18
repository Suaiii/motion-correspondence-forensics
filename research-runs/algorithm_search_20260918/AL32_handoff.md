# AL32 handoff — stable coordinates, six fixed points, no optimizer

Dispatch `cc-al32-stable-baseline-integration-20260919`; task AL32 only.
Worktree `D:/SUAI/codex/worktree/662f/脉冲神经网络`.
Branch `codex/al32-stable-baseline-integration`.
Freeze commit `0685fbf`; final result commit supplied in the substantive planner message.

建议execution=done、gate_result=pass，仅`stable_readout_metric_integration_reference`。一次冻结批次85项检查通过，无失败、无重跑。AL27原fail、AL25近抵消原记录及AL30回归身份保持。未修改旧源码/输入/报告或主DAG。

第一部分仅AL25归档positive_inner/negative_inner/near_cancellation，12个r_K直接复用原q、float.hex一致。s_H明确为已存Hda+Hdb，24次新float mean计算r_S/r_J，未调用旧readout/probe或重新滤波。原raw z/compact、负C、稳定r、字段符号、M重构/逆重构差全部保留。近抵消identity稳定r_K=1.3877787807807517e-17，原compact=0不变。固定w通过同一四项评分函数逐场hex一致；三个泛用12维dot此次差也为0，但不宣称任意归约bitwise一致。

第二部分独立使用AL30原三个known_regression面板，不含scale；各gamma=0/预定嵌入w两个固定点。Fraction核对坐标/度量/行与margin/惩罚；六点beta/gamma目标差均0，梯度映射最大差1.3877787807814457e-17，Hessian最大差6.938893903907228e-18，正则差0，均满足1e-12。嵌入惩罚精确21/4000=lambda||w||²；诱导BB^T正则保留，没有各向同性替换。两部分未拼成来源数据。

完整计数在evidence/report：12次场相加、24乘积/mean/归一化、12literal复用；6四项评分、3泛用dot、24场矩阵重构；9面板坐标乘法、6参数/6梯度/12Hessian映射；12固定目标求值内部60矩阵/dot与12数据mean；12精确字段参考、3精确面板参考。优化器/旧readout/滤波/probe/AE均0。新代码仅NumPy/stdlib，2线程、最大数组1152B，墙钟0.38995秒，RSS未测；无模型/权重/媒体/真实训练/概率/AUROC/Torch/SciPy Python/SSH/服务器/GPU，未执行或等待AL33。

交付AL32_protocol/inputs/config/freeze/started/evidence/report/handoff及artifact manifest，新源目录or1_stable_baseline_reference。118项历史文件与5依赖前后摘要不变；完整向量/符号/目标分项/梯度/Hessian/映射误差与调用轨迹保存。DEVLOG仅追加本包记录。建议规划端独立审查后安排新工作；此包结束，无后台进程。真实AE误差unknown/null及科学/资源/最终集门槛保持。
