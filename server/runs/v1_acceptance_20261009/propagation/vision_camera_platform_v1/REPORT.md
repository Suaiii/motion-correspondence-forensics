# B5：VISION 原生相机与真实平台传播证据包

## 1. 执行结果与使用范围

同一冻结批次的24个候选拍摄父键、72个文件已完整取得，72项完整视频解码及原生整数时间检查通过；视频总字节3,449,279,252，72个唯一媒体SHA。8设备、8品牌，各设备flat/indoor/outdoor各一父键，每父键包含native、YouTube、WhatsApp三版本。该包仅仅支持公开真实视频的来源、传播及输入时间资格诊断；独立数据复核仍待不同构建者执行。

## 2. 来源、选择与许可

作者入口：https://lesc.dinfo.unifi.it/VISION/ 。论文：https://link.springer.com/article/10.1186/s13635-017-0067-2 。数据README声明CC-BY-SA4.0；论文CC-BY4.0是单独许可。后续使用须保留来源、许可及修改说明。发布层许可不代替逐样本权利证明。

官方全目录普查包含648 native、622 YouTube、644 WhatsApp，共1,914视频、35设备/11品牌；两个BMP为辅助文件。2019勘误的两个父键及六版本排除。两处特殊.mov.mp4仅作为显式文件名join，源URL保留。此次24/72是固定子集，完整VISION下载未执行。

选择先于HEAD，基于完整三版本、勘误、设备/场景/运动模式及固定字符串SHA；没有利用文件大小、检测分数或MOS选取。设备顺序D17/D24/D16/D32/D08/D07/D23/D04，native→YouTube→WhatsApp逐组取得。冻结选择SHA：`6dfeb42df0ae72a35bda77894f5d5d22e011def34efbe91d648d3db0b4fa5228`。

## 3. 实验目的、方法和观察

### 3.1 传输完整性与原生时间

目的：确认用于传播比较的三个版本均为作者发布的完整对象，且每个版本有可复算的自身时钟。72次冻结HEAD定义URL、长度、ETag和Last-Modified；实际GET使用对象条件验证。完整下载记录SHA256，ETag仅作HTTP对象验证器，作者未发布媒体SHA。

逐文件ffprobe保留真实pts或pkt_pts整数、有理数time_base、视频codec/FPS/宽高/时长，以仅读容器header的补充查询取得format_name和容器时长；要求全部帧PTS严格递增。没有将best_effort时间写成原生PTS。native、YouTube、WhatsApp分别保存自己的时钟，平台时间不当作原相机时钟。ffmpeg完整遍历视频并对错误退出；音轨仅记录存在。普通元数据过滤GPS、日期及身份字段，作者原CSV仅限服务器受限目录。

| 版本 | 完整文件 | 视频字节 | 解码帧总数 | 有音轨文件 | PTS跨度范围(s) |
|---|---:|---:|---:|---:|---:|
| native | 24 | 2,596,837,191 | 50,382 | 24 | 61.567–74.843 |
| youtube | 24 | 527,212,331 | 50,548 | 24 | 61.567–74.842 |
| whatsapp | 24 | 325,229,730 | 50,381 | 24 | 61.567–74.843 |

这些结果支持完整对象与逐文件原生时间记录的工程可复算性，未证明隐含拍摄设置、上传会话或全球祖先独立性。

### 3.2 作者对应关系与固定灰度检查

24组的72个文件均获得官方per-device CSV唯一文件名映射，形成48条作者发布native→平台关系。映射仅支持作者声明的对应链；相似basename或灰度相似度不会升级为拍摄会话证明。

比较在各自PTS跨度的0.1/0.25/0.5/0.75/0.9位置取原始帧，固定±1/40、0归一化偏移，4种90度旋转、100%及58/64（名义90%）中心区域，共24个候选。解码缩放至96×64并提取64×64灰度中心；不改变保存的媒体。以中心化NCC衡量对应，双方灰度标准差至少4、至少3个有效位置，最佳固定候选的中位NCC≥0.8记作一致诊断，<0.3记作强分歧，其余保留未决。该最佳值来自预定有限窗口，没有按结果重新调窗口。

| 固定诊断状态 | 平台比较数（分母48） |
|---|---:|
| intermediate_correspondence_pending | 1 |
| reference_consistent_diagnostic_only | 47 |

所有中间值、低纹理或分歧项目保留具体父键和版本。该诊断能发现明显mapping问题，仅仅相似不能证明同源，也不能排除跨设备拍摄同一场景。

### 3.3 C2物理时间候选资格

每项直接使用原始整数PTS与time_base复算5方法×2轨道，共720个候选计划。D3共同轨道16独帧/8Hz、跨度15/8s、至少2s、误差≤1/16s；ReStraV请求24独帧覆盖2s、误差≤1/8s；overcoherence检查原生整数stride所产生有效FPS在8±5%；Native共同轨道8独帧/2Hz、3.5s跨度/4s容器包络。STREAM作者提取合同缺失，保持unknown。未补帧、更改原FPS或把重复槽位当独帧。

