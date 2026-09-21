# AL76：公开文件名 root 风险的语法敏感性核验

AL72使用了固定11字符root规则发现446个跨train/val候选root。AL76只检验该风险对预先规定文件名解析规则的敏感性，避免把单一启发式当成祖先证据。planagent本地执行，独立于AL36/AL68；不读取test、媒体、模型、服务器或GPU。

## 固定输入

重新读取AL71绑定的AIGVDBench main提交 `e38c75abda3d319c0c3072c77594f6eeef1c028f` 的完整train/val JSONL；响应哈希必须与AL71相等，否则停止并记录版本变化。只保存ID和解析摘要，不保存prompt正文。

预注册四种互不替代的字符串规则：

- G1：AL72规则，root恰为11个允许字符，后接`_scene_starttoend.mp4`，且end>start。
- G2：从右侧解析，stem最后一段为`starttoend`、倒数第二段为全数字scene，root为此前全部字符（允许root内部下划线）。
- G3：G2的root再要求长度恰为11，作为G1的独立重写核对。
- G4：root为首个下划线前的token，仅作宽松上界敏感性，不作祖先解释。

每个规则计算train/val可解析行、候选root数、跨划分root交集、涉及样本数、未解析示例。按排序集合与字典分组两条路径核对计数。不得因为结果修改规则或删除重叠样本。

## 交付

`reviews/AL76_FILENAME_ROOT_SENSITIVITY_REVIEW_20260922.md`、`AL76_EVIDENCE_20260922.json`和脚本。结论只能说命名代理风险在规则间是否稳定；任何root交集仍不能推出视觉祖先泄漏。若G1/G3一致，确认AL72机械实现；若G2也有明显交集，风险对root内下划线解析较稳健；若差异大，报告规则依赖并降低措辞。

AL76不放行数据、算法或训练。完成后保留AL36/AL68作为两项独立后续，不能重复派发研究窗口。
