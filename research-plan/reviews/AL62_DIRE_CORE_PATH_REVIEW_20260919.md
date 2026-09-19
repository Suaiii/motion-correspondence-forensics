# AL62：DIRE核心路径审查完成，结束源码补读支路

2026-09-19，planagent。按约定仅补读同一作者commit的4份核心文本，确认AL61入口所传配置的循环、clipping和图像输入路径。**pass仅指限定源码路径审查；模型复现、真实数值可靠性和来源机制均未评价。** 未导入/执行作者代码、未写或运行toy，没有模型、媒体、服务器、GPU或训练。

## 固定来源

commit `1f89fff15f0e478307cdea9abdfe06a52fe7838a`；仅读`gaussian_diffusion.py`、`respace.py`、`script_util.py`、`image_datasets.py`，均位于`guided-diffusion/guided_diffusion/`，共64509字节，小于128KiB。URL、读取时间、SHA256与Git blob核对见`AL62_SOURCE_RECORD_20260919.json`。AL61此前4份入口文件作为固定输入，不重新获取。下面所有行号均属于此commit；数字来自代码控制流的手工追踪，**没有执行作者函数得到运行回执**。

## 同一shell配置的两方向调用

AL61 shell显式`diffusion_steps=1000,timestep_respacing=ddim20,use_ddim=True,class_cond=False`；入口`real_step=0,clip_denoised=True`。`script_util.py`11—24、43—65的工厂defaults没有覆盖这两个入口字段；predict_xstart=False、rescale_timesteps=False。模型输出分支是EPSILON，learn_sigma=True对应LEARNED_RANGE（386—424），同一次模型前向分出误差/方差通道，不是两个前向。

[`respace.py`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/guided-diffusion/guided_diffusion/respace.py)29—34按升序搜索首个满足20个时点的整数stride。对1000和ddim20，首个stride为50，保留原时点0,50,...,950。72—86按原alpha累乘重建20个beta并建立timestep_map；123—128将压缩索引0,...,19映回这些原时点再调用model。这里没有追加时点999。

[`gaussian_diffusion.py`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/guided-diffusion/guided_diffusion/gaussian_diffusion.py)784、792—805对real_step=0遍历0,...,19，每步调用ddim_reverse_sample。697、704—718的重建遍历19,...,0，每步调用ddim_sample。两函数各调用一次p_mean_variance（553—560、601—608）；后者260行只调用一次已映射的model。

因此，**在该无条件配置成功完成一个batch且没有额外调用的路径内，是20次反演＋20次重建＝40次batch级直接model调用**。不是每图40个独立Python调用，也不乘batch大小后称GPU调用数；可称每张图参加40次去噪器求值。四个MPI进程各自处理shard，不能说一张图必经160次调用。单batch实际大小、UNet内部计算、墙钟/显存和耗费未知；40个ADM前向也不等于OR1的4次完整视频AE。

real_step非零会截取索引前缀，use_ddim=False进入不同分支；上述结论只用于已固定shell。未运行这些非默认路径，不将它们算作通过。

## clipping确实在两个方向内部生效

p_mean_variance先取得模型输出，按EPSILON预测x_start，随后`process_xstart`执行`clamp(-1,1)`（293—311）。重建ddim_sample用这个已裁剪pred_xstart重新推eps（566），再构造下一状态；反演ddim_reverse_sample也使用已裁剪pred_xstart重新推eps（611—620）。因此clipping并非仅仅保存图片时的格式处理，它可以改变后续整条反演/重建路径。

eta默认0，反演明确assert eta==0。重建每步仍调用`randn_like`（576），但有限数值的理想公式中其系数sigma为0，故不向sample添加非零随机项；**会消耗随机数状态**与“输出必随机”不同，也不能由此保证整个GPU执行逐位一致。输入noise在AL61被显式提供，没有走初始化随机noise分支。

系数数组构造为float64（132—143），但`_extract_into_tensor`1003行抽取后显式.float()；shell允许model转换fp16，不能据此将整条链统称float64精确求解或全fp16。

## 端点约定限定了可逆解释

构造器142—143行令alpha_prev首项为1、alpha_next末项为0。最后一次反演（压缩索引19，对应原时点950）用alpha_next=0；代入618—620，返回重新计算的eps。重建随即把这个输出作为索引19的输入，模型时标仍为950，系数使用该点有限的alpha，而非另设alpha=0的额外时点。最后一次重建索引0使用alpha_prev=1，输出pred_xstart。

这是可定位的离散端点和评估时标约定。它与中间clipping、有限步更新共同限制“前后过程是严格逆”的解释；**本审查不称其为已测bug，不断言它贡献了多少残差，更不能将残差自动归因为真实/生成来源。** 换scheduler或改端点会改变方法身份，未获许可不能修后再沿用原作者成绩。

## 输入与AL61文件表示闭合

[`image_datasets.py`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/guided-diffusion/guided_diffusion/image_datasets.py)14—74的reverse loader默认deterministic=True、random_crop=False、random_flip=False，这些值传入dataset，覆盖其构造器random_flip=True的默认值。165—186将图像转RGB、中心裁剪、转换float32后除127.5再减1，输出CHW及原路径。中心裁剪函数233—246先BOX逐次缩小，再按短边用bicubic resize，最后裁出目标分辨率。并非仅复制原像素网格；原始文件/实际颜色及库版本没有读取。

结合AL61：正方目标图像通常使后续reshape无需再改尺寸；`abs(imgs-recons)`在浮点计算，随后独立缩放/clamp/uint8保存，demo再resize/crop/normalize分类。原生文件臂与直接浮点臂应保持不同身份。这个合同只绑定已读源码，不绑定实际数据与checkpoint。

## 终结性缺口与下一独立任务

源码补读到此结束，不再追加第5份文件或另拆同一调用链。仍未知：精确论文实验commit/checkpoint字节、实际依赖/设备行为、残差文件格式与写盘参数的实测影响、训练/测试祖先与预处理一致性、壁钟/显存/费用、真正来源效果。AL61保持历史not_evaluated；AL62的局部源码pass不能倒填其未审范围或释放完整baseline运行。

下一AL63转向AL31仅核对名称/README的AIGVDBench原文协议，核查真实来源、生成组件版本和数据划分是否足够支持严格未见decoder评估；不读样本、媒体、清单或封存最终集。它与DIRE源码无继续依赖。另一独立AL36仍因科研任务401保持未派发。OR1、AL05/AL57/AL58失败、预算和真实运行门槛均不变。
