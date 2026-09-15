# task-hermes 项目适配层

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
