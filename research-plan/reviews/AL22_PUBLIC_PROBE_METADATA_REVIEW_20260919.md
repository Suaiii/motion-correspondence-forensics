# AL22：公开VAE配置、权重标识与留出边界

2026-09-19，planagent静态审查。核查两个候选公开模型库，没有选定OR1的probe bank、下载权重或运行模型。以下结论仅限固定版本的发布元数据，不等于本机/服务器加载验证。

## 1. 来源固定与实际读取

旧入口THUDM/CogVideoX-2b当前跳转到zai-org/CogVideoX-2b；记录重定向，不将两个名字计为两个独立模型。核查版本如下：

| 官方发布库 | 固定revision | VAE类 |
|---|---|---|
| zai-org/CogVideoX-2b | 1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01 | AutoencoderKLCogVideoX |
| Wan-AI/Wan2.1-T2V-1.3B-Diffusers | 0fad780a534b6463e45facd96134c9f345acfa5b | AutoencoderKLWan |

读取9份小文本/JSON，共64,078字节：两个模型API元数据、各自VAE配置/model_index/README，以及Cog的LICENSE。固定文本的字节数和Git blob SHA1与发布索引一致；本地SHA256见[来源清单](AL22_SOURCE_MANIFEST_20260919.json)。没有跟随模型卡里的视频、图片或模型下载指令。

官方入口：[CogVideoX-2b](https://huggingface.co/zai-org/CogVideoX-2b)、[Wan2.1-T2V-1.3B-Diffusers](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers)。API访问时两个库均为public且gated=false，这仅描述该次公开元数据访问。

## 2. 实际配置与AL17 SDK默认值

用stdlib AST读取AL17固定Diffusers提交a3e0b8ec的构造函数字面默认值，未导入模块。配置中明确给出的字段均与这个快照的默认值一致；比较回执见[配置审查](AL22_CONFIG_COMPARISON_20260919.json)。

| 项目 | Cog配置 | Wan配置/尚需SDK补充的字段 |
|---|---|---|
| latent通道 | 16 | z_dim=16 |
| 时间相关配置 | temporal_compression_ratio=4 | temperal_downsample=[false,true,true]；scale_factor_temporal未写入该配置，固定SDK默认4 |
| 主宽度/层数 | channels=[128,256,256,512]，layers_per_block=3 | base_dim=96，dim_mult=[1,2,4,4]，num_res_blocks=2 |
| latent尺度元数据 | scaling_factor=1.15258426，shift_factor=null，mean/std=null | 固定16维mean/std向量，完整值保留在配置 |
| 其他 | force_upcast=true；quant/post-quant关闭；记录sample H=480,W=720 | dropout=0；is_residual、patch_size、输入输出通道等7个字段缺省，依赖所绑定SDK |

Cog配置记录_diffusers_version=0.32.0.dev0，其model_index记录0.30.0.dev0；Wan两处记录0.33.0.dev0。这些生成配置时的版本字符串不构成当前SDK加载兼容性证明。尤其Wan配置缺失的字段应与SDK一起冻结；不能只保存config就认为运行语义完全固定。

依据：[Cog固定配置](https://huggingface.co/zai-org/CogVideoX-2b/blob/1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01/vae/config.json)、[Wan固定配置](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers/blob/0fad780a534b6463e45facd96134c9f345acfa5b/vae/config.json)。

与AL17相同，直接encode-mode-decode的中间潜变量约定不得与扩散pipeline的latent标准化混用。force_upcast配置也不能单独证明整个实际调用均以FP32执行。17帧和共同空间网格仍须真实wrapper验证；sample_height/width或生成模型卡的分辨率描述不替代这项验证。

## 3. 已有远端预期权重标识，尚无实际权重验证

两库均发布vae/diffusion_pytorch_model.safetensors。API提供以下LFS对象预期信息：

| 候选 | 发布大小（字节） | 远端声明的SHA256 |
|---|---:|---|
| Cog | 862,388,596 | a410e48d988c8224cef392b68db0654485cfd41f345f4a3a81d3e6b765bb995e |
| Wan | 507,591,892 | d6e524b3fffede1787a74e81b30976dce5400c4439ba64222168e607ed19e793 |

合计1,369,980,488字节是两个序列化文件的发布大小，不是下载量、显存需求、激活峰值或实际运行成本。当前只保存指向它们的元数据，没有读取这些文件的payload，也没有实测/核验本地或服务器上的权重字节。以后获得模型访问授权时，可对下载字节比对这两个预期摘要；不能现在标为实测通过。

配置相同不证明权重相同；文件摘要不同也不证明语义解码器独立，例如重新打包、dtype转换或张量命名转换都可能改变文件字节。相关留出审查需要模型来源、转换记录和必要的张量级比对，不能仅比较库名称。

## 4. 候选probe会改变什么“未见”主张

AL12已规定严格未见生产decoder不得属于训练生产decoder或probe bank。该条不能只在分类器训练集层面判断：某个生成器没用于拟合分类头，其VAE仍可能正是推理probe的一部分。

| 关系 | 可保留的描述 | 不能据此宣称 |
|---|---|---|
| 未参与检测器拟合的新生成模型，复用probe的同一decoder权重 | 生成模型留出、已见decoder条件 | 严格未见decoder |
| checkpoint名称不同，VAE架构/家族相同，权重关系未知 | 待核实的模型/家族关系 | 已证明独立的新decoder |
| decoder权重及来源经审查不在训练/probe中 | 对已定义排除范围的decoder留出 | 自动保证内容、真实来源或训练数据独立 |
| 公开来源只给系列名称，缺版本/组件记录 | 身份未决，应单列 | 把未知身份当未见证据 |

WORK_PLAN的最终候选池包含Wan、CogVideoX和HunyuanVideo等名称。若最终选择本次两类VAE作为probe，相关Cog/Wan样本必须先核实其实际decoder关系，不能仍仅凭“分类头未训练它们”将其全部计入严格未见decoder组。本轮没有检查最终集样本或这些系列所有checkpoint，因此不宣称具体样本已经重叠，也不把HunyuanVideo自动判为独立通过。

probe bank、训练生产D和留出D应联合预注册，再按既定原始来源/祖先隔离条件组集；不能看测试效果后更换bank或更改未见定义。本报告没有改写最终集或批准新的数据访问。

## 5. 发布许可与当前完成范围

Cog固定模型卡明确包括其VAE的Apache-2.0声明，并附带已读取的LICENSE。Wan固定模型卡声明Apache-2.0，但其指向LICENSE.txt的相对链接对应文件未出现在此次固定发布索引中；目前保留模型卡声明与该缺项，不将另一个仓库的代码许可静默代作此文件。实际使用和发布前仍须核对所采用版本的完整发布条件。

依据：[Cog固定模型卡](https://huggingface.co/zai-org/CogVideoX-2b/blob/1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01/README.md)、[Cog LICENSE](https://huggingface.co/zai-org/CogVideoX-2b/blob/1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01/LICENSE)、[Wan固定模型卡](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers/blob/0fad780a534b6463e45facd96134c9f345acfa5b/README.md)。

AL22按 `public_probe_metadata_and_holdout_audit` 完成交付：提供固定配置/远端预期权重标识和留出解释。模型加载、实际权重、输出合同、数值误差、资源门槛及新算法创新继续pending。本轮无SSH、服务器CPU、模型或GPU使用；累计历史实付与GPU时数仍未知。
