# AL18 运行前冻结：条件数值界与不可认证状态

cc-al18-numerical-contract-20260919；AL18；v1.5。
工作单SHA256 02f3f7dc2ee96fee2fa2439b84b94c971b111bd701153aab115e8fdb0e8f6b9c，主计划SHA256
5cc4f7b994c79853913cecb8d1bad9a46156f584fd33ca4712aee85c7b3fc8ec，均在冻结时验证。
只读采用AL15审查和AL16 N1/N2/N4/N5；AL17不作为真实probe准入，AL19由planagent独立处理。
旧or1_cpu及AL15全部输入/证据不改、不重跑。

## 1. 数值约定与界的来源

统一Euclidean范数，能量为sum平方，不与AL15的mean比例混用。
所有安全运算使用stdlib Fraction，h与eta使用精确有理数；普通浮点仅写入display_only，不参与比较或充当向上舍入。
本包不实现通用浮点区间库、不运行低精度AE，也不把float64/Python显示精度当真实模型误差界。

观测值以有理数字符串保存；非法NaN/Inf用显式tag冻结，运行时还原为实际非有限float用于拒绝检查。
若接受有限float，语义是该binary float本身对应的精确有理值，不是它背后未记录的数学真值。

Euclidean范数的平方根若为有理数，使用整数isqrt验证并给出精确值。
否则以固定60位dyadic上下界包住sqrt(q)，用整数平方比较验证方向；安全公式使用上界。
本工作单的实际例子全落在精确有理范数路径，非平方分支没有额外测试，不扩充场景。

每个误差/Lipschitz界都带basis。受控mock的analytic_mock或exact_rational_arithmetic可作为条件前提；
unknown/None/缺项或仅empirical_repeat_agreement不得转为0，也不给安全区间。
declared_valid_assumption也只是调用者给出的条件，接口不替实际AE证明该假设。
本批由明示的identity+符号误差等解析mock验证前提，不把来源标签与数值认证混为一谈。

## 2. 实现公式与适用条件

全接口检查0<h<=1、eta>0、有限观测、非负有限界，向量维度1..8。
N1：B_K=(delta_ab+delta_ba)/h²+rho_K，返回Euclidean误差球及保守坐标区间。
N2：ell_j=1-h+hL_j；依次传播首级及两个端点误差，再送入N1。
首/末混合的实际观测与精确有理混合之差也须符合已声明rho，不能把观察到的额外误差忽略。
N4：B_N=2*upper(||hat_z||)*B_z+B_z²+rho_N，能量区间与非负集合相交。
N5：在hat_d-B_D>0时，

    B_q=B_N/(hat_d-B_D)+abs(hat_n)*B_D/[hat_d*(hat_d-B_D)]+rho_q.

固定w=1、threshold=0，B_score=abs(w)*B_q+rho_s；只检查严格正/负间隔或边界未分离，不输出来源判断。
带rho的最终K、分子或比值观测如被显式提供，还检查其与观测端点/能量/商的算术偏差不超过对应rho。
未给出额外算术观测时采用Fraction精确计算；这仅适用于当前有理mock，不假设真实混合算术误差为0。

## 3. 状态及优先级

| 状态 | 含义 |
|---|---|
| invalid_input | 非有限观测/能量、非法h/eta、负界或形状/数值合同冲突 |
| uncertified_bound | 存在unknown/缺失或无有效依据的误差/L；没有把它填0 |
| denominator_lower_not_positive | 规定的N5下界hat_d-B_D<=0，无法使用该N5稳定性证书 |
| residual_energy_not_certified_positive | 已有条件区间，但不能从给定界证明响应能量或分母残差能量严格正 |
| conditional_interval | 给定误差假设下区间成立，且本阶段要求的能量下界严格正；不是来源正确性 |

非法公共数值/观测先拒绝；unknown界先于后续区间推导。所有状态origin_decision=null。
有效区间与信息量资格分开：residual_energy_not_certified_positive仍可以返回有效区间，
不是说真残差必然为0。分别保存numerator_energy_lower与denominator_residual_energy_lower，后者为
max(0,hat_d-B_D-eta)。不凭eta正就宣布有可用残差。

