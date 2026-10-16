# C9 首批强baseline资产入云

dispatch_id：v1-monitor-20261009-C9-first-baseline-weights。固定三个既有文件，没有重下权重或新增本地模型副本；仅本地/云端inference_assets_ready_v1新增代码、紧凑证据和这批文件。3/3本地完整SHA/大小、3/3云端传输后完整SHA/大小、3/3封存前云端完整重核均匹配，总868081656B。

## 固定资产

| 文件 | 字节 | SHA256 | 来源与当前准备范围 |
|---|---:|---|---|
| XCLIP-16 model.safetensors | 779789644 | b5db836d57b7e22001cb2bab581719e910b4c571d926fe839b5d07bc0ba2d03e | 既有本地HF snapshot d6184e3fd8780d04c85d0f1eabe5f94bf44d98f6；C8官方LFS散列匹配；本次两端完整读SHA |
| XCLIP config.json | 8897 | 43d49d757dc8a3ef3dfd242d7ebe0c2effcfa0404f9343864e50c45245f99d3a | 同一固定HF目录和配置；解析后与真实header静态对应 |
| DINOv2 ViT-S/14 pth | 88283115 | b938bf1bc15cd2ec0feacfe3a1bb553fe8ea9ca46a7e1d8d00217f29aef60cd9 | 原本地封存SHA，本次完整重核；官方SHA未知，保持来源区别，不替换ViT-B |

云端文件分别为本包assets/xclip16/model.safetensors、assets/xclip16/config.json、assets/dinov2/dinov2_vits14_pretrain.pth；完整绝对路径与NEXT_RUN/ASSET_LOCK/CLOUD_TRANSFER_RESULT绑定。原本地文件路径、mtime_ns、大小与读取1MiB块的实际回执在LOCAL_HASH_RECEIPT，无额外大本地复制。C8原计划仍只读。

## 首连接失败与同资产恢复

首XCLIP连接receiver103345/start_ticks4577648269、localSSH31136实际退出2，错误AssertionError:20GiB_plus_C9_A10_growth_floor；不是观察超时。首版只统计st_size，失败瞬间完整free/allocated快照未保存，瞬间预分配原因不能宣告已证实。原cloud_control.v1.py、stderr/stdout、FIRST_TRANSFER_FAILURE_RECEIPT及云端failure metadata均保留。

初始part554696704B，云端prefix9fb00814d1f4a46727832e82d671c64183f95533b651273b14d6b8f340ee6b67与同长度本地36362cfe…不同，恢复入口明确拒绝；v2没有启动receiver。完整本地文件重核仍是官方b5db…，没有源文件变化。按1MiB分段只读摘要，前513块完整匹配，最后16块异常；并非仅靠根窗口六点抽样宣称prefix完整。

已在云端failure_evidence保存原异常16MiB尾部，offset537919488、SHA87d70587065b9bfc37796923b923c6cafa17478e596f27111f9e1df01442ef00。核尾部副本后才将part缩到严格正确的537919488B；local/cloud prefix均为1e2a0c0d54a3f000371d5daa2fb8af812ea56a6b2bbd1c29518e0e49ce327b4f。旧PID确认消失，手动新receiver104074只从该偏移传剩余241870156B，不从头重传、不并发旧receiver。原异常partial可由该prefix+归档tail逐字节还原，最终复合SHA回到原9fb0…，未生成第二份combined大文件。异常tail的具体成因仍unknown，不把它归因于某个已证明的文件系统或SSH事件。

v3按协调addendum同时记录logical、allocated=st_blocks×512、charged=每文件max(size,allocated)，每字段使用同一次stat，remaining=cap-charged；完整资源快照在guard之前保存。原20GiB/C9 1.25GiB/A10 128MiB/RSS4GiB均未放宽，A10未重启。v2预分配方案仅为本地源码提议、未执行传输；实际v3没有预分配改变，只修统计。生产端改为单一父进程读取源并向SSH binary pipe送字节，避免跨进程共享源cursor；此为I/O边界约束，不能宣称已证明原异常由cursor造成。源码版本、diff、prefix拒绝、归档和新句柄都可追溯。

续传XCLIP实际59.0244s、config0.7936s（receiver104122）、DINO15.4463s（receiver104146），三者最终完整SHA匹配后原子part改名。无自动无界重试、没有换模型/账户/服务器或删除其他文件。

## 静态格式与接口事实

XCLIP safetensors读取8字节长度和70832B JSON header，共593tensor记录，其中344个vision_model.*，dtype F32/I64。全部offset连续、shape×dtype字节与区间一致、末端恰好覆盖payload。真实patch embedding与配置768 hidden/3channels/patch16、position197×768对应，vision层0..11、num_frames8匹配。它仅仅是容器/配置/视觉前缀的静态核查，未证明XCLIPVisionModel可加载、警告键是否完整处置或pooler_output实际forward。

DINO文件是Torch ZIP容器，177目录成员；仅目录名称/尺寸/CRC/compression metadata，未读取pickle body、torch.load或构造模型。因此键、shape、dtype与ViT-S class的严格对应仍unknown。本次能确认完整字节与封存源一致，不能把它写成已经执行的ReStraV encoder。

实际static PID/CPU4,5与峰值RSS17367040B在STATIC_CHECK_RECEIPT。三receiver实测self峰值分别19255296/16965632/19197952B，资源快照还记录各自private group成员/RSS；未超过4GiB。collect时C9 logical885342031B、charged885424128B、remaining456753152B，20GiB加双方剩余增长后margin368013312B；包含归档坏尾部及紧凑tar，不是复制整模型tar。最终占用以CLOUD_DELIVERY及FINAL_CLOUD_MANIFEST为准。

## 下一步与当前边界

B8在独立d3_inference_runner_v1承担逐样本离线runner，C9只交资产路径/固定revision/静态元数据，没有另写runner。A10/C9/B8都封存后由协调端锁真实CPU encoder消费和随后benchmark输入。B7提供的保守公开描述性候选8870引用/8803 SHA、A10可查询清单进度是当前派发状态；本包没有读检测分数或选测试样本，也没有重新验收祖先/机制数据。D11三输入独立数值pass与A9六例修补核验按新工作单继承，未重复。

NEXT_RUN给出已实际运行的v3只读资产probe命令、确切云端模型目录、D3 XCLIP-16/l2/fake=-std接口、ReStraV完整token/新fit-only头、依赖和RAM/缓存要求。timm/pandas/sklearn等环境缺口仍按C8保留；模型实际加载、encoder/head、逐样本完整评测、峰值/时长均pending。后续直接引用本包文件，避免复制868MB cache；历史ReStraV head不升级为新正式头。

时间过度连贯/Native448、720/压缩域/STREAM继续保留C8完整计划；Native完整state能否省底座与Tensor/pooler API问题尚未启动验证。没有pickle反序列化、模型初始化、媒体解码、预测、GPU或安装环境。原42D NO-GO、AL144/AL146冻结及v1科学门不变。累计花费/余额unknown，本次传输/CPU时数不能写成免费。完成封存即停止。
