# task-hermes 项目适配层

> **当前版本：cvpr27-20260918-v1.3。** DX03软件、DX04既有元数据描述审查已通过；100条旧时间值是best-effort字段，不等于已验证原生整数PTS。29项任务的状态与依赖以project.json为准，预算、正式数据和机制门槛未解除。

> **持续协作补充：** 派发去重与进展由 continuous_collaboration 记录。一个心跳内的里程碑与协作逻辑分支执行，参见 [执行补充](../COLLABORATION_RUNBOOK_2026-09-17.md)。下面v1/v1.1说明属于历史，不能覆盖当前入口。

> **当前计划版本：cvpr27-20260917-v1.1。** 25 项任务、11 个里程碑不变。gate_scope 区分软件与科研效果；RS04/RS05 的软件验收不释放尚缺预算、数据和新采样证据的支路。新机制必须纳入静态 patch 强基线。

> **2026-09-17 当前入口：[共享工作计划](../WORK_PLAN.md)。** project.json 为 cvpr27-20260917-v1：25 项当前任务、11 个里程碑；旧 16 项计划原样快照为 project_before_shared_plan_20260917.json，并保留于历史任务。下面 9/14 及更早的状态为历史。

## 当前命令与科学门槛

    python board.py validate
    python board.py next
    python board.py artifacts --task PL00
    python milestones.py check
    python milestones.py check --at 2026-09-23T19:00:00+08:00
    python -m unittest discover -s . -p "test_*.py" -v

board.py 的 next 同时检查父任务 done 和 requires_pass 指定的 gate_result=pass。执行结束但科学失败的任务可以 done，审查任务仍可继续；成功支路不会放行。它是本地适配器，不表示已连接外部 Hermes。

milestones.py check 是只读，支持带时区时间的模拟检查。普通里程碑 D-1/D0，关键里程碑额外 D-3；首次逾期后，状态未变不重复通知。已完成或明确延期的事项跳过。最终归档任务完成时返回 should_pause。

实际已输出提醒后，可用 milestones.py ack --receipt 实际检查结果.json --delivery-id 实际回合或运行标识 登记本地去重收据。ack 拒绝模拟 --at、过期计划及未来收据；不要把模拟测试登记为用户已收到提醒。收据不代表操作系统推送送达。

project.json 由 planagent 维护；科研角色交付独立证据报告，不并发覆盖任务表。提醒状态单独保存在 reminder_state.json。修改后先验证，再向已有任务交接。

## 历史说明

> 2026-09-14：当前为[第二阶段](../PHASE2_PLAN_2026-09-14.md)，16 项当前任务，P2A 启动审计已完成；`next` 放行 P2D、B01、P2C。原计划保存为 `project_before_phase2_20260914.json`。下方 R00/R01 状态属于早期历史。任务依赖完成只放行审阅；M01/P2G 的科学 pass/fail 还须由后续执行器显式检查。

本目录把研究计划表示为有依赖、可复核、可交接的任务图。名称 `task-hermes` 是本项目的适配层名称。它借鉴 Hermes Kanban 的持久任务、父任务依赖、review 与结构化交接，但并未在本机安装或启动 Hermes。2026-09-07 起，`project.json` 是唯一当前 DAG，采用反方审查后的 M0–M5 阶段；`project_legacy_v1.json` 和 `project_ccfa.json` 为历史。

```powershell
$py = 'C:\Users\ZHUyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py .\board.py validate
& $py .\board.py next
& $py .\board.py artifacts --task R01
& $py .\board.py export --output .\hermes-plan.example.json
& $py .\board.py validate --project .\project_legacy_v1.json
```

`export` 仅生成调用计划。父任务字段中的 `<HERMES_ID_FOR_Txx>` 必须在实际创建父任务后替换为 Hermes 返回的 ID。不要把本地 ID 直接当作 Hermes ID。

任务状态由研究人员或执行后端维护。把任务标为 `done` 前，应满足：依赖已经完成、必需产物存在、哈希已记录、适用的复核要求完成。`validate` 检查字段、状态、依赖与环；`artifacts` 报告存在性和当前哈希，并不自动完成科研验收。机械检查不能代替科研审阅。

当前 R00 为 review（先例差距需复核），R01 为 running（来源前缀检查完成，元数据/内容去重/协议未完成）。这表示局部工作状态，不是后台执行器正在运行。`next` 暂无输出表示后续任务尚未通过依赖门槛，不应跳过 M0。
