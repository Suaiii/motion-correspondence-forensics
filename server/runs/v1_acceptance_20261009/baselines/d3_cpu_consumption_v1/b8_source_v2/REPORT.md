# B8：D3 离线逐样本推理入口

## 实际交付范围

已在新namespace完成可执行入口、元数据组装、离线权重加载、全selection逐样本结果与同锁恢复代码。本批仅做语法、无副作用import/help/plan；18个runtime Python模块语法通过、6阶段软件检查通过，重依赖导入0、云端/媒体/模型初始化/encoder/GPU调用0、真实或fixture预测行0。编译与plan不作为实际加载/推理结果。

18项B8冻结输入SHA实际核对一致；源包、主WORK_PLAN/DAG/DEVLOG只读。模型大权重、环境和媒体未复制/下载，没有安装依赖、创建窗口或派生agent。协调端集成消息说明C9云端三资产完整SHA通过、A10结束；B8本批未访问云端或重新核验它们，需要协调端随后提供明确的execution/asset锁。

## 固定方法与准确变更

作者commit `c798fbc57fe0c4198d63a73732c2c0f9e4b4816c`；固定XCLIP-16对应`microsoft/xclip-base-patch16`，固定l2。保留作者forward AST：逐帧pooler_output→相邻L2距离→距离的一阶差分→`torch.std(...,dim=1)` sample correction1；float32、raw大为real，统一score_fake=-raw。

四个作者reader函数AST未变：数字JPEG顺序、prepared少于16取8否则取16、较长轴两侧各10%整数crop、Resize224、cv2 BGR保留、ImageNet mean/std/max255。snapshot中原作者文件只读参考；运行时只编译这四个函数和forward，不调用视频准备脚本或CSV Dataset的1000截断。

| 范围 | 实现处理 | 验证边界 |
|---|---|---|
| HF constructor | 同XCLIPVisionModel.from_pretrained，改为显式本地目录/local_files_only/float32；无联网fallback | 未加载模型 |
| checkpoint |完整文件SHA/大小/config；所有视觉必需键和shape，缺件不接受；unused text/多模态键分列 |实际key/shape检查待真实命令 |
| author数值与reader | AST逐函数一致，forward逻辑未替换 |依赖/CPU数值等价待encoder检查；历史作者环境未认证 |
| selection |整份冻结manifest顺序逐项，单视频batch；无每类1000上限 |完整真实推理未运行 |
| A7 evaluator_v4 |13个文件原字节复制到新目录，指标/采样不重写 |本批未重跑旧27媒体或完整合同套件 |
| A7 wrapper |未调用会写旧adapter_assets/cache的adapter_entry；直接复用prepared JPEG与scoreless records |新图片准备不在本入口 |

后续运行真实读取JPEG时逐帧核SHA，作者reader得到的float32 tensor还须匹配已封存input_record的tensor SHA/shape。native PTS/time_base、原生独帧、FPS重复与logical slots沿用v4 record链；模型观察另记224输入HW，原scoreless record中未执行encoder的字段不追改。

## 源身份、结果和恢复

execution manifest外部SHA、source SHA、role、selection/split、checkpoint/config、code/preprocess、cohort/protocol/support、依赖/cv2来源、seed及资源上限绑定同一个run identity。每项成功/失败事件有checksum和原始错误；数据门、读图、模型、schema失败都留在分母，源码键不认证祖先。成功prediction仅有真实forward产生的score；失败/pending无占位score。

恢复严格检查同锁成功记录和schema/metadata，失败默认保留，仅显式retry-failed重试。JSONL中断末尾保留原SHA归档，恢复完整行；坏中间行拒绝。结果按原manifest顺序重建RESULT_LEDGER，每个成员都在；预测成功子文件不会成为新的完整分母。实际恢复/资源kill路径代码已实现，本批仅语法验证，未用模型/假预测fixture模拟。

root字段含A10 DELIVERY与public overlay SHA；每行有明确approved_public_candidate和排除原因。first12必须叠加A10保守public资格，被排除项在模型初始化之前记录数据门失败，保留固定选择分母。A7 first12原/current fit身份绑定，不改名audit；fit的首encoder输出不得当audit成绩。

## OpenCV兼容及既有环境

实际读取D4 author_environment_lock：cv2提供分发为**opencv-python-headless=4.12.0.88**，不是硬要求另一个分发名。本入口接受显式提供cv2的opencv-python或opencv-python-headless，不伪造别名版本、不安装替代重包。

environment_lock.py只读取元数据/源字节，绑定实际模块选择、分发RECORD及native extension SHA；worker在任何cv2导入之前核对该来源与版本。D4参考Torch2.8.0+cu128、Torchvision0.23.0+cu128、Transformers4.57.6、NumPy2.3.2、Albumentations2.0.8；NumPy与作者requirements2.3.3的差异原样保留，不宣称历史字节重现。

本地E:/anaconda/python.exe用于软件验证，元数据记录Torch2.5.1且缺Transformers/Albumentations/SafeTensors；没有尝试用缺依赖环境加载模型。后续显式使用既有Linux Python和D4 dependencies/site，实际剩余JsonSchema/SafeTensors/psutil及所有版本由metadata descriptor冻结。`.bin`要求Torch>=2.6与weights_only，无unsafe fallback。

## 当前边界与下一步

默认CPU、batch1、最多2线程、group物理RSS4GiB、CUDA不可见，日志/临时cache仅新runtime output；禁止任何输出落到旧封存数据/资产目录。未来全量资源另定；首模型加载、encoder consumed HW、score、吞吐和峰值尚未实测。本次不读取既有真实预测，不计算指标，不选测试样本。

首入口仅仅读已有作者native-reference JPEG；matched实际输入未核时拒绝，不用元数据时间candidate代替runtime。祖先状态保留unknown；本包不放行科学机制或完整v1。

NEXT_RUN给出真实参数接口、冻结元数据组装、plan和后续run命令。完成这份可审入口后停止，真实首批须由后续明确命令接续。

## 最终交付停止点

按最后集成指令，本包完成有限验证即停止，不继续新增合同检查范围。全量source_role const=fit与in_domain_audit/development_audit producer兼容由A11接续；当前first12原fit不受影响。C9/C10的云端/输入状态仅记录协调端给出的事实，本包没有云端验证或真实encoder调用。下一步以真实CPU回执暴露的问题作必要修复。
