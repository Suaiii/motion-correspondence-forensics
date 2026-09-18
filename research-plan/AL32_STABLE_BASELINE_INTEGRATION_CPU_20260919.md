# AL32：稳定紧凑读出与正则坐标的CPU集成参考

researchagent_next执行，当前派发以主DAG为准。依赖已审AL25/AL29/AL30；不修改三者历史文件。新目录or1_stable_baseline_reference。本包检验数值公平性，不训练检测器。

## 固定输入与稳定特征

只选AL25归档的positive_inner、negative_inner、near_cancellation三项；使用其已存带符号滤波数组、D、q_direct，不调用旧readout或probe。协议中先固定case ID与源SHA，冻结后仅做新坐标处理。

对每个滤波，定义s_H=已存H(d_a)+已存H(d_b)，k_H=已存HK，

    r_S=mean(s_H²)/D,
    r_K=直接复用已存q_direct,
    r_J=mean(s_H*k_H)/D.

这明确选择了已有滤波场相加的浮点路径，不声称与重新滤波sum场任意bitwise相同。r_K不能再由raw z三项相减得到；每项须核对与归档q的float.hex相同。存raw z/compact、r、矩阵重构差与所有符号，不能裁负、改eta、抹掉近抵消原结果。两次mean只是新算术，不计额外AE。

用固定w=(1,-2,1/2,0)，每滤波gamma=(0,w_l,0)。通过同一个四项评分函数比较q与r_K；泛用12维dot另记浮点差，不要求它无条件bitwise相等。固定w是数学控制，不是来源预测权重。

## 诱导正则与目标坐标

采用AL29的M=[[1,1,2],[1,1,-2],[1,-1,0]]，四组分块扩展B。r=B z、beta=B^T gamma，gamma正则必须为(lambda/6)gamma^T(BB^T)gamma，lambda=1/1000。候选嵌入的惩罚应与lambda||w||²相容。

独立部分仅引用AL30原三个已知回归面板（aligned/full_rank/symmetric）的冻结行，不纳入新scale面板，不求解或训练。对gamma=0和上述固定gamma两个预定点，比较：

    L_gamma(gamma; Delta-r) 与 L_beta(B^T gamma; Delta-z),
    grad_gamma=B grad_beta,
    Hess_gamma=B Hess_beta B^T.

输入变换/矩阵度量用Fraction建立精确关系；浮点目标/导数检查容差固定1e-12。两个部分分开保存，不能把三个响应场与抽象Gram表拼成实际来源数据。正则/目标/helper可只读复用已审定义，但不改变旧模块。

## 执行与交付

新实现、全部选择输入、固定权重/矩阵/精确预期和协议先冻结提交，再一次运行。三个归档field和三面板×两点均完整保留，失败另存，不添加有利场、不调整容差/权重、不优化参数。AL27旧fail和AL30回归身份保持。

交付AL32_protocol/inputs/freeze/evidence/report/handoff及artifact manifest；标明literal q复用、一般坐标的理想等价与实际舍入差。真实AE误差unknown；新代码不提供实际模型/泛化认证。

NumPy/stdlib，2线程，dim<=12，单数组<=1MiB；所有输入是已归档小型数学证据。无模型/权重/真实媒体、Torch/SciPy、SSH/服务器/GPU、优化器调用、真实训练、来源概率或AUROC。通过仅 `stable_readout_metric_integration_reference`。
