# AL57：作者实现合同审查

2026-09-19，planagent。本文件为本轮最终审查，取代`AL57_SOURCE_CONTRACT_DRAFT_20260919.md`的“有限通过”表述：**审查已完成；已读作者入口的比较臂合同fail，论文性能和OR1效能未评价。** 只核对了固定公开commit的4份文本，未安装依赖、运行代码、下载权重/图片/数据或启动模型。

## 固定来源

作者仓库为`HaoyueBaiZJU/genai-detect`，默认分支`main`在本轮固定到 commit `db5ceb1e66786039054f2bacb956611abf14b69d`，提交信息为`Update README.md`，提交日期2025-07-08。仓库README的引用给出CVPR 2025页码28821—28830；arXiv正文对应2505.01008v2。仓库大小元数据约20,983 KiB，未克隆仓库；本轮仅用GitHub API树和4个raw文件。

来源记录：`AL57_SOURCE_RECORD_20260919.json`。记录包含API/raw URL、UTC取得时间、字节数、SHA256及Git blob SHA1；四个文件总计22080字节。临时源码缓存已删除，未把源码副本放进仓库。

## 静态代码可确认的行为和阻断点

[`eval_fake_vs_real.py`](https://github.com/HaoyueBaiZJU/genai-detect/blob/db5ceb1e66786039054f2bacb956611abf14b69d/eval_fake_vs_real.py)行23—88定义每图评估。输入RGB转换并resize到512×512（42）。主流程两臂显式传`mask_image=None`（195、209），声明的`--mask_image_path`没有读入图像或传入调用；因此没有可追溯的有效mask。**不能推断库收到None后会成功生成无mask输出**，库版本与错误路径未读取。

每个输入的预定循环是`num_gen`次，默认3（29、247），每次设置`torch.manual_seed(seeds+i)`（51—53）并调用inpainting pipeline（53—59）；默认推理步数50、guidance7（253—254）。若成功返回，输出先stack后平均（65—66），输入也仅仅是同一图复制3份再平均（46—48）。这给出计划中的3次pipeline请求、各50步，不能当作已实际完成150次网络前向：scheduler、CFG batching、内部AE及失败执行数均未核验。

评分使用整幅`mean_gt_sample`和`mean_outputs`（71—81），没有按mask选出遮挡像素。代码对RGB PIL张量只`.float()`，没有显式除255（44、62），但PSNR声明`data_range=1.0`（75），MS-SSIM声明`data_range=2.0`（69）。L1和MSE（变量l2）同样作用于平均输出（80—81）。这些都是固定文本的静态事实；依赖版本、输出PIL模式和实际数值未运行验证，不能推断论文所有图表都使用此入口。

主函数加载基础`botp/stable-diffusion-v1-5-inpainting`（177—180），命令行声明LoRA路径和scale（237、250），但在该commit的这一入口没有调用`patch_pipe`或`load/tune`来加载LoRA；仅仅导入了相应符号（14）。因此代码文本没有闭合论文所述“对齐替代模型已用于检测”的执行链。训练脚本另行存在，但不能用入口中的未调用参数替代加载事实。

`training_scripts/inpainting_lora.sh`行1—40明确是一个训练轨道：SD inpainting模型、`./data/ldm100_0.5k`实例目录、`train_inpainting`、512分辨率、batch1、累计步2、UNet/text/TI学习率、LoRA rank8、最大TI与tuning步数各3000、CUDA设备`cuda:1`。它支持“需要目标生成样本/训练配置”的权限判断，但不能证明脚本曾经成功运行或论文使用的精确数据、步数和墙钟成本。README行31—49要求另外下载真实/伪造/mask数据，行59—67给出50步、guidance7的评估入口；本轮未下载。

[`utils/metric_utils.py`](https://github.com/HaoyueBaiZJU/genai-detect/blob/db5ceb1e66786039054f2bacb956611abf14b69d/utils/metric_utils.py)行100—124把传入的正类分数标1，调用sklearn AUROC/AP，FPR使用默认0.95召回位置。评估入口217将fake_psnr作正类；没有L2的AUC/AP调用，因而无法核对论文L2消融的方向或实现。num_gen默认3仅对应已读入口，不能冒充论文实验K。

还有三个明确的静态阻断点，不能忽略后写成可复现通过：README59使用`eval_real_vs_fake.py`，树中实际文件名是`eval_fake_vs_real.py`，且README64的`--checkpoint_folder`没有对应argparse参数；实际入口245把`type`误写成`ctype`，与所导入标准argparse不相容；`evaluate_folder`在145等行返回NumPy数组，221却直接传给`torch.cat`。这是文本可定位的接口错误推断，没有运行作者程序产生错误回执。仓库其他未读文件可能提供不同入口，但不改变这条路径不可直接验收的判断。

## 与论文和OR1的边界

论文§3.1—3.2描述遮挡条件恢复、K次随机恢复以及目标API样本上的LoRA对齐。固定代码显示预定的“重复生成—均值—分数”结构，但有效mask和LoRA加载没有接入，也有上述入口阻断点；训练脚本仍保留目标样本/训练轨道。README、脚本和入口不能合并为一条已运行的论文管线。

该先例的方法操作是条件扩散/inpainting恢复；已读入口计划每次50步请求，对齐版本另有训练成本，但实际执行成本仍未知。OR1是两个固定完整重建器的软步交换、共享前级后的4次E+D调用。两者没有相同调用单位，也没有同一标签、时间支持或未见decoder合同。该先例属于“恢复检测”近邻，但没有证明OR1软交换q已被同一方法覆盖，亦没有为OR1增加任何新信息或性能证据。

PSNR/MSE还需避免一个错误解释：按论文标准公式，固定正MAX下PSNR是MSE的严格递减函数。两分数若共用这里同一个平均输出，先平均图像本身不会破坏PSNR与负MSE的排序等价；将MAX统一从255改成1也仅增加固定偏移，不能单独解释排名指标差异。SSIM的data_range问题另论。精度、无穷值处理、跨通道聚合与依赖版本未经核对，故实际排名未验；已读代码没有L2指标评估链，不能归罪某一具体错误导致论文消融差异。

与此不同，论文附录A.2的平均逐次距离和代码的平均图像后距离，本来就是不同统计量。其差可包含补全随机方差；这是真正需要单独推导的对象差异。后续AL58只审查该代数及与来源间隔的关系，不再为了修补这条未验收入口而追加第5份源码或运行模型。

## 结论与下一步

AL57记**done/fail（已读比较臂源码合同）**。四份文件支持默认3次平均、mask未接入、LoRA加载未接入及静态入口错误；不足以绑定论文masked轨道、完整成本或版本。当前不把该入口列成可直接运行的强比较臂，不采取“先修到能跑再沿用原成绩”的处理。论文方法先例仍有效保留，源码合同失败不代表其论文结果已被否证，也不为OR1提供优势。

两项独立后续为AL58恢复聚合的方差项与来源间隔反例审查，以及AL36反方算法准入审查。AL36继续等待研究端正常恢复，尚未发送。AL58直接检验一个由已读算子产生的可否证问题，允许用本职数学审查推进；均不释放付费模型/媒体或正式科学门槛。
