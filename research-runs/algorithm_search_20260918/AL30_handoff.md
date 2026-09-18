# AL30 handoff — one frozen recovery batch

Dispatch `cc-al30-accuracy-budgeted-stop-20260919`; task AL30 only.
Worktree `D:/SUAI/codex/worktree/662f/脉冲神经网络`.
Branch `codex/al30-accuracy-budgeted-stop`.
Freeze commit `1fa8bb8`; final result commit supplied in the single planner message.

建议执行done、门槛pass，范围仅`accuracy_budgeted_optimizer_reference`。94项检查通过，无失败、无重跑、无阈值调整；AL27仍done/fail且全部历史字节保留。新通过不追改旧失败，也不产生真实检测/科研创新结论。

唯一算法变化是`tau_stop=min(1e-10,2lambda*1e-9/2)`；候选精确1e-12，实际float1.0000000000000002e-12；自由精确1/(6e12)，实际float1.6666666666666667e-13。原objective.py字节一致，原z/配对/权重/正则/零初始化/200步/Armijo全部保留。未知梯度舍入界为null，严格参数认证false，原参数与目标1e-9验收未放宽。

三旧面板标known_regression，唯一新增full_rank_scale使用delta=1/8。满秩回归自由头自然到第5步，坐标差5.329070518200751e-15；新增尺度自由头4步，坐标差1.7763568394002505e-15。全部标量比较最大坐标差2.3092638912203256e-14、最大目标差5.551115123125783e-17。旧full_rank初始与前4步归档逐项等于新轨迹相应前缀；新规则在原终点尚不满足停止条件，无手工补步。Gram288项（回归192/新控制96）、秩/零梯度/空和非有限边界均符合预期。

实际12次输入尝试、10求解入口、8有效头、2空支持、2非有限拒绝，21次线性求解、35次完整目标求值、3个标量参考159次导数求值。所有接受步长1，未数值覆盖回溯/线性失败分支。原生线程2、最大数组1152B、墙钟0.21701秒、RSS未测。无模型/媒体/真实训练/probe/readout/Torch/SciPy Python/服务器/GPU，无来源概率/AUROC，未执行或等待AL31。

交付AL30_protocol/inputs/config/freeze/started/evidence/report/handoff及artifact manifest；完整向量/梯度/Hessian/试探/停止/标量轨迹在evidence。新源目录or1_head_accuracy_v2。105项历史文件（含AL27完整13项）及5依赖前后摘要一致；DEVLOG仅追加本包执行记录，主工作区和DAG未修改。建议规划端独立审查新门槛、归档与单批次范围，再决定后续任务；不自动扩展数据、模型或资源。此包已结束，无后台作业。
