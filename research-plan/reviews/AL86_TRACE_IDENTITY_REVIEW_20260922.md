# AL86：四调用记录身份的反方审查

本审查不修改或重跑 AL84 批次。源文件与原始证据的字节哈希见 `evidence.json`。

## 发现

AL84 的 `bridge.py` 用 `_same(a,b)` 比较 base 与 soft-input 张量：`np.allclose(..., rtol=1e-12, atol=1e-12)`。因此记录若将 `Rb_x.input` 改为与 `Ra_x.input` 仅差一个 float64 ULP，并同步更新该行自己的 input_sha256，身份检查仍可接受；同样的容差还适用于 `Pb` 和 `Pa` 的外层输入。

这违反 AL84 工作单中“输入身份/样本对应”的严格绑定意图。它仅是静态控制流推导；本包没有执行该攻击、没有产生新的数值批次，也没有访问模型、媒体、服务器或 GPU。`reference.py` 的算术独立性不能修复身份校验漏洞。

## 结论

AL84 原 `software_pass=true` 只保留为历史运行输出，任务验收撤回为 `done/fail`（`trace_identity_contract_incomplete`）。原四调用代数和八个大类拒绝结果仍可作有限预计算诊断，不能作为严格身份桥接通过。后续修复应在冻结配置中加入跨调用 exact byte identity（或预注册的明确量化规范），另设攻击和正常输入一次性重跑；不能覆盖 run_v1，也不能把真实 probe/效能门打开。
