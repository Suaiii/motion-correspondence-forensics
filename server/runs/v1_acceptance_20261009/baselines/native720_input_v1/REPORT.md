# C7 Native720p 实际CPU输入准备

dispatch_id：v1-monitor-20261009-C7-native720-input。用户授权范围是原D4三个fit输入的新720配置，分母固定3，不按效果/内存替换，不打开新holdout或分数。本包补齐一个强baseline的输入变体，没有提出检测算法。

## 来源与版本

工作单SHA为ed5a242caa52b8819bfa113d4b3995e7ddd819be0280b43cd63b124e1467f37c；13项只读来源/上下文锁、固定输入与配置见INPUT_LOCK。原D4 selection SHA35bf2e01103d4ed6667a2716dba7c67bbc3dd1b16079ae45cd1deb44b1e6ad3e，448p真实记录SHAac048e88693a26b0c89e2700ff5f27eceffc220e421ff3dd214a4738af1633bf。作者loader源SHA0ddfdca6b17954475bfd908d1a3d482cc4269917959ae3e6635f00a4096052b1，720 YAML SHA09b08a5c3b92a2a6045c5eb8b883ea4117b2ef15a829c105f197a1a19ee0a41c。

Qwen JSON仅配置：revision66285546d2b821cf421d4f5eb2576359d3770cd3，config SHA7ed3eed5be6924cc800e8a5e53fc405c1aab1aaf36bad65c33403b36c56827f5，preprocessor SHAf2058c716eef96ccaed1cc1e2d0c08306b62586d535b28d9d08e691b2fab7ca0。作者相对JSON路径改为本包镜像绝对路径；历史作者checkpoint的processor版本一致性仍未知。

原class/functions与collate中的processor调用表达式保持AST；仅编译被调用class和该表达式，未执行作者模块的模型初始化。源class AST SHA5066dd6ef6f8e2e91196950015363f88b03030e5c74d71fcbb61235600907c5f。Decord reader以1线程封装调用，返回像素未变换；观察get_batch/asnumpy、indices、实际帧数和像素SHA，异常/黑帧fallback则报失败。test phase沿用原D4确定性选帧，三次RNG state均未改变；source role始终fit。

## 一次有效prepare的真实观察

三条记录原生整数PTS/time_base由冻结D4元数据与原run_001 native probe继承；本轮对原probe bytes、完整整数序列和time_base再核对，没有重扫时间或新增时间来源。actual Decord ordinal采样与448记录完全相同；媒体SHA在prepare前后匹配。完整源PTS、选中PTS、有理显示秒、batch像素SHA、tensor形状/SHA与canonical服务器路径在每条record。此来源绑定仅仅继承原D4范围，不补成样本祖先或相机机制认证。

| 固定输入 | 索引（两轨相同） | 448实测栅格 H×W | 720实测栅格 H×W | loader→逻辑槽 | 720 grid_thw | 720 tensor形状 |
|---|---|---|---|---|---|---|
| Vript real Scene-070 | 0,14,28 | 336×588 | 532×952 | 3→4 | 2,38,68 | 5168×1176 |
| OpenSoraL_109233 | 见完整record，同原448 | 448×448 | 504×504 | 4→4 | 2,36,36 | 2592×1176 |
| t2vz-ec035ada… | 见完整record，同原448 | 448×448 | 504×504 | 4→4 | 2,36,36 | 2592×1176 |

三个时间选择/PTS均相同；独立原生支持3/4/4，processor逻辑槽4/4/4。real最后temporal patch的两帧实际相等，奇数3帧的末槽补为4；新增原生帧数为0。配置上限没有令输入固定到720高。本固定3条均得到较大栅格，这一有限观察不能推广到所有视频或解释为检测增益。

训练声明差别见CONFIG_DIFFERENCES：448 YAML是真实CSV `./data/real_images/real_kinetics.csv`，720 YAML是 `./data/real_images/real_kinetics_70k.csv`；本次仅比较输入，没有核实两CSV数据集相同、训练相同权重或尺度效果，因此不是相同训练数据/权重的尺度消融。

## 进程、资源与失败

第一次启动supervisor99976/worker99977在导入adapter之前的来源SHA循环退出1，原错误为云端D4根下parity.jsonl不存在。本地该文件是聚合导出；首个worker没有EXECUTION_LOCK、Torch/processor初始化或prepare。RUN_RECEIPT、worker.stderr与SOURCE_PROBE完整保留，不能将该启动写成成功。

按实际云端库存另存v2，仅修正local-only聚合引用，加入3条冻结native probe/time_base核对，使用独立claim/log/PID/receipt。作者逻辑、输入、配置未改变，diff与CODE_LOCK_V2可核对。v2 supervisor100322/start_ticks4577265102、worker100323/start_ticks4577265106真实执行3次prepare，三条均成功，退出0；没有因观察超时重启或重解码整个旧27条。另有本地发现阶段FileNotFound/selection schema/缺paramiko，以及一次PowerShell内嵌Python引号错误，均仅影响发现/源码生成，未启动媒体实验；DISCOVERY_FAILURES与RECOVERY_REASON记录其影响。

监督wall5.4573s，实际worker wall4.4041s，user CPU4.307502s、system CPU0.556712s。watchdog的/proc进程组峰值908111872B（866.043MiB），worker getrusage峰值870670336B，分别报告不同测量。原448单输入峰值RSS没有保存，不能补出严格配对内存差。CPU固定4/5，物理RSS4GiB、云端128MiB，本地100MiB；初始现场保留20GiB与A8/D10/C7/B7剩余增长后margin1276591567B，执行后仍约1.27GB，未触发资源保护。

环境：Python3.12.3、Torch2.8.0+cu128、torchvision0.23.0+cu128、NumPy2.3.2、Decord0.6.0、Transformers4.57.6；复用既有D4依赖，无新安装。CUDA未初始化，encoder/head/model调用0；没有媒体/权重下载、本地媒体或新生成服务。媒体和数值tensor留服务器处理内存，全部传回仅仅是代码/config/metadata/log。本项目累计资金与GPU剩余仍unknown；本次CPU时间不等于云端费用账单。

## 记录合同与验收状态

新native720_contract验证method/variant、720 YAML和JSON SHA、固定source/role、完整原生PTS与选帧、有理显示秒、真实processor_size、面积上下限、grid/patch/tensor维度、loader边界、补槽、RNG与无模型声明。实际3条均通过；另5个仅修改已观察元数据的矛盾分别覆盖variant、config SHA、PTS、loader边界及patch rows，8/8实际CLI预期匹配。它们是实施者软件自测，无新decoder/processor调用。

仅仅标记`accepted_current720_metadata`，不验证自报tensor SHA的独立数值重算或作者历史pipeline、模型实际消费HW；后者保持null/unknown。D9已对A7限定修复独立通过，当前C7变体是新增合同，仍需不同执行者独立复核。C6封存pending快照未覆盖，STREAM继续unsupported。数据/祖先/来源/相机/生成器机制、模型收益与完整v1均未放行，AL144/AL146与旧42D冻结保持。
