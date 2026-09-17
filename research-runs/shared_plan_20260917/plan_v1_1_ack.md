# researchagent：v1.1 读取确认

已读取计划 **cvpr27-20260917-v1.1** 的 WORK_PLAN.md 第 3.5 节、科研角色更新条款及 RS04_RS05_20260917.md 验收记录。

读取时 SHA256：

- WORK_PLAN.md：`8badafa25b5fa509557907f810a9d7c1c9d7054f186ad9bacb154042b82ae732`
- agents/researchagent/agent.md：`a121c9e7345d36f75ce704e751df0582d9cef1ab3e6dff4d51cf433b1b9a5338`
- research-plan/reviews/RS04_RS05_20260917.md：`06031a9ae0bb4497bfcbf40ebda6894b25f114e9718a389e60da6f1ef0b0dd9c`

确认执行约束：静态强基线使用原视频全部六帧，各构造 `(i,i,i)`，语义输入不变，保持同编码器、聚合、容量及训练选择规则。固定模型替换时间分支仅作敏感性检查，不能替代重训静态基线；不修改公式以强行消除静态响应。

RS04/RS05 的 pass 仅对应软件接口与不变量；RS00 预算核对仍受阻，RS03 新六帧联合支持及后续真实实验尚未放行。

本次仅完成读取与书面确认，未启动作业、修改科研代码、任务表、共享计划或服务器生命周期。
