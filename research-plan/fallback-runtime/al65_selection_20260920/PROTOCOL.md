# AL65-v1：固定五情形的精确CPU对照

实际执行者planagent，因科研任务01a0ba9d启动层call_id错误接管；主DAG已登记。工作单AL65_SELECTION_MECHANISM_CPU_20260920.md中的6格、两源相同1/6基律、五组保留概率和两个方向固定的二值评分不变。

在首次批次前冻结cases.json、reference.json、selection_controls.py、run_batch.py与本协议。freeze.json只记录真实时刻/代码与输入哈希，不执行科学算术；随后仅执行一次run_batch.py --output run_v1。日志与全部原始概率输出保留。失败不调整情形/方向/容差，按工作单最多一次缺陷驱动版本修复；不能覆盖run_v1。

逐类选择后分布为p_y(x)s_y(x)/E[s_y]。保留概率是已知toy输入；不能当真实数据可获oracle。Z匹配在共同Z支持上令目标m(z)正比于min(P0(z),P1(z))，保持各类P(Q|Z)。报告重叠质量与各类共同支持外质量，不把平衡后子集当原全体。

IPW只在声明6格选择概率全部正时用已观察分布除s并归一化；任何s=0则输出完整目标不可恢复和null，不能用配置中知道的原始base偷偷填补缺失格。允许另一源独立计算其可恢复分布。

reference.json中的预测为执行前人工推导：二值分数AUC=1/2+(r1-r0)/2，r_y是该源取高分的概率。实际AUC程序用完整两分布36个格对求和，与二值边际公式和固定期望比较。概率总和/同选择等分布/逆概率返回原分布等检查直接比较数值对象，不使用自相等或预填通过清单。

有限概率算术无拟合/随机种子；它可说明筛选解释足够制造差异，不能证明真实数据存在该机制，不能算五种子性能或CCF-A算法贡献。每类只有6个概率单元，没有大数组、依赖安装、媒体、网络、模型、服务器或GPU。Windows运行以OMP_NUM_THREADS=2作为上限，实际过程仅单Python线程；Python分配峰值单独实测，不当作全进程内存。

执行命令：已配置Python -X utf8 research-plan/fallback-runtime/al65_selection_20260920/run_batch.py --output run_v1。完整源码与配置需要先留Git提交；冻结源文件一旦生成freeze.json不得在此次运行前更改。交接交由恢复后的不同执行者复核，当前实现者自检不是独立科学审查。
