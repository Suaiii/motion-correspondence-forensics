# 新算法研究：联合可实现性与对应条件化高阶信息

计划版本：cvpr27-20260918-v1.4。用户于2026-09-18明确要求持续研究和开发，以形成能冲击CCF-A的新算法。本文给出下一轮可执行研究问题；候选尚未通过创新性或真实性能验收。

## 目标与当前判断

C保留为冻结参考候选和反例来源，不再把继续完善C视为唯一主线。当前最关键的问题是：在静态外观、两两对应、采样和容量已被控制时，究竟还需要什么可观测信息，才能构造可迁移的生成视频判别信号？

先审查两个可否证方向。最多并行维护两个未裁决候选，不能通过换名称、拼模块或重复旧测试宣称新算法。

## H-J：不确定对应的联合可实现性缺陷

设三个帧的候选patch集合大小为m，固定单帧质量pi_a、pi_b、pi_c；第一轮均为1/m。
Q_ab、Q_bc、Q_ac为非负、总质量1且单点边际一致的两帧软联合对应。检查是否存在一个三帧联合分布Gamma，同时产生这三个两帧边际。最小原型为：

    D_J(Q) = min_Gamma (1/3) sum_(ab,bc,ac) ||M_pair(Gamma) - Q_pair||_1
    Gamma >= 0
    M_a(Gamma)=pi_a, M_b(Gamma)=pi_b, M_c(Gamma)=pi_c

M表示求边际。先用m=2/4/8的小规模线性规划获得可复核参考解，不部署大张量或训练模型。

可否证假设：乘法可组合性隐含的条件独立性会惩罚某些本来可实现的多峰软对应；联合可实现性可能将“对应歧义”与“无法共存的对应关系”区分。研究端必须构造兼容但乘法不一致的例子，以及各对合法但共同不可实现的例子，并证明边界。

必须比较：C式乘法JS、相同Q上的条件转移乘法、简单循环残差、熵/边际误差。若从row-softmax改为双随机Q，所有对照共享相同Q，另列归一化变化，不能把归一化收益计入新目标函数。

必做反例：静态重复帧、理想循环平移、多峰歧义、非交换置换、遮挡/缺失质量。若某些有效静态输入也不可实现，明确反例，不事后相减或调温度使其归零。若该量仅重述已有多视图同步/MM-OT目标，或没有超出简单循环残差的决策差异，则该版本的创新主张不通过。

本指标只使用Q，不能声称恢复了Q中不存在的新信息。其潜在贡献须落到可证明的归因条件、有效的新推断/学习目标及真实数据独立增量，而不能仅仅是“用了最优传输”。

## H-T：对应条件化的不可约多帧统计

探索沿跨帧对应关系聚合三时刻连通统计，并与同一/两时刻约束下的参照分布比较。例如：

    T_abc = sum_ijk W_ijk (z_ai-mu_a) tensor (z_bj-mu_b) tensor (z_ck-mu_c)
    Delta_T = T_observed - E_reference[T | declared one/two-time constraints]

这是需要被具体化和攻击的候选定义，不是已经成立的算法。研究端必须交代W、参照分布、读出与推断复杂度；如果W和参照仅由相同Q确定，不能宣称获得新的高阶观测信息。

第一轮构造具有相同单帧统计/两帧边际、但三帧联合结构不同的受控过程。区分“每一对的边际相同”和“全部两两矩阵组成的观测元组相同”；前者不能自动证明任意使用所有两两信息的模型都无法区分。可用Rademacher奇偶过程作为理论诊断，但不可把该人为标签当作生成视频机制。

比较同输入的无序/静态聚合、普通三阶统计、未对齐三阶统计、条件化统计及C。核查特征公共旋转/符号、纹理幅度、熵和对齐误差；读出如果借助真实轨迹、标签方向或其他对照拿不到的oracle，单列上界，不计为可部署方法。高阶共现不自动意味着时间方向机制，须单独检验时间重排。

