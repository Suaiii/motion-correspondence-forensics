# AL50：配对图与最小费用匹配的误差稳定条件

2026-09-19，planagent。固定 Fraction 构造的 8 项检查通过；没有枚举实际匹配、读取样本、重估标准化、训练模型或访问服务器/GPU。AL50 只验收 `matching_perturbation_margin_math` 范围。

## 描述误差与 caliper 图

对标准化描述 b_i，设 `||e_i||_2/sqrt(p) <= epsilon_i`，则 pair RMS 距离误差满足

    |d_hat(i,j)-d(i,j)| <= epsilon_i+epsilon_j = delta_ij.

固定 caliper c=0.5 时，若 `d+delta<c`，边必然保留；若 `d-delta>c`，边必然排除。落在 `[c-delta,c+delta]` 内的边可能翻转。若标准化均值/尺度也重估，不能直接沿用 epsilon：在 `sigma>epsilon_sigma` 下，一个坐标可用保守传播项

    |b_hat-b| <= (epsilon_x+epsilon_mu)/(sigma-epsilon_sigma)
                  + |x-mu| epsilon_sigma/[sigma(sigma-epsilon_sigma)],

但真实 `x,mu,sigma` 与误差界仍需协议绑定。

## 同基数最小费用匹配身份

令 squared cost `C=d^2`。若距离误差界为 delta，则

    |C_hat-C| <= 2 d delta + delta^2 = eta.

对 cardinality m 的匹配 M，总成本误差至多 `sum_{e in M} eta_e`。若 M* 与次优同基数匹配 M2 的冻结成本间隔

    Delta = cost(M2)-cost(M*)

满足 `Delta > sum_M* eta_e + sum_M2 eta_e`，则 M* 的身份保持；统一界 `Delta>2m eta_max` 是更粗的充分条件。Delta=0 时字典序只提供确定输出，没有扰动鲁棒性；只保存最小费用值不够，必须保存匹配边、候选图、次优间隔和误差来源。

固定例用 present distances `[1/5,3/10]`、absent `[7/10,4/5]`、delta=1/100。present/absent 图边均远离 c；两同基数匹配成本差 `7/25`，粗稳定阈值 `101/2500`，满足严格间隔。该例是公式控制，不是 AL12 真实配对证书。

结论只说明怎样在未来绑定真实误差和间隔后认证离散配对不翻转。它没有说明 AL12 的实际匹配已稳定，也没有排除 caliper、标准化、祖先代表或输入分布混杂。AL23 的平局和 ID 记录要求保持；不能扩大 caliper、重排 ID 或在结果后重新配对。未放行真实实验、来源收益或 CCF-A 主张。
