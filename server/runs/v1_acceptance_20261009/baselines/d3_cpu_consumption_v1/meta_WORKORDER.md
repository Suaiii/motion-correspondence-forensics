# C10：固定12输入的首次真实D3 CPU推理

dispatch_id: v1-monitor-20261009-C10-d3-cpu-consumption

状态：工作单已准备；只有协调端补齐封存B8输入锁并发消息派发后生效。此前C9已完成；本包是独立新CPU运行，不能将C9资产取得记为推理。

目标：固定作者XCLIP-16/l2离线模型消费12个已验证CPU输入，产生真实逐样本分数与加载/encoder时间和RSS。该12条均为已暴露fit，不能用它们给出泛化或机制通过结论。本批一次、seed=0、batch_size=1、float32 CPU。无需等待正在实施的A11全量producer或D12 ReStraV。

## 写入/资源

仅写本地/云端 `baselines/d3_cpu_consumption_v1/`。云端总cap128MiB、本地32MiB，运行输出32MiB，CPU4/5及最多2线程，进程组RSS4GiB；资源账本RESOURCE_LEDGER_033要求20GiB空闲底线，统计logical/allocated/charged并按尚未使用的增长计算剩余预留，运行前复核。B8/D12/A11只有本地任务，云端新增预留为0。仅现有22647服务器，无GPU/租用/充值/安装/额外下载；实付与预算余额unknown。

源码/输入/缓存/结果各放独立子目录：原字节复制封存B8完整所需代码与13份evaluator到自有source目录，保持内部相对布局和CODE_LOCK；显式参数传prepared-root/asset-dir/dependency-path/input/output，避免默认路径覆盖上游。所有已有资产/帧/依赖原地只读，不复制大payload或JPEG。不得直接运行会写回A7/D4旧目录的adapter。

## 固定输入与真实执行

1. 校验C10固定输入锁；D3_FIXED_INPUT_CANDIDATES_032记载原12条顺序与A10判定，全部approved，4real+4OpenSora+4T2V-Zero，source/current/previous role全部fit。保留candidate ancestor_id但ancestry_status=unknown。既有C2理想时间网格不作为实际reader映射。
2. 从候选事实创建B8 typed selection、prepared index和A7原字节记录的d3子集；所有源记录SHA与每条canonical record摘要分别保留。A7 inherited/input_records.jsonl SHA4c5ee6966d1726d02231f1cccac545252d105cd89d877d086ed56ff61c9fd5d9。199张prepared JPEG都已云端SHA核对；实际消费前8/16张由原记录决定。原生probe字段为pkt_pts，保留native integer PTS/time_base。不要重新解码旧27条或这12条视频。
3. D4依赖路径依次为 `fingerprint_cpu/author_input_parity_v1/dependencies/site` 与 `baselines/input_qualification_v1/cpu_deps`，均云端v1_acceptance根下。用B8环境锁入口记录实际cv2提供者opencv-python-headless4.12.0.88及模块/扩展身份，禁止虚构opencv-python或安装别名。core版本已在D3_PREPARED_INPUT_REMOTE_CHECK_032实际读取；仍按实际运行环境封存。
4. 唯一XCLIP目录为C9 `baselines/inference_assets_ready_v1/assets/xclip16/`。model779789644B/SHA b5db836d57b7e22001cb2bab581719e910b4c571d926fe839b5d07bc0ba2d03e，config8897B/SHA43d49d757dc8a3ef3dfd242d7ebe0c2effcfa0404f9343864e50c45245f99d3a。C9本地DELIVERY SHA3ab5caae83353c4410204837ab925d74e9f52a48c6f34566cc8347f1b7bce412。repository/revision microsoft/xclip-base-patch16@d6184e3fd8780d04c85d0f1eabe5f94bf44d98f6。完全offline，使用原地safetensors。
5. 按B8最终CLI先产生无score的冻结执行manifest/asset锁、plan，再运行显式run。保存实际命令、PID/start_ticks、退出码与日志，不以连接/plan成功代替模型执行。实际检查所有必需视觉key/shape严格加载，未用text键另列；不得容忍随机缺权重。记录pooler_output和实际输入HW/shape、tensor SHA、raw作者sample std和score_fake=-raw；标签不能用于改变方法、方向、阈值、帧或超参数。
6. 保存完整12条success/failure/pending账本。每条断点可恢复，同锁不重复成功项。观察超时不重启。若失败，先保存精确模型/依赖/接口错误；仅可在自有新路径做必要的小封装或向协调端报告具体缺口，不改作者forward/预处理/样本，不扩seed/调参，不自动从头重试。原失败与修复差异必须保留，版本变化不冒充同锁恢复。

## 验收与交付

验收是实际encoder消费与逐样本输出；复用B8/A7 evaluator，不另写指标。无需重跑合同套件/旧媒体审查或为了报告生成假数据。分别记录模型加载成本、prepared-JPEG读取/preprocess、encoder/head耗时、进程组观测峰值与未观测限制；原视频准备耗时不属于本次推理时间。12fit数据不作为性能论文表或最终确认。

封存REPORT、HANDOFF、DELIVERY、运行源码/锁/命令/原始逐样本输出和精简成员SHA；大资产仍原地，仅回传紧凑证据。若12/12成功，按真实耗时和内存给出完整A10 public8870refs/8803SHA下一批的资源估计，注明A11全量producer/角色兼容仍待接线；其他强baseline保持队列。未满足项照实pending，完成后停止，不新建窗口或派生agent。
