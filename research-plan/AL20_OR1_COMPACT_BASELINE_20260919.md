# AL20：OR1有限交叉响应分解与紧凑强基线

待派发给researchagent_next；当前仍只执行AL18，不并发启动本任务。依赖AL12/AL15/AL19的已审查产物；不依赖AL18数值实现。

科学问题：OR1的四维能量比可否由同四调用下的普通交叉增量能量和内积精确重构？若可以，不能仅与八个单步误差比较就把遗漏的对齐统计当独立新信息。目标是明确最强紧凑对照及剩余可检验贡献，不修改候选以制造差异。

限定工作：

1. 从v_j=R_j-id、P_j=id+h v_j推导有限h的精确交叉增量关系，不只引用h趋零展开。定义d_a=[v_a(P_b(u))-v_a(u)]/h、d_b=[v_b(P_a(u))-v_b(u)]/h，核查K=d_a-d_b及线性滤波能量展开。
2. 为每个固定H_l列mean||H_l d_a||²、mean||H_l d_b||²及mean内积的完整三元组，明确共同分母、eta和支持；判断哪些压缩才会遗漏候选所用统计。数学可重构性不能直接替代有限样本训练比较，也不自动证明全候选失败。
3. 给具体等四调用baseline特征和固定/学习读出合同，保留完整端点强基线；区分“确定函数无新观察信息”“不同归纳约束”“真实增量”三类主张。明确4权重候选与更强维度/容量对照的实际参数，不靠零padding伪装匹配。
4. 仅对AL15归档中的固定线性、非线性、冗余三个基础维度案例的主h trace作精确读后核查，不重新调用core、不搜索旧输入、不拟合分类器。若定义有误交付反例，不覆盖旧结果。

产物AL20_method_baseline.md、必要的精确trace摘要、AL20_handoff.md、artifact manifest，写现有独立工作树research-runs/algorithm_search_20260918；需要新分析脚本时使用独立or1_baseline_audit目录。输入/公式及使用的trace ID须在核查前列清楚。

CPU仅stdlib/Fraction或NumPy，2线程、数组<=1MiB；无媒体/模型/权重/服务器/GPU/训练。通过仅为 `finite_response_baseline_contract`，不能释放正式科学与资源门槛。尚未派发前不执行；最终读主DAG中的唯一dispatch_id。
