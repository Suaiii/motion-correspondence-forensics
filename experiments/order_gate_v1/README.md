# 有界的时序记忆必要性检查

600条预抽开发视频：300个新的Vript原视频前缀、150个OpenSora、150个t2vz，排除首轮120条对应的真实前缀与fake路径，并在预处理中排除匹配旧样本哈希的文件。按各来源60/20/20分为fit/calibration/audit。质量规则与上一轮一致，无结果导向补样。

四模型为未对齐/对齐 × GRU/无序均值池化MLP。均为49,601参数；无序池化对照保持CNN骨干，总参数匹配不等于计算量或优化难度完全匹配。缓存仅存两种输入表示，两个读出共享同一数组。3个种子、20轮、仅clean训练；不重复尝试训练配方。

主门槛在protocol.json中固定：clean开发audit上aligned_GRU相对aligned_bag的种子均值概率AUROC增益至少0.02、配对区间下界大于0，且至少2/3种子同方向，才支持继续扩大时序记忆研究。未通过门槛时降低SNN/状态输运优先级；这不是证明所有时序方法无效。

副检查为raw/align效果、两种图像域退化和8维无序残差统计逻辑回归。全部结果均报告。diagnostic_protocol.json固定8维统计及学习器，不做特征挑选。流程：tests→prepare→cache→train→statistics_probe→evaluate→decide。

所有脚本经E盘research-runtime/enter.ps1启动，数据和结果仍仅属于历史开发范围。当前不包含新生成器、独立真实来源或正式最终测试。预算为600条、缓存30分钟、GPU训练30分钟；不启动远程或付费任务。
