# AL25：四滤波共同支持读出与紧凑基线的CPU实现

执行researchagent_next，唯一派发ID以主DAG为准。输入AL12、已审AL20及AL16/AL19的数值/坐标限制；新目录or1_filtered_readout，不改旧源码/输入/结果。

此包补充此前未完全指定的边界与kernel，标识为 `OR1-readout-1`，不回写AL12历史草案。仅NumPy/stdlib合成张量，没有模型或真实媒体。

## 固定实现合同

输入为已给定的d_a,d_b,v_a,v_b四个同形THWC数组，K=d_a−d_b。仅T=1..2、H/W=3..5、C=3的有限参考域；暂不接入BCTHW真实wrapper或17帧probe，T仅mock槽位。浮点主路径固定float64。

空间算子使用相关形式（不翻kernel）：

- identity；
- Laplacian：[[0,1,0],[1,-4,1],[0,1,0]]/4；
- Sobel-x：[[-1,0,1],[-2,0,2],[-1,0,1]]/8；
- Sobel-y：Sobel-x转置。

所有滤波使用共同valid内部区域；identity也裁到H-2、W-2的同一位置。每个通道分别计算，不padding、不重采样，所有输出在T/内部H/W/C的全部元素上均匀取mean平方/内积。缺共同支持或非有限输入拒绝，不补齐。

每个滤波保存N=mean(HK)^2、E_a/E_b、D=E_a+E_b+eta及q_direct=N/D，eta固定1e-12；同时保存A=mean(Hd_a)^2、B、带符号C=mean[(Hd_a)(Hd_b)]及z=(A/D,B/D,C/D)、q_compact=z1+z2−2z3。内积不得取abs，分母/支持与候选完全共用。

先相减后取能量与先做三个能量/内积再相减在有限精度下可能不同。保留原始compact值、差值和精确参考，不能静默裁负值、改eta或把消去误差包装为候选信息增益。真实误差界保持unknown；这次toy的精确参考不提供真实AE数值认证。不拟合w或输出来源标签/概率。

## 七个预定算术场景

T=2,H=W=5,C=3；x=(列索引−2)/4，y=(行索引−2)/4。把下列标量场乘固定通道系数(1,2,−1)，复制到两个mock时槽。只为mean/通道/边界合同，复制不作独立样本。

1. 四场全0：q=0、分母仅eta，不能判真。
2. d_a=1,d_b=0,v_a=1,v_b=0：恒等有能量、三个导数滤波为0。
3. d_a=x,d_b=0,v_a=x,v_b=0：核验线性坡度及方向；mean尺度明确。
4. d_a=x²+y²,d_b=0,v_a=x²+y²,v_b=0：核验离散Laplacian/方向响应和同支持。
5. u=x+y，d_a=2u,d_b=u,v_a=u,v_b=0：正内积与差分能量。
6. u=x+y，d_a=−u,d_b=u,v_a=u,v_b=0：负内积保留，不能被abs覆盖。
7. d_a=1+2^-28,d_b=1,v_a=1,v_b=0：相近交叉量的消去诊断。完整记录浮点差；不以普通容差把两个路径描述成数学严格相等，也不要求所有硬件恰产生同一消去值。

这些是给定响应场的软件输入，不声称由真实AE产生。执行前用独立Fraction参考/解析关系固定期望和容差：正常场能量/重构绝对误差1e-12，消去场另报精确正值、实际差和运算顺序，不事后改阈值。参考生成不能调用候选滤波实现。

额外合同仅三类：不同shape、任一NaN、空间边长<3，全部拒绝。先冻结实现、全部实际输入、协议/精确预期和依赖摘要，再单次执行；所有失败保留，新修复独立版本。不调用AL15/core、AL18或模型来生成输入，不追加旧trace或随机场。

## 交付和资源

AL25_protocol/readout_spec/inputs/freeze/evidence/report/handoff及artifact manifest；注明选定的valid边界是新的明确补充，真实部署兼容尚未验证。输出支持数、4维q/12维z、所有原始能量及状态、精确/浮点差、哈希、成本和失败。

仅NumPy/stdlib、2线程、每数组<=1MiB，最大原始张量150元素。允许本工作单的合成空间滤波；无Torch/SciPy、真实图像/视频、权重/模型、SSH/服务器/GPU、拟合分类器或toy AUROC。通过仅 `filtered_tensor_readout_reference`，不释放创新、数据或资源门槛。
