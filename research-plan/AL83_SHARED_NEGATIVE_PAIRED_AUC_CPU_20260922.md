# AL83：共享负类与祖先权重的完整配对macro点估计

执行者planagent，按持续科研CPU接管授权在独立fallback-runtime/al83_shared_auc_20260922实施。外部provider故障已有回执，不重发AL36/AL68、不创建会话或代理。AL81原始fail保留；本任务以AL37/AL42的定义为父成功条件，AL81仅为已完成失败输入。

## 固定定义与接口

- 每条record包含唯一sample_id、ancestor_id、label(整数0/1)以及generated类的generator；负类generator必须null。每个生成器正类与**全部共享负类**比较。
- 权重字典按祖先给定非负整数（拒绝bool），全体sample/method/tag使用同一个字典。正负同祖先的pair权重W²保留。权重缺失/额外、负数/分数/NaN非法。
- 显式固定methods=[candidate,baseline]、score_tags=[diagnostic_a,diagnostic_b]、generators=[g1,g2]，每个method/tag必须有恰好全体ID的有限分数；label/generator/ID错误均拒绝，禁止从现有scores推断缩小全集。两个tag只是人工诊断，不是训练种子。
- 先逐tag/g得到AUROC，再generator等权macro；delta[tag]=candidate_macro-baseline_macro，最后tag等权mean_delta。任何必要组缺正/负权重则返回invalid原因与null，不计算valid-only总体或悄悄改G。
- 主算法按分数排序/合并同分块，累计较低负类权重，保存two_U整数分子和denominator=2*Wp*Wn，O(n log n)；独立参考用Fraction逐pair比较，不import主模块或复用排序/选择帮助函数。

## 固定输入与验收

config明确保存六条样本、四个祖先A/B/C/D、两个generator和两个tag的全分数表。正负跨类共享A/B，负样本3条供两个generator共同使用；g1有2条正类、g2有1条。权重四例：全1、仅A加倍、B为0导致g2无正类、全0。全1手工预期candidate/baseline tag-a为23/24和2/3、delta=7/24；tag-b各3/4、delta=0，均值7/48。A加倍均值1/8（逐项明细写config）。

额外解析检查：全同分AUC1/2、全正序1、反序0、一个零权重；行顺序逆转不改结果；改一个method/tag使另一个tag保持且汇总改变；同祖先正负的加权tie项必须明确保存。主输出每个cell原分子分母和Fraction参考完全一致，不以两个最终均值相同代替。

拒绝案例：重复/空ID、缺ancestor、label不为0/1或bool、负类附generator/正类缺或未知generator、缺少/多余method/tag/sample分数、非实值/bool/NaN/Inf分数、缺少/多余/负/非整数/bool祖先权重。测试只捕获预定InputError及错误码；异常或失败必须进入最终failures。

## 执行和证据

标准库1线程，无媒体/模型/服务器/网络/随机/bootstrap/训练/CI。源码、config、拒绝清单和参考先保存，静态审查/编译后freeze，再提交冻结版本，执行一次新run_v1。输出拒绝覆盖；失败保留traceback、部分checks与exit code，不删除重跑目录。真实ISO时间、wall/processCPU、输入/config/源码与历史保护哈希自动写入。

交付core.py、reference.py、config.json、run_batch.py、freeze、run_v1/evidence和HANDOFF。仅统计软件通过，不实现CI或宣称真实增益；自测不冒充另一科研者复核。结束后准备AL84四调用输出身份桥接（不依赖该统计模块），AL36与AL68仍为独立后续；不能停在空队列轮询。
