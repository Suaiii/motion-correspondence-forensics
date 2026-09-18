# 科研任务启动故障与CPU研究接管

任务：科研冲击；失败回合：01a0b51f-acc3-7331-a21d-e5bcce16e8f2。
wait_threads与read_thread均返回failed/systemError，items为空；错误为HTTP400
unsupported_parameter，参数access_programs.cyber，提示该组织未启用access_programs。
这属于任务启动接口故障，不能记录成算法失败或已执行工作包。

本机config.toml及全局状态键的针对性检查未找到该参数的可修改设置。
未更换账户/组织、申请未获授权程序或反复提交相同启动请求。相关授权由产品/组织配置决定，
参见[官方说明](https://developers.openai.com/zh-Hans/docs/cyber-safety)；具体错误的修复路径尚未确定。

为落实持续研究，planagent在独立fallback-runtime路径推进已批准的CPU数学/原型任务，
保留原研究端代码与数据。最先完成的结构检查见AL03_PRIOR_SCREEN_20260918.md。
研究任务恢复后先核对任务表当前执行者，读取接管成果并交叉复核，不能重放旧派发。

该故障未影响49714服务器的SSH和公钥登录；它也不改变预算、数据与GPU训练门槛。

后续恢复：通过现有send_message_to_thread工具，将该任务明确设为本主机可用的普通
gpt-6-astra，执行仅读取计划/角色的启动校验。回合01a0b533-d603-7ff1-b483-642a1133fa27
成功完成，科研端实际返回v1.4与读取哈希，未进行实验。该操作没有改变账户/组织身份、
申请或使用Cyber访问程序，也没有改动安全权限。恢复只证明普通研究任务可正常运行；
不得据此声称原Cyber授权已开通。之后按新工作包分工，不能重放旧失败派发。
