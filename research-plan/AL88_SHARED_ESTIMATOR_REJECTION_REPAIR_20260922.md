# AL88：共享祖先点估计器拒绝测试修复

AL85审查发现：invalid-suite runner 将完整 weight-schemes 字典传给 core，而不是选择 `all_one`，因此缺 method/tag/score 等病例都在权重键检查处短路，证据中的“通过”没有核对预定错误码。AL85的源码、输入、输出和pass判定保持历史，不覆盖。

本包复制AL85的固定源码/config/reference，仅修复测试驱动：每个非法病例统一使用冻结 `all_one` 祖先权重，确认其实际预定错误码；valid cells、Fraction参考、四种权重、顺序不变性和tag差异重新执行一次。输出每个拒绝案例的输入变更与错误码，任何异常/错误码不符都导致fail。

先静态编译并冻结新runner/config/source哈希，再运行唯一v2批次；不改AL85历史目录。无模型、媒体、网络、服务器、GPU、bootstrap、CI或真实数据。
