# AL73：公开候选 root 的来源映射核验

- 实际完成：2026-09-22T03:22:36+08:00
- 执行者：planagent；范围限于作者公开 GitHub 仓库的树、README 和小型 val 元数据；未读取 test、媒体、图片、权重、预测或服务器。
- 证据：`AL73_EVIDENCE_20260922.json`，修复记录后 SHA256 `b8201a92cf6b689cfa8fad20cd92eb21d645811cb384361dda530f3e3ab5fc77`；记录保留初版哈希和修复原因。

## 发布树与请求

固定 main 提交为 `e38c75abda3d319c0c3072c77594f6eeef1c028f`，树未截断，共7个条目。受限筛选后只有 `README.md` 与 `data_splits/val.jsonl` 在4MiB文件上限内；`train.jsonl`超过本包单文件上限，AL71已经完整审计它的ID层。四次请求的URL、状态、字节和SHA全部保存在证据记录中。

README包含模型规模、来源/发布说明和split叙述，但没有样本级 `ancestor_id`、origin映射或摄像来源表。val清单解析为3000条、字段仅 `Video_id` 与 `Video_Prompts`；没有 label、source、generator、ancestor、license、PTS/time_base 或 decoder 字段。公开树中没有独立的source/lineage/mapping/ancestor元数据文件可供本包核验。

## 对 AL72 风险的回答

公开仓库没有提供能够把446个候选 root映射到真实来源或视觉祖先的机器可核对表。README中的aggregate模型/来源信息不构成样本级映射；文件名中的root也不能直接解释为YouTube、摄像来源或父视频。AL72发现的446个跨train/val候选root因此仍是**未解决的命名代理风险**：它足以要求作者映射或实际媒体审计，不能单凭它宣称数据泄漏。

公开 train/val 文件仍可支持作者划分层面的黑盒基准复现规划，需披露：ID互斥已核验、候选root风险未核验、媒体/许可/标签字段不在清单中。机制归因和最终确认需要额外来源/祖先、原生时间、标签、许可和处理链证据。

## 结论

AL73：**done / pass（公开来源映射审查范围）**。

- 通过：仓库版本和请求可复算；没有发现公开的样本级来源映射文件；val schema边界明确。
- 未解决：446个候选root跨划分风险；真实视觉祖先、生成器、标签和许可未知。
- 不推出：作者划分错误、视觉泄漏已发生、检测性能无效或正式数据门通过。

AL68原生PTS核验和AL36 OR1反方准入审查仍保持独立；研究窗口提供方故障没有被本包绕过。
