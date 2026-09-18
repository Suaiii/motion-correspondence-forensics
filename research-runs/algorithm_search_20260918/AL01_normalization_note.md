# AL01 同目标数值恢复：保留初始失败

初始冻结提交5689d3e，第一次结果提交81e7087。
AL01_evidence.json保留failure_preserved状态及全部成功/失败行：三个m4/4/8特征例的普通Sinkhorn达到20,000步仍未收敛。
摘要碰撞、经典公式对照、默认正温度回归、malformed拒绝和数值边界均已运行；失败中断了相应归一化和后续大/小幅度输入检查。
本次不修改这些文件，不改变tau=.1、输入数组、同Q比较、科学判据或归一化残差1e-12。

正核矩阵的双边缩放是均匀行列约束下min sum_ij Q_ij(log(Q_ij/K_ij)-1)的唯一正解。
固定列对偶beta，精确消去行约束后Q_ij=softmax_j(logK_ij+beta_j)/m。
凸对偶F(beta)=mean_i logsumexp_j(logK_ij+beta_j)-mean_j beta_j；
梯度为列质量-1/m，Hessian=[diag(sum_i P_i)-P^T P]/m。
固定最后一个beta=0解除常数自由度，用Newton与固定回溯规则求同一驻点。
固定最多100步、每步最多40次回溯；Armijo系数1e-4，目标舍入停滞时允许残差降低至.9倍的步。
不修改K或熵目标，不添加正则，不对温度或输入调参。

每对保存完整raw/balanced Q、逐步列残差、log行列缩放、单点质量误差及
log(Q/K)=logu+beta的驻点证书。满足原行列质量和乘性缩放形式即是同一严格凸KL投影的数值证据。
原本已收敛的m2实例用于同解对照；其余三个仅补上首次被阻断的归一化结果和幅度数值检查。
初始约束LP、helper和所有预冻结源码只读。最终推荐使用joint_v2的H-J接口与balance_newton的归一化诊断接口；
joint_v2.normalization_pair保留为已知有收敛覆盖限制的初始数值算法，不能声称它已被暗中修复。

```powershell
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/al01_v2/recover_normalization.py prepare
# 先提交新求解器与冻结记录，再执行：
& E:/AAGenvid/.conda_envs/d3_cuda/python.exe research-runtime/algorithm_candidates/al01_v2/recover_normalization.py run
```

源与依赖摘要均冻结于AL01_normalization_freeze.json。新结果写AL01_normalization_recovery.json，
不覆盖AL01_evidence.json，不把数值恢复称为科学改进。仍然只用本地CPU两线程，独立科学复核pending。
