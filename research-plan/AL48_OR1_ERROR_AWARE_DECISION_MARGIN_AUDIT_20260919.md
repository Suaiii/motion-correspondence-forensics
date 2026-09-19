# AL48：OR1 误差界与读出决策间隔的条件审查

负责人 planagent；接续 AL16、AL43、AL47。仅作符号/区间设计，不访问模型、媒体、服务器、GPU 或真实样本。

对固定分数 s=w^Tq 和阈值 tau，假定 AL16 的分子/分母界给出每个 q_l 的可信绝对误差上界 B_q,l；推导 `B_s=sum_l |w_l|B_q,l + rho_s` 以及 `|s_hat-tau|>B_s` 时决策符号稳定的条件。分别处理 `s_hat-tau` 落在 [-B_s,B_s] 的 undecided 区域、分母没有正下界、边界/支持变化和经验误差界。

将决策稳定性与来源正确性、AUROC、coverage 和跨 decoder 泛化明确分开。误差界未知或仅由重复浮点结果估计时，不颁发 certified margin；只登记 empirical_precision_check。固定阈值不得在标签结果后重选，低分/不稳定样本进入预定 fallback，不静默删除。

交付 AL48_OR1_ERROR_AWARE_DECISION_MARGIN_REVIEW_20260919.md 与 exact 公式回执；不重跑 AL16/AL32、不追加数据、不执行 JVP 或模型调用。研究资源/创新门槛保持。
