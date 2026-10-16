# B2：生成模式与条件祖先补证首包

dispatch_id：v1-monitor-20261009-B2-mode-provenance。完成时间：2026-10-09T02:14:55.411754+08:00。

## 1. 实际交付与状态

**3,718条现有fake已生成证据overlay；256个冻结SVD候选源祖先的小包取得256个，完整解码/原生时间QC通过256个，失败0个。** 新SVD按官方成员、官方源ID和论文I2V生成协议记为 **E1/cohort-linked**；精确条件图像、取帧索引、checkpoint/seed和实际generation-request仍unknown。仅仅字节取得、可读及官方关联得到补充，机制数据gate没有通过。不同执行者的审查仍pending A。

旧B v2传播包没有重制。主WORK_PLAN、project.json、DEVLOG、原始v1/扩展包及其他窗口产物没有写入。

## 2. 现有fake的逐项查证

| 资产 | 数量 | 新恢复证据 | 未恢复字段 |
|---|---:|---|---|
| T2V-Zero | 1003 | UUID精确匹配官方Pair1成员和官方VidProM prompt标注；发布生成协议为T2V | 实际请求、checkpoint、seed和请求级mode |
| OpenSora | 990 | 官方论文报告T2V；RoboVid源文件清单精确关联990条已有来源路径 | 官方archive member–prompt crosswalk及样本请求 |
| AEGIS Sora | 107 | 86个编号精确匹配本地SoraPrompt表 | 21个编号未匹配；官方请求/模式未证 |
| AEGIS Kling | 111 | 14个编号精确匹配本地KLingPrompt表 | 97个编号未匹配；官方请求/模式未证 |
| 原OpenAI-Sora | 7 | 保留已有文件身份与SHA | 原sample–prompt/模式映射unknown |
| Luma/Pika/Vidu扩展 | 1500 | 核对官方test的Video_id字段与原zip member | 数字输出名无已证crosswalk；不按表行号猜对应 |

总计恢复 **1,103份可逐项关联的prompt候选**，其中1,003来自固定版本官方标注，100仅为本地编号表。2,000条RoboVid fake精确关联原split来源路径；随机real/fake配对不作条件祖先。官方标注文本的SHA和原文件SHA逐项保存；不把标注prompt填成已认证actual_prompt。现有3,718条严格generation_mode仍unknown，不覆盖旧记录。

`existing_mode_overlay.jsonl`逐条附asset ID、原输出SHA、精确join键、行号、源文件SHA、证据层级与缺失字段。官方成员关联、发布生成协议、实际逐样本请求是分别记录的三种证据。品牌支持某模式没有用作逐条mode标签。

## 3. 官方来源、访问条件与锁

