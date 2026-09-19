# AL62：DIRE核心路径的一次终结性补读

planagent，独立于AL36。AL61的4份入口文件核对了残差8位保存和demo仅分类，但未覆盖真正diffusion/scheduler实现。AL61完整合同保持not_evaluated，不作为成功父门槛；本包只针对已定位的缺失调用，不重新读入口或运行模型。

固定作者仓库`ZhendongWang6/DIRE`及commit `1f89fff15f0e478307cdea9abdfe06a52fe7838a`。仅允许读取该commit以下4份文件，总量<=128KiB：

1. `guided-diffusion/guided_diffusion/gaussian_diffusion.py`
2. `guided-diffusion/guided_diffusion/respace.py`
3. `guided-diffusion/guided_diffusion/script_util.py`
4. `guided-diffusion/guided_diffusion/image_datasets.py`

输入为AL61报告/来源记录和AL60正文审查。核对shell的ddim20/1000/real_step0经过工厂和SpacedDiffusion后到底生成哪些循环、每循环多少直接model调用；clip_denoised是否两方向都真正作用到pred_xstart，影响eps或状态更新的位置；输入加载的归一化、裁剪与原图支持。分清解析调用计数与实际walltime/显存，不证明权重、外部库、运行结果或来源机制。

只读文本并验Git blob/SHA256，不import/exec作者代码、不写或跑toy、不克隆仓库、不下载图片/数据/模型、不访问服务器/GPU。不再扩展第5份依赖。若这4份仍不足，给终结性缺口清单并结束该源码审查支路，不能再用相同问题不断拆包。停止该有限源码支路不等于停止其他独立研究。

交付`reviews/AL62_DIRE_CORE_PATH_REVIEW_20260919.md`与`AL62_SOURCE_RECORD_20260919.json`，引用实际函数/行、精确默认参数/条件分支，记录float残差与文件残差界线，给比较臂能否绑定的限定判断。只读推断不称复现通过，不把发现处理因素当OR1创新支持。AL57/AL58等失败保留，真实模型批次仍须另行算法/数据/资源准入。
