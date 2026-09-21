# AL71：AIGVDBench公开train/val清单划分完整性审计

负责人：planagent；实际开始：2026-09-22T01:46:51+08:00。AL69仅读取了train前缀与完整val，AL70证明公开val前20个ID不在当前服务器开发manifest中。本包补充一个独立最小信息：完整读取公开train/val元数据，核对解析错误、重复ID和跨划分交集。没有test内容、媒体、模型、标签推断或GPU。

## 输入与范围

固定URL：`https://raw.githubusercontent.com/LongMa-2025/AIGVDBench/main/data_splits/train.jsonl` 与 `.../val.jsonl`。最多读取各12MiB，记录响应SHA、字节、HTTP状态与实际读取范围；不访问test.jsonl、HF媒体、权重或任何预测。每行只解析JSON对象，记录空行、错误行、缺少Video_id/Video_Prompts、重复Video_id、扩展名异常；不保存prompt正文，只保存字段存在和prompt哈希统计。

集合运算：精确字符串ID集合交集、各自重复计数、大小、按ID排序的首尾摘要哈希。ID交集为空只证明发布清单层面没有重复文件名，不证明视觉祖先独立；重复或解析错误保留为release-quality风险。

## 交付与失败

交付`research-plan/reviews/AL71_SPLIT_INTEGRITY_REVIEW_20260922.md`与`AL71_SPLIT_INTEGRITY_RECORD_20260922.json`，绑定输入/源码/输出哈希。若train存在错误行或重复，公开划分只能标为metadata-partial，不静默修复；若划分完整，结论也仅限文件ID层面。AL68原生时间核验、AL36 OR1反方审查和正式数据gate继续独立。
