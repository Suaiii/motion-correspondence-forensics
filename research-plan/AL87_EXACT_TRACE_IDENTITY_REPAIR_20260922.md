# AL87：四调用记录的精确身份桥接修复

AL84/AL86已证明近似身份比较不满足合同。此包只在独立fallback-runtime复制必要的四调用算式，加入跨调用exact float64 bytes身份校验；不改写AL84/AL86旧产物。

固定输入复用AL84已冻结trace但以新源码读取。有效case要求Ra_x与Rb_x的输入canonical float64 bytes完全相同，Ra_Pb输入等于由Pb计算出的bytes，Rb_Pa输入等于Pa计算出的bytes；每条记录的自身SHA仍需匹配。固定一个一ULP攻击并同步攻击行SHA，必须被`base_input_exact`拒绝；再保留一个有效case、角色错配和布局错配。

输出d_a/d_b/v_a/v_b/K并调用一次只读AL79 reducer，独立算术参考逐项核对。先静态编译与冻结config/input/source哈希，随后仅运行一次正式批次；不得执行模型、媒体、网络、SSH、服务器、GPU或CI。若修复失败，保留原因并保持AL84/AL86 fail。
