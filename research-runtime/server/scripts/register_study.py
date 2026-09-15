"""Install the accepted DAG while retaining the previous project snapshot."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.common import read,write,sha


def main(project):
    project=Path(project);prior=read(project)
    backup=project.with_name('project_before_cvpr27_20260910.json')
    write(backup,prior)
    def task(identifier,milestone,title,parents,status,hypothesis,work,acceptance,artifacts,owner='research-engineer'):
        return {'id':identifier,'milestone':milestone,'title':title,'assignee':owner,'parents':parents,'status':status,
            'hypothesis':hypothesis,'work':work,'acceptance':acceptance,'artifacts':artifacts,
            'budget_policy':'CNY3000 and 180 paid GPU-hours; stage reservations required; no provider lifecycle verified'}
    tasks=[
        task('S00','M0','服务器可迁移执行底座',[],'done','相同配置可在新执行入口中复现数据处理、训练与中断恢复。',
             ['可迁移入口和数据根路径','清单、预算、缓存、训练与最终访问约束','合成端到端与位级续训测试'],
             ['软件测试通过','历史研究结果不被改写','不冒充远程硬件验收'],
             ['../../research-runtime/server/README.md','../../research-runs/server_runtime_validation_v3/validation.json']),
        task('S01','M0','服务器接入、计费和持久盘核验',[],'blocked','目标服务器可在已批准预算内稳定保存数据并执行训练。',
             ['确认SSH主机与数据盘挂载点','核对GPU/CPU/RAM与驱动','记录价格、磁盘保留及停止计费动作'],
             ['真实连接与硬件证据','报价和停机规则明确','不得将停止Python等同停止计费'],
             ['../artifacts/cvpr27/server_doctor.json','../artifacts/cvpr27/provider_quote.json']),
        task('D00','M0','公共数据版本与清单审计',[],'done','版本化公开清单可揭示影响独立划分的来源候选重叠。',
             ['固定两个HF仓库commit','验证5份清单对象哈希','统计源前缀/提示跨split候选','实测远程ZIP索引'],
             ['发布版本和输入哈希齐全','候选重叠不冒充内容去重','未声称已获得视频'],
             ['../artifacts/cvpr27/dataset_catalog_20260910.json','../artifacts/cvpr27/release_metadata_audit.json','../artifacts/cvpr27/cogvideox15_zip_index.json']),
        task('D01','M0','服务器视频子集与祖先映射验收',['D00','S01'],'todo','两个真实来源和四个生成器可组成可核查的独立开发池。',
             ['分批下载选定成员','核对T2V、许可和来源/参考/提示映射','去重并排除历史595条','冻结6000条机制集'],
             ['未知祖先单列不伪造verified','原视频及派生视图不跨角色','真假及各来源QC计数齐备'],
             ['../artifacts/cvpr27/mechanism_manifest.jsonl','../artifacts/cvpr27/ancestry_audit.json']),
        task('S02','M0','100条服务器端全链路profile',['S00','S01','D01'],'todo','单卡和分片缓存可在阶段预算内支持正式机制实验。',
             ['预留profile预算','测量解码/光流/控制/推理','补测训练吞吐与实际账单','冻结任务时间与缓存上限'],
             ['实际100条完成或全部失败原因记录','显存、时间、缓存增长与费用可追溯','无超预算后台资源'],
             ['../artifacts/cvpr27/server_profile.json','../artifacts/cvpr27/provider_profile_receipt.json']),
        task('M01','M2','新数据内部区域与共同mask排假',['S02'],'todo','正确对应对匹配插值对照有来源外独立增量。',
             ['五种输入、两个支持区域','三个种子与固定校准','RAFT/插值核固定子集诊断','来源外开发及nuisance探针'],
             ['两项macro差值>=.02且区间下界>0','至少两个种子为正','OOD同方向；失败允许完成但只释放备用诊断'],
             ['../artifacts/cvpr27/mechanism_gate.json','../artifacts/cvpr27/mechanism_report.md']),
        task('B01','M1','公开强基线与新颖性核对',['S02'],'todo','当前线索包含超出强表征和已有方法的研究空间。',
             ['DINOv2 LR/MLP与普通对齐','D3/ReStraV/WaveRep/RIFT原生复现','RIFT/G2VD/DCPT/WaveRep逐项差异表','预训练来源重叠核对'],
             ['原生与匹配协议分表','所有失败复现记录','不把网址或适配器当复现完成'],
             ['../artifacts/cvpr27/baseline_report.md','../artifacts/cvpr27/novelty_matrix.json']),
        task('M02','M3','门槛支持的最小算法或唯一备用诊断',['M01','B01'],'todo','多对照差分提供超出单对照、拼接容量和普通融合的增量。',
             ['主门槛通过才训练多对照方法','失败时仅固定半数稳定位置一致性诊断','两条都失败则记录转向而非堆结构'],
             ['程序检查前序证据哈希与gate结果','容量和增强对照完整','不使用最终确认结果选路线'],
             ['../artifacts/cvpr27/method_decision.json']),
        task('E01','M4','规模曲线、消融及最终协议锁定',['M02'],'todo','主方法增量在规模、来源和处理链变化下保持。',
             ['3000/6000/12000/24000规模曲线','冻结强基线、参数、阈值和主比较','检查最终来源与预训练污染'],
             ['测试打开前签署开发审查','无增量则停止赶稿','完整费用和代码锁定'],
             ['../artifacts/cvpr27/final_protocol.json','../artifacts/cvpr27/development_review.json']),
        task('E02','M4','一次性外部确认',['E01'],'todo','未知生成器与新真实来源满足预设效果与最差组门槛。',
             ['至少7000条确认数据','未见H265与复合路径','记录失败组和全链路成本'],
             ['macro增益>=.02且配对区间下界>0','最差组>=.03、clean损失<=.01','三个生成器和新真实来源；失败保留'],
             ['../artifacts/cvpr27/final_predictions.json','../artifacts/cvpr27/final_decision.json']),
        task('R27','M5','独立复核与论文证据包',['E02'],'todo','不同复核者能够从锁定产物重建论文主表。',
             ['独立重算表图','核对主张、失败结果和限制','完成可编辑图、正文和补充材料'],
             ['不同于实现者的复核记录','最终试验不回流调参','所有主张有可重算依据'],
             ['../artifacts/cvpr27/independent_review.json','../artifacts/cvpr27/claim_evidence.json'],owner='independent-reviewer')
    ]
    tasks[1]['blocker']='用户已决定另租服务器。AutoDL租用浏览器已打开，等待用户登录；实际库存、报价、余额、持久盘和新SSH端点尚未核验。未租用或启动付费实例。'
    updated={**prior,'schema_version':'0.4','updated':'2026-09-10','project':'cvpr2027-operator-controlled-video-forensics',
        'goal':'在3000元与180 GPU小时上限内建立可迁移视频取证算法及独立证据，满足门槛后冲刺CVPR 2027主会。',
        'canonical_plan':'CVPR2027_MASTER_PLAN.md','tasks':tasks,'historical_tasks':prior['tasks'],
        'budget':{'total_cny':3000,'paid_gpu_hours':180,'categories':{'storage':500,'profile':200,'mechanism':1000,'method':1000,'recovery':300}},
        'storage_policy':{'primary':'confirmed_server_pending','local_workspace':'E:/aNB/TECH/脉冲神经网络','raw_videos':'server_read_only','portable_manifests':'root_relative_POSIX','secrets_in_repository':False}}
    write(project,updated,replace=True)
    print('REGISTERED',len(tasks),'active tasks; retained',len(prior['tasks']),'historical tasks')


if __name__=='__main__':main(sys.argv[1])
