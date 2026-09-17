# 共享计划与核验入口

当前科学方案见[WORK_PLAN](WORK_PLAN.md)，任务状态见[project.json](task-hermes/project.json)。
两个角色由根AGENTS.md显式路由；当前计划版本v1.3只更正时间证据来源和交付状态，
不更改v1.2的C软件定义、实际采样规则或科学门槛。

## 保持冻结字节

.gitattributes对规划、研究源码与运行证据关闭自动文本换行转换。冻结摘要使用实际
文件字节；Windows的core.autocrlf不能把CRLF/LF转换后仍当作同一冻结输入。
提交时逐项核对暂存Git blob与工作树字节。不要为通过检查而重新生成冻结输入摘要。

DX04原冻结分析计划和输入表仍在原路径，保持原字节；其历史“完整原生PTS”表述
由[DX04勘误](reviews/DX04_20260918.md)和WORK_PLAN 3.7限缩为归档best-effort呈现时间。
旧v1.2 WORK_PLAN保存在[历史快照](WORK_PLAN_before_timestamp_clarification_20260918.md)。

## 本地只读核验

使用已有Python环境；规划检查只需要标准库，DX04算术检查需要NumPy，DX03还需PyTorch。
以下命令在仓库根目录执行，不包含服务器或训练操作。

    python -X utf8 research-plan/task-hermes/board.py validate
    python -X utf8 research-plan/task-hermes/board.py next
    python -X utf8 -m unittest discover -s research-plan/task-hermes -p "test_*.py" -v

计划端历史核验回执及脚本位于reviews。verify_dx03_20260918.py和verify_dx04_20260918.py
拒绝覆盖已有结果；复核者应在独立副本中另设输出位置，不能删除或覆盖原证据。
研究侧DX03回放入口check_candidate_c_cpu.py需要唯一新输出文件；重现原版本时，
--work-plan指向上述v1.2历史快照。DX04入口audit_candidate_c_existing_pts.py绑定原冻结
输入并拒绝覆盖已有输出；新回放会产生新的执行时间和当前WORK_PLAN摘要，不是原回执。

计划端核验只证明给定文件和算术一致，不替代真实媒体校验、预算核对或独立科学复核。
reminder_state.json仅为此任务的通知去重记录；新副本不能把它当成用户已经收到新通知。
