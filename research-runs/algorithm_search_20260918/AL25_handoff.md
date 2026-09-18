# AL25交接：OR1-readout-1共同支持参考完成

cc-al25-filtered-readout-20260919；AL25；researchagent_next。
工作树 `D:/SUAI/codex/worktree/662f/脉冲神经网络`，分支 `codex/al25-filtered-readout`。
冻结提交53cfb0b先于首次候选调用；结果提交见消息。主DAG和旧文件未改，AL26未执行/等待。
工作单SHA256 472e4f302d0ffce04bda5df972550e7781ecffeae18dc7c7cadf0d63e24c1e5a已实读核对。

## 完成范围

新增明确版本OR1-readout-1：float64 THWC，相关形式identity/Laplacian除4/Sobel-x除8/其转置，
共同valid内部且identity同裁；均值包含全部T/H/W/C标量。旧AL12草案未回写。
全部七场与三类非法输入按原工作单冻结后单次执行，无未预期失败。

每个原始字段[2,5,5,3]、150元素；每个滤波输出[2,3,3,3]、共同支持54元素。
完整4q_direct/4raw_compact/12z及原始N/E_a/E_b/D/A/B/带符号C、20个带符号滤波数组均在证据中。
紧凑summary只是提取原值，便于审查，不重算模型。
正C=(1/3,0,1/4,1/4)，负C=(−1/6,0,−1/8,−1/8)；没有取abs。

近抵消identity的精确N=2^-55、精确q=2^-55/(2+10^-12)>0；本机direct约1.3877787807807517e-17，
raw compact=0，raw能量相减也为0。全部精确/浮点差与运算顺序保留，未裁负/改eta。
当前硬件未出现负compact，不要求其它硬件相同，也没有添加场景强迫负值。
浮点差不是来源信息增益；实际AE误差仍unknown，toy参考不授予真实认证。

正常六场按固定1e-12绝对容差通过；消去例单列不以普通容差称数学完全相等。
三个错误（shape不一致、NaN、空间边长<3）滤波前拒绝，0额外滤波。
仅测试最大正常shape，T复制不算独立样本；全部预定v_b=0，非零E_b尚无该套数值覆盖。

## 资源与文件

7成功+3拒绝readout、140个合成字段滤波、168个mean乘积；真实AE/probe/AL15核心调用0。
NumPy/stdlib，Python串行/native cap2实测；最大数组1200字节，RSS未测。
wall .2242508秒、CPU .109375秒，不含启动/最终写出/写作。
无Torch/SciPy/模型/权重/真实图像视频/SSH/服务器/GPU或分类器拟合，无遗留进程。

源码or1_filtered_readout/{readout.py,freeze.py,run.py}；产物AL25_protocol/readout_spec/inputs/freeze/evidence/report/
readout_summary/handoff及artifact manifest，均在algorithm_search_20260918。

| 对象 | SHA256 |
|---|---|
| readout.py | c189fc469f38ca576f91e220f11a9bfe897941a6331950758c6506b20e68a53b |
| readout_spec | 088109738d233171fb7d34f4f7ccf3057abf5a1778e3e8061e0d2e9fc69abd94 |
| 实际输入/精确预期 | 08722458abbe0d7b0745dbcf47341c36f456dab35f9463546047f0fffb59a921 |
| 全部结果 | cc76e97ebb003350461c49827f15c1b53f55662ff75d0b9887bd4fb5b4eca421 |

此前产物/相关源码与本次依赖在运行前后保持摘要。复核使用run.py --output <new-path.json>，不要覆盖本次结果。
建议仅按filtered_tensor_readout_reference独立审查，再决定新边界合同能否接入未来wrapper；
真实17帧/BCTHW、媒体预处理、权重与误差绑定均pending，不因本包通过触发真实或付费阶段。
AL05 fail、预算6000元/初始180 GPU小时、未知实际使用与全部科学/数据/最终集门槛保持。
