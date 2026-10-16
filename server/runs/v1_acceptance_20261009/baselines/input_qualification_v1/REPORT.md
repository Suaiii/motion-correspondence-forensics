# C2：真实输入资格与 CPU 解码首包

dispatch：`v1-monitor-20261009-C2-input-qualification`。全部新输出在 `baselines/input_qualification_v1/`。D2 正在审的原指标器、schema、adapter、旧 C 交付均保持原字节。

本轮完成 **7,436 个 clean 媒体和 B v2 的 336 个输出**的时间资格/帧计划，共 **77,720 条 method×track 记录**；已按 A 当前 fit 与原 fit 的交集冻结 12 个边界样本，实际执行 CPU 解码与空间前处理。没有 encoder、head、训练或 GPU，没有读取 holdout 检测分数。来源/祖先/模式仍 unknown；机制数据门继续 FAIL。

## 1. 作者输入合同

`method_input_contracts.json` 为每条约束绑定 C 已冻结的作者 commit、源码 SHA、函数行号与 processor config 字节。

| 方法 | 作者参考策略 | matched 的明确条件 |
|---|---|---|
| D3 | ffmpeg 8 FPS、最多 3 秒 JPEG；reader 至少 8，准备数量≥16则前16；10%长轴 crop、224 resize，cv2 BGR+ImageNet normalization | 本包冻结 16 张互异原帧、15/8 秒跨度、8 Hz、误差≤1/16；作者 fallback8 单列，不能将 B7 改成8 |
| ReStraV | 中心2秒、请求24，TorchCodec repeat_last；RGB `/255`→224 bicubic antialias；21D几何头最低8帧 | 参考预算24个独帧、2秒共同窗口、误差≤1/8；B7既不足最低8，也不足默认24 |
| 过度连贯 | ST至少2帧、最多16，原 FPS整数round stride至8 FPS；有效FPS须在±5%；CLIP-L224 processor | 冻结16独帧和15/8秒跨度；4 FPS无法原生达到8，30/4=7.5 FPS也超出±5% |
| Native-scale | 2 FPS、中心最多8；140k config `temporal_pad=false`，不足8时 loader 返回短序列；patch时间维2 | 出版参考8帧需3.5秒 PTS跨度，本包完整共同 envelope 为4秒。B7可取0/0.5/1/1.5秒共4帧，仅短序列时间候选；Qwen processor/token/隐式 padding仍待运行核对 |
| STREAM | 原始 I-frame、coded MV、pre-deblocking prediction residual；没有取得作者 executable sampling contract | 最低帧数/时长为 unknown，光流/RGB差分不得补位 |

Native-scale odd T 的 processor 隐式补齐规则未取得，因此不签独帧资格。B7没有被填成8/16/24；其4帧候选也没有冒充出版论文8帧输入。

## 2. 全 clean 资格统计

下表是**时间/采样 recipe 候选数**，不是完整方法运行通过数。包括全部已暴露角色，actual CPU 读取仅12个 fit 样本。所有完整方法 gate 仍 false，来源匹配的机制比较数仍0。

| 方法 | native/reference recipe 或时间候选 / 7,436 | matched 时间候选 / 7,436 |
|---|---:|---:|
| D3 | 7,290 | 6,271 |
| ReStraV | 7,290 | 5,289 |
| 过度连贯 | 4,164 | 4,164 |
| Native-scale | 7,120 | 4,180 |
| STREAM | 0，全部 unknown | 0，全部 unknown |

原 v1 的 OpenSora/T2V-Zero matched default24 ReStraV 单元均为0；Native-scale 8帧/2Hz完整共同窗口也均为0。D3 matched OpenSora为982/990，T2V-Zero为0/1003。过度连贯 matched T2V-Zero和Sora为0；其整数stride+5%规则排除大量约30 FPS real，不能删掉这些行后只报平均。这些是输入限制，未产生检测成绩。

扩展 Luma/Pika/Vidu与OpenVid-HD的高帧率资产提供时间候选：D3与ReStraV合计2999/3000；它们仍没有逐样本来源/生成模式/真实祖先证明。不能借较高时间资格解除严格机制门。

所有排除原因、原始分母、source/generator/role/variant/profile单元留在 `sample_eligibility.jsonl`、`frame_plans.jsonl`、`eligibility_matrix.csv`。原生整数PTS来自锁定 manifest，12个实测样本另逐一与现场 ffprobe整数 `pkt_pts`/`pts`、rational time_base核对；没有用 best_effort 或容器FPS构造缺失原帧。

## 3. B v2 的有效信息边界

B是48候选祖先×7 variants=336；共同支持为7个4Hz瞬间，跨度1.5秒，display envelope1.75秒。C2保留全部输出，另外继承 A 当前组件隔离：2个旧回执冲突组件对应14个 B 输出仍不投入模型。这14条是 A 角色限制，不能称新 B 媒体或管线失败。

