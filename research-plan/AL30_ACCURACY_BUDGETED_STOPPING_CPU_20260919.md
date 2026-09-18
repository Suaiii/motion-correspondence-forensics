# AL30：按参数误差预算定义停止条件的独立修复批次

执行researchagent_next，唯一dispatch以主DAG为准。AL27必须done，且其fail永久保留；本任务是失败后的新软件修复，不是原包续跑或成功支路。

输入AL27最终冻结与失败回执、reviews/AL27_REVIEW_20260919.md、AL23强凸性合同。新目录or1_head_accuracy_v2；只读复用原数学定义，不能改原or1_head_reference或旧报告/输入/结果。

## 唯一算法变更

参数验收仍epsilon_x=1e-9、目标差容差仍1e-9。mu=2lambda_head，停止阈值改成

    tau_stop=min(1e-10, mu*epsilon_x/2).

原始z、T、lambda_candidate=1/1000、lambda_free=1/6000、均匀权重、初始化0、最多200次迭代、Armijo c=1e-4、步长1按1/2缩小、下限2^-40保持。不得按结果改lambda、配对、阈值或额外添加Newton步。新模块在这条统一规则下自然停止。

记录数学mu、实际float正则、计算阈值和梯度残差。没有梯度舍入误差界，不能把这个策略称为认证误差<=1e-9；仍须与独立标量数值参考按原容差比较。严格保证需要另有||g_hat-g_true||<=mu*epsilon_x/2，不允许填0。

## 冻结检查

1. 原AL27三个面板原字节引用作为已知回归，标签明确regression，不当新增独立证据。分别保存新结果，不覆盖原失败。
2. 唯一新尺度检查：原full_rank的正侧偏移从1/4改为1/8，其余z0、T、lambda和12对均不变。它是优化尺度控制，不是重新定义原面板或实际来源数据。候选梯度仍在0精确消失；自由头对称标量导数为−delta/(1+exp(delta*b))+b/250，delta=1/8。
3. 空配对和非有限两类边界沿用。不要增加随机面板、超参搜索或分类性能评测。

实现、全部实际输入、阈值、解析预期和独立标量参考代码先冻结提交，再一次运行。标量参考保持固定[0,64]括区、宽度1e-13、最多128次二分，保留全部导数轨迹。结果按参数/目标1e-9检查，若仍失败则原样交接，不二次放宽/搜索。

区分旧AL27失败、原面板回归和唯一新增软件控制；所有目标/梯度/Hessian、试探/接受步长、调用和失败完整记录。一次修复解决的是停止条件与既定精度的尺度关系，不改变科研假设或宣称真实收益。

## 资源与产物

AL30_protocol/inputs/config/freeze/started/evidence/report/handoff及artifact manifest；新目录独立。NumPy/stdlib、2线程、维数<=12、每面板配对<=12、每数组<=1MiB。仅上述合成凸目标求解，无模型/读出/probe、真实媒体/数据、Torch/SciPy、SSH/服务器/GPU、真实检测器训练、来源概率或AUROC。通过仅 `accuracy_budgeted_optimizer_reference`。
