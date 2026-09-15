# 首轮神经网络训练结果

本轮为本地开发 pilot，不是论文主结果。全部模型从随机初始化训练，未下载预训练权重。

| 模型 | 条件 | AUROC 均值±种子标准差 | BAcc 均值 |
|---|---|---:|---:|
| frame_mean | clean | 0.5972 ± 0.0347 | 0.5833 |
| frame_mean | jpeg70 | 0.5949 ± 0.0382 | 0.5833 |
| frame_mean | gaussian5 | 0.5972 ± 0.0347 | 0.5833 |
| raw_temporal | clean | 0.6806 ± 0.0208 | 0.6250 |
| raw_temporal | jpeg70 | 0.6875 ± 0.0139 | 0.6250 |
| raw_temporal | gaussian5 | 0.6759 ± 0.0145 | 0.6389 |
| aligned_temporal | clean | 0.8056 ± 0.0184 | 0.6944 |
| aligned_temporal | jpeg70 | 0.8125 ± 0.0120 | 0.6944 |
| aligned_temporal | gaussian5 | 0.8310 ± 0.0488 | 0.7083 |

同一clean开发校准集选择 checkpoint 与阈值，阈值固定应用于三种条件。audit从未用于训练早停或改分数方向。种子标准差不是数据集置信区间。

训练样本保留 118 条；分组计数：{'fit': 70, 'calibration': 24, 'audit': 24}。质量剔除和原因见 qc.json，无替补样本。

raw_temporal 与 aligned_temporal 都是相同CNN+GRU，仅残差对齐不同，使用共同有效mask；frame_mean是逐帧CNN表征均值分类，容量不同，不能当作严格等参数时序对照。

clean为统一4fps、中心2秒、方形中心裁剪128px的开发输入；jpeg70和gaussian5是在空间预处理后生成的图像域压力条件，不是实际平台转码。

剩余局限：只有Vript真实源与两种旧生成器；已有历史数据被检查；没有语义匹配、独立来源最终测试和全面内容去重。输入统一不保证彻底消除编码/重采样捷径。

已保存逐视频概率、每轮损失、最优checkpoint、模型参数量、训练耗时、峰值显存及加载复核。这里只报告实际训练结果，不说明SNN优于ANN，也不作CCF-A可发表性结论。