终止条件：统计与已知三阶方法等价；需要未提供的高阶oracle才能分辨；差异完全由静态统计/任意坐标符号/信息量不公平解释；在冻结扰动下失效。终止该版本后保留负结果并形成修订假设，不能在同一受控例子上无限调参。

## 首包 cc-round-5-algorithm-search-20260918

任务AL01执行H-J；任务AL02执行H-T。二者只依赖已完成的RS01/DX03，可以在同一包内依次完成，无需等待预算或真实数据。planagent同时负责AL03近邻与替代解释审查；AL04准备共同的压力测试接口。随后AL05统一进行候选取舍与真实验证预注册。

本包输入：v1.4工作计划、原C代码与DX03/DX04审查、本文。新代码放入独立的research-runtime算法候选路径，旧A/C代码、配置、回执和100条暴露数据保持原样。

本包计算：已有本地CPU运行时、2线程、小规模合成数组/LP；m<=8，单次工作数组目标不超过512MiB，不安装大型依赖、不下载模型、不读取真实视频、不执行GPU或分类器训练。参数和开发样例先写配置；独立检查种子/场景与开发分开。数值种子不计为真实实验五种子门槛。

每个任务交付到research-runs/algorithm_search_20260918/：

- AL01/AL02_design.md：问题、公式、必要假设、最近方法差异、计算复杂度。
- AL01/AL02_evidence.json：输入/代码/配置哈希，固定对照与反例，实际命令、资源和结果。
- 可运行最小原型与逐案例结果；保留失败，区分解析命题、数值检查和未知项。
- round5_handoff.md：task_ids、计划版本/哈希、候选hypothesis_result=supported/refuted/inconclusive、可复核证据、下一项工作。软件通过不覆盖hypothesis_result。

先给可检查的数学/软件成果，再扩展。若AL01被反例否证，完成其负结果交付后继续独立的AL02；不因一个候选失败而停止整包。目标在9月19—20日形成第一轮取舍，时间是协调目标，不是强制杀进程的时限。

## 直接近邻与待核查风险

- [CRW](https://arxiv.org/abs/2006.14613)：路径乘法/软对应是继承基础。
- [Probabilistic Permutation Synchronization](https://openaccess.thecvf.com/content_CVPR_2019/html/Birdal_Probabilistic_Permutation_Synchronization_Using_the_Riemannian_Structure_of_the_Birkhoff_CVPR_2019_paper.html)：不确定对应与同步不能单独当作新颖性。
- [Measure Synchronization](https://openaccess.thecvf.com/content_CVPR_2020/papers/Birdal_Synchronizing_Probability_Measures_on_Rotations_via_Optimal_Transport_CVPR_2020_paper.pdf)：分布层面的循环一致性已有研究。
- [M3G](https://arxiv.org/abs/2405.19532)：多边际匹配已用于多视图表征；H-J须比较目标函数和输入信息。
- [High-order Tensor Pooling](https://arxiv.org/abs/2110.05216)：高阶池化本身已有先例。
- [SemanticMoments](https://openaccess.thecvf.com/content/CVPR2026F/html/Huberman_SemanticMoments_Training-Free_Motion_Similarity_via_Third_Moment_Features_CVPRF_2026_paper.html)：预训练语义特征的三阶时间统计是直接近邻，普通三阶统计必须作为基线。
- [D3](https://openaccess.thecvf.com/content/ICCV2025/html/Zheng_D3_Training-Free_AI-Generated_Video_Detection_Using_Second-Order_Features_ICCV_2025_paper.html)：二阶视频检测对照；不能仅提高统计阶数就宣称突破。

这些来源目前提供路线风险输入；摘要/公开入口的核对不替代全文公式、代码与实际复现。AL03/AL05分别记录检查深度，不能由本列表宣告新颖性通过。

## 真正的推进标准

AL01—AL04输出知识和可检验原型，不能直接称为CCF-A成果。AL05仅可放行候选进入真实验证；正式数据、预算、profile及冻结协议仍单独验收。最后仍须满足相对最强匹配基线macro AUROC增益>=0.03、配对95%区间下界>0、至少4/5种子为正，以及跨来源/未见生成器和全部混杂对照。
