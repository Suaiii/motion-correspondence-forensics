# AL81：固定祖先权重的配对macro-AUROC计算原语

planagent依据持续科研CPU接管授权，在独立fallback-runtime/al81_paired_auc_20260922实现。已记录researchagent provider启动失败，不重复派发；这是独立的估计量软件，不依赖AL45的IUT审查通过，不使用真实分数/媒体/模型/服务器/GPU。

## 数学与接口

沿AL37/AL42固定目标：每个生成器的正样本与共享负样本构成视频边际AUROC，各视频权重等于其祖先簇的给定非负整数权重。所有方法、种子、类和生成器使用同一权重字典；正负来自同祖先时出现W²项，不偷偷排除。每个诊断种子先generator等权平均，再对种子等权平均candidate-baseline差。单个generator/seed/方法缺支持时整个macro为invalid/null，禁止缩小G或只平均valid项。

主实现为分数排序的累计负类权重算法，精确处理平局1/2，O(n log n)；独立参考为标准库Fraction逐正负样本对求和，不调用主排序函数。整数权重用两倍U整数分子保存，不用不必要的浮点舍入。

输入为固定小型合成fixture：6个样本、4个祖先（正负跨类共享A/B）、2个生成器、2个明确标为diagnostic而非真实训练的score tags、2个方法。主表完全写入config；权重含全1、A加倍、删去g2全部正类、全0四种。额外解析基例为全平局、完全正序、完全反序和带零权重。不得用这些人工分数声明检测/泛化收益或4/5种子标准。

检查每个方法/tag/g的原始分子分母与Fraction参考完全一致；共同权重与W²语义、行顺序不影响结果、缺类/全0保持invalid。拒绝重复ID、无效标签、缺失/多余分数、NaN/Inf、负/非整数/布尔/缺失祖先权重。scores为有限实值logit，无概率范围假设。

源码/config/预期先freeze，再运行一个批次写新的run_v1，失败/exception保留，不删除重跑。标准库，1线程，无随机/训练/bootstrap。交付core.py、reference.py、config、runner、freeze、run_v1/evidence与handoff；自测不计独立科学审查。

本包不选择最强基线、不构建置信区间、不解决cluster-bootstrap覆盖率，AL45仍为独立方法学门槛。软件通过仅使未来冻结预测可计算正确的描述性配对统计，真实来源、科学准入与最终集门槛不改变。后续两项保持AL36反方审查、AL68数据核验；统计推断只在其方法学条件单独明确后实施。
