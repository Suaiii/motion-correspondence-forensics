# CVPR 2027 共享科研工作区

本文件是两个角色的共同入口。遵守上级 E:/aNB/TECH/AGENTS.md 的科研证据规则；用户的新指令优先于本工作区约定。

## 开始工作

每次开始或恢复任务，依次读取：

1. research-plan/WORK_PLAN.md：当前目标、算法方案、验收标准和日程。
2. research-plan/task-hermes/project.json：唯一当前任务状态、依赖、预算和里程碑。
3. DEVLOG.md 的最新记录，以及当前任务引用的证据。
4. 当前角色对应的 agent.md。这些文件由本入口显式要求读取，不假定会自动发现。

## 角色路由

- planagent：当前任务“Plan9.16”，任务 ID 01a0aea6-38cb-77e1-8f1f-aba2a8dce36b；读取 [规划角色](agents/planagent/agent.md)。
- researchagent：现有任务“科研冲击”，任务 ID 01a09db1-3c10-7710-b866-130d4cc44d9e；读取 [科研角色](agents/researchagent/agent.md)。
- 用户明确指定角色时，以用户为准。新任务仅处理排期、状态或提醒时使用 planagent；执行研究代码、数据或实验时使用 researchagent。职责不清且会造成冲突时，先读共享记录再澄清。
- 角色文件不等于新建了软件 agent。本工作区使用上述已有任务，不自动创建新任务或派生 agent。

## 共享事实与写入责任

| 内容 | 维护者 | 位置 |
|---|---|---|
| 研究目标、主候选、验收标准、工作时段 | planagent | research-plan/WORK_PLAN.md |
| 任务状态、依赖、日期、预算、里程碑 | planagent | research-plan/task-hermes/project.json |
| 实际代码、运行证据、失败解释 | researchagent | research-runtime、research-runs、DEVLOG.md |
| 提醒去重记录 | planagent 的提醒运行 | research-plan/task-hermes/reminder_state.json |
| 正式科学判断 | 用户与导师，agent 整理记录 | 对应审查报告 |

修改共享状态前重读文件并检查是否有并发变化。科研角色通过独立交接报告建议状态变更，不直接覆盖任务表。仅仅文件存在、测试通过或实验结束，不代表科学假设成立。

## 不可省略的边界

- 预算是项目累计 6000 元、初始累计 180 GPU 小时；已用额度先核减，未知余额不得写成零消耗。预算不等于自动购买、充值或租新实例的授权。
- 大视频、解压、特征与训练默认在服务器；本地仅保留代码、清单、哈希和紧凑证据。不得保存密码或私钥。
- 任务执行状态与 gate_result 分开。依赖成功机制的任务，父任务必须 done 且相应 gate_result=pass；failed experiment 可以 done，但不能释放成功支路。
- 现有局部秩响应属于诊断/对照；原局部对应可组合性及C保留作冻结参考。v1.4新候选以WORK_PLAN 3.8和ALGORITHM_SEARCH_20260918.md为准，候选不能混称或提前宣告成功。
- 最终集只在方法和协议冻结后打开；已有暴露的开发池不能重新命名为最终确认集。
- 100条MS/VC2旧before.pts来自归档best_effort_timestamp_time，不等于已核实的原生整数PTS/time_base。完整记录数量、时间字段来源和原生时间验证分别报告，见WORK_PLAN第3.7节。
- 正式复核由不同于主实现者的复核者承担，机械回放不能冒充独立科学复核。
- 个人工作时段不构成实验强制终止时间。按定义清楚的批次完成、保存可续跑状态并遵守已授权停机安排。
- 里程碑提醒分支只做检查与通知，不启动训练、购买资源或投稿；仅在里程碑窗口、首次逾期或实质变化时提醒。
- 用户于 2026-09-17 新增持续协作授权：按 [持续协作执行补充](research-plan/COLLABORATION_RUNBOOK_2026-09-17.md) 审查并派发现有科研任务。因应用仅支持一个心跳，持续协作与里程碑提醒在同一 cvpr-2027 中分支执行；不改变预算和科学门槛，不重复启动工作包。
- 用户于2026-09-18进一步要求持续研究与新算法突破。读取[持续科研规则](research-plan/CONTINUOUS_RESEARCH_20260918.md)：预算/服务器/真实数据仅阻塞相关支路，算法设计、理论反例、CPU原型和近邻审查继续；队列空时必须先补充有科学价值的独立任务。完成交接触发续接，10分钟心跳补漏；不把检查次数当成果。
