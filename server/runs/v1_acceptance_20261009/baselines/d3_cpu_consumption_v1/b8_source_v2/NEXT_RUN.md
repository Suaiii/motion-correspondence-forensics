# 后续真实 D3 CPU 命令

本文件是后续命令说明，本批没有执行以下操作。协调端消息已说明 C9 三资产云端全 SHA 通过、A10结束；本入口仍需取得对应的精确执行/资产/环境/输入锁参数。无新下载或安装命令。

## 1. 当前安全入口

本地仅验证可用 Python：`E:/anaconda/python.exe`。该环境缺 transformers/albumentations/safetensors，不作为推理环境。

```powershell
& 'E:/anaconda/python.exe' -X utf8 -B 'E:/aNB/TECH/脉冲神经网络/research-runs/V1_ACCEPTANCE_20261009/baselines/d3_inference_runner_v1/runner.py' plan
```

## 2. 协调端需要冻结的四份元数据

- typed selection JSONL：完整顺序，`sample_id/source_sha256/role/ancestor_id/ancestry_status=unknown/source_family/generator_family/label_fake/processing_id/pts_field`，以及 A10 的 `approved_public_candidate`、`public_gate_reasons`。first12维持原/current fit；不能因为第一轮推理把fit改名audit。排除成员可保留在固定12分母，worker会在模型前保留数据门失败记录。
- prepared index JSONL：每条 `sample_id/source_sha256/prepared_folder/prepared_frames`；`prepared_frames`是作者目录全部数字JPEG按数值排列的`name/sha256`。复用 D4 已封存 JPEG，不能以最近原生帧计划替代作者 FPS8/JPEG reader。可含外部已锁 `timeline_evidence`。
- scoreless input records JSONL：可用A7 `inherited/input_records.jsonl`，SHA `4c5ee6966d1726d02231f1cccac545252d105cd89d877d086ed56ff61c9fd5d9`。assembler仅取method=d3的同sample记录，不重新解码或运行旧27。
- identity JSON：`cohort_id/seed/split_sha256/protocol_sha256/support_lock_sha256/A10_delivery_sha256/public_gate_overlay_sha256`，均为本次正式锁；identity.example.json中的null是未填参数，不能当冻结真值。

资产锁要求 `version=d3_asset_lock/1.0,status=frozen,repository=microsoft/xclip-base-patch16,revision=d6184e3fd8780d04c85d0f1eabe5f94bf44d98f6`，以及 C9 DELIVERY SHA、config SHA、checkpoint SHA/字节。资产目录采用`config.json`和`model.safetensors`或`pytorch_model.bin`；不联网回退。checkpoint为官方完整多模态也可，文本/投影等未用键单独记录；视觉必需键/shape必须完整。`.bin`仅支持安全weights_only、Torch>=2.6，禁止unsafe fallback。

## 3. 既有环境与 cv2 来源

已读取D4 author_environment_lock：Torch2.8.0+cu128、Torchvision0.23.0+cu128、Transformers4.57.6、NumPy2.3.2、Albumentations2.0.8、`opencv-python-headless=4.12.0.88`。现行依赖与历史作者环境的字节等价未认证；NumPy与作者requirements的2.3.3不同，原差异保留。

后续沿用已有 `/root/miniconda3/bin/python` 和 D4 `dependencies/site`，先收集真实分发/源码锁；descriptor只读取分发元数据、模块/native extension字节，不导入cv2/Torch或模型。它同时核对所选分发RECORD与实际cv2 core文件，不能虚构opencv-python版本或另装重包。

```bash
PYTHON=/root/miniconda3/bin/python
B8=/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/baselines/d3_inference_runner_v1
D4_SITE=/root/autodl-tmp/cvpr27/runs/v1_acceptance_20261009/fingerprint_cpu/author_input_parity_v1/dependencies/site
# NEXT_META为协调端新授权的元数据目录；不是任何旧封存包。
"$PYTHON" -B "$B8/environment_lock.py" --cv2-distribution opencv-python-headless --dependency-path "$D4_SITE" > "$NEXT_META/d3_environment.json"
```

