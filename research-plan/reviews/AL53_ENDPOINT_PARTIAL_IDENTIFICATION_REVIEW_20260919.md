# AL53：有误差与正则性先验时完整端点的部分可辨识范围

2026-09-19，planagent。AL53 仅作集合/误差界数学审查，没有数值例、模型、媒体、服务器或 GPU 调用。它补充 AL52 的精确非唯一边界，不能把未知真实 AE 的正则性填成已知常数。

对固定 probe R，已查询输入输出为 (x_i, yhat_i)，且真实输出误差满足 norm(R(x_i)-yhat_i)<=epsilon_i。若在包含查询点和目标点 p 的开域上有已知 L-Lipschitz 界，则

    R(p) lies in U_i(p) = closed_ball(yhat_i, epsilon_i + L*norm(p-x_i)).

若目标输入是估计值 phat、真实 p 满足 norm(p-phat)<=epsilon_p，用三角不等式将半径替换为 epsilon_i+L*(norm(phat-x_i)+epsilon_p)。在已知输出域 Omega 内，真正可行集合只能写成 U_R(p)=Omega intersection_i U_i(p)。

这是必要外包络；不同查询误差和 Lipschitz 界未必同时达到，交集不自动是精确可实现集合。若没有已知 L、输出域或邻域信息，集合可能无界，AL52 的非唯一性不会被有限软查询消除。

对 AL51 的两个未查询端点，若 U_a/U_b 分别是 R_a(r_b) 和 R_b(r_a) 的可行集合，则 C=R_a(r_b)-R_b(r_a) 落在 Minkowski 差 U_C={u_a-u_b}。共享网络/输入误差可能相关；没有相关合同只能用该外包络，不能拼两个分别最优端点。

若固定 q 读出分数 s 的误差集合完全落在阈值 tau 一侧，只能称给定先验下的决策集合稳定；跨越 tau 必须 undecided。它不提供来源正确性、AUROC、coverage 或跨 decoder 泛化。q 还需要 AL16 的分母正下界和平方误差传播。

AL52 的宽平滑类给出 C 不唯一；强而事前绑定的 L、输出域、误差和相关性先验可缩小集合，两者不矛盾。新增 R_a(r_b) 与 R_b(r_a) 是一般非碰撞情形的直接信息候选，碰撞/h=1/结构先验时可复用；是否值得调用由误差界、阈值分离和成本决定，当前均 unknown。

失败边界：经验局部斜率不作全域 L；valid-only 估计不作总体覆盖；两个端点分别可行不代表差值共同可实现；集合稳定不写成来源正确；不在 audit 后选择 L、阈值、fallback 或调用。AL53 的 pass 仅限 endpoint_partial_identification_design 公式清楚；无模型/媒体/训练/服务器/GPU，无新算法准入。
