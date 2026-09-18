# AL20 核查前输入与公式登记

包cc-al20-al24-baseline-matching-20260919，子任务AL20；新目录or1_baseline_audit。
工作单SHA256 7784b52940d94799926f867ea47ed01f5801be88455c7c6628a5fbb56dcfa3d3。
原AL15_evidence.json SHA256 076ae934e740d72943ca2e9f1b9c5cda27ffd8ecc2611a7ca8b386e88646c3ec。

只对下列3条预定基础维度、主h=1/8归档trace做数学读后核查：

1. linear_exact__development_base__sample_0__h0.125
2. nonlinear_remainder__development_base__sample_0__h0.125
3. noncommuting_but_redundant__development_base__sample_0__h0.125

固定取每族第一个观察，不因读出结果切换到另一向量。第一与第三的原数值设置可能相同，不能当独立样本。
JSON可为定位ID而解析整文件，但只有这三项进入算术，其他trace不探索、不筛选。
不导入或调用AL15 core，不运行probe、不拟合。若ID/摘要不符则保留失败，不另找替代。

先登记有限h公式：v_j=R_j-id，P_j=id+h v_j，

    d_a=[v_a(P_b(u))-v_a(u)]/h,
    d_b=[v_b(P_a(u))-v_b(u)]/h,
    K=d_a-d_b.

同一固定线性H与相同支持上，N=mean||HK||²=A+B−2C，其中
A=mean||Hd_a||²、B=mean||Hd_b||²、C=mean< H d_a,H d_b >。
每个三元组使用候选完全相同的分母D=mean||Hv_a||²+mean||Hv_b||²+eta。
本次归档核查只采用H=identity；真实四滤波不执行。其一般合同使用线性代数推导。

用Fraction.from_float把归档浮点数作为其确切binary值，核对向量/能量/共同分母恒等式。
归档q是浮点计算结果，另记录它与精确有理表达的差，并仅按已存标量复核舍入路径；
不把普通float差或显示值冒称严格数学相等。没有重调eta或候选lambda。

独立构造12×4的T，每列对应三元组系数(1,1,−2)，精确核对T^T T=6I。
只推导lambda与lambda/6在同函数子空间的关系，不做任何权重拟合或泛化推断。
协议/脚本/config/输入摘要先冻结提交，再执行本读取审查。
