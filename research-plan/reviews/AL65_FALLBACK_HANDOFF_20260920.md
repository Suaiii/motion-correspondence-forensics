# AL65接管交付：筛选机制有限支持CPU对照

2026-09-20，planagent fallback-runtime。科研专项冲击任务`01a0ba9d-c4e1-7b52-abc8-e47f32c282fb`在启动后因`function_call_output requires call_id`失败，未产生代码/证据；按持续科研规则在独立`research-plan/fallback-runtime/al65_selection_20260920`临时路径执行已授权CPU包。AL36未被自行替代，仍等待不同执行者恢复。

## 执行回执

冻结文件由`freeze.json`绑定，运行命令为：

`C:\Users\ZHUyi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -X utf8 research-plan/fallback-runtime/al65_selection_20260920/run_batch.py --output run_v1`

实际回执：`software_pass=true`、116项直接对象检查、0失败、0错误；没有模型、媒体、网络、服务器、GPU、分类器拟合或随机模拟。冻结源码提交`d7bcb06`后仅成功执行一个批次。Python3.12.14；含元数据/哈希处理的记录wall_seconds约0.480、process_cpu_seconds约0.156，tracemalloc记录的Python分配峰值116310字节，非全进程内存。开始/finished_at字段只包围数值与哈希部分，不能用其约0.021秒差值替代完整wall计时。OMP_NUM_THREADS实际未设置，代码没有创建并行线程或使用原生数组库。完整证据在`run_v1/evidence.json`，摘要在`run_v1/summary.json`；哈希由主DAG记录。

## 固定情形结果

分数均固定为“大值指向Y=1，平局1/2”：`f_Z=|Z|`，`f_Q=1[Q=1]`。

| 情形 | 观察 f_Z / f_Q | Z共同支持后 f_Z / f_Q | 解释 |
|---|---:|---:|---|
| S1 全保留 | 1/2 / 1/2 | 1/2 / 1/2 | 零差异基线 |
| S2 仅Y0按Z筛选 | 2/3 / 1/2 | 1/2 / 1/2 | 不匹配的Z筛选可制造f_Z信号；共同支持匹配移除它 |
| S3 两类同Z筛选 | 1/2 / 1/2 | 1/2 / 1/2 | 相同选择机制不制造源差异 |
| S4 Y0的Z=±1完全缺失 | 5/6 / 1/2 | 1/2 / 1/2（仅共同Z） | 观察源差异可很大，但Y1的共同支持外质量为2/3；全总体不可由观测恢复 |
| S5 Z相同但Y0按Q筛选 | 1/2 / 13/20 | 1/2 / 13/20 | 匹配Z不能消除未匹配的Q选择机制 |

已知全正选择概率时，oracle逆概率恢复回固定基础分布；S4的零选择概率返回`full_population_unidentifiable_zero_propensity`和null，不偷偷使用基础真值补缺。该oracle只说明可识别性条件，不能当真实数据可用方法。

## 科学边界

结果支持一个受控替代解释：来源池或筛选规则不同，足以在抽象特征上制造分离；按共同Z匹配只能处理Z支持和边际差异，不能自动处理Q条件差异或零支持。它不证明AIGVDBench、OpenVidHD或当前真实数据确实有该偏差，也不否定OR1真实效能；它只要求未来机制实验记录筛选/覆盖并在支持条件内配对。

经典概率算术不构成新算法，不能计入CCF-A突破。该实现是planagent接管的自测，不是独立科学复核；恢复后由不同研究执行者审查，机械回放也不能替代导师/用户复核。

## 下一步

1. AL66审查在未知筛选概率下，观测到的条件分离是否足以支持源类排序；仅推导可辨识条件和反方解释，不重复五情形、不再运行toy。
2. AL36由不同执行者完成OR1反方准入审查；研究任务恢复后同时先审AL65接管产物，不能重选情形或改分数方向。

AL05的fail、AL58的执行合同fail、OR1未准入、预算与真实媒体/GPU门槛均未改变。
