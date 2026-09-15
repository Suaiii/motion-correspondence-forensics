"""Apply frozen development go/no-go criteria and preserve all outcomes."""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from run import digest, dump


def paired(pred,rows,models,condition,gate):
    source_rows={r['sample_id']:r for r in rows if r['role']=='audit'}
    ids=sorted(source_rows)
    y=np.array([source_rows[s]['label_fake']for s in ids])
    strata=[np.array([i for i,s in enumerate(ids)if source_rows[s]['source']==name])for name in sorted({r['source']for r in source_rows.values()})]
    probabilities={m:np.array([np.mean([r['prob_fake']for r in pred if r['kind']==m and r['condition']==condition and r['sample_id']==s])for s in ids])for m in models}
    if not all(np.isfinite(p).all()for p in probabilities.values()):raise ValueError('Missing or invalid predictions')
    a,b=models
    auc_a=float(roc_auc_score(y,probabilities[a]));auc_b=float(roc_auc_score(y,probabilities[b]))
    rng=np.random.default_rng(gate['bootstrap']['seed']);diff=[]
    for _ in range(gate['bootstrap']['replicates']):
        ix=np.concatenate([rng.choice(g,len(g),replace=True)for g in strata])
        diff.append(roc_auc_score(y[ix],probabilities[a][ix])-roc_auc_score(y[ix],probabilities[b][ix]))
    return {'a':a,'b':b,'condition':condition,'n':len(ids),'auc_seed_mean_prob_a':auc_a,'auc_seed_mean_prob_b':auc_b,
            'delta':auc_a-auc_b,'paired_stratified_percentile95':np.quantile(diff,[.025,.975]).tolist(),
            'caveat':'development historical pool; bootstrap conditions on fitted seeds and does not represent new-generator/real-source uncertainty'}


def main(root):
    cfg=json.loads((root/'protocol.json').read_text(encoding='utf-8'))
    ev=json.loads((root/'evaluation.json').read_text(encoding='utf-8'))
    pred=json.loads((root/'predictions.json').read_text(encoding='utf-8'))
    rows=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    train=json.loads((root/'training_complete.json').read_text(encoding='utf-8'))
    assert ev['predictions_sha256']==digest(root/'predictions.json')
    assert ev['manifest_sha256']==digest(root/'manifest.json')
    assert ev['protocol_sha256']==digest(root/'protocol.json')
    if (root/'decision.json').exists():raise FileExistsError('Decision already exists; no overwrite')
    for item in ev['results']:
        group=[r for r in pred if all(r[k]==item[k]for k in ('kind','seed','condition'))]
        assert len(group)==len({r['sample_id']for r in group})==item['n']
        y=np.array([r['label_fake']for r in group]);p=np.array([r['prob_fake']for r in group])
        assert abs(roc_auc_score(y,p)-item['auc'])<1e-12
        assert abs(balanced_accuracy_score(y,p>=item['threshold'])-item['balanced_accuracy'])<1e-12
    primary=paired(pred,rows,('aligned_temporal','aligned_bag'),'clean',cfg['decision_gate'])
    seed_deltas=[]
    for seed in cfg['seeds']:
        value={r['kind']:r['auc']for r in ev['results']if r['seed']==seed and r['condition']=='clean'}
        seed_deltas.append(value['aligned_temporal']-value['aligned_bag'])
    checks={'minimum_effect':primary['delta']>=cfg['decision_gate']['practical_minimum_auc_delta'],
            'lower95_above_zero':primary['paired_stratified_percentile95'][0]>0,
            'at_least_two_positive_seeds':sum(d>0 for d in seed_deltas)>=2}
    supported=all(checks.values())
    comparisons=[primary]
    for models in [('raw_temporal','raw_bag'),('aligned_bag','raw_bag'),('aligned_temporal','raw_temporal')]:
        comparisons.append(paired(pred,rows,models,'clean',cfg['decision_gate']))
    stats=json.loads((root/'statistics_probe.json').read_text(encoding='utf-8'))
    clean_stats=next(r['auc']for r in stats['metrics']if r['role']=='audit'and r['condition']=='clean')
    decision={'gate':'continue_mechanism_research_only'if supported else 'deprioritize_order_specific_memory',
              'meaning':'Passing supports another independent mechanism experiment, not publication readiness; failure means insufficient support in this bounded design, not proof that temporal methods cannot work.',
              'checks':checks,'primary':primary,'seed_deltas':seed_deltas,'secondary_comparisons':comparisons[1:],
              'fixed_residual_statistics_clean_auc':clean_stats,'criteria_sha256':digest(root/'protocol.json'),
              'verifier_sha256':digest(__file__),'verified_metric_groups':len(ev['results']),
              'scope':'Primary criterion frozen before preprocessing/training; secondary analyses do not override primary gate.'}
    dump(root/'decision.json',decision)
    lines=['# 扩大样本后的止损判定','',
           '本轮为有预算上限的开发实验，不是外部确认测试。主比较在训练前冻结；各模型均为49,601参数。','',
           f"判定：**{'继续独立机制验证，暂不扩成复杂SNN' if supported else '未通过记忆结构门槛，降低SNN/状态输运优先级'}**。",'',
           '| clean 比较（种子均值概率的AUROC） | 差值 | 配对95%区间 |','|---|---:|---|']
    for r in comparisons:
        lo,hi=r['paired_stratified_percentile95'];lines.append(f"| {r['a']} − {r['b']} | {r['delta']:.4f} | [{lo:.4f}, {hi:.4f}] |")
    lines+=['',f'主比较三个seed差值：{[round(x,4)for x in seed_deltas]}。冻结门槛为均值概率AUROC增益≥0.02、配对区间下界>0、至少2/3种子同方向；实际检查：{checks}。',
            '',f'副检查：8维无序残差统计逻辑回归的clean开发audit AUROC为{clean_stats:.4f}。它不包含显式时序记忆；即使较强，也不能直接证明神经模型只利用统计量。',
            '', '全部四模型、三种子、三条件结果见report.md，原始概率见predictions.json。主要表格中的种子AUROC均值与本表先平均概率再算AUROC不是同一个统计量。',
            '',f'共保留{len(rows)}条视频，12次fit。训练总耗时{train["wall_seconds"]:.1f}秒；质量剔除不补样。文件/源前缀与首轮隔离不保证prompt和语义独立；真实来源仍只有Vript。',
            '', '后续决定：'+('先验证错误对应、遮挡和不同采样条件下机制是否保留，再考虑固定LIF对照。'if supported else '不继续在同一audit上堆叠SNN、双记忆或调参；优先检查残差表示、简单统计与codec/采样响应，并换独立数据来源验证。'),
            '', '否定范围：仅针对本轮小型CNN+GRU与等参数无序MLP，在当前数据和优化设置下没有足够证据支持记忆优势。固定参数预算不保证优化难度、状态容量或实际算力相同；源外测试仍欠缺。']
    (root/'gate_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    dump(root/'artifact_hashes.json',{str(p.relative_to(root)):digest(p)for p in root.rglob('*')if p.is_file()and p.name!='artifact_hashes.json'})
    print(json.dumps({k:v for k,v in decision.items()if k!='secondary_comparisons'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);args=p.parse_args();root=args.run_dir.resolve();assert root.drive.upper()=='E:';main(root)