源为作者[GenVidBench项目](https://genvidbench.github.io/)和[固定发布库](https://huggingface.co/datasets/jian-0/GenVidBench/tree/701cafb6f999d7ea0cbf3c354df6177311a4d824)，revision固定为 `701cafb6f999d7ea0cbf3c354df6177311a4d824`。本轮取得官方Pair1/Pair2 labels、HDVG/ VidProM标注、HDVG成员表及核验代码；七个HF小文本的Git blob SHA均与事前发布树一致。GitHub commit、完整文件SHA和HTTP回执在sources.lock与source_validation中。sources.lock的“未下载大媒体”仅仅描述元数据锁定时点。

作者[论文v3](https://arxiv.org/html/2501.11340v3)把SVD列为I2V，并说明条件来自HD-VG视频帧。当前实际关联链是：**SVD归档成员→Pair2官方样本号→HDVG官方class/source-ID表→同号原HDVG成员**。文件名里的描述是配套caption，不是已证SVD文本输入。确切条件图像二进制、取帧时点/裁剪和真实请求没有公开取得，不靠生成视频首帧替代。

官方项目README声明数据CC BY-NC4.0；此次用途限非商业科研开发证据，不再分发。仓库Apache2.0是代码条款，未用它覆盖数据或上游HDVG素材。逐样本上游权利仍unknown，正式权利gate未通过。

另调查了[VBench作者I2V方案](https://github.com/Vchitect/VBench/tree/master/vbench2_beta_i2v)：它公开条件图像/crop/URL/caption和输出命名协议，条件字段更完整；但当前尚无在预算内锁定的逐项输出访问/hash和实际请求包，故保留为补证入口，未把未知媒体替换成证据。

## 4. 冻结选择与祖先/曝光检查

固定selection seed43，按source ID和成员名SHA排序，不读取模型分数，每个不同候选source ID取一条，最多256；冻结后无替补。先核对官方SVD成员与HDVG源ID，排除既有候选source ID及相同已知prompt文本。

- quick-open实际观察13,369个非solid MP4成员；仅读取1,571,116字节索引/头，没有把quick-open当整归档完整列表或整归档SHA。
- 可用候选13,194；排除175个既有候选源ID命中。
- 现有v1/扩展真实端候选源ID共2,328；另有界读历史metadata得到102个候选ID。
- 冻结256个不同候选source ID，对以上候选集合和已知prompt hash交集均为0。

这些是官方键与有界曝光筛查；不能证明视觉近重复不存在、所有历史数据已扫全或256个祖先已科学独立。caption相同也不自动证明它是I2V输入；真祖先、共享input image和模型预训练曝光仍待A核验。

## 5. 真正取得与校验了什么

利用非solid RAR5按冻结成员HTTP范围获取，严格检查206/Content-Range/长度；原始成员头与quick-open缓存逐字节一致，再构造独立小RAR，经UnRAR解压并核对size/CRC。保存完整原生MP4，无裁剪、统一帧率、补帧或训练预处理。原输入归档声明LFS SHA仅作发布锁；**实际没有下载或核验全部4,464,368,372字节归档**。

对每个取得文件保存输出SHA、来源压缩span SHA、原头、mini-RAR SHA、解压退出码与原始日志。ffprobe现场取整数pts/pkt_pts和rational time_base，严格递增并保存完整序列；ffmpeg -xerror/err_detect explode完整解码，未用best_effort代替原生时间。

取得有效文件数256、唯一输出SHA256、候选source组256；原生帧数分布为{14: 256}，共检查3584帧。本执行者的只读复查核验256/256，未发现与v1/扩展已有字节SHA交集。构建者自查仅仅属于软件证据，不自签独立科学审查。

条件素材目前仅取得官方源ID/成员/caption映射。quick-open观察范围没有PNG/JPEG；HDVG原媒体在约80GB嵌套包内，超过本包6GiB预算，且帧索引未公开。没有下载错误条件图像或把模型输出帧冒充input image。

**新时间兼容性限制：**256条均为14帧、10FPS，原生PTS跨度13/10秒、容器时长1.4秒。旧B v2的目标PTS跨度3/2秒在本包0/256条上可用，不能直接复用其七点窗口。后续必须由不同执行者审核更短的真假共同时间协议与real对照；不得补帧、插值或裁剪后改称原始媒体。14帧也不能用来推断精确SVD checkpoint版本。`native_time_support.json`保存逐分母汇总。

## 6. 资源与完整性

获取前冻结了访问条件、容量、计划和脚本哈希；预计新增资产171,193,150字节，另留64MiB余量。每条输出前重新检查本namespace全部资产≤6GiB、全盘空闲≥20GiB。亲和性最多2CPU，单作业，原生工具显式1线程；进程地址空间4GiB，无GPU、detector、付费生成API或新实例。

本轮range实际取得85,585,065字节；receipt时本namespace全部资产216,197,039字节（0.2013GiB），结束盘空闲30.840GiB，获取/QC墙钟731.436秒。本地只保留代码、清单与紧凑证据，媒体和完整压缩/解码日志在远端。历史GPU小时与实际费用保留unknown/null。

## 7. 交付、复核与最小剩余缺口

入口COMPLETION.json；首包文件包括STARTUP、sources.lock、existing_mode_overlay、join_audit、acquisition_plan/lock、manifest/receipt、exceptions.summary、mode_coverage及review_field_diff.csv。数据角色统一为 **development evidence**，没有自动并入fit、calibration或最终确认集。有效新成员仅释放A的不同执行者核验。

A可只读执行：

```bash
/root/miniconda3/bin/python /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/mode_provenance_v1/review_b2.py
```

最小补证为：对这256个官方样本逐条取得精确input image SHA、原clip/帧索引与裁剪配置、生成器checkpoint revision/seed及原request→output关联；同时解决原始素材权利和已证祖先闭包。若作者仅能提供发布层映射，继续保持E1开发用途。另一个可调查路径是VBench的小型可访问input–output对子，但须先锁访问/条款/文件hash，不由此首包自动放行。
