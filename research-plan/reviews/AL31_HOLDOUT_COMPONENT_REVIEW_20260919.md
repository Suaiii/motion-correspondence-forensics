# AL31：候选公开资源名称已核实，decoder身份仍须逐版本绑定

2026-09-19，planagent。仅审查公开总体说明与模型组件元数据；没有请求dataset文件列表、样本manifest、媒体或分数，没有访问本项目封存最终集。

## 1. AIGVDBench名称及作者入口

资源名称可核实为AIGVDBench，对应论文《Your One-Stop Solution for AI-Generated Video Detection》，arXiv 2601.11035v1（2026-01-16）。论文摘要指向LongMa-2025/AIGVDBench，该仓库README又链接同一论文，已核对双向关联。[论文元数据](https://arxiv.org/abs/2601.11035v1)、[固定作者README](https://github.com/LongMa-2025/AIGVDBench/blob/e38c75abda3d319c0c3072c77594f6eeef1c028f/README.md)

作者公布31个生成模型设置，涵盖T2V/I2V/V2V，总视频量超过440k；README另列生成视频约422k及20个开源、11个闭源模型。总量、生成量和发布版本口径应分列，不能直接写成本项目已下载或验收库存。README将OpenVid-HD列为真实来源的支持方，但这不提供任一具体视频的来源、祖先、使用条件或原生PTS证明。[作者发布说明](https://github.com/LongMa-2025/AIGVDBench/blob/e38c75abda3d319c0c3072c77594f6eeef1c028f/README.md)

本轮没有读取样本级拆分，未核实各类实际可用数量。CVF检索条目列出CVPR2026信息，但本次直接页面读取403；论文身份确认以已取得的arXiv元数据和作者仓库为依据，不冒充已审阅整篇基准论文。

## 2. 名称不能自动映射为独立decoder

| 已查公开描述 | 本轮支持的事实 | 仍未核实 |
|---|---|---|
| AIGVDBench列出CogVideoX | 该家族在发布说明中出现 | 具体生成版本、VAE来源/转换和权重摘要 |
| 列出Wan2.1 | 可区分到2.1名称层级 | 1.3B/14B、T2V/I2V实例对应的实际组件 |
| 列出Hunyuan | 该名称在开源模型列表中出现 | 是否原始HunyuanVideo、1.5或其他确切版本 |
| 声明31个生成模型 | 基准覆盖多个生成设置/任务 | 是否有31个不同decoder；本轮没有这种证据 |

表中未决项是本次有限README审查的边界，不宣称其他作者资料或未来授权的数据元记录一定也缺失。T2V/I2V/V2V是不同任务条件，不能仅按一个家族名字合并后称为同一来源/剂量比较。

## 3. 官方组件说明提供了两个具体提醒

原始HunyuanVideo官方README描述自训练的因果3D VAE，时间/空间压缩分别为4和8；HunyuanVideo-1.5官方说明则为时间4、空间16。仅用“Hunyuan”这一家族名无法选择对应接口。架构比率相同不证明权重相同，版本比率不同也不自动证明所有训练来源独立。[原始版本固定说明](https://github.com/Tencent-Hunyuan/HunyuanVideo/blob/e748c73ac064728bf6bd15b1cdb8161e55a4f331/README.md)、[1.5固定说明](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/60783e704160023913bee78f0b47036d393d4dfa/README.md)

复用AL22已固定的CogVideoX模型卡时，量化示例明确将5b的text encoder/transformer与2b的VAE组装。这是作者公开的组件组合例，说明整模型名称不能唯一决定重建器；它不证明AIGVDBench实际采用了该组合。[固定模型卡](https://huggingface.co/zai-org/CogVideoX-2b/blob/1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01/README.md)

因此，若以后选择AL22的Cog/Wan候选probe，相关基准家族需先核实到生产decoder组件，才能使用“严格未见decoder”称呼。仅仅未参加分类头拟合、整模型名称不同或使用另一个模型库，都不够。本轮没有选定probe bank，也没有认定某个实际测试样本已发生重叠。

## 4. 后续绑定与完成范围

在访问任何批准的数据支路时，分别记录：发布版本、生成任务类型、生成模型revision、decoder来源及转换记录、预期/实际权重摘要、来源与祖先证据，以及其相对训练模型和probe bank的关系。关系unknown时单列未决，不填成独立通过；同一祖先/衍生视频仍按既有规则分组。

本轮3个查询、6个primary入口/既有固定来源，读取README及摘要元数据，原始正文仅在内存中使用。URL、revision、字节数与SHA256见[来源记录](AL31_PUBLIC_SOURCE_RECORD_20260919.json)。未请求数据样本、媒体、模型权重或运行环境。

AL31按 `public_component_identity_metadata` 完成有限审查。名称确认与总体描述不替代RS02/RS03的实际来源/祖先/时间字段验收，不改变封存最终集、预算或算法创新门槛。
