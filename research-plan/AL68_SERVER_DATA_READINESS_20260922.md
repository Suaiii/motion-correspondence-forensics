# AL68：现有服务器开发样本的数据可用性核验

授权：用户2026-09-22要求恢复、安排任务进入已开机服务器，并明确计费由用户负责。计费未知不再阻塞现有实例的本包；不购买、不充值、不扩容，不把未知用量写成零。主DAG指定researchagent_window为执行者，源码与报告在a77e独立工作树。AL36与本包独立。

## 输入与要回答的问题

主状态：E:/aNB/TECH/脉冲神经网络/research-plan/task-hermes/project.json。连接只读server_connection.json，以13340端点和已有密钥为准，不保存凭据。

已读服务器清单见SERVER_DATA_MANIFEST_INVENTORY_20260922.json。它是字段盘点，尚不能把首条示例推广为所有行，也不能由某清单缺字段推断整个数据集不存在该字段。

科学问题：现有HD-VG/CogVideo开发原文件是否保留可抽取的整数PTS/time_base与可核对文件身份，使后续小型机制实验能使用真实时间，而非从标称FPS合成时间？另核验历史清单的来源/标签/祖先/许可状态，明确哪些内容已有证据、哪些仅是状态字符串。

## 执行顺序与边界

1. 读取现有13份小型manifest；逐份记录字节SHA256、解析错误、行数和字段/状态分布。代码源码哈希表单独分类，不算样本清单。不得静默跳过解析错误，不把重叠清单相加当独立样本库存。
2. 从pair2_frozen_transfer_v2/accepted_manifest.json按source分层、sample_id字典序，各取最多4条HD-VG和CogVideo记录，共最多8条；先冻结选择ID、原始记录哈希与配置。只使用已经暴露的开发文件，不改样本角色；C及旧MS/VC2 100条保持冻结。缺文件/哈希不符直接记录，不临时换样本。
3. 冻结独立的stdlib+ffprobe脚本，随后在服务器CPU执行一次只读核验。原媒体先核对文件SHA256；提取stream time_base、codec、width/height、整数frame pts及best_effort字段，分别记录缺失、非单调、重复值和时间差。名义FPS单独列出，不填补缺失原生值。通过pts*time_base得到的秒值仅指当前存档文件时间，不能称为摄影设备原始采集时钟。对本次最多8条样本不要求内部生成器 checkpoint/seed/VAE 信息；这些字段按公开基准/机制归因/最终确认的用途分层报告。
4. 工具版本、源码/配置/输入哈希、逐样本证据、命令、exit code、实际起止/CPU时间写独立目录。本包不调整采样、不产生分类预测、不训练、不调OR1，不复跑旧AUROC。无需为得到pass重复执行；执行失败保留并提出后续修复。

只允许现有服务器、2 CPU线程以内、串行8条probe，每条最多60秒，全部核验最多15分钟，新增输出不超过100MiB。若工具缺失，报告环境缺口；不自行安装大依赖。禁止媒体/模型下载、生成、训练或GPU作业；小型源码上传和紧凑证据回传允许。输出位置为服务器/root/autodl-tmp/cvpr27/runs/al68_data_readiness_20260922的新目录，禁止覆盖任何旧批次。

旧acquire_native_pts.py合同未启用。本包是另立的现有开发文件只读数据核验，使用独立脚本；不修改/伪造旧合同，也不解除旧采集器保护。

## 交付与判据

- 独立工作树research-runtime/data_readiness_20260922/下的源码、配置及freeze记录。
- research-runs/data_readiness_20260922/AL68_report.md、AL68_evidence.json、AL68_handoff.md。
- 每条时间结论与源文件哈希绑定；记录哪些来源字段仅声明/有链接/有实际可读证据。
- gate_scope=existing_development_data_readiness；只验收上述可观测数据条件，不能宣称泛化、创新、源类因果效应或独立科学复核。
- 同时给出公共基准复现、受控机制、最终确认三种用途的可用/缺失项。闭源生成器没有checkpoint/seed/VAE哈希不自动否决其公共黑盒评测用途；它不能用于已知内部组件的机制归因。

无论核验成功或失败，都继续独立AL36。完成后向Plan9.16交接实测结果和提交；不可自行改主DAG、推master、生成更多任务或启用训练。接下来至少保留数据来源/划分证据补齐与固定强基线接口两项独立建议。
