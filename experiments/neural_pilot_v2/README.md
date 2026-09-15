# 第二版训练配方调整

在第一版训练和开发校准曲线显示过拟合后、两版任何audit评测之前，冻结本版本。网络结构不变；学习率0.0003，weight decay0.01，训练批次均匀选clean/JPEG70/gaussian5，并做序列一致水平翻转。

仅以clean calibration选择checkpoint和阈值；audit不参与调整。JPEG70与gaussian5为已见训练条件，不宣称未见退化泛化。多个因素一起变化，结果不能归因于单个超参数。

缓存来自neural_pilot_v1，经输入、协议契约、manifest和各缓存文件SHA256验证后，以同盘硬链接只读使用。代码快照、配置、每轮损失、最优权重、加载验证及逐视频预测分别保存。

执行顺序与v1相同：prepare、cache、train、evaluate；始终通过research-runtime/enter.ps1，使用新的run-dir。结果及负结果见research-runs/neural_pilot_summary_2026-09-08.md。
