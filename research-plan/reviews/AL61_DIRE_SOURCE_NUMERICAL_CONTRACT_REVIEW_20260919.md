# AL61：DIRE入口与文件表示已核对，核心数值路径未闭合

2026-09-19，planagent。完成约定的4份固定源码文本审查，**完整数值/比较臂合同仍not_evaluated**。没有运行或导入作者代码，没有模型、权重、残差图、真实媒体、服务器或GPU访问。本报告只给出已读入口能支持的事实，不以源码存在代替复现通过。

## 固定来源与读取范围

作者仓库[ZhendongWang6/DIRE](https://github.com/ZhendongWang6/DIRE)在本次公开API观测中为archived，固定commit为`1f89fff15f0e478307cdea9abdfe06a52fe7838a`，日期2024-09-26，提交说明为数据/模型链接更新。README给出ICCV2023信息并链接AL60已读arXiv2303.09295；这是作者元数据，不能把2024快照认定为2023实验当时的精确版本。

只读取README.md、demo.py、guided-diffusion/compute_dire.py、guided-diffusion/compute_dire.sh，共14895字节。全部SHA256及Git blob SHA1已与固定树校验，来源URL/时间/文件大小见`AL61_SOURCE_RECORD_20260919.json`。达到4份上限后停止，未读取内部scheduler、diffusion类或训练数据loader。

## 已读路径和真正的输入表示

[`compute_dire.py`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/guided-diffusion/compute_dire.py)第85—104行先调用`ddim_reverse_sample_loop`，再依`use_ddim`选择`ddim_sample_loop`或`p_sample_loop`；同一个模型对象传入两阶段，`noise=imgs`与`noise=latent`分别是反演和重建的输入。两阶段都传入`clip_denoised`和`real_step`。这些是接口传递，未证明内部clipping位置、循环次数或数值可逆性。

第106行先计算浮点张量的`abs(imgs-recons)`。随后重建图和输入显示张量各经`(x+1)*127.5`、clamp到[0,255]、uint8转换；**DIRE来自转换前的差，不能改成两个已保存8位图的差**。残差自己在第115行另经`dire*255/2`、clamp、uint8转换，然后RGB转BGR写盘（第140—143行）。这条保存路径丢失原浮点残差精度，不保证原理论残差与文件输入相同。

写盘沿用`os.path.basename(paths[i])`（第137行），没有统一改成指定扩展名或显式设置写盘参数。实际文件格式、输入归一化、图像loader与原数据字节均未核验；不能在此声称全部文件无损或把数值阈值、误差上界当作已证。空间处理还包括非方图的CenterCrop与尺寸不符时的bicubic interpolate（第31—39、86行）。

[`demo.py`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/demo.py)第40—45行通过`get_network(args.arch)`加载分类网络/权重，默认arch为resnet50。第51—68行只读一张RGB模式文件，经Resize256、CenterCrop224、ToTensor、可选ImageNet mean/std归一化，交给模型并取sigmoid。**demo本身没有调用反演或计算DIRE**；结合README第57行的残差训练目录，使用DIRE分类checkpoint时需要先提供正确残差表示。不能把直接喂原RGB称为已按论文完成DIRE，也不能因demo不包含预计算就判论文实现无效。`get_network`实现和checkpoint仍未读取。

## 配置、调用成本及未读依赖

[`compute_dire.sh`](https://github.com/ZhendongWang6/DIRE/blob/1f89fff15f0e478307cdea9abdfe06a52fe7838a/guided-diffusion/compute_dire.sh)第6—9行显式给出`ddim20`、`use_ddim=True`、`diffusion_steps=1000`、class_cond=False、image_size256、use_fp16=True以及四进程MPI示例。它是可读配置，不是本轮执行：没有申请四张GPU，亦不等于用户单4090实例能以相同配置运行。

Python入口本地defaults声明use_ddim=False、num_samples=-1、clip_denoised=True、real_step=0（第150—164行），最后还用未读`model_and_diffusion_defaults()`更新。应分开裸入口、shell示例及实际最终参数；不能仅凭裸默认值宣告论文采用随机采样，也不能忽略shell的显式覆盖。`ddim20`暂时只是传递给构造器的字符串，内部时间映射/循环/每步网络调用均未闭合，AL60从论文读到的两方向20步不能由此升级成测得40次调用。

若class_cond为真，入口第82—84行随机取类别再传入两阶段；已读shell将其设为假。入口没有证明所有条件模式都确定性复现。模型参数fp16转换也不等于整个输入/残差链都为fp16；实际dtype、clamp行为与缓存仍需各自证据。

## 科学影响与交接

未来比较必须区分原生“浮点差→残差8位文件→分类器预处理”与任何直接浮点残差适配。量化、饱和、存储/尺寸路径可能改变判别统计，但本轮未证明它们造成了作者性能，也没有证明OR1更好。OR1稳定r包含q的同信息强对照、原生来源/处理协议、成本和创新门槛不变。

完整数值合同未通过，原因是4份已读文件没有包含实际diffusion/scheduler和data-loader实现；这是有界审查留下的明确缺口，非访问故障，不能伪装成成功或整体等待。下一AL62限定一次终结性补读：同commit的gaussian_diffusion.py、respace.py、script_util.py、image_datasets.py四份文本，仅闭合输入、时间映射与clipping路径；再缺依赖就保留unknown，不连续拆包无限增加同类阅读。独立AL36反方准入审查继续保持科研端401未恢复、尚未派发。
