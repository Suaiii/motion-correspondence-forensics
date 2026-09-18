# AL12 直接近邻与构造差异审查

版本AL12-OR1 / 2026-09-19；仅资料与设计，未复现作者模型或训练。
对应设计见AL12_method_design.md。已纳入al14-prior-context-20260919资料补充。
下述“不同”仅指所查公式/流程不同，**不等于完整查新通过或效果优越**。
普通数学、额外处理数据及标签合同均不能各自充当算法创新。

## 1. G2VD：原始公式、标签与推断边界

直接读[G2VD 2607.04607v1](https://arxiv.org/html/2607.04607v1) III-B/III-C/III-D。
式(4)构造X_rec=D(E(X_r))；式(5)—(8)用真实与重建的RFFT幅度融合、保留重建相位；
式(9)再做像素融合。其X_cf在式(3)与因果分支式(10)/(11)中标为fake；
偏置分支式(12)—(14)将同一X_cf标为real，式(15)/(16)另加HSIC并加权两个分类损失。
推断仅用视频骨干及因果分支，不要求现场执行这些重建。

| 维度 | G2VD所查版本 | OR1设计 |
|---|---|---|
| 摄像来源的重建 | 因果分支将X_cf作为fake训练 | C_i^(1)/C_i^(2)仍为摄像来源0，处理属性另记 |
| 反事实对象 | 重建及幅度/像素对齐的训练样本 | 同一个u上两条已知软重建顺序的响应 |
| 核心约束 | 双分支标签目标+HSIC | 等调用量双顺序及一阶抵消；在同D同k层内排序 |
| 测试开销 | 原生推断不做CFIPipeline | 固定公共probe pair，4次AE调用，额外成本必须测量 |

OR1保持不同的来源标签目标，并不据此宣布G2VD标签错误。只改标签不能构成OR1贡献。
作者原生任务/标签应单列；来源标签适配版本是本项目适配，不能当作者复现成绩，
也不能用其对摄像重建的原生fake标签设置一个注定输掉来源FPR的对照。

## 2. 重建误差与重建对比：直接且强的重叠

### AEROBLADE

[2401.17879v2 §4式(1)/(2)](https://arxiv.org/html/2401.17879v2)定义单AE重建距离及多个AE的最小距离；
§5.5的“deeper reconstruction”是加入DDIM inversion/denoising步骤，**不能据标题写成已核实反复应用同一AE的算法**。
它已经覆盖“用公共AE探测未知生成图像”和“多个AE误差比较”的主要思想。
本轮先读v1，再核对v2对应段落；均不支持把§5.5写成反复AE的T^k。本设计的自重复AE仅是自定义强对照。
OR1区别在主动双顺序软步和抵消，而非仅使用AE或增加重建次数。
单步全误差、同4次调用预算的自重复重建，以及OR1全部端点对的学习器都是必要强基线。

### DRCT

[PMLR 235:7621–7639，ICML2024](https://proceedings.mlr.press/v235/chen24ay.html)及作者
[固定README 01aa7d0b6de903cf3208801f8f6b469edffbc762](https://github.com/beibuwandeluori/DRCT/blob/01aa7d0b6de903cf3208801f8f6b469edffbc762/README.md)
明确：真实/生成图像都经diffusion reconstruction，训练用margin-based contrastive；原真实标real，
生成、真实重建、生成重建这三类标fake。它已经覆盖“重建困难样本+对比训练”。
本轮没有获取完整论文损失推导，故不虚构其triplet公式/采样器细节，也不把README当论文逐式复核。
OR1的来源标签、同生产decoder/深度匹配和测试时双顺序响应不同；普通contrastive本身没有创新归属。

该README仅新增7,889字节，SHA256 `41d6e4dcc1a1a1622339f966ab68a7ee2363d501c0aeb95c8e2e62a752981351`；
已核验Git blob与固定commit，未读或运行其训练代码。PMLR PDF经网页工具转到octet-stream而无法解析，
OpenReview返回验证页；没有绕过验证。一个作者列表检索关联到2404.16687，实际为NTIRE质量评估论文，已排除，未当作DRCT来源。

### DIRE / FakeInversion

[DIRE 2303.09295](https://arxiv.org/abs/2303.09295)本轮仅摘要层补查；不以此声称新的全文复核。
[FakeInversion 2406.08603v1 §3式(5)—(7)](https://arxiv.org/html/2406.08603v1)已读：
从输入预测条件、DDIM反演及重建，把原图/解码噪声/重建供分类器使用。
它已表明确定性或近确定性probe可作为归纳偏置，不需要声称增加原输入的信息。
OR1不使用未知生成器反演或真实prompt，但固定公共probe与响应学习也不是新理念。
是否主动交换顺序确有增量仍需同信息、同计算量的强比较。

## 3. 普通增强、一致性与域对抗不是新损失

另外补读[Aligned Datasets Improve Detection of Latent Diffusion-Generated Images，2410.11835v3 §4](https://arxiv.org/html/2410.11835v3)：
只用AE重建摄像图像就构造fake训练集，普通BCE还比较是否在batch内显式配对。
因此“对齐重建数据+普通分类”已有直接方法；改为本项目origin-target必须写成适配。
它不自动等价于两条主动顺序路径，也不因原生R标签不同就可以被设为必输的来源对照。

下面是本项目必须实现的**通用对照定义**，不冒充作者的精确训练复现：

    L_aug = E_(u,Y,T) CE(f(Tu),Y),
    L_cons = L_aug + λ E ||f(Tu)-f(u)||²,
    L_domain: classifier minimizes L_Y, feature extractor opposes a domain classifier.   (B1)

T使用相同重建/传播池，来源标签不改变；对照获得同等配对和处理记录。
仅换成这类loss、加HSIC或多一个分类头，都不足以成为OR1差异。
[DANN，JMLR17(59),2016](https://jmlr.org/papers/v17/15-239.html)提供域对抗基础；
[CDAN 1705.10667v4 §3.1–3.3式(2)—(4)/(9)](https://arxiv.org/html/1705.10667v4)明确联合特征与预测的条件域对抗。
因此“条件”“分域”或“对比”不能作为查新通过的理由。
OR1不学习一个域判别器，不用未知测试域样本做目标适配；其候选部分是主动已知probe路径的抵消结构。
匹配排序损失仍是普通配对logistic，主设计已明示。

## 4. RIFT、WaveRep及处理顺序取证

- [RIFT 2609.00742v1 §2.4–2.5](https://arxiv.org/html/2609.00742v1)：沿用AL09方法核查，残差、serial correlation、条件NLL/MI已有。
  OR1不靠正交宣称独立，也不只是替换其micro统计；需比较同信息条件残差基线。
- [WaveRep作者项目](https://grip-unina.github.io/WaveRep-SyntheticVideoDetection/)及AL09继承的固定审查：VAE重建与法证增强是强相关基础。
  本轮未新增其源码或解锁全文，旧partial状态保留。频带替换/重建增强可与任意读出共用，不能给OR1独占配对数据。
- [Bayar–Stamm，Electronic Imaging 2018作者稿](https://research.coe.drexel.edu/ece/misl/wp-content/uploads/2018/04/BayarStammEI18.pdf)：
  本轮阅读摘要/引言的方法范围，已存在针对不同处理顺序的conditional fingerprints与CNN。
  OR1主动对同输入施加两种已知顺序，预测来源而非未知历史顺序，目标与输入不同；处理次序差异本身绝不原创。

如果普通处理历史在OR1中解释了效果，就只能报告处理依赖失败，不能把任务悄悄换成溯源来保住成功叙事。

## 5. 有限差异与剩余风险

### 新的直接近邻：Commutator-Induced Uncertainty in VAEs

[2605.23449v1 §3.1式(2)、§3.2](https://arxiv.org/html/2605.23449v1)已读。
该文在一个受训练Lie-group VAE内比较D_img(G_iG_j ξ)与D_img(G_jG_i ξ)，
并以生成元/BCH差异关联输出敏感度，随后约束该VAE。OR1不能首创“decoder顺序敏感”或二阶交换项。

| 映射层级 | 明确关系 |
|---|---|
| 响应模板 | 二者都是F(T_iT_j z)−F(T_jT_i z)；OR1形式上取F=identity、z=u、T_j=P_j^h |
| 算子约束 | 原文T为同一latent空间的指数Lie变换；OR1为两个固定完整AE的观测空间软重建，一般不是该Lie-group VAE类 |
| 局部阶数 | 原文BCH与OR1的Euler软步都含经典二阶交换项；除以h²不产生新数学 |
| 训练目标 | 原文训练VAE的不确定性/形变约束；OR1冻结probe，对同D同k的来源标签排序 |
| 可用信息 | 原文使用内部生成元/latent离散码；OR1不使用未知生成器latent，仅固定公开AE |

仅在抽象功能形式上相同，不足以认定带全部算子/训练约束的算法严格等价；但也足以否定该响应概念的独立首创。
剩余的可审查对象仅是来源匹配监督和完整重建probe的具体实例化。若这只是已有模板换任务而没有有用归纳偏置，
应在CPU执行前no-go。论文的物理/几何类比不作为OR1的真实性依据，本包未独立复核其完整理论。

| OR1设计部件 | 既有基础/是否独立贡献 | 本包能支持什么 |
|---|---|---|
| 公共AE探针 | AEROBLADE/DIRE/FakeInversion等已有 | 不作为创新 |
| 来源标签下重建数据 | 合同/监督目标选择 | 不以改标签当算法贡献 |
| paired logistic、条件匹配、归一化 | 通用学习/统计 | 不作为新基础数学 |
| 软步交换与二阶抵消 | 经典Taylor/交换子数学；2605.23449已有decoder顺序响应 | 响应概念不原创，具体实例待审 |
| 同D同k匹配+推断双顺序 | 在已查具体方法中未见相同流程 | 仅为受限构造差异，不是首创证明 |
| 真实条件来源增量 | 未测 | 不支持、不能放行GPU |

本轮已经命中直接顺序响应近邻；没有检索到完全相同训练/推断流程仍不等于不存在，相关实例化需独立查新。
若独立审查发现完整覆盖，直接no-go；即使结构不同，也必须击败全部一阶/重复/完整端点强基线。
特别地，完整端点输入已足以计算K；主张只能是有限数据下有用的归纳结构，不能声称信息论优越。

## 6. 下一审查建议

可将OR1送交**CPU代数/路径合同草案审查**，仅检查算子抵消、非交换但无增量的失败例与处理/标签一致性。
不因为采用经典数学就预先拒绝构造，也不因为写出新流程就宣布创新成立。
真实候选准入需要AL13合同、probe时间对齐及权重版本绑定、完整强对照、来源外/decoder外评估与预算验收。
