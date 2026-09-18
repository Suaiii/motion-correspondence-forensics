# AL25 运行前协议：OR1-readout-1

唯一包cc-al25-filtered-readout-20260919，工作单SHA256
472e4f302d0ffce04bda5df972550e7781ecffeae18dc7c7cadf0d63e24c1e5a。
新目录or1_filtered_readout。旧AL12缺少完整边界/kernel的部分在此明确补充，旧草案/代码/结果不改。

## 固定数值与共同支持

float64 THWC，四个输入d_a,d_b,v_a,v_b同形；K先由d_a−d_b得到。
域为T=1..2、H/W=3..5、C=3；本批正常场固定[2,5,5,3]，每个原始数组150元素。
使用相关形式，不翻kernel：identity、5点Laplacian/4、Sobel-x/8、其转置Sobel-y。
全部采用空间valid内部，identity也裁到同一区域，无padding/插值/重采样。
本批输出形状[2,3,3,3]，每滤波/每场均对54个标量均匀取mean，含全部T/内部H/W/C。
复制的两个时槽不算独立样本。响应场不是RGB媒体，不按像素范围clip它们。
完整可机读合同在AL25_readout_spec.json；真实BCTHW、17帧、时钟/媒体入口仍pending。

每滤波保存N、E_a/E_b、D=E_a+E_b+eta、q_direct=N/D；
同时保存A/B/带符号C、z=(A/D,B/D,C/D)和raw q_compact=z1+z2−2z3。
输出顺序identity/laplacian/sobel_x/sobel_y，z12是各组三项拼接，不是匹配描述b。
额外保存raw(A+B−2C)及其先算分子再除D的诊断，但不替换主compact定义。
绝不abs(C)、裁负compact、改变eta或选择有利运算顺序。

## 独立精确参考

freeze.py仅stdlib/Fraction，不导入候选或NumPy。原始x=(col−2)/4、y=(row−2)/4，通道系数(1,2,−1)。
用解析算子结果构造完整带符号滤波参考，不调用任何候选相关实现：

| 标量场 | identity | Laplacian/4 | Sobel-x/8 | Sobel-y/8 |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 |
| 1 | 1 | 0 | 0 | 0 |
| x | x | 0 | 1/4 | 0 |
| x²+y² | x²+y² | 1/16 | x/2 | y/2 |
| x+y | x+y | 0 | 1/4 | 1/4 |

每个d/v场按工作单的尺度乘上述响应，再乘通道系数、复制到两个时槽。
对这些精确响应逐元素求Fraction均值，预存全部能量/内积/D/q/z。
eta的数学参考为1/10^12；同时保存实际float literal的确切binary有理数及其参考q，以分开表示误差。
所有原始场值都是可精确表示的dyadic数，冻结时验证float往返一致。

## 七场和三类错误

正常六场严格按工作单：全0、常量、x坡度、二次场、正内积(2u,u,u,0)、负内积(−u,u,u,0)。
第七场为(1+2^-28,1,1,0)，均乘固定通道系数；identity的精确N=2^-55，精确q严格正。
不追加随机场、旧trace或新的消去变体。
三类非法输入只为：不同shape（一个字段T=1）、一个NaN、共同空间边长H=2；全部在滤波前拒绝。

六个正常场的带符号响应、原始能量、z和q以绝对1e-12核查；每个实际float按自身binary值与Fraction参考比较。
第七场保存所有精确/浮点差，不对compact规定某个硬件固定结果；
只要求本明示非零dyadic差的direct路径保持非零、共同支持/核/带符号响应及有限性符合合同。
compact可因消去得到0或负小值，不能把它裁掉或解释成候选获得新信息。
该场也不以“低于普通容差”被描述为两条路径数学严格相等。

每场保存20个滤波响应数组（5个信号×4滤波）；检查它们的符号和完整共同支持，
因此坡度方向错误不能被仅平方能量掩盖。实际模型误差界始终unknown。
toy精确参考只是这一输入的算术基准，不提供真实AE认证；q=0、eta-only亦不判真。

## 冻结、资源和调用

提交全部源码、spec、实际输入/精确预期、依赖摘要后单次执行。
正常7次readout，每次20个合成场滤波与24个mean乘积，共140滤波/168 mean乘积；
3个非法readout在滤波前拒绝。实际AE/probe/AL15核心调用0。
仅NumPy/stdlib；Python主计算串行，NumPy原生线程cap2，使用ctypes核验自带BLAS配置。
每数组<=1MiB，原始每场150元素、滤波输出每场54元素；不把进程RSS冒充数组大小。
不使用Torch/SciPy、模型、权重、真实图像/视频、SSH/服务器/GPU或分类器拟合。

```powershell
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_filtered_readout/freeze.py
# 提交冻结之后：
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_filtered_readout/run.py
```

失败保留；已冻结实现修改另立版本/回执，不改预期/eta或隐藏负值。AL26由计划端独立处理。
本次仅filtered_tensor_readout_reference，AL05 fail及创新、预算、真实来源/最终集门槛不变。
