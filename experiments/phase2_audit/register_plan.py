"""One-time local DAG migration; preserves the previous plan and evidence."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT/'research-plan/task-hermes'
sys.path.insert(0, str(BOARD))
from board import validate

path = BOARD/'project.json'
before = path.read_bytes()
data = json.loads(before)
backup = BOARD/'project_before_phase2_20260914.json'
if backup.exists():
    raise FileExistsError('Phase-2 migration already recorded')
verification = ROOT/'research-runs/phase2_evidence_audit_20260914/verification.json'
assert json.loads(verification.read_text())['status']=='pass'
task = {t['id']:t for t in data['tasks']}
assert not any(k in task for k in ['P2A','P2D','P2C','P2G'])

def new_task(ident, milestone, title, parents, hypothesis, work, acceptance, artifacts, status='todo'):
    return dict(id=ident, milestone=milestone, title=title, assignee='research-engineer',
                parents=parents, status=status, hypothesis=hypothesis, work=work,
                acceptance=acceptance, artifacts=artifacts, phase='phase2',
                dataset_version='legacy and exposed external development; new-source acceptance pending',
                seed=[17,29,43,59,71], budget={'paid_jobs':False,'phase_proposed_gpu_hour_ceiling':40,
                'phase_proposed_cny_ceiling':400,'within_existing_total':True},
                code_revision=None, config_hash=None, split_hash=None,
                checkpoint_hash=None, rejection_policy='Preserve valid negative results; no automatic escalation')

audit_artifacts = ['../../research-runs/phase2_evidence_audit_20260914/'+n for n in
                   ['report.md','results.json','predictions.json','models.json','input_lock.json','artifact_hashes.json','verification.json']]
audit = new_task('P2A','M0','第二阶段事实回放与配对证据审计',[],
    '内部融合数字可复算，但来源外增量及配对必要性可能不成立。',
    ['五个冻结 LR 对照','祖先分组 bootstrap','类别/来源内双端置换','保存模型、预测、输入输出哈希'],
    ['重现历史内外部点估计','独立公式复算和模型概率回放','解释与统计限制记录'],audit_artifacts,'done')
audit['artifact_sha256'] = {p:hashlib.sha256((BOARD/p).read_bytes()).hexdigest() for p in audit_artifacts}
audit['review'] = {'reviewer':'primary agent mechanical replay','verdict':'pass','independent_scientific_review':False}
audit['result'] = {'external_delta':0.0034, 'external_delta_ci95':[-0.05731,0.06471],
                   'pairing_necessity':'not established', 'claim_status':'exploratory only'}
data['tasks'].append(audit)
data['tasks'].append(new_task('P2D','M1','已接触样本登记与采样精度一致性', ['P2A'],
    '来源祖先分组、角色登记和统一精度可使后续比较具有可核查的共同协议。',
    ['登记所有已接触外部 ID/哈希和可知祖先','4fps/128 回放与 8fps/224 新轨分开',
     '固定小样本 float16/float32 等价检查','冻结新开发与最终确认角色，未知祖先单列'],
    ['外部已接触池不会流入最终确认','精度差异及指标影响完整报告','数据许可状态链接 D01'],
    ['../artifacts/phase2/exposure_registry.json','../artifacts/phase2/protocol_equivalence.json',
     '../artifacts/phase2/split_contract.json'],'ready'))
data['tasks'].append(new_task('P2C','M2','H1 受控相对响应原型与本地性能测量',['P2A'],
    '多对照相对响应可实现，且不由插值次数或支持区域差异解释。',
    ['四个匹配错误对应和相对响应图','普通差分/多对照/归一化组件对照',
     '已知平移、零纹理、越界和共同支持测试','100 条旧开发视频 profile；无来源外选模型'],
    ['所有分支相同采样和 mask','退化分母/截断率可审计','给出全链路时间与失败样本'],
    ['../../experiments/operator_response_v1/protocol.json','../artifacts/phase2/operator_validation.json',
     '../artifacts/phase2/operator_profile.json'],'ready'))
task['D01']['blocked_reason'] = 'Accepted multi-source training and OOD manifests remain incomplete. MSVD/Sora/VEO3 local external-development videos now exist, but licences, cross-source ancestry, acquisition bias and new-role sampling need acceptance. Earlier availability blockers are historical, not proof that no external video exists.'
task['D01']['work'].append('2026-09-14 phase2: audit existing ComGenVid as exposed development; acquire/accept sufficient real-source diversity and preserve unseen final ancestors.')
task['B01'].update(status='ready',parents=['S02','P2A'],phase='phase2')
task['B01']['work'] += ['优先 D3/STALL 同 ID 原生参考；与匹配 DINO 表征轨道分表',
                       '核对光流残差/时空一致性先例；未经逐项比较不宣称新颖']
task['M01'].update(title='H1 相对算子响应的来源外验收',parents=['S02','D01','P2D','P2C','B01'],phase='phase2',
    hypothesis='受控相对响应在新真实来源和未见生成器上超过简单融合与强表征基线。',
    work=['起步约2400条fit/calibration与900条OOD开发目标，不是已获样本',
          '固定两未见生成器；采样和精度各臂一致','单对照、多对照、归一化、拼接、DINO对照',
          '随机编码器五种子；确定性LR不伪造种子稳定性','祖先分层bootstrap与mask/插值核排假'],
    acceptance=['预注册macro增益>=.03且配对CI下界>0','两OOD生成器同方向，worst组下降<=.01',
                'clean损失<=.01、留出整视频退化增益为正','所有失败组保留；负结果允许完成研究任务但不放行方法'],
    artifacts=['../artifacts/phase2/h1_protocol.json','../artifacts/phase2/h1_predictions.json','../artifacts/phase2/h1_decision.json'])
task['M02'].update(title='H1 支持下的可靠性读出或失败解释',parents=['M01','B01'],phase='phase2',
    hypothesis='只有H1成立时，可靠性读出才可能在相同覆盖率下提供额外泛化收益。',
    work=['检查H1结论及证据哈希，通过才运行H2','比较均匀/同覆盖率随机/可靠性/mask-only',
          'H1失败只做一次原因诊断，不自动训练新架构','最多选择一个候选；SNN继续低优先级'],
    acceptance=['H1通过和失败分支均记录明确决定','不以丢弃困难视频换高分','没有可靠性增益则保留H1最小模型'],
    artifacts=['../artifacts/phase2/h2_or_failure_report.json','../artifacts/cvpr27/method_decision.json'])
data['tasks'].append(new_task('P2G','M3','第二阶段 Go/No-Go 与唯一候选冻结',['M01','M02','B01','P2D'],
    '一个最小候选能够满足预设外部开发增量、对照和成本门槛。',
    ['汇总H1/H2/失败结果','核对来源、基线和预算','决定扩容或延后投稿；不打开最终集'],
    ['明确pass/fail，不以任务done冒充方法通过','只有pass才释放规模化训练','保存唯一候选和主张证据矩阵'],
    ['../artifacts/phase2/stage_decision.json','../artifacts/phase2/claim_evidence.json']))
task['E01']['parents'] = ['P2G']
task['E01']['work'].insert(0,'必须检查P2G科学结论为pass；done或产物存在本身不释放训练。')
data.update(updated='2026-09-14',canonical_plan='PHASE2_PLAN_2026-09-14.md',active_phase='phase2')
data['direction_decision']['phase2_update'] = 'Relative operator responses prioritized; external fusion gain unestablished; pairing necessity unproven; unconditional source adversarial learning not required.'
data['phase2'] = {'plan':'PHASE2_PLAN_2026-09-14.md','entry_tasks':['P2D','B01','P2C'],
                  'prior_project_sha256':hashlib.sha256(before).hexdigest(),
                  'paid_jobs_started_this_turn':False,'audit_wall_seconds':15.078,
                  'proposed_reservation':{'gpu_hours':40,'cny':400,'within_original_total':True,'activation':'verify remaining budget, accepted data and instance lifecycle first'}}
errors = validate(data)
assert not errors, errors
assert path.read_bytes()==before, 'Concurrent plan edit; stop'
backup.write_bytes(before)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('VALID',len(data['tasks']),'tasks; original plan preserved:',backup.name)
