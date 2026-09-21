# AL79：逐样本时间分块RGB归约的新实现

当前研究端的provider配置失败已有回执，AL78最终为done/fail。planagent按持续科研规则在独立fallback-runtime/al79_rgb_reducer_20260922执行此CPU软件任务；不修改AL78、AL25、AL32源码、证据或工作树，不重复派发研究线程。

## 修复对象

AL78除了缺少Fraction参考，源码中的blocks仅用于检查而未实际切块，顶层filters将所有B样本合并，r_S使用H(d_a+d_b)而非AL32规定的Hd_a+Hd_b，验证病例与预注册不符。故不能沿用旧9项pass作为接口或分块通过。本包独立实现以下冻结定义：

- 输入已计算好的float64 RGB场d_a/d_b/v_a/v_b；显式BTHWC或BCTHW，无模型/媒体或新probe。
- 输出q形状B×4，r形状B×12，各样本独立。K在块内先作d_a-d_b再相关滤波；S在块内作Hd_a+Hd_b；r_K直接引用同一q值。
- 时间块是真实切片；每个块保存各滤波N、sum(HK²)、sum(S²)、sum(S·HK)、sum(Hv_a²)、sum(Hv_b²)。合并能量和与N，计算Dmean=(Va+Vb)/N+eta，然后分别计算q=(K2/N)/Dmean、rS=(S2/N)/Dmean、rJ=(SK/N)/Dmean。无跨B聚合或平均块比值。
- 四个核/valid内区/eta=1e-12同AL25；通道RGB，无DINO投影。拒绝无穷/NaN输入和中间溢出；输入及单个工作数组<=2MiB，已有NumPy/stdlib，环境原生线程上限2。

## 固定验证（代码与config冻结后仅一个正式批次）

沿用未通过的AL78问题，使用可复算的二进制有理数格点，避免Fraction把十进制字符串误认为实际浮点输入：

1. C1：B=2,T=3,H=7,W=8,C=3；不同B的场不同；时间块[1,2]。核对BTHWC/BCTHW、逐样本单独调用/调换B顺序与结果一致。每个样本用独立逐标量Fraction相关卷积核对N、五个能量和、q/r。
2. C2：B=1,T=7,H=9,W=7；每帧常数d_a=t+1,d_b=0,v_a=2^t,v_b=1，块[2,5]。核对总和归约与整段一致；identity滤波下均值块比值与全段比值必须出现可观测差异（>1e-3）。Fraction独立参考。
3. C3：全零RGB，B=1,T=2,H=5,W=5，块[1,1]；q/r为零且Dmean=eta。
4. C4：d_a=1,d_b=1-2^-26,v_a=v_b=1，B=1,T=3,H=5,W=5；identity q解析值为(2^-26)^2/(2+eta)，高通q=0；逐样本q与r_K须bitwise相同，无clamp。
5. C5：B=1,T=17,H=32,W=48，格点场，块[5,7,5]；整段/分块/两布局一致，记录实际过滤块shape，分块路径不产生全T过滤数组。
6. C6：B=1,T=4,H=7,W=7，d_b=-d_a，块[1,3]；S和rS/rJ为0，单步交叉能量负（独立参考），q保持非负；Fraction独立参考。

拒绝病例逐个验证ReducerInputError及码：缺场、shape不等、C≠3、空间内区为空、T/B为空、layout未知、dtype非float64、NaN/Inf、浮点/布尔时间边界、负/倒序/空/重叠/缺口/未覆盖时间块、单数组超限、有限输入引发中间溢出。仅捕获预期异常才算通过。

容差预定atol=1e-12、rtol=1e-11；Fraction使用Fraction.from_float获得实际输入和eta，标量循环不导入归约器核函数。实际数字/失败由程序写入，禁止手填通过。参考算术是独立实现的自测，仍不是不同研究者的科学复核。

## 证据和边界

先完成静态审阅/编译检查、配置、源码哈希与freeze.json，再运行一次run_v1。runner创建新目录且拒绝覆盖；失败时写error.json与已完成检查并停止，绝不删除重跑目录来制造pass。始终保留AL78 fail。记录真实ISO时间与wall/processCPU、源码/config/场字节哈希、块形状和数组最大规模；峰值RSS未知，不以数组规模冒充RSS。

交付reducer.py、reference.py、run_batch.py、config.json、freeze.json、run_v1/evidence.json、HANDOFF.md。任何软件pass仅释放readout接口，不能释放真实模型、媒体、来源、效能或创新门槛。至少两项独立后续保持：AL36反方准入，AL68现有服务器数据核验；另可准备无需真实模型的ProbeBatch输入身份连接检查，不重复旧toy或公开命名审计。