descriptor中的`dependency_versions/cv2_provider`须锁入execution manifest。JSONSchema、SafeTensors、psutil等实际版本由descriptor读取，不编造当前未核版本。

## 4. 生成 execution manifest，先 plan

下列变量为协调端填入的实际已冻结路径/SHA；不读取任何运行中的A10/C9中间表。

```bash
"$PYTHON" -B "$B8/assemble_manifest.py" \
  --selection "$TYPED_SELECTION" --selection-sha256 "$SELECTION_SHA" \
  --prepared-index "$PREPARED_INDEX" --prepared-index-sha256 "$PREPARED_SHA" \
  --input-records "$A7_D3_RECORDS" --input-records-sha256 4c5ee6966d1726d02231f1cccac545252d105cd89d877d086ed56ff61c9fd5d9 \
  --environment "$NEXT_META/d3_environment.json" --environment-sha256 "$ENVIRONMENT_SHA" \
  --identity "$COORDINATED_IDENTITY" --identity-sha256 "$IDENTITY_SHA" \
  --output "$NEXT_META/d3_execution.json"

"$PYTHON" -B "$B8/runner.py" plan \
  --execution-manifest "$NEXT_META/d3_execution.json" --manifest-sha256 "$EXECUTION_SHA" \
  --asset-lock "$C9_ASSET_LOCK" --asset-lock-sha256 "$ASSET_LOCK_SHA" \
  --asset-dir "$XCLIP_LOCAL_ASSET_DIR" --prepared-root "$D4_PREPARED_ROOT" \
  --dependency-path "$D4_SITE" --output "$NEW_D3_OUTPUT"
```

`plan`只读元数据，不读JPEG/config/权重payload，不初始化模型，也不写预测。`metadata_plan_valid_not_model_validated`仅表示参数/版本合同已配齐。

## 5. 后续独立授权的首个 encoder 命令

```bash
"$PYTHON" -B "$B8/runner.py" run \
  --execution-manifest "$NEXT_META/d3_execution.json" --manifest-sha256 "$EXECUTION_SHA" \
  --asset-lock "$C9_ASSET_LOCK" --asset-lock-sha256 "$ASSET_LOCK_SHA" \
  --asset-dir "$XCLIP_LOCAL_ASSET_DIR" --prepared-root "$D4_PREPARED_ROOT" \
  --dependency-path "$D4_SITE" --output "$NEW_D3_OUTPUT" \
  --cpu-affinity 0,1 --checkpoint-every 1 --max-output-mib 32
```

固定CPU、至多2线程、单视频batch、group RSS4GiB、CUDA不可见。其他CPU编号/全量输出预算须后续明确安排；本次没有实测模型内存、吞吐或真实分数。首轮应核对视觉权重加载、真实encoder consumed HW、prepared tensor SHA和score方向，不能从编译/plan外推加载成功。

同命令同输出目录可恢复；成功记录只有完整输入/selection、checkpoint/config、code/preprocess、环境/cv2来源及资源锁相同才复用。失败默认保留，显式`--retry-failed`才重试，旧错误不删。JSONL末尾中断保留原文件SHA归档后恢复，坏中间行拒绝。

`RESULT_LEDGER.jsonl/RUN_SUMMARY.json`覆盖每个预定成员，含失败/pending；`predictions.jsonl`仅含真实成功。指标必须另以同expected support锁处理缺项，不以success文件行数替代完整分母。

first12为fit仅用于该范围真实encoder/score接入，不调用audit evaluator计算成绩。A7 v4 `evaluate`会拒绝fit/calibration/final_confirmation；正式audit的role/cohort、权重和阈值/支持锁须另冻结。祖先unknown不会改成verified，祖先CI仍可能pending。

首入口仅支持已封存作者native-reference JPEG路线；matched处理的实际准备/runtime资格未在本包建立，不以时间候选补作已执行。
