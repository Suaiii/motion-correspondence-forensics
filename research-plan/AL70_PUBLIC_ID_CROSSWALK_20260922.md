# AL70：公开Video_id与现有服务器文件交叉核验

负责人：planagent；开始：2026-09-22T01:41:35+08:00。这是AL69之后的独立最小新增信息任务，不运行模型、不下载媒体帧、不训练，不重做AL68的原生时间核验。

## 问题

AIGVDBench公开train/val清单已经确认只有`Video_id`和`Video_Prompts`字段。当前服务器拥有candidate200、combined_candidate130、mech4fps、pair2等历史开发清单，但其来源和命名可能不同。本包只回答公开ID是否能与当前服务器的已有文件/manifest通过严格basename或记录字段相交，避免把“有公开清单”误写成“服务器已有同一数据”。

## 范围和固定输入

- 公开入口固定为AL69记录的`https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/main/data_splits/val.jsonl`；重新读取一次仅为得到确定ID集合，记录响应SHA，最多读取8MiB，不读test。
- 解析前20个按文件顺序的有效`Video_id`和前20个`Video_Prompts`哈希，冻结为输入。不得按结果筛选。
- 服务器只读检查`/root/autodl-tmp/cvpr27/data`下已有manifest的路径/sample_id/archive_member/file basename字段；最多读取已列出的AL67/AL68 manifest文本，禁止扫描媒体内容、下载或改文件。匹配规则只用规范化basename和精确ID，大小写/扩展名规则预先写明；模糊语义不算匹配。

## 交付与失败

交付`research-plan/reviews/AL70_PUBLIC_ID_CROSSWALK_REVIEW_20260922.md`和`AL70_CROSSWALK_RECORD_20260922.json`，含公开输入、服务器manifest SHA、逐ID匹配结果/未匹配原因、命令与时间。若交叉为空，这是有信息的结果：公开评测数据与当前开发池分离，不能直接复用。若有匹配，也仅证明文件名/记录交集，不证明标签、祖先、许可、PTS或生成器身份。

本任务完成不能放行正式数据或OR1；AL68原生时间核验和AL36反方审查继续独立。不得创建新会话或派发重复的公开文献审查。