对N5未通过的例子，数学结构d=e_a+e_b+eta确实给d>=eta；本包没有声称真实分母可为负。
状态说的是**工作单规定的hat_d-B_D检查未通过**，不使用eta兜底绕过这项稳定性/无信息域要求。
等于阈值的零区间仅标boundary_or_uncertain，拒绝或低q也不能转为“真实”标签。

## 4. 固定8族、147项记录

所有正常h取1/4、1/8、1/16，主1/8。每族全部角点都保留。
非法h例在每个nominal_h组内提交明确的0、5/4或NaN；nominal_h不被冒充实际合法h。

| 族 | 每h项数 | 实际输入与预定关系 |
|---|---:|---|
| F1 N1端点放大 | 4 | true_ab=(1/8,0)、true_ba=0；两端首坐标误差±1/1024；B=2delta/h²，相反符号达到界 |
| F2 零真响应伪响应 | 4 | 两真端点0，同四角点；观测K可非零，区间仍含真0 |
| F3 N2调用误差 | 16 | identity、x=(1/2,1/4)，a0/b0/ab/ba误差各±1/1024；全部16角点；B=4epsilon/h |
| F4 N4能量 | 2 | true_z=0，hat_z=±1/64，Bz=1/64；BN=3/4096，分子[0,1/1024]；d=1/4+eta、BD=0 |
| F5 N5比值 | 4 | hat_n=1/4、BN=1/16、hat_d=1/2+eta、BD=1/8；全部四个允许真值角点覆盖，不声称界最紧 |
| F6 分母/能量状态 | 2 | hat_d=eta、BD=2eta不通过N5下界；另一例BD=0、hat_n=BN=0无已证正能量 |
| F7 未知/非法 | 16 | 固定unknown端点/L、经验零界、负界、NaN/Inf端点/混合/能量/界、h/eta非法；详见config固定名册 |
| F8 相同但有偏重复 | 1 | 真端点0，两次读出均1/1024；unknown误差仍未认证，解析bias界另给覆盖0的N1结果 |

总(4+4+16+2+4+2+16+1)*3=147。没有新增随机/自选有利输入或误差符号，没有参数/阈值拟合。
冻结脚本仅按纸面闭式生成观测模板和精确预期，不导入候选bounds模块或运行probe。
候选返回值由独立预期和角点真实误差双重核对，安全比较不使用浮点容差。

## 5. 调用账本

F3运行48次四调用受控identity mock，共192次R调用；每次记录调用输入、理想identity输出、误差和实际输出。
这里是新的有界误差mock，未调用AL15核心，更不是实际AE。
F8每h两次常量偏差端点readout，共6次，单列为repeat_endpoint_readouts，不混入四调用推断成本。
其他族的端点/能量是固定提供的数值输入，不假称执行了模型来获得它们。
公开数值合同查询预计156次（F4每项N4+N5，F8每项unknown+known N1）；这些有理算术不是额外probe调用。

两次重复一致仅检查所列mock读出；源未知时不据重复差=0产生B=0。已知bias界来自mock解析定义，
不是由重复结果估计。所有记录显示来源、条件/经验资格与数学真值范围，不报toy AUROC或真假分数。

## 6. 冻结、资源和失败

新目录or1_numerics，旧or1_cpu和AL01/04/06/09/12/15档案校验但不运行。
先提交代码、配置、147项实际输入/预期、协议和外部依赖摘要，然后执行一次。
失败保存，已冻结源码修复须新版本/回执；不改标签、角点或h。
纯Python stdlib，两个数值worker上限；维度实际1/2（<=8），不分配NumPy数组，数值容器内存单列，RSS不作虚假推断。
不导入NumPy/SciPy/Torch，不读模型/权重、真实滤波/媒体，不SSH/访问服务器/GPU或拟合分类器。

```powershell
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_numerics/freeze.py
# 提交冻结后：
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_numerics/run.py
```

本包只验收conditional_numerical_contract_software。实际AE的误差/L/滤波边界/低精度安全、创新、来源/数据与付费阶段均不放行。
