# E 盘研究执行约定

代码、原始资产引用、缓存、临时文件、配置、检查点和研究输出均使用 E 盘。现有 Python 位于 `E:\AAGenvid\.conda_envs\d3_cuda\python.exe`，无需重复安装环境或复制原视频。

统一入口：

```powershell
& 'E:\aNB\TECH\脉冲神经网络\research-runtime\enter.ps1' -Script 'E:\aNB\TECH\脉冲神经网络\research-runtime\check_environment.py'
```

入口在子进程范围设置 TEMP/TMP、Python 字节码、Torch、Hugging Face、CUDA、扩展编译、Numba、Matplotlib、pip 和 uv 缓存路径，禁用 user site 和模型联网下载。现有已缓存权重需显式引用 E 盘路径；不通过缺失文件触发在线下载。系统应用和驱动自身的日志不由该入口控制。

2026-09-07 已检查：RTX 4060 Laptop 8 GB，PyTorch 2.5.1+CUDA12.1、numpy2.2.6、OpenCV4.12.0、sklearn1.7.2。环境详情见 environment.json。

目录：`experiments` 放实验协议与脚本；`research-code` 放经过测试的模块；`research-runs` 放版本化运行产物；`research-plan/task-hermes/project.json` 放当前任务依赖。原始数据仍在 `E:\AAGenvid`，保持只读。
