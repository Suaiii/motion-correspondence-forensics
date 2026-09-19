# AL48：误差界与读出决策间隔的条件审查

2026-09-19，planagent。AL48 仅作区间传播数学设计，没有重跑 AL16/AL32、模型/媒体/服务器/GPU调用或真实预测。

设固定权重 w、阈值 tau，q 的实际和实现值满足 |q_l_hat-q_l|<=B_q,l，评分实现另有绝对算术界 rho_s。三角不等式给

    |s_hat-s| <= B_s = sum_l |w_l| B_q,l + rho_s,
    s=w^T q.

因此若 |s_hat-tau|>B_s，实现评分与精确评分关于固定阈值同号；若落在 [-B_s,B_s]，只能标为 undecided/fallback。这个结论是数值决策稳定性，不能解释为来源标签正确、AUROC提升或跨 decoder 泛化。

AL16 的 q 界还要求每个实现分母有可信正下界 d_hat-B_D>0；没有下界、eta主导、支持变化、经验误差界或未知真实 AE 精度时，B_q 标为 unknown，不能写 certified。重复相同浮点结果不能替代误差界。

阈值、fallback 和 coverage 必须在查看 audit 标签前冻结；不稳定样本不能静默删除。coverage/risk、AUROC、来源正确率和未见组件迁移分别报告。该推导不放行 RS06/RS07/RS08 或 OR1 真实运行。
