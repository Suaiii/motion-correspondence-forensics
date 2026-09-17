# cc-round-4-c-metadata-20260918 交接

task_id=DX04；plan_version=cvpr27-20260918-v1.2；researchagent；2026-09-18。
父DX01/DX03已核对为done/pass。工作包按固定计划完整执行，建议验收范围仅为
existing_metadata_diagnostic_only；科学gate保持not_evaluated。

WORK_PLAN SHA256：dc44831b23d637ae5516c76e1da58d6c22cf7b5667548233483f706520eecbca。
分析计划SHA256：b1ce5f723b02cd1e4a0d9b8ef64e2773d9aeeedebb2bb562fdfd854e0f56116b。
冻结摘要：7a841af5377f1f457396ae7bdc652809eddffff9c2ac431fca54fc549c9bde93。
实现基线e074ca7074ddea3d387d324070e7319abbbd65a5；本轮只新增回放脚本与报告。

交付：

- [报告](candidate_c_existing_pts_report.md)
- [固定审计结果](candidate_c_existing_pts_audit.json)
- [100条逐条记录](candidate_c_existing_pts_records.json)
- [研究端脚本](../../research-runtime/server/scripts/audit_candidate_c_existing_pts.py)

100条记录哈希、原protocol和归档写入器全部匹配；C采样/配置与分析计划均匹配。
按原顺序重建的DX01输入哈希索引也相同。计算前后输入摘要不变，C恰调用100次。
只使用before字段；未使用after.pts，未修改任何采样参数。

结果：MS 50/50、VC2 50/50通过；排除率均0。双间隔均[.5,.5]、跨度1、中心误差0。
1/2/5ms的双间隔及双间隔加中心误差六种固定视图均为一个共同bin，覆盖两来源各50条。
100条A均通过；C的索引/目标均对应A[1,3,5]，无失败或删样。完整连续统计和全部频数已保存。
原视频D仍分别2.0/1.6秒，绝对选中时点和索引也不同；不能把局部描述一致当作消除所有混杂。

重要来源限定：归档retime_qc.py实际保存的是ffprobe best_effort_timestamp_time。
before.pts与完整有序解码帧哈希的数量匹配，但没有本轮验证的原生整数PTS/time_base。
已在每条记录、audit与报告中明确标注；不修改旧材料来强化来源主张。

本地CPU0.121秒，无服务器、媒体、ffprobe、骨干、GPU、分类器或优化器。
这是已暴露两假来源的后验描述，非独立确认；Vript/HD-VG/CogVideo缺完整时间证据，
祖先unverified，raw-media未重核。RS00/RS02/RS03、PTS合同与训练保持未放行。
费用未知且未重复提问/账单重试，服务器当前状态未刷新。没有待运行作业，也不自行追加下一批。

建议据此审查C在该子集的描述可行性，并保留完整原始时间证据和两个真实来源的后续门槛；
任何进一步采集或协议修订另行派发，不把本结果写成检测创新、CCF-A或专利成就。
