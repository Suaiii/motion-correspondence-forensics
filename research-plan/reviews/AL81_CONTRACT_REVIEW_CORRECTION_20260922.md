# AL81完整估计量验收更正

本次planagent静态核对AL81工作单、core.py、reference.py、run_batch.py及其原始回执。旧源码/回执/交接保持原样；正式状态以主DAG及本文件为准。没有重跑旧批次。

1. core.macro按`generator[i]==g`分别筛负类；工作单与AL42规定每个生成器使用共享负类。两者是不同统计对象，不能把前者当后者通过。
2. 没有ancestor_id字段；权重以sample整数ID传入。`ancestor_A_double`把一个生成器所有正负样本一起加倍，无法检验跨类、跨生成器共享祖先及W²权重。
3. `auc_rank`使用正负双循环O(n_positive*n_negative)，reference.py也是逐对同一公式。没有实现预定排序累计负权重算法。
4. 配置中的两个seed/tag没有被runner消费，paired_macro未被runner调用；回执只包含candidate/baseline各自macro，没有标签间的配对差/均值。
5. 配置未冻结实际fixture分数、祖先与完整预期；非法输入拒绝、平局/全序/逆序/零权重独立基例及原始分子分母未完成。最终两项检查即使false也没有进入failures，因此`software_pass`并非全部检查的合取。

以旧runner全1权重的同一分数手工核对：原分组负类给candidate=15/16、baseline=11/16、差=1/4；若按合同改用三条共享负类，则candidate=23/24、baseline=2/3、差=7/24。此为条件分母改变的解析示例，没有真实模型或新性能结论。

AL81保持执行done，gate_result改fail；只能保留该旧fixture上两个类似逐对程序一致的观察，不保留共享祖先/种子配对/排序实现通过。AL82引用上述错误验收，依赖AL81 pass，故转review-blocked/not_evaluated；其JMLR来源与统计层次讨论仍可引用，但不能沿用对AL81实现的事实陈述。无需修改父任务或删除requires_pass来维持表面通过。

新AL83将在独立路径实现共享负类、显式祖先权重、固定generator/tag全集与排序累积点估计，完整冻结后与独立Fraction逐对参考核验。AL81的fail不回改，AL45的CI/IUT门槛不变。
