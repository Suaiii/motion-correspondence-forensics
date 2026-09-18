# AL15 交接：固定向量核心与mock合同通过

dispatch cc-al15-or1-cpu-20260919；AL15；researchagent_next。
执行任务01a0b54a-3a46-72c0-9f2c-58bdb49c6424。
工作树 `D:/SUAI/codex/worktree/662f/脉冲神经网络`，分支 `codex/al15-or1-cpu`。
冻结提交f897e0c在首次核心调用之前；结果提交见交接消息。

执行完成，建议进入**software_algebra_and_mock_contract**范围review。
没有创新/真实机制/模型接口通过的结论，AL05 fail保持。
已实读v1.5主DAG、AL12_REVIEW与AL15工作单；主计划摘要仍为
5cc4f7b994c79853913cecb8d1bad9a46156f584fd33ca4712aee85c7b3fc8ec。
源a4cfdeb最终草案摘要91e856957b34beb14c3f098ce7f078594cb0529268367ec120f3eb1da2f78292，
已与Git blob核对；原JSON仍保留draft_not_authorized字节，当前授权写在新冻结与回执。

## 实际结果

- 8族、14个向量观察×5个既定基础/嵌入/置换变体×3个h，共210次核心求值，全部预期关系通过。
- 与Fraction预先闭式K最大绝对差0；本批多为dyadic精确输入，不外推为真实低精度安全。
- 非线性余项在h=1/4、1/8、1/16时分别为1/64、1/128、1/256，逐值核验。
- 参数probe互换反号、能量/同比值不变；可交换/平移零响应、非交换但普通误差可解释、相同输出多重集等退化全部保留。
- 核心840调用，输出拒绝4调用，重复诊断6调用，总850；每条路径a/b各一次，所有初始缓存独立且为空。
- 10种无效支持/有限值/声明合同按预期拒绝；固定交替mock差.125被诊断捕获。没有未预期失败。
- 来源C/R/R2=0、G/G2=1与处理次数分列；有效来源表通过、4种错误表拒绝，元数据测试不调用probe。

主比值始终用mean和固定eta=1e-12，补维后主比值最小变化-5.109357381627433e-11。
没有把容差内差异说成严格不变量；sum/mean的等价eta_sum=n*eta和缩放eta的嵌入诊断分别列出。
三维例K的1/16/0是sum能量，不是mean。真实图像四滤波没有实现或运行。

## 产物与摘要

源码：research-runtime/algorithm_candidates/or1_cpu/{core.py,config.json,freeze.py,run.py}。
证据：AL15_protocol.md、AL15_inputs.json、AL15_freeze.json、AL15_evidence.json、AL15_report.md、本报告与清单。
全路径均位于本独立工作树；主DAG和旧AL01/04/06/09/12证据/相关源码摘要运行前后保持。

| 对象 | SHA256 |
|---|---|
| core.py | c838e34a1fb196b1955d9a0b43d2939830249b6259a3195f693b1d35c6961c13 |
| config.json | ed2dea574565bf65844ab9694474078f2a26b48af6278d915f803296ff928884 |
| run.py | eb69ccd2065760df4a9bdb09ea059e77766cdecc46bea00aa30ac3211de0f536 |
| 全部输入/预期 | 86b601c79629bf5da747d23722aba8d1a13abe78146b3f4424fa27b300b8bab2 |
| 全部结果/调用账本 | 076ae934e740d72943ca2e9f1b9c5cda27ffd8ecc2611a7ca8b386e88646c3ec |

运行：E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_cpu/run.py。
复核必须用新--output路径，不覆盖当前回执或重新生成冻结输入。

## 资源与限制

NumPy2.2.6/stdlib，Python3.11.15；BLAS由ctypes实测配置为2线程，未导入SciPy/threadpoolctl/Torch。
最大显式数组512字节、维度8；RSS未测。运行内耗时.2130661秒、进程CPU .140625秒；不含启动/最终写出/写作。
无媒体、真实滤波、模型/权重、服务器/GPU、分类器拟合或toy AUROC，无遗留进程。
确定性重复一致不保证数值准确；mock槽位与声明clock不等于视频物理对应；嵌入不是独立真实种子。

真实4滤波、配对训练、视频wrapper及检查点/时钟仍pending；AL16由planagent独立负责，本包未执行它。
下一具体动作是独立复核此核心/账本，并用AL16已审查合同决定是否另派数值拒绝域接入包；
不能由本包软件通过自动启动真实或付费实验。预算、未知实际累计消耗、来源/祖先/PTS/最终集及正式门槛全部保留。
