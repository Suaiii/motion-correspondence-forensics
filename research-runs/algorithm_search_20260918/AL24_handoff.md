# AL24交接：抽象匹配与标量凸目标参考通过

包cc-al20-al24-baseline-matching-20260919；子任务AL24，与AL20独立。
工作树 `D:/SUAI/codex/worktree/662f/脉冲神经网络`，分支 `codex/al20-al24-baseline-matching`。
冻结提交bef69a4先于首次匹配/目标求值；结果提交见包交接消息。
执行完成，建议按matching_and_objective_reference_software审查，无创新或真实检测通过结论。

## 实际结果

G1按最大基数选交叉对，基数2/费用5/16；G2选对角费用0；G3完整保留两个费用0平局，字典序选对角。
G4无可行边且no_training_support；空表求解w/value均None，不与非空零差分的解析w=0混同。
重复ID与nonfinite b两种输入错误按合同拒绝，未新增图或随机例。

固定q=(3,1)/(2,0)给M1差分[1,1]、M2差分[3,−1]；M1绑定G3实际选择，M2仅为预定未选中平局。
lambda保持1e-3，w=1处梯度分别−.2669414214、+.2963904795。
只沿首坐标求解：M1 t≈4.6651204124、M2 t≈.4530260127，均45次二分，落在预定(1,10)/(0,1)。
最终计算梯度残差约4.47e-15/9.51e-14，浮点括区宽约9.09e-13；没有有效exp/导数舍入界，因此不是严格优化证书。
零差分的最优0由解析性质单列；没有做真实检测器或通用四维拟合，没有来源概率或分类性能。

6次匹配入口、4次标量求解入口、100次值/梯度/Hessian联合求值，模型/probe调用0。
纯stdlib，每数值池最多2worker且两池不并发；本次每池实见1worker。
wall .151062秒/CPU .046875秒，最大描述子容器估计1384字节（非RSS）。实际每侧2，硬限制4；b维12/q维4。

## 产物与摘要

源码or1_matching_reference/{matching.py,objective.py,config.json,freeze.py,run.py}。
AL24_protocol.md、AL24_inputs.json、AL24_freeze.json、AL24_evidence.json、AL24_report.md、本报告与artifact manifest。

| 对象 | SHA256 |
|---|---|
| matching.py | 46da2dc7c5c55bfe54a9b715686766d6e4ade4c0af0edc99fd486e9c03997acc |
| objective.py | fe996ce1417b09b870b1998e02f041e8b8a6bf5844a2329919f218ccf0f55ecc |
| 实际输入/预期 | ad83c543ac4b0a40004ca533dc90e1b0d036aea0026eff9abd9a8a2d325a16a0 |
| 全部结果 | f5268ff4ff5be16d7e1e1dab064c157a62f64f73e68232361b008ca842578b57 |

原or1_cpu/or1_numerics及历史结果不改，执行前后摘要相同。主DAG只读，无遗留进程。
没有模型/权重/滤波/媒体/SSH/服务器/GPU、正式训练或预算动作。
完整四维/真实标准化/祖先匹配仍pending；解存在和唯一都不证明算法创新或来源泛化。

建议下一步先冻结完整比较中的匹配表与正则度量，再考虑经单独授权的四维/大规模实现与本小参考比对。
不得用M2替换G3选中结果，也不把ID重命名带来的配对变化当独立种子。所有科学与资源门槛保持。
