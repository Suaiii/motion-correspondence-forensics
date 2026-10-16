# 工作单 B：传播处理与统一物理时间首包

完成时间：2026-10-09T01:28:25.055335+08:00。dispatch_id：v1-acceptance-20261009。执行窗口：01a11c81-06c6-7941-94b7-51efc512b199。

## 1. 当前可用版本与结论

**使用 `v2/` 的 protocol、manifest 与 build_receipt。根目录 v1 及其媒体、原命令和回执全部保留。** `ACTIVE_BUNDLE.json` 是本窗口交接入口；不改变主计划或 DAG。

| 层级 | 实测状态 | 支持范围 |
|---|---|---|
| 软件与处理链 | completed / pass | 48 输入、336 活跃输出；原生轨、转码、空间变化、时间重采样与组合处理可回放 |
| 本小包字节与时间数据 | 48/48 输入现场 SHA / PTS通过；336/336 输出现场复查通过 | 仅仅本次冻结开发输入及其派生链 |
| 样本来源、权利和独立祖先 | unknown / pending A | 没有补造样本级生成回执、生成模式或祖先证明 |
| 机制效果与新算法 | not_evaluated | 未运行分类器、特征提取、GPU或机制实验；科研 gate 未通过 |
| 不同执行者复核 | pending A | 构建者的机械自查与重放仅仅是软件证据 |

## 2. 输入冻结与四种分母

输入仅取已有质量排除后的 RoboVidSM **fit** 角色、clean 视频。资格先检查原生严格递增 PTS、有理数 time_base、至少1.5秒时间支持、七个不重复的最近邻源帧、最大125ms采集误差、偶数尺寸且不超过1920×1080、单文件不超过32MiB。然后用固定 SHA 排序选真实24、OpenSora12、T2V-Zero12。没有使用模型分数；冻结后的失败不替换。外部/生成器留出和扩展包未读取或补样本。

原 fit 资格池数量：real=1586、OpenSora=794、T2V-Zero=800。元数据不合格记录5条，选择短缺为0。

- 原始clean文件48；唯一输入 SHA48。
- 候选祖先/来源组48：真实按文件名中 Scene 前的视频前缀保守合并，fake按已有 sample identity 合并；**这些不是已验证独立祖先数**。random_pair 不作祖先。
- 活跃派生视图336；唯一输出 SHA 为312。一条输入的七条视图不能统计成七个独立样本。
- 每个处理单元：real24、OpenSora12、T2V-Zero12，共21个 label/generator/transform单元。

本包真实来源仅仅为 Vript 发布资产、假端仅两个已知生成器；不能声称满足三真实来源/四生成器、T2V/I2V或全数据机制准入。

## 3. 冻结处理表

| 轨 | 处理 | 时间 | 空间 |
|---|---|---|---|
| identity_native | 字节原样复制，保留完整原生媒体与音频 | 消费者按冻结物理时间视图读取 | 原生 |
| native_crf18 | libx264 CRF18 | 0帧至最接近1.5秒的原生帧，保留原生节奏 | 原生 |
| native_crf32 | libx264 CRF32 | 同上 | 原生 |
| resolution384_crf18 | 同一编码，Lanczos等比例缩放与补边 | 同原生窗口 | 384×384 |
| time4_crf18 | 同一编码，选七个不同源帧，显式-r4 | 统一七个PTS与4FPS封装 | 原生 |
| matched384_time4_crf18 | 时间与空间联合处理 | 同统一时间轨 | 384×384 |
| matched384_time4_crf32 | 联合处理加较强转码 | 同统一时间轨 | 384×384 |

除identity外均仅视频流，去音频/字幕/数据及源metadata；preset medium、yuv420p、GOP48、禁场景切换/B帧、编码time_base=1/60000、MP4 timescale60000、12M码率上限/24M buffer。参数、顺序、命令数组与哈希逐条保存；真实和fake使用同一表。这里的转码是云端CPU上的模拟处理，没有真实平台上传/下载证明。它不冒用旧OSN/WeChat/WhatsApp回执。

原生尺度轨保留原编码栅格尺寸；不能把native-scale baseline强迫缩到384。补边保留画面宽高比线索，因此共同尺寸仅仅控制输出尺寸，不能宣称消除了全部来源混杂。原生轨、统一时间轨和联合轨须分别报告。

## 4. 物理时间、原生PTS与真实映射

目标采样点为0、1/4、1/2、3/4、1、5/4、3/2秒。原点是首个native PTS乘以rational time_base；最近邻并列取较早索引。每条时间轨恰有七个不同的源帧，没有插值、重复补帧或以FPS推算原始PTS。

输入现场 ffprobe 使用实际返回的整数 `pts` / `pkt_pts` 字段，存字段计数与完整序列，逐条对照冻结输入。编码前 `showinfo` 记录实际进入处理链的源PTS；它须与计划选中的native PTS完全相等。输出再次ffprobe，保存整数PTS/time_base、实际帧映射、偏移和量化误差；没有用best_effort替代native整数。

