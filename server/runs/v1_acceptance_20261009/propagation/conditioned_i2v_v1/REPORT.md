# B3：条件图像关联与长原生时间 I2V 开发证据包

dispatch_id：v1-monitor-20261009-B3-conditioned-i2v。实际窗口：01a11c81-06c6-7941-94b7-51efc512b199。完成：2026-10-09T03:14:27.903611+08:00。

## 1. 实测交付与使用边界

**49个官方原图键/源URL祖先组，49份原图与49份16:9 crop均取得并完整解码；主包为Hunyuan49+Wan2.2 49=98个原生视频。** 六族各2个固定probe全部完整下载/QC；其中4个已包含在主包，另8个保留。因此唯一输出文件总数106，不能把12+98写成110。106/106读取复查通过，主包98/98满足C2四个已知方法的互异原帧时间候选合同。

仅仅完成publisher-key关联、原始二进制、时间数据与软件校验。实际generation request、实际crop/input选择、seed/checkpoint仍unknown，actual_condition_sha256全部null。没有独立科学审签、模型/训练/encoder/GPU或最终角色分配；机制gate未通过。原图不是real视频，本fake-only包没有AUROC。独立复核pending A。

## 2. 原始来源与锁

来源为[VBench作者公开数据](https://huggingface.co/datasets/Vchitect/VBench-I2V_sampled_video)，固定revision `d1977eff951fad22ac7ac11059f6939f570a78eb`，现场官方API private=false/gated=false/disabled=false。Arena源码固定 `e814acd7c78fa83206d01fe8e3641f70ed0c3f30`，仅仅静态审读其公开下载成员路径，未执行Space、token读取或投票/feedback函数。GitHub合同固定 `fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490`。

[作者I2V说明](https://github.com/Vchitect/VBench/blob/fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490/vbench2_beta_i2v/README.md)列出原图/crop/源URL/bbox/caption及`prompt-index.mp4`规则。实际匿名取得Google Drive官方i2v-bench-info：355个图像元数据；1118条官方prompt–image_name配置形成5590个sample0–4名称。顶层15个配置目录不等于15个独立生成器族。本包只调查冻结六族，Wan2.2的多个配置没有重复计族。

原图目录和16:9 crop目录当前匿名页面各显示50项，精确metadata/full-info/输出键交集为49。页面与JSON/hash均保留；没有假称全355图像目录已完整列出，也没有下载整个数百GB仓库或origin/crop ZIP。

代码LICENSE为Apache2.0，与数据/上游照片条款分开。该视频仓库没有提供可核对的数据license/card；每个照片的官方原URL已记录，逐项权利仍待审查，不从代码许可推导数据授权或声称素材权利通过。

## 3. 冻结probe、时间判定与选择

先按seed61的SHA排序选两个共同原图键；固定base caption、无camera后缀、sample-index0。六个族各取这两项，共12probe；每次用官方固定size/LFS SHA，不看检测结果。C2合同与原生Fraction采样源码直接锁哈希复用，没有修改C2或降低误差/独帧门。

| 家族/配置 | 取得视频数 | native FPS | 实际帧数 | PTS首末跨度秒 | 四个已知matched时间候选数 |
|---|---:|---|---|---|---:|
| HunyuanVideo-I2V | 49 | 24/1 | 129 | 16/3 | 49 |
| Wan2.2-I2V-A14B (w:o prompt-optimized) | 49 | 16/1 | 81 | 5 | 49 |
| LTX-2-I2V (wo prompt aug) | 2 | 24/1 | 121 | 5 | 2 |
| CogVideoX-5b-I2V | 2 | 8/1 | 49 | 6 | 0 |
| gen-4 | 2 | 24/1 | 242 | 241/24 | 2 |
| i2vgen-xl | 2 | 8/1 | 14 | 13/8 | 0 |

Hunyuan129帧24FPS，跨度16/3秒；Wan81帧16FPS，跨度5秒。24FPS/96帧是C2给出的充分配置示例，Wan没有被填成96帧：其16FPS原生stride2达到8Hz，2秒窗口可取24个互异帧，8帧2Hz共同窗也有真实支持，因此逐方法候选合同通过。完整author sampler/processor/encoder parity未运行，STREAM合同仍unknown。

CogVideoX虽然6秒，但8FPS的2秒窗口不足ReStraV默认24个互异帧；I2VGen-XL14帧/8FPS、13/8秒跨度不足共同长时间合同。它们的两个probe均保留，没有替换到通过。LTX-2/gen-4的probe也通过已知时间合同，但按事前固定family优先级只选Hunyuan与Wan。不是根据画质或真假可分性排序。

扩量在probe实测后另冻结：49个可核对原图组跨两族，每组每族仅sample0一个。每族比上限64少15，保留不足；没有拼外部/holdout或重新选条件补足。没有转码、补帧、裁剪视频或借容器FPS制造时长。

## 4. 条件关联到底证明了什么

每个视频精确join官方prompt_en→image_name→官方源URL与原图文件ID，取得原图SHA；同名16:9 crop文件也取得SHA并与官方bbox尺寸核对。原图/crop均全量解码；49个原图原始SHA及decoded-RGB SHA均各49种，没有此包内相同原图字节/像素重复。49个祖先在两族间共用相同group ID。

16:9 crop是取得的**发布者候选条件素材**。原图、crop、输出命名与文档关联不能独自认证该模型实际请求使用哪一个crop/resize，也不能把生成首帧当输入。actual_condition_sha256、实际prompt hash、generation-request、checkpoint和seed继续null/unknown。sample-index0不等于seed0。crop bbox与原图源URL保留，所有camera变体和同图ratio/配置需按原图祖先合并，不能另算独立祖先。

在已有v1/扩展和B2视频SHA目录中没有新输出的逐字节命中；B2没有已取得的实际condition image hash，因此旧condition交集是unknown，不是已证零。stock照片URL与已有YouTube候选源ID属于不同键，不能用无精确字符串命中宣告祖先独立。真实视觉近重复、预训练曝光与上游权利仍待A。后续whole-generator holdout还需同时防止共享原图祖先跨fit/audit泄漏。

## 5. 真实传输、QC与失败保留

远端官方HF/Google域名连接失败Errno99、IPv4 Google探针超时与Git raw条件JSON路径404已保留；本地匿名官方HTTPS可达。采用HTTPS→有界RAM→现有SSH流式传输，**本地媒体落盘0**。协调端原1024-byte前缀测试只证明传输；本包每个视频都用完整full模式核对官方size/LFS SHA、两端SHA和SSH exit0，106个视频均通过。

每次写入前限制单视频64MiB、原图32MiB、crop8MiB、namespace总3GiB和全盘剩余20GiB；不覆盖同名、不自动重试失败。条件图片通过两端stream SHA、图片完整解码、原图/crop尺寸校验。网络/解析实现失败回执与已取得素材保留，不换账户或模型。若条件二进制缺失或尺寸不符，依赖视频会blocked_condition，而非继续盲下或替补。本次没有发生素材/QC失败。

ffprobe保留真实整数pts/pkt_pts、rational time_base、全序列和字段来源；ffmpeg -xerror/err_detect explode完整解码。C2同时输出native/reference与matched互异帧计划，包括重复数、采集误差和排除原因。没有用best_effort或名义FPS合成原帧，没有fake-only检测指标。

## 6. 资源与回执

事前最坏预留2,267,107,615字节，小于3GiB；最终receipt时全部依赖/元数据/图像/视频/QC产物约0.3173GiB（340,674,161字节），盘空闲30.259GiB。本地当前仅紧凑metadata/代码/清单约32.39MiB，低于100MiB；媒体和图像均服务器保存。

CPU affinity0,1、原生工具各1线程、单作业、RAM4GiB；GPU作业0。唯一视频传输收据墙钟累计275.875秒，图像传输累计328.593秒，完整图像/收口阶段33.021秒；逐视频native probe/decode另有实际命令回执。计费与历史GPU小时仍null。

## 7. 交付与独立接续

COMPLETION.json为本包入口；sources.lock、probe/selection锁、106行manifest、98图像校验、input_output_associations JSON/CSV、time_qualification.csv、ancestry_exposure、unknown_fields、原HTTP/SSH与native QC回执均齐备。原B/B2、A/C/D、WORK_PLAN/DAG/DEVLOG未改。

不同执行者可只读运行：

```bash
/root/miniconda3/bin/python /root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/propagation/conditioned_i2v_v1/review_b3.py
```

本实现者该读取器实测106/106，仅仅构建者机械验证。A需独立审查官方图像键/输出join、crop歧义、LFS/图像字节、原生PTS、C2独帧采样、资源边界与祖先暴露。真实对照视频、许可证、实际请求/seed/checkpoint与processor/encoder依赖仍不具备；没有自动释放GPU或科研门。
