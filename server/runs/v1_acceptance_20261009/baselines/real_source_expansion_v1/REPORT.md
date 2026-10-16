# C4：KoNViD-1k 完整长时序真实端交接

dispatch：`v1-monitor-20261009-C4-konvid-real`。仅写`baselines/real_source_expansion_v1/`；全部媒体和原metadata ZIP只在指定服务器namespace，本地仅紧凑源码、目录、nativePTS/资格/hash及回执。旧C/C2/C3、D和共享状态只读。

## 1. 实际完成状态

- 官方完整发布数：**1200**；取得并逐项处理的Flickr源ID：**1200**。
- verified媒体：**1200**；唯一文件SHA：**1200**；原生integerPTS/rational time_base与完整decode通过：**1200**。
- 有至少4秒真实PTS跨度：**1200**。失败记录：**0**，原始分母不因失败改变，不替换样本。
- publisherFlickr父源ID数：**1200**；已核实独立相机祖先数：**unknown**，不能混用这两个数。
- AV仅记录存在：audio present=1161、absent=39，没有音频检测或AV分数。

12probe按SHA256(FlickrID)固定选择，12/12通过CRC/大小、全视频decode与至少4秒原生时间支持后，才依据工作单继续完整1200成员发布集。没有选质量较高子集或读检测分数。

## 2. 官方身份和下载回执

官方页面：[MMSP Konstanz](https://database.mmsp-kn.de/konvid-1k-database.html)；同页列出的官方hostZIP端点，保留HEAD、ETag、Last-Modified、Range及完整目录。全体目录1201项（1200视频+目录），完整归档与提前冻结的member路径/大小/CRC/offset/属性一致。写入前拒绝绝对路径、..、符号链接、加密条目与超限单文件。

完整视频归档2,407,293,394字节，**完整读取**后的本次SHA256：

`3528bf99b4d8bad23ced543a45c9a338a14ff567cd6e1bfa2be967c3daed5def`

原metadata ZIP SHA：`13af8b028536bf1864361396d6b41c92dc143d359de51eeb76130fc6a48eddbe`。没有作者公布SHA或签名，自算SHA及ZIP CRC仅证明本次获取/恢复身份，不能宣称作者字节认证。

首次严格HTTPS在两端因证书过期失败，HTTP链接也重定向到该HTTPS。peer证书notAfter2026-10-05，日期校验例外明确保存；CA/signature、hostname和peer SHA pin仍验证，TLS仍加密，仅匿名公开数据，没有账户/表单/作者联系。**不是当前日期有效TLS**；该传输限制保留给独立来源审查，不升级数据门。原回执、公开证书与OpenSSL文档依据见TLS_TRANSPORT_NOTE和date_exception_probe。

全归档支持从`.partial`实际字节偏移恢复，If-Match/Content-Range/ETag和证书pin不一致即停止；失败原回执保留，禁止从零重发整个批次。已完成状态锁在archive/resume receipts。

## 3. 发布处理、来源与权利

metadata文件名含`original/cut_centercrop_960x540_8s`，归档文件则为FlickrID.mp4；采用数字stem=metadata FlickrID=publisher文件名前缀的明确join，全量错配0。metadata中的original不是相机原片证书。实际发布片段、裁剪/缩放和重编码历史与未知字段说明见SOURCE_RIGHTS。

作者论文说明源自Flickr/YFCC100m的CC候选，源筛选排除ND并有尺寸/时长/FPS要求；属性分析用了裁剪/缩放版本。当前发布clip不是未处理相机原件，精确trimoffset/重编码命令、原作者设备与绝对相机时钟unknown。[作者原文](https://www.uni-konstanz.de/mmsp/pubsys/publishedFiles/HoHaJe17.pdf)

仅使用FlickrID、publisher文件名与发布处理字段；MOS、个体质量评分及crowdworker browser/user_data没有参与选择、资格或报告，相关原metadata不落本地。官网研究使用/引用要求与源CC声明不替代每条当前许可、署名、再发布和相机真实性核验。

## 4. C2时间候选

| 方法 | native/reference recipe/时间候选 | matched时间候选 |
|---|---:|---:|
| d3 | 1200 | 1200 |
| restrav | 1200 | 1200 |
| overcoherence | 381 | 381 |
| native_scale | 1200 | 1200 |
| stream | 0 | 0 |

这些不是完整方法runtime通过或检测指标。真实分母1200全部保留；overcoherence按冻结的整数stride至8FPS±5%合同，会排除约30FPS的视频，未改FPS、补帧或转码来强行过门。全部视频仅real publisher label，没有fake对照，因此本包cell AUROC仍undefined。C2完整作者decoder/processor parity与模型前向未执行。

## 5. 有界旧证据交集

对A/A2/B/B2/B3六份既有metadata做有界media-SHA/已声明parent键/Flickr命名空间比较，读取38285724字节，未开旧媒体或改旧证据。相同文件SHA交集累计0；显式Flickr ID交集累计0。详情及输入SHA见bounded_intersections。

其他平台ID不与Flickr ID等同；空SHA/异命名空间交集不能证明无视觉转载、裁剪或共同相机祖先。后续需要逐项原资源/作者/许可/跨平台映射及独立近重复筛查。该来源可补公开描述性benchmark，是否构成第3个独立真实采集族、机制归因或正式祖先门仍unknown，不由C自签。

## 6. 资源与状态

远端总新增4,902,043,726字节（归档、媒体、metadata、checks和回执全计），上限6GiB；最终可用27,121,864,704字节，仍保留20GiB底线及其他包2GiB。C4进程affinity0/1、RAM RLIMIT_AS4GiB，ffprobe/ffmpeg显式1线程，CPU总上限2；未启GPU/模型/权重/训练/AL144/AL146，也未新租实例。资金与历史GPU小时unknown，未写为零消费。

首轮catalog因归档ID文件名与publisher处理文件名不相等而join不足，旧源码和失败回执保留；修订使用三方FID/prefix join，未改12个固定排名或依据MOS/模型分数补样。旧默认HTTPS失败同样保留。

交接入口COMPLETION.json、delivery_hashes.json、manifest.jsonl、qualification_matrix.csv；逐条PTS与full-decode命令/check回执仅指定目录可回放。所有新增材料development evidence，scientific gate=false，独立数据/来源复核pending。完成后不自行再开窗口、跨聊天消息或启动新实验。

## 最终冻结

最终stat资源快照见FINAL_RESOURCES.json，测量点在小型控制文件封签之前；没有追加媒体hash、decode、下载或探针。C4已冻结，后续独立来源/祖先复核另包执行。
