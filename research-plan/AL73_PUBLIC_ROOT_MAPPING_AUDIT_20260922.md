# AL73：公开候选 root 的来源映射核验

planagent本地审查，承接AL72发现的446个跨train/val候选root。目标是查明作者公开仓库是否提供能解释文件名root、来源、生成器或原始视频关系的映射文件，避免把命名代理误写成视觉祖先。

## 固定范围

1. 固定AIGVDBench作者仓库 `LongMa-2025/AIGVDBench` 的实际main提交；最多4次公开GitHub API/raw请求，总响应上限24MiB。
2. 读取一次递归文件树元数据，筛选路径名包含 `source`、`origin`、`metadata`、`lineage`、`ancestor`、`mapping`、`label`、`model`、`generator`、`split` 或 `README` 的小型文本/JSON/JSONL/CSV文件。只读文件大小不超过4MiB，最多选5个；不读 `test.jsonl`、媒体、图片、权重或预测。
3. 对选中文件记录提交路径、大小、SHA和字段/行结构。若有ID映射，按AL72 446个候选root的精确字符串或文件ID查询；若仅有生成器统计或论文说明，单列为非映射证据。不得把YouTube ID、11字符前缀或caption自动升级为祖先证据。
4. 比较作者映射字段与AL72的固定候选root集合，输出覆盖率、未覆盖数、冲突/一对多关系和缺失字段。所有计数来自脚本，不能手填。

## 交付与边界

交付 `research-plan/reviews/AL73_PUBLIC_ROOT_MAPPING_REVIEW_20260922.md`、`AL73_EVIDENCE_20260922.json` 和可回放脚本。结果仅支持公开元数据解释；有映射不等于已核实原生PTS、视觉祖先或许可，无映射也不等于数据不可用。AL68原生时间核验、AL36 OR1反方审查继续保持独立，不重发失败窗口，不启动GPU或下载媒体。