| 版本 | 方法 | 轨道 | 实际候选状态 | 文件数 |
|---|---|---|---|---:|
| native | d3 | matched_processing | temporal_ready | 24 |
| native | d3 | native_reference | recipe_ready_frame_map_adapter | 24 |
| native | native_scale | matched_processing | temporal_ready_processor_pending | 24 |
| native | native_scale | native_reference | temporal_ready_processor_pending | 24 |
| native | overcoherence | matched_processing | ineligible | 23 |
| native | overcoherence | matched_processing | temporal_ready_processor_pending | 1 |
| native | overcoherence | native_reference | ineligible | 23 |
| native | overcoherence | native_reference | temporal_ready_processor_pending | 1 |
| native | restrav | matched_processing | temporal_ready | 24 |
| native | restrav | native_reference | recipe_ready_frame_map_adapter | 24 |
| native | stream | matched_processing | unknown | 24 |
| native | stream | native_reference | unknown | 24 |
| whatsapp | d3 | matched_processing | temporal_ready | 24 |
| whatsapp | d3 | native_reference | recipe_ready_frame_map_adapter | 24 |
| whatsapp | native_scale | matched_processing | temporal_ready_processor_pending | 24 |
| whatsapp | native_scale | native_reference | temporal_ready_processor_pending | 24 |
| whatsapp | overcoherence | matched_processing | ineligible | 23 |
| whatsapp | overcoherence | matched_processing | temporal_ready_processor_pending | 1 |
| whatsapp | overcoherence | native_reference | ineligible | 23 |
| whatsapp | overcoherence | native_reference | temporal_ready_processor_pending | 1 |
| whatsapp | restrav | matched_processing | temporal_ready | 24 |
| whatsapp | restrav | native_reference | recipe_ready_frame_map_adapter | 24 |
| whatsapp | stream | matched_processing | unknown | 24 |
| whatsapp | stream | native_reference | unknown | 24 |
| youtube | d3 | matched_processing | temporal_ready | 24 |
| youtube | d3 | native_reference | recipe_ready_frame_map_adapter | 24 |
| youtube | native_scale | matched_processing | temporal_ready_processor_pending | 24 |
| youtube | native_scale | native_reference | temporal_ready_processor_pending | 24 |
| youtube | overcoherence | matched_processing | ineligible | 24 |
| youtube | overcoherence | native_reference | ineligible | 24 |
| youtube | restrav | matched_processing | temporal_ready | 24 |
| youtube | restrav | native_reference | recipe_ready_frame_map_adapter | 24 |
| youtube | stream | matched_processing | unknown | 24 |
| youtube | stream | native_reference | unknown | 24 |

recipe_ready、temporal_ready及processor_pending仅描述时间或配方计划。D4 readiness修订单独锁定，未覆盖C2。作者loader/processor输出、Native720p、STREAM提取器及模型实际运行均未在B5执行。时间候选通过不会升级为完整baseline通过。

### 3.4 与已有库的有界交集

仅读取旧v1/extension目录数据库及B2/B3/C4冻结manifest的已登记SHA，不重读旧媒体。

| 元数据范围 | 已登记SHA行数 | 与本包字节SHA命中 |
|---|---:|---:|
| v1 | 9,236 | 0 |
| extension | 3,000 | 0 |
| B2 | 256 | 0 |
| B3 | 106 | 0 |
| C4 | 1,200 | 0 |

本包内部相同字节组：0。VISION设备/拍摄文件名与旧YouTube、Flickr、HDVG及图片键处于不同命名空间，精确键不命中不能证明来源独立。全库视觉近重复、跨设备共同场景与独立拍摄session仍unknown。本包新增一个有文档的VISION便携设备采集来源族，8品牌或3版本不会当作3个独立真实来源族。

## 4. 失败保留与接续生命周期

初版ffprobe4.4.2不支持stream_side_data请求；第二版泛用side_data请求得到packets_and_frames并触发旧解析失败，两版回执与日志保留。qc_v3显式frame/stream请求，仅计实际frame及原生pkt_pts，通过完整检查。第一次取得的三文件未因软件修复重新下载。

v3在53/72、17完整父组及第18组两成员后因BrokenPipeError [Errno32]停止，旧PID56314已不存在。此次v4锁定相同selection、53项下载/QC与命令输出哈希，直接复用已完成文件和QC；从剩余19项接续。旧manifest、失败、日志、下载和状态文件均保留。

云端监督PID 96911、工作PID 96912，记录boot_id与start_ticks；stdin=DEVNULL，stdout/stderr落本namespace常规日志，独立于SSH生命周期。工作退出码0、监督资源异常null，进程组峰值RSS 130,809,856字节。CPU0/1，RAM4GiB，零GPU/模型调用。

## 5. 资源、可用性与限制

封存前实测全namespace逻辑占用 3,492,068,811字节、分配占用 3,495,419,904字节，≤4GiB；全盘空闲 23,302,422,528字节，扣20GiB底线、B5剩余上限及A8/D9剩余增长后余量 952,647,680字节。A8合计128MiB，D9合计64MiB；C5/A6/D7/A7/D8已终态，仅释放未来增长预留，原文件保留。实际费用与历史GPU余额未知，保持null。

本地仅交付紧凑代码、来源和回执、原生PTS及SHA清单，不含视频、灰度特征、原始个人字段CSV。可用于作者发布平台处理的real-only诊断、候选输入资格核查和后续保守分组提案。检测模型、二分类AUROC、低FPR确认、三独立真实来源族、祖先留出及机制成立均未验；real-only AUROC无定义。历史曝光保留为development角色，不改名最终确认集。

## 6. 交付与复核入口

COMPLETION、VERSION_LOCK、manifest、处理关系、逐文件C2计划、固定灰度诊断、有界交集、失败未决和完整文件SHA清单均冻结。当前72项receipt一致性检查通过，属于构建者的软件核对，独立科学/数据复核仍pending。A8若接入此包，应追加新的冻结输入锁，保留独立复核状态。到此结束固定批次，无下一批次或模型任务。
