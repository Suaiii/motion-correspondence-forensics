# AL14：重建基线、标签与顺序敏感近邻

2026-09-19，planagent独立一手来源审查。为AL12设计提供输入，不修改其正在写入的文件。
本包没有运行作者模型、下载权重、读取媒体或判断候选真实效果。
AL12完整公式尚未交付，因此下面不作它与既有方法完全等价或创新已通过的判断。

## 1. AEROBLADE：独立探针取最小误差，deeper不是泛指反复AE

已读[AEROBLADE arXiv:2401.17879v2](https://arxiv.org/html/2401.17879v2) §4式(1)—(2)、§5.2及§5.5。
其原生距离为Delta_i(x)=d(x,D_i(E_i(x)))，多模型读出为min_i Delta_i(x)，较小距离指向生成图像。
它独立应用各AE，并不由该公式产生T_A(T_B(x))与T_B(T_A(x))的比较。
[作者仓库文档](https://github.com/jonasricker/aeroblade)保存负距离，因此max与论文的最小误差方向相容，不能误判符号。

关键更正：§5.5的Using Deeper Reconstructions增加DDIM反演/去噪的深度，t=0才是仅AE。
不能仅凭“deeper”标题把该节写成反复施加同一AE的T_i^k。
作者仓库的实验脚本名也不能替代方法定义。是否另有同AE迭代或异AE交错方法，应另给精确来源。

匹配基线须使用相同可获得AE池、输入帧与空间支持，保存每个Delta_i及其固定聚合。
原生图像协议、视频逐帧聚合适配和额外训练的误差向量分类器分别命名；
最优匹配AE的作者结果不能直接声称在未知decoder上可用，更不能将论文AP抄成本项目结果。

## 2. DRCT：原生标签与本项目来源控制不同

已读[DRCT正式PMLR论文PDF](https://raw.githubusercontent.com/mlresearch/v235/main/assets/chen24ay/chen24ay.pdf)
Figure 3、§3.1—3.3式(1)—(5)。四类训练数据为真实、真实重建、生成、生成重建；
原生二分类标签为真实0，其余三类均1。重建包含latent加噪与DDIM去噪，不只是VAE前向。
同类别特征对由margin损失拉近，异类别分开，再与分类交叉熵混合；论文默认margin=1、lambda=.3。

因此在本项目origin-target下把摄像重建R/R2标为摄像来源，是任务/标签适配，
不能把改标签后的训练叫原生DRCT复现。应保留原生processing-oriented标签结果作为独立轴，
另报匹配数据/容量、标签明确适配的对照，并披露额外训练和重建成本。
原目标下故意识别重建为fake，不等于在原论文自己的任务中失败。

PDF来自PMLR页面指向的公开文件，2,989,977字节，SHA256
79bff1d93c6fb548e4165da9707f637fdcaf081690def4682842f0f562c3a2a7。
本次仅在内存解析相关页，不在工作区保存大PDF，也没有复现作者代码。

## 3. AlignedForensics：匹配内容的VAE重建增强已有明确先例

已读[Aligned Datasets Improve Detection of Latent Diffusion-Generated Images，ICLR2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/9ead108421b202494d01b5060d12aa34-Paper-Conference.pdf)
§3—4：用摄像图像的纯VAE重建构建fake类，训练检测器；Ours-Sync在同一batch保留原/重建配对并同步增强。
这覆盖“用同内容重建减少部分训练混杂”的基本思路。该方法不要求在检测推理时再执行重建。
其标签目标、推理权限和计算位置，与本项目摄像来源反事实控制不同，必须分别比较。
不把“加入真实VAE重建”或“同步增强”单独作为本项目新颖性。

## 4. 新发现：解码器顺序敏感已有Lie-group VAE近邻

已读[Commutator-Induced Uncertainty in VAEs，arXiv:2605.23449v1](https://arxiv.org/html/2605.23449v1)
§3.1—3.2，特别是式(1)—(2)。它学习Lie群VAE，在固定离散编码下比较
D(G_i G_j z)与D(G_j G_i z)，并把解码器顺序响应与有限BCH偏差作校准。

这里的G_i/G_j是单个受训练模型内部的连续群作用，不是两个固定完整AE重建映射。
故“decoder order sensitivity”概念不是空白，但不能仅凭相同术语认定AL12的可能构造完全等价。
AL12应逐项比较算子作用域、是否学习探针、可见输入、校准对象、训练目标及推理资源。
本次没有采用该文所有几何/不确定性解释作为已证明事实，也未复核其全部定理或作者实验。
若候选用BCH解释完整非线性AE复合，必须给相应连续流、近恒等与可微等前提；
否则仅称有限次序响应，不能借用未满足条件的Lie理论保证。

## 5. 需要固定的强对照合同

| 比较臂 | 输入/处理权限 | 必须单列的差异 |
|---|---|---|
| 单探针和多探针最小误差 | 同一预定探针池与原帧，保存每个误差 | 训练free与训练后向量头分开 |
| 普通重建误差完整向量 | 候选获得的所有原始及中间路径输出同样可供对照 | 容量和路径/调用预算匹配，不以少看路径的弱对照替代 |
| 原生DRCT/AlignedForensics | 按作者标签与训练构造 | 处理目标不能与origin-target主表混合 |
| 来源标签适配版 | 摄像重建仍按已冻结来源目标处理 | 清楚标适配与再训练，不能写原生复现 |
| 若候选交换A/B顺序 | AB、BA路径都给普通特征聚合/误差对照 | 路径顺序、总调用数、随机性、缓存与后处理一致；次序效应不自动意味着生成效应 |

所有原生图像方法若改成视频，需要冻结帧选择、聚合、数据划分与计算成本。
若候选实际额外调用多个完整视频VAE，必须计入profile与预算，不能仅比较最后一个轻量分类头。
AL13已给来源/处理/祖先/时间合同；本表补基线原生定义，不放行任何真实批次。

## 检索深度与交接

对“commutator/autoencoder/generated-image detection”和“reconstruction order/diffusion detection”作了有限查询，
命中上述2026预印本。检索不是全面查新或专利检索；未命中同一完整构造不等于原创已证。
CVF读取路由403与OpenReview验证页未绕过，改读公开作者arXiv及PMLR文件；
DRCT的web解析器不接受octet-stream，因此用公开URL在内存中解析PDF。

已通过context_update_id=al14-prior-context-20260919向科研任务发送一次具体资料更正和近邻链接，
未重复派发AL12或启动实验。AL14可按primary_source_baseline_contract范围结项，
候选最终等价/差异判断仍待AL12完整交付及后续审查。
