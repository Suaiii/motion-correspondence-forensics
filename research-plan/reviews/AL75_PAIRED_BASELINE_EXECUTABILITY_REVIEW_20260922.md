# AL75：OR1强匹配基线的可执行性缺口

- 实际完成：2026-09-22T03:39:07+08:00
- 审查者：planagent；仅接口/证据合同审查，未运行toy、模型、媒体、服务器、GPU或分类器。
- 输入记录：`AL75_INPUT_RECORD_20260922.json`，SHA256 `d010adb8f4f24455170ca539f55ce3583b08be3cb66c9dc0f7332f83f5158004`。

## 已有接口能做什么

1. `or1_filtered_readout/readout.py` 的 `compute` 只接收四个 `float64`、THWC 布局、同形状数组 `d_a,d_b,v_a,v_b`；限制为 `T=1..2,H/W=3..5,C=3`，在共同空间内用四个固定滤波器输出 `q4_direct`、raw compact q 和 z 诊断。它拒绝NaN/Inf、形状不一致和超出小参考域的输入，返回 `classifier_fitted=false`。
2. `or1_stable_baseline_reference/kernels.py` 的 `four_term_score` 只实现四个标量特征的固定加权分数；`fixed_objective` 接收12维抽象差分、参数和度量矩阵，用于AL32算术检查。它没有视频帧、reconstructor、AE调用或训练/校准入口。
3. `AL25_readout_spec.json` 明确真实 wrapper 仍 pending，尚未绑定BCTHW或17帧媒体/探针接口。`AL32_report/handoff`明确本批次没有调用AE、probe、optimizer、旧readout、模型、媒体或GPU；r_K直接复用归档q。
4. `AL12_method_design.md`的真实构造才规定固定两个公开重建器、主步长h=1/8、四次完整AE调用、K_h和四个q特征。当前本地代码没有把该构造落成冻结身份/权重/输出张量的生产接口。

## 具体桥接缺口

**输入权限与调用合同。** 现有readout不生成 `d_a,d_b,v_a,v_b`，也没有规定一条视频怎样得到四次AE输出、batch/frame维度、颜色/特征投影或失败样本处理。把任意数组reshape成THWC会破坏算子含义；需要冻结 `ProbeBatch` schema、四次调用顺序、h、重建器身份、权重哈希、精度和相同输入预处理。

**通道和空间域。** 参考实现强制C=3、H/W≤5，实际DINO或重建场的通道数和空间大小不由现有文件决定。若增加固定投影/池化到C=3，投影参数、训练角色、容量和所有q/r对照必须共享；若直接换成真实维度，则应新版本化readout，不能把软件参考当作已兼容wrapper。

**公平头比较。** AL32证明的 `r_K` 包含已有q，因此q-only头与r/full头应读取同一四调用输出，使用同一pairing、matching、calibration、正则和选择预算。当前没有真实的q-only/r-full训练器、概率校准、祖先分组split、五种子协议或per-sample预测保存接口；仅复用四项score不能称为强匹配基线。

**统计与数据角色。** AL67/AL69—AL73表明公开ID可用于受限黑盒规划，真实来源、祖先、原生时间、许可和候选root风险仍未封口。开发池、机制集和最终集没有由本审查释放；不能借接口审查放行OR1真实训练。

## 最小后续实现任务

研究端恢复且AL36/data gates有证据后，另立一个新任务（不复用失败包）冻结：

- `ProbeBatch`：sample/ancestor/role/split、原始文件哈希、R_a/R_b权重与wrapper哈希、h、四次调用输出、dtype/shape、失败码；
- 同一输出生成q-only与r/full两头，固定同一线性/逻辑回归配方、lambda、pairing/calibration和种子；
- 先做静态/容量/增强/来源/采样对照，再决定是否进入真实机制pilot；保存逐样本预测与区间；
- 任何q相对r的收益都必须满足预注册的macro增益、配对95%下界、4/5正种子和未见生成器条件。

这只是一个接口桥接任务建议，不是执行授权，也不证明q有新信息。若研究端认为同一完整r头已足以覆盖q的公平比较，可把q-only实现作为匹配消融而非创新模块；该选择需在预注册前固定。

## 结论

AL75：**done / pass（本地 paired-baseline 接口审查范围）**。目前可以复算软件算术参考，不能在已有证据上执行公平真实数据 q-vs-r 比较；OR1 innovation_admitted 和 real_experiments_authorized 继续为 false。AL74的公开标签语义结论、AL36反方准入和AL68原生时间核验保持独立。
