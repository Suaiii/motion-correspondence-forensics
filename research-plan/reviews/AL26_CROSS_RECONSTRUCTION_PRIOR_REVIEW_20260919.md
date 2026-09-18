# AL26：交叉重建与响应对齐的定向近邻

2026-09-19，planagent。完成4个定向查询及3篇新增primary正文审查。查新范围有限：本轮没有核实一个完整等同OR1四调用/双probe/匹配来源读出的先例，也没有据此取得首创或创新准入结论。

## 检索与证据

查询聚焦cross reconstruction、多个autoencoder重建、reconstruction trajectory以及commutator与forensics/reconstruction。精确查询、命中选择和访问情况见[清单](AL26_QUERY_AND_SCOPE_20260919.json)。本轮不将AL14已审AEROBLADE、DRCT、Aligned Datasets和2605.23449重新计为新增近邻。

CVF页面经web工具访问返回403；相同官方公开PDF使用普通无凭证HTTPS读取成功。PDF只在内存中解析，没有保存文件；正文临时提取共149,725字节，审查后移除全文缓存，只保留来源URL、字节数、SHA256和紧凑审查。[获取记录](AL26_RETRIEVAL_RECORD_20260919.json)不宣称本地存在完整论文副本。

## 直接相关的三类已有方法

**FIRE（CVPR 2025，§3.2–3.4）** 对原图和学习的频域掩码处理图使用同一个AE，拼接两张绝对重建误差图，再分类；训练还包含频域掩码及重建对齐项。它已覆盖“处理前后重建响应有用”和频率引导这类宽泛表述。论文所示路径与OR1的两个完整probe软步顺序交换不同，不能仅因都比较响应就声称等价。原生FIRE及同任务适配对照应进入后续比较设计，不能只比较单步误差。[方法正文](https://openaccess.thecvf.com/content/CVPR2025/papers/Chu_FIRE_Robust_Detection_of_Diffusion-Generated_Images_via_Frequency-Guided_Reconstruction_Error_CVPR_2025_paper.pdf)

**Beyond Generation（CVPR 2025，§3.2–3.3）** 以多强度加噪/去噪图构造特征学习任务，并包含无额外噪声的VAE重建类别；下游用真实图像特征的GMM似然判别。它提醒我们，处理强度和低层差异可以形成有用表征，不能将其收益独归双probe交互。其预训练及一类密度判别与OR1配对排序不同；本轮没有复现其方法或把其似然直接套用到OR1。[方法正文](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhong_Beyond_Generation_A_Diffusion-based_Low-level_Feature_Extractor_for_Detecting_AI-generated_CVPR_2025_paper.pdf)

**B-Free（CVPR 2025，§4及Fig.3）** 用真实图像的自条件扩散重生成和inpainting构造内容对齐训练集，并训练DINOv2初始化的分类器；纯AE重建作为对齐比较项。内容对齐/降低语义捷径已有明确先例，不能把“更公平的配对”本身当原创。该文把重生成样本放在fake侧；OR1的摄像来源R/R2标签合同不同，原生与来源任务适配版本必须分开，不能静默改作者标签后冒称复现。[方法正文](https://openaccess.thecvf.com/content/CVPR2025/papers/Guillaro_A_Bias-Free_Training_Paradigm_for_More_General_AI-generated_Image_Detection_CVPR_2025_paper.pdf)

未读取“Recovery-based Black-Box Detection…”的正文，不凭索引标题推断其恢复算子、适用媒体或与OR1是否等价。其余检索中的生成/增强论文和会议总索引没有用于方法判断。

## 对OR1主张和下一步的影响

结合AL14/AL20，当前不能单独主张以下概念原创：顺序差/局部交换项、重建对输入处理的响应、频域重建差、内容对齐，以及普通配对logistic损失。AL20又给出完整交叉增量三元组对q的精确包含关系。

尚待实证的是特定四权重约束、固定完整probe和既定来源合同的组合，能否在强匹配对照下形成可迁移增量。形式不同不证明有贡献；普通方法的函数类包含也不自动否定有限样本的归纳约束价值。必须对照紧凑自由读出及其相容正则、完整端点、普通处理响应，以及已有重建/内容对齐方法。

FIRE等原生图像方法与视频、来源标签及四调用协议并非直接同一条件。后续适配应明确输入、监督目标、参数和调用成本，原生结果单列；这份审查没有批准视频适配运行或新增训练。AL25保持既定合成读出工作单，不在运行中换成频域掩码、增加论文损失或重选输入。

AL26按 `targeted_cross_reconstruction_prior_review` 完成限定查新；创新准入与检测增益仍未通过。没有实际模型/媒体/服务器/GPU实验，没有把文献中的性能数字计入本项目结果。
