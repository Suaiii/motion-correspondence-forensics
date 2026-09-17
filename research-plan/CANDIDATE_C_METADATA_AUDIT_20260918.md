# DX04：C 在既有开发元数据上的固定分析

工作包：cc-round-4-c-metadata-20260918。计划：cvpr27-20260918-v1.2。
负责人：researchagent；验收：planagent。仅本地 CPU 元数据，不启动服务器。

## 目的与边界

核查已实现的居中三帧 C 在既有完整原始 PTS 上的资格、两个实际间隔及中心偏移，
为后续真实来源审计准备可回放的记录。这批数据已参与 A 的诊断，因此属于后验开发分析，
不是新的预注册独立确认或机制实验。不得根据本次结果更改 C、选择最有利分箱或调参重跑。

DX04 的父任务为已验收的 DX01 与 DX03。它仅仅使用本地既有 JSON 元数据，不要求
访问预算未核清的实例；不能放行 RS00/RS02/RS03 或训练。

## 固定输入

- 名单以 research-runs/overnight_20260911/checkpoint_v1/retiming_diagnostic/protocol.json
  的原有 selection 为准：50 MS、50 VC2，不新增、重抽或按结果删除样本。
- 只使用对应记录的 before.pts；须核对 sample_id/source、status、完整帧哈希数量，
  并核对归档写入器 code/retime_qc.py 与 protocol.script_sha256。
- 输入哈希见 reviews/dx04_input_freeze_20260918.json。先检查其中的 protocol、写入器、
  全部 100 条记录及 C 采样/配置摘要。任何不符先报告，不能从名义 FPS 或旧选帧补齐。
- after.pts 禁用于分析；不重新计算像素或读取任何视频。祖先状态沿用 unverified，
  原始视频哈希和解码内容未在本轮重新核验。

## 固定操作与输出

1. 每条调用一次已验收的 choose_centered_three。保留入选/排除状态、具体理由、
   原帧索引、选中 PTS、目标 PTS、三个有符号选择误差、两个实际间隔、实际跨度、
   native_duration 和 center_error_seconds。缺字段作为数据问题，不能静默省略。
2. 按来源报告总数、资格数、排除率；对两个间隔、跨度、三个误差、中心误差和原生时长
   分别报告最小/最大/均值/标准差及距目标的最大差。它们是诊断变量，不新增模型输入。
3. 对两个实际间隔的联合向量，以及两个间隔加中心误差的联合向量，分别用事先固定的
   1/2/5 ms 分箱（floor(x/q+0.5)）报告每来源频数、共同 bin 数和共同支持记录数。
   三种精度全部保留；负误差的取整规则明确，不据此声称连续时间完全匹配。
4. 在同一原始输入可通过 A 时，核对 C 的原帧索引/目标对应 A[1,3,5]；A 不通过时单列，
   不因此删去 C 合格样本。不重跑旧八帧普查、响应图、骨干或检测器。
5. 说明哪些旧混杂在这个已暴露子集的描述量中消失或保留；区分观察到相等、分箱相交和
   科学上的可交换性。Vript/HD-VG/CogVideo 完整原始 PTS 仍缺失，不推断真假共同支持。

所有统计无标签拟合、无分类器、无 AUROC、无方向/阈值选择。不得使用本次结果主动
修改采样器、主公式、训练配方或 C 的身份。若需要修订，仅提出独立假设供后续审查。

## 交付与验收

研究端新增 candidate_c_existing_pts_report.md、candidate_c_existing_pts_audit.json、
candidate_c_existing_pts_records.json 和 collaboration_round_4.md，放在
research-runs/shared_plan_20260917。回放脚本由研究端维护，历史报告只读。

交付绑定 dispatch_id、执行计划版本、完整输入摘要、脚本/采样配置摘要、实际资源和
限制。逐条数量可守恒、排除可追踪，科学门槛字段保持 false/not_evaluated。
软件或描述统计通过只能支持 existing_metadata_diagnostic 的范围验收。
本包完成即交接；不因为心跳仍运行而自行启动下一采集或训练批次。
