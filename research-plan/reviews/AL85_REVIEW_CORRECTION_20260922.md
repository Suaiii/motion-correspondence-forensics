# AL85验收更正

静态审查 `run_batch.py` 发现 invalid-suite 调用的是 `mutate(cfg,name)["weights"]`，即包含 all_one/A-double/B-zero/all-zero 的方案字典，而 `core.macro` 需要单一祖先权重字典。因此缺 method/tag/score 与非法权重病例没有到达预定校验层，统一提前返回 `weight_keys`；AL85 21项“通过”不能支持原合同的拒绝覆盖，AL85改为 done/fail。

AL85 valid-cell 的7/24、11/48及独立Fraction结果保留为诊断，不能称完整软件合同。AL88在隔离路径将每个 malformed case 显式绑定 `weights["all_one"]` 后重新验证，旧AL85源/config/input/output未覆盖。