| 方法 | B native/reference候选 /336 | B matched候选 /336 | 可解释范围 |
|---|---:|---:|---|
| D3 | 322 | 0 | reference可能重复原帧；matched至少8原帧，B只有7 |
| ReStraV | 322 | 0 | reference repeat24单列；matched 7不够21D最低8，更不够默认24 |
| 过度连贯 | 84 | 0 | reference若原采样满足8FPS才有候选；共同4Hz网格全不合格 |
| Native-scale | 321 | 322 | matched仅4帧2Hz短序列时间候选，processor和出版8帧等价性未过 |
| STREAM | 0，unknown | 0，unknown | 代码/提取器和采样最小值缺失 |

Native-scale matched322=real161、OpenSora84、T2V-Zero77。每个variant有元数据级的两类候选，但没有 Qwen runtime 测试、严格来源 real support 或机制结论。`B_comparison_eligibility.csv` 记录89个 variant/profile单元，空类明确保留；其中 class-defined 仅是条件分母，完整作者方法与 source-matched 标志全为false。

## 4. 真实 CPU 检查

冻结选择：real/OpenSora/T2V-Zero各4；每组覆盖最少原帧、最短时长、最大像素、固定SHA排序，real最后一格优先覆盖OC合格FPS。A当前role与历史role都必须fit，候选组件不重复。没有替换失败样本或从外部/holdout补样本。

**实际结果：36个方法入口，29次 decode+spatial pass，7次资格拒绝未解码，0运行失败。**

- D3：12/12；ReStraV：12/12。
- 过度连贯：5次通过，7次因FPS不满足8±5%而跳过。四个T2V-Zero均为4 FPS；三个real为约30 FPS；另一个25 FPS real有效FPS=25/3，位于容差内。
- 每次实际读取的视频均核对输入 SHA、全现场整数PTS序列、time_base、已选原帧PTS与 ffmpeg showinfo；像素原帧只按计划索引取出，前处理tensor有限且形状 `[T,3,224,224]`，输出 SHA/shape/重复数量有回执。
- CPU affinity `[0,1]`，Torch intra/inter-op2，ffmpeg decode/filter/output各1线程，OpenCV1线程。decoder主体 wall16.584657秒，模型调用0。
- 张量仅保留在服务器RAM，未写 `.npy` 或下载媒体/frames。日志、hash和简要回执已回收本地。

**作者参考等价性的具体缺口必须保留**：当前可执行 decoder是显式native-index/PTS适配器。D3的作者ffmpeg fps→JPEG真实源帧绑定、ReStraV的未锁TorchCodec backend、过度连贯的AutoImageProcessor4.57.6像素字节parity尚待单独回放。本次D3仅验证BGR/crop/resize/normalize primitive，未伪造JPEG/FPS等价；ReStraV空间primitive与作者源码配置一致；OC按固定processor config进行手工空间primitive，未加载HF模型。故29次通过支持输入读取/空间软件，不能签论文reference复现或检测效果。

## 5. 最小补足条件与可运行前清单

`readiness_checklist.json`逐方法列权重、代码、依赖、输入与存储门。推荐最小共同新增视频条件为：**实际4秒、native24 FPS或其可满足整数stride的倍数，4秒内≥96个互异帧；保存原始整数PTS/time_base、原生尺度与生成/采集回执。** ReStraV还必须由冻结24目标实际选出24独帧；Native-scale出版8帧/2Hz输入必须有3.5秒真实跨度；OC8Hz实际stride/tolerance必须核对。24FPS是确定性充分配置建议，不把任意≥24FPS都称合格。

真假共用相同物理支持和B处理表。来源需至少3个独立采集族、4个生成器族与逐样本T2V/I2V/prompt/image/model-version闭包；OpenVid、Vript等发布名称不替代这些证据。新采集/新B时间支持另经协调端授权；当前2秒/4FPS素材不能靠转码、重复或改容器FPS补成4秒/24FPS。Native轨保留原始尺度，Qwen的processor尺寸/token预算单独验收。

## 6. 版本、失败与存储

- 首次资格脚本在import前有syntax failure，源码与raw回执保留 `*_v1_failed.py`、`qualify_run001.*`。
- metadata v2误将B `status=completed`按`ok`判断，产生错误的B QC排除；全部五份输出做gzip逐字节验证归档在 `metadata_v2_status_parser_failed/`。metadata v3修正为completed+all checks，重算全量，无分数参与。旧失败未覆盖成pass。
- 当前CPU的12个fit选择与v3重新冻结选择SHA相同，所以没有重复执行不受该状态解析错误影响的29次解码。
- OpenCV按作者要求4.12.0.88仅安装到新C2 `cpu_deps/`，约151MB；原环境、旧指标器与作者源码未改。没有大型权重下载。
- 当前远端输出约350.6MB（约334.3MiB，含依赖和完整失败归档），低于512MiB。完整逐样本JSONL保留服务器，本地仅 compact证据与CSV；最终精确hash/路径见 `remote_artifacts.json`。

本包完成的是输入资格首轮与限定CPU适配。STREAM、完整作者sampler/processor等价、encoder/head、五seed、严格数据门与GPU仍pending。未知资金与历史GPU小时保持null。C2自测不冒充独立科学复核。
