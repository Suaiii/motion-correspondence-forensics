# 新科研窗口实际启动回执与接管

2026-09-20，planagent。用户要求新科研窗口的创建请求已落实为实际任务 **科研专项冲击 · 算法与CPU原型**，ID `01a0ba9d-c4e1-7b52-abc8-e47f32c282fb`，独立工作树 `D:/SUAI/codex/worktree/a77e/脉冲神经网络`。已用navigate工具在当前应用打开该任务；不是只有client创建收据。

read_thread及一次wait_threads确认：回合`01a0ba9d-c930-7e02-8b6f-092f8651ec2c`在启动后约35秒失败，错误为 `function_call_output requires call_id on HTTP requests`。回合仅有确认包的commentary和文件存在性/旧记忆查询；新工作树git状态为空，AL65源目录与证据均不存在。这个启动层失败没有任何科学结果，不重发、换账户/组织或更改模型规避。

该commentary将自己的ID错报为旧`01a0b54a...`，真实身份以工具thread.id和工作树为准；其包确认支持它读到了AL36/AL65任务摘要，不代表已完成内容读取或实现。最新wait cursor为`6266bfba-1e72-42c6-9a7b-73fd2ca08dff:1`。

不同历史错误分列：旧科研任务`01a0b54a...`同样报call_id协议错误；归档任务`01a0ba4b...`曾报默认gpt-5.4不支持；早先401与产品额度故障也保留。planagent之前未获用户指定而覆盖旧任务模型的操作不再重复，新任务使用默认设置。

按CONTINUOUS_RESEARCH的启动故障接管规则，AL65只在`research-plan/fallback-runtime/al65_selection_20260920`临时实现已批准的有限支持CPU对照，不碰科研工作树与历史代码。真实执行者记planagent，AL36仍需不同执行者的反方审查，不能自己替代独立复核。恢复后先读主DAG及接管产物，交叉审查或接下一独立包，不能自动重跑。

服务器读数是00:45左右的带时间观测：13340在线，4090显存与GPU利用率0、无计算进程，12核/90GiB。未查询新账单或启动训练，实际费用仍unknown。CPU对照本地运行，不以服务器闲置为理由放行GPU。本回执不能保证之后服务器状态不变。
