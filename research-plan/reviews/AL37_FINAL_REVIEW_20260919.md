# AL37：macro、pooled 与五种子差的限定统计对象审查

2026-09-19，planagent。AL37 按 `paired_macro_seed_estimand_design` 范围结项为 done/pass。该 pass 仅表示统计对象和缺失处理的数学设计审查完成，不表示真实数据、训练、统计协议冻结或方法收益成立。

主对象固定为每个预定种子先求各生成器/来源组 AUROC，再求 generator-macro，最后求五个种子的配对差平均；pooled AUROC 和集成分数 AUROC 单独报告。共享同一真实负类池、正样本数为 `n_g` 时，pooled 是按 `n_g` 加权的组 AUROC；不同负类集合时才额外引入跨组排序，不能混写成 macro。

固定排序例子经 Fraction 计数核对：两组的组内 macro 均为 1，方法 macro 增量为 0，但组特定负类集合下 pooled 从 1 变为 3/4。该例没有真实样本、随机模拟或结果选择，仅用于阻止统计量混用。回执见 [AL37_MACRO_SEED_ESTIMAND_EXACT_20260919.json](AL37_MACRO_SEED_ESTIMAND_EXACT_20260919.json)。

重抽单位固定为祖先连通簇，簇内视图、真样本、生成样本和方法预测共同移动；缺失正/负类或生成器的重抽先记 invalid，不能事后补类或切到 view-level bootstrap。训练随机源、checkpoint 和匹配输入未绑定时，五种子保持 unknown；重复确定性头或 CPU 顺序不计作独立种子。

限制：尚未绑定真实样本、祖先清单、缺失比例、训练随机性、重抽代码或正式统计协议。因此本任务不释放 RS06/RS07/RS08，不改变 +0.03、配对 95% 下界>0、4/5 同方向门槛，也不构成 CCF-A 突破。
