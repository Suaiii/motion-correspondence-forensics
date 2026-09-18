# AL18 交接：条件数值合同有限CPU包完成

cc-al18-numerical-contract-20260919；AL18；researchagent_next。
执行任务01a0b54a-3a46-72c0-9f2c-58bdb49c6424。
工作树 `D:/SUAI/codex/worktree/662f/脉冲神经网络`；分支 `codex/al18-or1-numerics`。
冻结提交8ff3400先于首次候选调用；结果提交见交接消息。
原147项结果已单独归档0546f63；其后同包接口补充使用独立v2冻结4a771f7，未改v1结果。
建议进入conditional_numerical_contract_software独立review，不授予创新/真实模型/数据/付费阶段资格。

主计划v1.5 SHA256仍5cc4f7b994c79853913cecb8d1bad9a46156f584fd33ca4712aee85c7b3fc8ec。
AL18工作单已实读并绑定02f3f7dc2ee96fee2fa2439b84b94c971b111bd701153aab115e8fdb0e8f6b9c，
另读主DAG、AL15_REVIEW与AL16合同。主DAG未改，AL19未执行/等待，AL17未被当作真实probe准入。

## 实际交付

新目录or1_numerics实现N1/N2/N4/N5与固定w=1、threshold=0的分数误差式，纯stdlib Fraction。
先冻结8族147项实际输入/精确预期、源码/配置/依赖，再单次执行，所有预定角点和h=1/4、1/8、1/16保留。
没有未预期实现/覆盖失败，未发现所查界的反例；所有错误/未知状态本身均按预期保留。
以上仅针对原147项；之后planagent发现两项公开接口缺口，已另版处置，不能由固定集合通过覆盖它们。

主状态计数：有效条件区间24、正残差能量未证69、N5分母下界不正3、界未知/无有效依据12、非法输入39。
区间有效与能量资格分开；拒绝/低q/含0不映射为真实标签，所有origin_decision=null。
N5未通过的下界是hat_d−BD，不声称结构上d>=eta失效；未用eta兜底绕过指定稳定性门槛。

| h | N1两端delta=1/1024的B_K | N2四调用epsilon=1/1024、L=1的B_K | F8已知单端bias后的B_K |
|---:|---:|---:|---:|
| 1/4 | 1/32 | 1/64 | 1/64 |
| 1/8 | 1/8 | 1/32 | 1/16 |
| 1/16 | 1/2 | 1/16 | 1/4 |

N1相反符号达到界；N2的(-,+,+,-)与其反号达到界，完整16角点均保存。
N4得到BN=3/4096、分子[0,1/1024]；N5四个(n,d)角点全覆盖，不宣称最紧。
F8重复差精确0但unknown误差仍不认证；解析bias界来自mock定义，不从重复差推得。
固定score的正号稳定只表示数值性质，既未训练分类器也未给来源正确性结论。

## 成本与算术

192次有界identity R mock（48项×4），6次端点重复readout单列；156次数值合同查询是有理算术，不是额外AE。
AL15核心/真实AE调用均0，未重跑旧210项。每个R mock有完整输入/理想值/误差/输出账本。
安全比较全部Fraction无浮点容差；普通float仅展示，不称严格上界。
本批范数均有精确有理平方根；通用非平方dyadic包络路径未被这些固定例子触发，已注明。
数值范数统一Euclidean和sum平方，不与旧mean尺度混用。

两个stdlib数值worker实际出现，维度最大2，最大单数值容器估计288字节（非RSS）；无NumPy/SciPy/Torch。
wall .2213142秒、进程CPU .09375秒，不含启动/最终写出/写作。
没有权重/媒体/真实滤波/服务器/SSH/GPU/训练，无遗留进程。
项目累计使用仍unknown；6000元/初始180 GPU小时及所有正式门槛保持。

## 文件和摘要

源码research-runtime/algorithm_candidates/or1_numerics/{bounds.py,config.json,freeze.py,run.py}。
产物AL18_protocol.md、AL18_inputs.json、AL18_freeze.json、AL18_evidence.json、AL18_report.md、本报告和artifact manifest。
原AL01/04/06/09/12/15及or1_cpu源码在运行前后摘要未变；解释器和Fraction模块摘要已绑定。

| 对象 | SHA256 |
|---|---|
| bounds.py | 3ac18e29774aaa9f2eeecb593f2a8e8233d864b0a69cdd6156520fee640d5984 |
| config.json | 496888e78f5c0ddb58aadbe188648bcac2a4ddda48ccd48ac1b410950c01b6e6 |
| 全部输入/预期 | 3e91b7eddc14bcfbb7e541651f9e19b5d9d3d462696cd4aa0b9949684f93314a |
| 全部结果/账本 | b56917ec8688c534cddaf82ba3f2a503cd48f5388b9faf1cb26d42053e250c9f |

复核：E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/or1_numerics/run.py --output <new-path.json>。
不覆盖旧回执，不为复核重生一组样本。v1冻结源码未改，新增v2及定向回执单列如下。

## 同包接口问题和v2回归

独立审查的两项实际问题：N5 hat_q=NaN且B_D unknown时先返回未认证；N2忽略显式hat_k=[NaN]并为内部0给区间。
原样审查证据已归档AL18_interface_findings_source.json，SHA256
8e2bec74ec47ddce3de2437c5b52ddff3a9cffb882961f057f2ee1567ddd3604。
本执行者没有重跑这2个v1探针，原147项/旧AL15也未重跑。

bounds_v2.py先验证N5显式hat_q；N2先验证并支持显式hat_k、已知界时传入endpoint_result，
另明确公开schema拒绝未支持输出字段。原bounds.py/输入/结果均保持。
仅两模式及相关有效/未知/值消费/schema控制，共8种×3个h=24项，4a771f7先冻结后运行，全部通过。
非零控制hat_k=1/64返回实际1/64及区间[0,1/32]，未被静默替换成0。

| 新对象 | SHA256 |
|---|---|
| bounds_v2.py | 7a16a0f3335d57ff22d1409c0a3cc77273a05f8fc76d5a558d6b044bf764c5a5 |
| v2定向输入 | e76f638de2a7c3efa4c3c9fede72a10c94ab48a8a9cc5fb2624c4af9c9dcd94d |
| v2定向结果 | a1b268ac8b25b1a2c3551214160ee5e802d55a4c1c74adcf82b9a27a4b20c7a3 |

额外24次公开合同查询，新增R/端点readout均0；本执行者整个包为180次数值查询、192个R mock、6个readout。
planagent的2次v1审查探针外部单列。v2 wall .1141327秒，两worker上限下实见一个worker；没有声称v2全量重跑原147项。
新回放入口为interface_regression_v2.py run --output <new-path.json>，不覆盖定向回执。
原审查JSON的CRLF原字节保留，格式检查采用CRLF-aware设置。

下一具体建议：独立核对本包精确界/状态，然后审查是否需要新的静态wrapper数值元数据接入，
保持unknown/empirical/conditional分列，不能用这些mock的已知L/误差替换真实AE未知值。
实际probe profile仍需新候选/资源/来源/输出时钟与AL19相关合同的门槛；本包不自动派发或开启真实阶段。
