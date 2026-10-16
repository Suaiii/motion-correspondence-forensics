# A7 输入合同修复与软件恢复交付

## 版本与继承范围

本包由A实现，接续原C窗口HTTP400/context_length_exceeded后缺失的最终软件版本。原C失败回合仍failed；已完成媒体实验不因应用失败作废。原12个fit视频、原RNG、27条scoreless输入记录全部字节保留，SHA4c5ee696...；D3×12、ReStraV×12、Native448p×3。D7已在snapshot019用不同执行者真实重放27条、与D4/C5索引与tensor精确一致；此处仅仅继承该版本范围。A7没有重跑媒体或77720行。

## 两项P2的复现与修复

三份固定最小JSON分别是：改time_base为1/1而保留display秒数、改loader返回24为1、把base与selected PTS全改0而保留非零display starts。旧snapshot019实际调用均退出0接受；新v4均退出2，拒绝指向原生时间/start矛盾或loader返回边界矛盾，不按sample_id特判。

F1在新record_contract中以Fraction连接native_time_base、逐阶段slot map与整数PTS、display start、target与正duration、最终selected PTS。display start与native PTS×time_base直接一致可验证；不从记录猜原点偏移。不同原点需外部hash绑定证据，连接输入/trace身份、完整native数组、显式offset及观测时间，缺证据为unverified。既有1/1000000秒display误差保留。不同native index允许一致PTS的数值合同；D7全零反例拒绝仅因其原非零display秒数矛盾。软件一致不认证源真实性，完整source/native-duration物理证明不由自报record建立。

F2按实际方法返回边界检查，D3/ReStraV loader等于decoder/reader实际返回tensor槽；ReStraV24包括尾部repeat_last，15只是valid display前缀。Native loader边界在processor首个temporal tail之前，允许3物理槽→4逻辑槽，并绑定current config factor2、实际grid/patch rows/shape及补槽数。不能统一等于第一stage输出或最终逻辑槽。未知processor/方法边界保留未核实。原重复策略reference_policy.py未改，合法FPS内部重复、末端补槽及显式时间控制继续支持。

## 实际验证与软件入口

本地和云端完整48项有限检查全部通过：27条原记录、D7三反例、额外时间/槽数冲突、有证据原点转换与缺证据拒绝、coherent重复PTS、FPS及显式控制、D5原回跳库/CLI拒绝、合法尾重复/FPS/staged/control库与CLI一致。另3项固定Native边界验证使用独立数值槽3→FPS4→loader尾补5→processor6：loader5通过，第一stage4与最终6均拒绝。它仅仅是数值合同测试，未运行decoder。

云端新adapter wrapper仅初始化成功，原adapter/class/function体字节/AST不变，components与tensor_capture空、prepare调用0、CUDA未初始化；峰值父RSS约634MiB，低于4GiB。真正27条张量/PST/原索引精确证据来自旧C5/D7，不能把初始化当新媒体回放。可调用入口及API见README，源码与改动diff在本目录；evaluator_v4仅input_record.py修改及新增record_contract.py，其余算术/support/evaluation/admission/reference policy/schema字节相同。

## 适用性与未验项

当前D3是实际FFmpeg FPS→JPEG→BGR作者reader，原C2最近PTS轨为独立适配协议，不能混称等价。ReStraV采用显示区间，Native分loader与processor；逻辑补槽新增原生帧数0。OC继承D4的5入口/7排除，未重跑。Native720p、STREAM完整输入、历史作者依赖/config精确复现、encoder/head实际消费HW与权重均pending或unknown。完整数据、祖先/相机/生成器机制、分类效果与GPU均未放行，旧42D NO-GO保持。

## 失败、资源与独立复核

首个测试脚本的staged夹具把PTS误填索引，原validator正确拒绝，修复测试时间单位后保留旧源码/输入。云端D5顶层聚合夹具和D7最小文件未同步到相应旧位置，先前45检查缺三反例不作完整验收；复制冻结小JSON到A7并强制三份夹具计数后完整48通过。首个wrapper初始化用4GiB虚拟地址上限导致已有Torch共享库不能映射；仅将新wrapper保护改成0.05秒物理组RSS/namespace监视，原源/环境不变，新的初始化通过。原失败说明、原C失败回执与版本均保留。

云端固定CPU2/3，RAM物理4GiB、新增128MiB，本地100MiB；无新媒体/环境/模型下载或GPU/encoder/head调用。现场预留20GiB底线、B5剩余4GiB上限、D8剩余256MiB及本包剩余128MiB；旧C5/A6/D7已停止的占用保留，未再增长预留。主WORK_PLAN/DAG/DEVLOG与A6/C5/D7/snapshot019全部只读。

本包完成可审软件实现与有限自测；受影响v4补丁及新path wrapper的不同执行者复核仍pending。D7的旧版本PARTIAL和两项P2历史结论保留；不能自签独立修复通过或将软件一致性当科学接受。封存后由协调端安排复核，不自行派发/新建窗口/启动新批次。
