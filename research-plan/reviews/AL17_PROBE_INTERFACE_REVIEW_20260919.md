# AL17：OR1公开VAE接口的静态接入审查

2026-09-19，planagent。结论仅限固定SDK源码的接口审查：存在可进一步绑定的直接重建入口；实际权重、数值精度、17帧输出、时钟及完整四调用运行均未验收。没有导入模型、下载权重或访问服务器。

## 1. 固定来源和审查范围

审查 Hugging Face Diffusers 提交 `a3e0b8ec235c27a6c17a21976daf7fd32d819d05`（提交日期2026-09-18T12:06:16Z），5份官方源码文本，共183,952字节。逐文件SHA256、Git blob SHA1和原始URL见 [清单](AL17_SOURCE_MANIFEST_20260919.json)。保留源文件许可声明，仅解析/阅读文本，没有导入这些模块。

这是一个SDK实现快照，不能称为已部署服务器版本或原论文模型复现。AL09保存的Cog SAT生成导出入口有首latent处理；本次审查不同的直接VAE接口，不追改AL09结论。

## 2. 重建必须走同一潜变量约定

两类直接 `forward(sample_posterior=False)` 都是 `encode(x).latent_dist.mode()` 后接 `decode(z).sample`。共同的 `DiagonalGaussianDistribution.mode()` 返回均值。此直接路径中，没有插入用于扩散模型输入的latent标准化：Cog的scaling_factor、Wan的latents_mean/std不能凭名称再乘一次。未来若另选pipeline接口，应以那个接口自己的约定重新绑定，不能混用。

依据：[Cog直接forward](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_cogvideox.py#L1405)、[Wan直接forward](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_wan.py#L1409)、[posterior mode](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/vae.py#L742)。

这些入口接收模型域张量，不负责把RGB媒体解码成统一像素域。本轮没有核查媒体预处理器，故RGB范围、归一化、颜色空间、空间裁剪与逆变换仍是待绑定项，不能直接宣称两个probe已经共享输入域。

## 3. 17帧仅有条件静态形状推断

| 直接非tiling路径 | 源码中的时间处理 | 17帧的条件静态预期 |
|---|---|---|
| CogVideoX，时间压缩比4、样本分批8/latent分批2 | 首批吸收余数；两次奇偶不同的时间池化/插值 | 编码9+8帧，经两级变为3+2 latent；解码3+2 latent为9+8帧，合计17 |
| Wan，两个时间下采样阶段、普通Wan2.1式非residual配置 | 首帧单独编码，之后每4帧；首个latent不时间展开，之后每个展开为4帧 | 首1加四个4帧块编码为5 latent，解码1+4×4=17帧 |

Cog的奇数下采样保留首帧，其余按2池化；奇数上采样保留首时间位、其余按2展开。偶数分支整体按2处理。Wan的时间resample依赖跨块cache：第一次仅设置状态，后续时间卷积/通道交错执行时间展开。因此不能把每块都当独立重置，也不能从stride直接推断可见周期。

依据：[Cog编码/解码分批](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_cogvideox.py#L1125)、[Cog下采样](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/downsampling.py#L320)、[Cog上采样](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/upsampling.py#L390)、[Wan时间resample](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_wan.py#L269)、[Wan分块](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_wan.py#L1133)。

上述计算以给定配置、空间尺寸合法、相关因果卷积保持所述块长度为条件；没有实际张量执行。Cog源码的支持注释是1或8k或8k+1，不能由这个17帧例推广所有4k+1。Wan编码循环 `1+(T-1)//4` 也不保证任意长度尾部完整消费。未来wrapper应拒绝未批准长度，不能静默裁掉尾帧或复制补齐。

相同输出长度仅仅是运算槽位候选，不证明输出像素与输入具有物理对应，也不证明源视频PTS。输出clock必须另作声明并与输入原生整数PTS/time_base分开记录。

## 4. 状态和clamp是实际算子的一部分

- Cog非tiling `_encode/_decode` 在每次完整调用内创建局部 `conv_cache=None`，在片内块间传递。Wan将feature cache保存在实例属性中，encode/decode常规路径前后清理。未来应串行调用同一Wan实例，按完整R调用重置，不能让a/b路径共用片内状态。异常退出也须明确清理；本轮没有证明所有tiling/异常分支安全。
- Wan `_decode` 明确执行 `torch.clamp(out,-1,1)`；此Cog直接解码路径未见相同末端clamp。不能在包装时无记录地删掉Wan clamp，或给Cog加上clamp后仍称为原接口。两者输出域及外层软步中的范围处理必须统一声明。
- clamp连续但在边界一般不可微；有限h的OR1端点差仍有定义，AL12的C²局部交换项解释不能无条件套用。AL16的端点误差界不依赖C²，但真实误差界和Lipschitz常数仍未知。夹断产生的顺序响应是需要单独反例/对照审查的替代解释，尚未证明它解释实际模型收益。

依据：[Wan清理和解码clamp](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_wan.py#L1123)、[Wan末端clamp](https://github.com/huggingface/diffusers/blob/a3e0b8ec235c27a6c17a21976daf7fd32d819d05/src/diffusers/models/autoencoders/autoencoder_kl_wan.py#L1210)。

## 5. 下一阶段仍须满足的合同

真实接入前绑定SDK/依赖、模型repo与revision、权重/配置摘要、posterior模式、输入归一化与逆变换、clamp位置、dtype/device、空间支持、17帧策略、tiling及cache生命周期。实际运行另记录全部中间槽位/shape、有限值、clamp占比、四次核心调用成本和独立精度诊断成本；严格拒绝未声明处理。

本审查没有形成可运行wrapper，也没有下载对应checkpoint配置。实际profile仍须独立科学及资源准入；AL05 fail、最终集封存和未知累计消费保持不变。后续有意义的独立工作为：审查clamp/坐标变化本身的响应反例，以及在已知误差的CPU mock上接入AL16数值状态合同。二者不能被称为真实视频检测突破。

AL17按 `static_probe_interface_review` 完成交付；真实接入可行性为有条件候选，运行验收保持未评估。
