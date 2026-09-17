# 原始 PTS 采集器准备交付

2026-09-18；researchagent；plan cvpr27-20260917-v1.1。
工作范围：为缺失的真实来源完整时间戳准备采集与恢复工具。没有采用新采样协议，
没有修改第二轮资源合同的 execution_authorized=false。实现基线为 3fe8fa9。

## 已实现

[采集器](../../research-runtime/server/scripts/acquire_native_pts.py) 默认仅读取合同和
候选清单，输出选样与缺少的执行条件，不打开原始媒体。选样先按原始 SHA256
及 sample_id 排序，每个已知 origin_group 取一代表，再按来源截取前五。
不足五条时不复制补额；ancestry_status 保留未知标记，不能以组名替代来源验收。
final/test 角色被拒绝。

实际 --execute 仅接受 Linux 服务器路径，且必须有另行 adopted 的合同、
明确批准记录、父任务与实例证据、清单和采集器源码哈希、本批费用及计费时数额度、
报价和固定 billing_started_utc。已知历史消耗会参与累计上限检查，未知值不改成零。
启动时的资源时钟不会因续跑而重置；它是计费暴露估计，不是实际账单。
一个输出目录只允许一个采集器持锁；崩溃遗留锁必须核对对应进程后人工处理，
不能仅因超时删锁重启。

每文件先核验原始 SHA256，探测覆盖原视频的完整第一视频流，不使用截断区间。
只启动一个 ffprobe、一个线程，属于合同最多两个 worker 内的串行实现。
原始 JSON、stderr、整数时间戳、rational time_base 和 best-effort 时间戳分开保存；
native PTS 缺失不会由 FPS 或 best-effort 自动填充。重复、倒序和缺失保持原序并标记。
原始 stream/frame duration 等字段保留在探测 JSON 中，不从名义 FPS 制造时间序列。

成功状态仅表示探测进程正常结束、无 error stderr、JSON 可解析及元数据归档。
它不是视频质量、采样资格、真假共同支持或数据来源验收。解码错误、源变化和资源
不足单列 acquisition_failed，不自动剔除视频并称为质量不合格。

续跑要求合同、清单、工具、ffprobe 版本及原始 SHA 一致，并重新核验全部输出摘要。
校验失败创建独立 attempt，保留旧文件；失败结果不复用为成功。采集器不会下载、
转码、抽特征、训练、启动服务器或自动关机。未来批次完整结束并同步后，外层执行
负责人仍须按用户既定安排核对作业并停机，不能把脚本结束当作停止计费。

## 未来合同需要补齐的绑定字段

原草案保持不动。若经审查采用，新的合同需填写以下字段：

- 顶层 status=adopted、execution_authorized=true、approved_by、approval_receipt、
  parent_gate_receipt、existing_instance_receipt、collector_sha256。
- inputs.source_manifest_sha256 绑定完整候选清单。
- budget.approved_batch_max_cny、approved_batch_max_hours、current_hourly_rate_cny、
  batch_allowance_receipt、billing_started_utc、next_file_reserve_cny。
- 原累计上限和已知实际用量不得被擦除；无下载、无 GPU、无最终集规则保留。

每个 candidate 需要 sample_id、source、relative_path、source_sha256、origin_group、
ancestry_status、data_role=development_candidate。relative_path 必须在显式服务器
根目录内；输出目录必须为其子目录。该格式不是现存来源清单已通过验收的声明。

仅生成计划的调用形式：

    python acquire_native_pts.py --contract <contract.json> --manifest <manifest.json>

未来实际采集才添加 --execute、--server-root 和 --output。本轮没有执行该路径。

## 验证与限制

[16 项测试](../../research-runtime/server/tests/test_native_pts_acquisition.py) 通过，
最终测试执行0.341秒，使用本地临时的非媒体字节与模拟 ffprobe JSON。
subprocess 边界全部替换为 mock，**未执行 ffprobe 或其他第三方程序**。
检查覆盖 >2^53 时间戳精度、无效 time_base、PTS 缺失与倒序、选样稳定性、
最终集拒绝、未授权 CLI 拒绝、dry-run 不读取原始文件、源变化、摘要损坏后重取、
stderr 错误、资源中断保留、快速结束但输出超限、路径越界及累计预算异常。

资源监控按0.1秒轮询；输出可能在两次检查间超出限制，故该限制不是操作系统硬配额。
完整原始哈希读取及 ffprobe 初始化也会消耗服务器计费时间；next_file_reserve_cny
须覆盖保守启动/收尾开销。合同审核者需按实际磁盘、报价及文件规模确定额度。
本轮尚未验证服务器 ffprobe 版本和真实文件解码表现，也未执行中断后的真实进程恢复。
上述条件应在未来十文件小批次中核验，不能用 mock 测试取代。

新增仅数十 KB 代码/证据，本机无视频、模型或特征缓存。未刷新服务器状态或账单，
RS00、RS03 与正式创新结果仍未通过。后续应先审查采样提案与资源合同，然后采集
实际 PTS 并判断是否具备受控机制实验条件。
