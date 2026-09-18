# AL27 handoff — completed execution, failed software gate

Dispatch: `cc-al27-multidimensional-head-20260919`, task AL27 only.
Research task: `01a0b54a-3a46-72c0-9f2c-58bdb49c6424`.
Worktree: `D:/SUAI/codex/worktree/662f/脉冲神经网络`.
Branch: `codex/al27-multidimensional-head`.
Freeze commit: `dc78269` (all source/actual inputs/config/protocol/freeze receipt committed before numerical work).
Final result commit is supplied with the one substantive planner message, avoiding a self-referential hash.

建议状态：execution=done，gate_result=fail。69项检查中68项通过；满秩自由头达到预定梯度L2停止阈值9.867353717817214e-11 <=1e-10后，仍与独立标量根相差3.158438133255004e-8，未达到预定坐标容差1e-9。目标差仅5.551115123125783e-17不改变失败。保留原结果，没有追加Newton步、修改阈值或重跑。本次包已结束，无后台进程。

三个固定面板的Fraction秩、初始梯度零性、192项逐组Gram条件、子空间目标恒等、空/非有限边界均符合预期。对齐面板自由解与Tw相等；满秩候选唯一零最优、自由目标更小；对称面板均零最优。全部仅仅是人工凸目标软件控制，不能宣称检测增益、OR1真实否证或创新通过。

实际6个有效头、2个空头、2个输入拒绝；16次线性求解，26次目标求值，2个标量参考共106次导数求值；原生线程2、最大数组1152字节、批次墙钟0.21897秒。无probe/readout/model/media/真实训练/SSH/GPU，无Torch/SciPy Python调用。冻结源、选定依赖及92项历史文件前后不变。

交付：AL27_protocol.md、AL27_inputs.json、AL27_config.json、AL27_freeze.json、AL27_started.json、AL27_evidence.json、AL27_report.md、本交接、AL27_artifact_manifest.json；源目录or1_head_reference含freeze.py/independent.py/objective.py/run.py。完整向量、Hessian和调用轨迹在evidence内。DEVLOG追加当前失败说明。清单包含交付摘要，不包含自身摘要；最终commit在消息中标识。

规划端下一步仅审查失败及协议精度关系。如需进一步数值执行，应另定冻结工作单；不通过事后放宽坐标容差或仅修改最大迭代数覆盖失败。主工作区/DAG未修改，未执行或等待AL29；继续保留原始z坐标。依赖软件成功的支路不应因execution=done而自动释放。科学/资源/最终确认门槛全部保持。
