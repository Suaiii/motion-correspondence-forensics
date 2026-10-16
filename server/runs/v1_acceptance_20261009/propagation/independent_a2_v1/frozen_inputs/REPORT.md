# A2：real 来源与裁剪祖先实际补证

日期：2026-10-09，北京时间。工作单：`v1-monitor-20261009-A2-real-provenance`。

## 1. 本轮实际完成

**3,718 条 real 已全部取得唯一的官方身份／成员元数据关联。** `real_provenance_overlay.jsonl` 逐条绑定原 asset ID、SHA、发布版本、匹配键、已取得字段和仍未知的字段。正确关联3,718，歧义0、缺失关联0、重复键0；这里的“正确”指发布者身份键匹配，并不表示每条原相机链和使用权都已完整验收。

| cohort | real文件 | 实际回收与匹配 | 仍缺什么 |
|---|---:|---|---|
| Vript | 2,000 | 828个官方源视频ID/URL；2,000条官方裁剪边界；2,000个官方成员CRC/大小一致 | 原始整视频字节版本、部分上游权利与真实性人审；新映射独立复核 |
| AEGIS DVF | 109 | 官方meta/mapping身份一致；全部唯一命中作者YouTube real成员；84 train、25 val | 数字ID对应的原始YouTube URL与绝对裁剪区间 |
| AEGIS补充YouTube | 109 | 官方original_id与unified_index身份一致；按原ID显式构造YouTube链接；作者标签camera/real | 每条原视频版本／下载及绝对裁剪日志 |
| OpenVidHD | 1,500 | 全部唯一命中官方CSV和分包清单；1,499条合格文件帧数与CSV相符 | 具体上游分支、原URL和原视频绝对裁剪时间；坏视频继续排除 |

本包没有取得新视频，没有GPU、生成或训练调用，也没有修改首包split、主任务表、WORK_PLAN/DEVLOG或其他窗口文件。机制门保持FAIL。新关联由本窗口实现，须由其他执行者复核。

## 2. Vript：从文件名线索推进到官方源→clip证据

