# 居中三帧 C 软件实现与对照验证

DX03；cc-round-3-c-software-20260918；cvpr27-20260918-v1.2。
执行日期2026-09-18；源码起点40f5bb0084955ef7e16edd23b872767047237779。
状态：离线软件交付完成，待计划端范围验收。科学机制与真实数据门槛未通过。

## 实现与假设

显式配置为 [candidate_c_centered3_v1.json](../../research-runtime/server/configs/candidate_c_centered3_v1.json)。
新增 choose_centered_three，按末首 PTS 差加中位帧间隔估计 D，中心为首 PTS+D/2，
目标为中心前后0.5秒及中心。D≥1.5−1e-6、最近帧、1e-9平局选早、最大误差
0.125秒加1e-6数值容差、三个原帧互异。误差界仅是软件资格，不是来源时间匹配证明。
原 choose_six 保持不变；相同输入下 C 与 A 的1/3/5位置在已测 CFR/VFR样例中一致。

NumPy/Torch 新增 correspondence_response，按显式 candidate_id 选择帧数及三元组。
旧 six_frame_response 是 A 包装器，默认仍是六帧六组；未知候选/B被拒绝。
响应公式、温度与三种尺度不变，不对静态响应人为归零。
LocalComposability 默认仍为 A，C 必须显式指定，不能把三帧补成六帧。

| C 比较臂 | 局部三元组 | 语义输入 | 独立对应矩阵 | 组合乘积 | 可训练参数 |
|---|---|---|---:|---:|---:|
| temporal | (0,1,2) | 同三个全局向量 | 3 | 13 | 217,057 |
| static | (0,0,0)、(1,1,1)、(2,2,2) | 同三个全局向量 | 3 | 39 | 217,057 |
| anchor_static | (0,0,0) | 同三个全局向量 | 1 | 13 | 217,057 |

anchor_static 仅为起点匹配诊断，局部只观察帧0；不能替代同三帧 static 强基线。
固定模型的分支替换继续标为敏感性，不称为静态重训。
make_candidate_control_models 创建三个参数初始化相同、存储独立的头；
本轮只有前向及梯度检查，没有优化器步、分类拟合或 checkpoint选择。

## 可追踪的输入、缓存与 checkpoint

descriptor 记录 candidate_id、frame_count、triplets、branch_mode、aggregation、
control_scope、支持模式、采样源码哈希、温度/尺度/网格及语义帧。
响应图额外记录实际算子设置；分类头拒绝候选、组定义或算子不匹配的图。

cache_identity 要求原始/处理视频/骨干SHA256、严格递增且互异的原帧索引、
有限递增PTS、预处理、精度和增强身份。协议与这些字段共同生成摘要，不能仅凭
特征形状或文件名认定兼容。它不会自动把旧 A/八帧缓存转换为 C；真实数据中
有条件的逐帧复用仍需另行核对像素、处理流、原帧与骨干身份。

checkpoint_payload/load_compatible_checkpoint 要求匹配完整协议和头结构。
缺少身份的旧 raw state_dict、A/C互用、不同分支、旧采样哈希、异常参数形状、
dtype或非有限值均拒绝；检查发生在权重加载前。
PyTorch 原生 load_state_dict 仍是底层复制接口，工厂仅用它复制新头初始化；
**实验恢复必须走兼容性接口，不能直接加载未标记的旧权重绕过检查。**
这些接口尚未验证来自真实训练的 checkpoint或分布式/GPU状态恢复。

candidate_training_specs 生成 temporal/static及可选anchor的独立配方记录，
要求清单、划分、种子、增强、优化器、选择规则、头结构一致，诊断身份分别保存。
这只是未来训练规则检查，未冻结真实实验清单或授权训练。

## 实际验证

[最终验证回执](candidate_c_cpu_validation.json) 记录33项通过：原21项A回归完全保留，
新增12项C测试（含多个子用例）。覆盖C与A子集、VFR、时长/误差容差、平局、
重复/缺失/非有限/倒序PTS、三帧形状、NumPy/Torch一致、相同语义、容量、
独立参数存储、输入detach、可训练头梯度、语义回退、固定头敏感性、
平移null、缓存区分、checkpoint拒绝及配方一致性。

最终执行时间10.815秒（含检查后接口与null证据收集），Python3.11.15、
PyTorch2.5.1、NumPy2.2.6、本地CPU两线程，CUDA未初始化。
使用已有环境，无依赖安装。此前两次通过回执保留为 initial 和 checkpoint_checks，
最终审查以 candidate_c_cpu_validation.json 的源码哈希为准，不覆盖旧科研证据。

| 合成条件 | temporal/anchor 响应最大差 | 解释 |
|---|---:|---|
| 循环平移特征、完整支持 | 4.44e-16 | 满足精确等价条件；分类头logit等价也通过测试 |
| 相同平移、固定内部支持 | 0.550633 | 掩码破坏交换条件，不能外推完整支持等式 |
| 非交换重排、完整支持 | 0.146647 | 固定空间扰动受中间索引几何影响 |

非交换重排的直接JS差仍约1.87e-16；直接组合的置换不变与固定空间扰动响应的
非交换性应分开解释。所有数字来自随机合成token，没有真实DINO或图像平移证据。
它们不是检测效应量、AUROC、显著性或算法创新成绩。

## 资源与限制

没有SSH、开机、ffprobe、媒体访问、模型下载、骨干推理、GPU或真实训练。
费用/计费小时/报价仍未知；没有激活PTS合同，没有重复账单探测。
当前实例状态未刷新，旧关机证据仅是历史观测。观察到的组合乘积差异不等于
FLOPs或GPU墙钟比值，未执行完整视频profile。

建议仅验收 offline_software_only。下一真实工作仍需明确预算/本批额度、
源清单与祖先检查、完整PTS以及采样支持审计，然后才决定机制实验是否放行。
本实现不能支持CCF-A录用、专利新颖性或阶段性创新已经成立的结论。
