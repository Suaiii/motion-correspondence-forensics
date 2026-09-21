# AL70：公开 Video_id 与现有服务器文件交叉核验

- 实际时间：2026-09-22T01:45:39+08:00
- 公开输入：AIGVDBench validation `val.jsonl`，3000行完整读取，响应 SHA256 `2f9cba82d02f97c1c26a2f59694c24151683c29eae12f2e6c739574005e5f84f`。
- 固定选择：按文件顺序取前20条可解析 `Video_id`，不按匹配结果筛选；prompt只保存SHA，不把文本当标签证据。
- 服务器输入：13340端点已有12份manifest，只读读取文本并记录各自SHA；没有打开媒体、抽帧、模型或GPU。

## 结果

20个公开 validation ID 与这些现有 manifest 的 `path`、`raw_path`、`archive_member`、`fake_file`、`real_file`、`sample_id`字段做严格basename/精确值匹配，得到 **0个匹配ID、0条匹配记录**。

这意味着当前服务器上的 candidate200、combined_candidate130、ComGenVid、mech4fps、profile100以及pair2开发manifest不能被当作AIGVDBench validation的已下载副本。它们可能来自不同来源、不同命名或不同任务；本交叉核验没有证明服务器其他未列目录绝对不存在同名文件，也没有读取媒体内容。

## 科学含义

- 公开AIGVDBench的train/validation划分可用于规划可比黑盒评测，但还需要单独取得并冻结实际媒体、标签和许可证据。
- 当前服务器开发池与公开基准之间没有被本包证明有重叠，因此不能将已有开发AUROC移植为AIGVDBench结果，也不能称作公开基准复现。
- 0条交集只回答文件身份交叉问题；它不证明任何样本的祖先、原生PTS/time_base、codec、标签来源或许可。
- AL68仍需核验已有开发样本的原生时间；AL36仍独立判断OR1是否准入。正式数据门继续 `not_evaluated`。

## 输入绑定

服务器manifest的12项路径、大小和SHA记录在 `AL70_CROSSWALK_RECORD_20260922.json`。该记录的SHA256在写入后绑定；本交付只属于数据身份审计，不是算法或效能结果。

## 结论

AL70：**done / pass（严格公开ID—服务器manifest交叉范围）**。下一步若要做公开基准评测，应先生成授权来源的实际媒体manifest，再执行独立的原生时间、标签、祖先和许可核验；不能用文件名交集或论文规模替代这些门槛。