固定取得官方revision `acc278efb0ee249d646eef8a6b023595ca7efb93` 的long/short源视频索引。现有2,000条全部属于long索引，828个源ID全部与索引 `id` 和 `webpage_url` 一致。long索引51,303,634字节的完整SHA与独立取得的官方LFS值一致；short索引也保留了版本与实际文件SHA。[官方字段说明](https://github.com/mutonix/Vript/blob/main/DATA.md)。

官方裁剪元数据在大视频ZIP内。通过只读取ZIP尾部结构、central directory、JSON局部头与 `_cut_meta.json` 成员，检查了固定版本的全部1,095个clip ZIP目录，回收828份裁剪JSON。**没有请求任何视频成员payload。** 对现有2,000条视频流式计算CRC/大小，与官方目录对应clip成员全部一致；这核实了现有文件与官方clip成员的关联，整份上游ZIP SHA未计算。

每条clip的 `span`、`duration` 已落入overlay：起止时间是作者在原视频上的十进制elapsed time，而当前clip的整数PTS/rational time_base另列。没有将源裁剪字符串或名义FPS冒充原始整视频的整数PTS。[官方cut_meta含义](https://github.com/mutonix/Vript/blob/main/DATA.md)。

先前“索引插入顺序÷10可定位ZIP”的四例查证失败已保留；全量目录恢复没有依赖该猜测。两线程阻塞传输版本被记录中断并保留已完成回执，后续使用一条async事件线程与一条DNS线程接续；CPU仍限制在两核、RAM4GiB，失败回执不自动重试。最终全部1,095目录完成，无获取失败，2,000条clip成员关联完成。

**来源身份并不自动证明纯相机画面。** Vript是泛化的web视频caption集合。实际官方平台类别中，297条属于Film & Animation，195条属于Gaming，共492条已写入真实性人审候选单；类别不能直接推出fake，原label未改。Vript原metadata中的license字段仅11条声明Creative Commons复用许可，其余1,989条未给该字段；这是采集时元数据快照，不是本轮逐条权利认证。[Vript集合及研究使用条款](https://github.com/mutonix/Vript)。

## 3. AEGIS/DVF：精确键、采集支路及公开训练暴露

实际取得AEGIS-Full的436条OOD元数据，其中218条real。**viewer `row_idx` 不等于 `meta.unified_index`**：例如页面第0行的unified_index为245。本轮用官方 `meta.unified_index`、`original_id` 与mapping CSV路径联查，218条全部唯一一致，不用显示行号或相似caption配对。[官方字段定义](https://huggingface.co/datasets/Clarifiedfish/AEGIS-Full/blob/ef9844a430927e37ea8e70d1dbb5a167eed10860/README.md)。

AEGIS-Full元数据JSON是官方datasets-server的实际snapshot，保存每页URL、原响应SHA和取数前后仓库revision；revision均为 `ef9844a430927e37ea8e70d1dbb5a167eed10860`。固定版本的139,641字节OOD Parquet也已取得并通过官方LFS SHA，但本次标准库过程未解码它，没有声称API JSON与Parquet字节等价。

109个DVF数字ID进一步精确命中作者commit `5386f817bee109ce4d43312e44d6f510484342b8` 的 `youtube / 0_real/<id>.mp4`：**84条在作者train、25条在val**，没有同名多重命中。这将原“InternVid或YouTube”的泛称收束到具体YouTube real成员支路；原平台ID/URL仍未取得，数字前缀不能当成经证实的原视频祖先。[作者train](https://raw.githubusercontent.com/SparkleXFantasy/MM-Det/5386f817bee109ce4d43312e44d6f510484342b8/splits/train.json)、[作者val](https://raw.githubusercontent.com/SparkleXFantasy/MM-Det/5386f817bee109ce4d43312e44d6f510484342b8/splits/val.json)、[DVF源数据说明](https://arxiv.org/html/2410.23623v1)。

该训练暴露属于作者MM-Det/DVF数据合同，不能把这些real声称为相对作者已训练检测器的新真实来源；它不代表本项目偷偷将AEGIS投入fit。本轮没有模型推理、权重或分数读取。

109条补充YouTube real已关联作者original_id、collection=self-collect、camera/real标签及原有clip信息。URL由作者ID和YouTube来源显式构造，未逐页抓取平台、更没有假称完成了新的平台下载。每条绝对裁剪start/end仍缺。[AEGIS采集与标准化协议](https://arxiv.org/html/2508.10771v1)。

## 4. OpenVidHD：实际全表join与时间字段边界

固定版本 `d8a63bd22989c80b5734ec2bb989f4e1b61a5807` 的OpenVidHD CSV299,852,057字节、分包JSON15,284,572字节均通过独立官方LFS SHA。扫描完整**433,509行**，按video精确键与分包成员匹配，1,500条全部唯一。大metadata只留服务器；本地为选中行、证据哈希和逐样本overlay。[官方数据入口](https://huggingface.co/datasets/nkp37/OpenVid-1M/tree/d8a63bd22989c80b5734ec2bb989f4e1b61a5807)。

1,499条合格视频的native帧数与作者CSV `frame` 一致；已排除H.264坏视频少55帧，原错误未覆盖。文件名里的`starttoend`区间与实际`frame`相比：790条相差0，**710条相差21帧**。作者CSV有fps/seconds，但没有原视频URL、具体上游分支或绝对shot起点；所以不能仅仅把名称区间除以FPS写成原YouTube视频绝对裁剪时间。

保留202个候选源ID与上游train、56个与val的交叉。选中OpenVid的1,500个文件名源token中，5个见于更大的官方Vript long索引，但不在本轮828个Vript源ID内；它们是后续扩展时的共同源线索，不能写成当前包已发生泄漏，也不能由当前精确ID交集为零证明全部祖先独立。

官方项目给出了其他上游集合及分包路径；本轮查证过作者代码入口和作者推荐的mapping，但它们没有提供当前1,500项的原URL/原始shot时钟。Panda全量元数据公开入口为2.73GB，超过本包“小metadata”范围；不擅自取得整份大表，以后可要求发布者提供按1,500个键过滤的源URL/时间映射。[OpenVid作者说明](https://github.com/NJU-PCALab/OpenVid-1M)、[Panda元数据格式与规模](https://raw.githubusercontent.com/snap-research/Panda-70M/main/dataset_dataloading/README.md)。

## 5. 来源族与可用主张

`source_family_evidence.json` 区分平台、发布包、采集协议、原视频、clip和派生。当前Vript的828个原ID与AEGIS补充109个原ID没有精确交集；同一YouTube平台没有自动把它们合并成同一原视频。DVF的数字成员与OpenVid的原父链仍有缺项，**三个独立真实相机采集族尚未验收**。

- 公开描述性黑盒benchmark：3,718条都有发布者身份键关联，仍须保留继承label、质量排除和真实性人审限制。没有把缺相机签名或秘密生成日志扩成全部公共数据不可用。
- 保守祖先隔离：Vript已可用官方source ID、裁剪JSON和成员CRC/大小关联提出分组。`replacement_split_conflicts.jsonl` 保留旧fit/calibration/audit交叉；首包split未修改，新增证据仍须不同执行者复核。
- 机制归因：真实身份补证不能替代fake任务模式、条件图像/prompt祖先、跨来源同处理对照及新方法效果，机制门保持FAIL。

## 6. 最小新增采集单与交接

`minimal_acquisition_plan.json` 已真实核对两种入口，没有取得视频或提交表单：

1. **LIVE-VQC**：作者明确的手机相机采集集合，官方研究使用条款与访问表单可读。提议先按元数据资格固定48个原capture，最坏媒体1.5GiB、处理预留0.5GiB；下载入口/member大小与设备/场景键须在获准入口返回后核实。来源标签和使用条件不能凭第三方转载填齐。[官方入口与条款](https://live.ece.utexas.edu/research/LIVEVQC/index.html)。
2. **UVG-VCM的小型stereo camera控制**：UnderPark、AuditoriumWalk各左视图HEAD为200，长度1,244,160,000字节且支持Range；未来各取2秒共497,664,000字节。左右视图同一capture不能当独立祖先，SyntheticAerial/Drone/City必须排除。raw YUV没有原始容器PTS，需独立审查作者frame clock替代合同，不能把新mux的PTS冒充原始PTS。[作者数据与CC-BY4.0](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/index.html)。

**completed**：全部3,718条发布者身份join；Vript2,000条完整裁剪与官方成员CRC/大小核验；AEGIS精确键与DVF作者成员／支路回溯；OpenVid全表／分包join；原祖先关系overlay、类别人审候选、来源族证据与实查新增采集单。

**pending**：新join的不同执行者回放；492条泛web来源的真实性人审；109个DVF原URL、AEGIS逐项绝对裁剪、OpenVid上游分支/原URL/shot时钟；逐项上游权利及全局祖先；B2的fake模式/条件素材记录合并。原机制门和旧失败不改。没有向其他聊天自行发送消息。