本次最大最近邻采集误差：real: 20.000 ms; OpenSora: 0.000 ms; T2V-Zero: 0.000 ms。这些误差仍存在；七个名义时点相同不能抹去各输入的实际采集时间差。统一输出 PTS=[0,15000,30000,45000,60000,75000,90000]，time_base=1/60000；**PTS首末跨度1.5秒，七个1/4秒显示区间对应容器时长1.75秒**。二者分别记录。

既有八帧DINO缓存没有用作此包的统一时间输入；七帧物理时间视图须由后续baseline adapter明确消费，不得直接复用旧8×768缓存并改名。

## 5. 保留的失败与修复

v1完成336输出、12/12字节确定性重放，所有七帧输出PTS正确。但是108条时间轨的容器末帧时长继承原始名义FPS，造成平均FPS/总时长不一致；36条T2V-Zero轨因原输入恰为4FPS未显出此问题。`time_metadata_issue_v1.json`逐条保留旧输出哈希、时长与错误解释；仅仅v1的早期软件pass不验收这一加强后的时间封装合同。

v2在新增输出前冻结协议，仍用同一48输入与同一七轨；仅加显式输出-r4，重建144条时间轨。192条identity/原生/分辨率视图直接引用经过核验的v1输出，不重复生成。全部144条现在7帧、4FPS、时长7/4秒，并通过每帧包时长复查。v2新增6/6重放字节、映射和解码哈希一致；未替换样本、改label或根据模型效果调参。

原31条传播失败、400组跨平台字节重复、10条黑帧及五帧历史排除等原始证据未被更改。本首包没有声称修复全部历史传播链。

## 6. 校验与资源

实际输出：336活跃视图，构建失败0；其中288个非identity输出的解码yuv420帧内容或尺寸均观察到变化。逐条保存parent/output SHA、命令/配置/版本哈希、退出码、原始stdout/stderr、解码帧MD5和PTS映射。另一个读取器现场对全部336输出及48输入重核SHA、整数PTS、映射唯一性、统一轨每帧包时长，结果336/336；该读取器仍由本实现者编写，不自签独立科学验收。

CPU亲和性限6核、每次仅一个作业；解码/滤镜/编码各显式1线程，x264 lookahead1线程。编码前最坏预算与每个输出前动态守卫均执行：全包新增媒体≤4GiB，全盘空闲≥20GiB。未启动GPU。

- 全部版本及18次重放媒体：142,900,435字节，0.1331GiB。
- v1墙钟335.146秒，v2墙钟109.745秒；最终读取复查62.140秒。输入准备另有逐命令时间回执。
- v2结束数据盘可用34,113,777,664字节，31.771GiB。
- 本地仅代码、冻结清单、哈希与紧凑回执；媒体与原始日志留在服务器。本轮实例支出和历史GPU累计仍unknown/null。

## 7. 交付与不同执行者复核

有效bundle在服务器 `/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/v2`；其中manifest同时引用根目录既有192输出与v2新144输出。

| 文件 | 作用 |
|---|---|
| v2/protocol.json、v2/selection.json、v2/freeze_lock.json | 生效协议、相同48输入及冻结哈希 |
| v2/manifest.jsonl、v2/build_receipt.json | 活跃输出、真实映射、回执与资源 |
| input_checks.jsonl、prepare_receipt.json | 48个输入现场原生时间/SHA |
| time_metadata_issue_v1.json | 108条原时间封装失败及保留旧版路径 |
| propagation_v1.py、correct_time_v2.py | 原始构建器与限定修复器；代码均已锁哈希 |
| replay.py、self_integrity.json | 可回放读取器与本实现者机械自查结果 |
| package_summary.json、ACTIVE_BUNDLE.json | 分母、单元数量与接续入口 |

论文无关的FFmpeg接口依据使用[官方命令文档](https://ffmpeg.org/ffmpeg.html)；最终合同以服务器4.4.2实测字段和回执为准。

窗口A可在自己的namespace运行下列命令。replay按冻结SHA规则每label×非identity处理轨取一条，共12条，最多2CPU，输出前检查共享空间；输出目录必须此前不存在。`integrity`只读，不生成媒体。

```bash
/root/miniconda3/bin/python /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/replay.py integrity --bundle /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/v2
/root/miniconda3/bin/python /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/replay.py replay --bundle /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/v2 --output-root /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/data_audit/b_replay_20261009
```

请独立核对输入确属fit、原生字段来源、祖先未知项、identity全片与分析窗口、七帧PTS/1.75秒封装区别、共同处理表与来源混杂限制。源码与机械重放通过仅仅支持处理链验收；正式来源/祖先/许可证准入、机制判断、扩大数据和GPU pilot仍按协调单依赖执行。
