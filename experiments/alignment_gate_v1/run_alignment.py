"""Frozen correspondence/interpolation diagnostic; reuses the locked bag training recipe."""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path
import cv2
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
BASE = PROJECT / 'experiments/order_gate_v1'
sys.path.insert(0, str(BASE))
import run as engine
from video_io import decode, corrupt, warp_previous
from model import VideoBaseline
from decide import paired

ARMS = ['raw', 'correct', 'wrong_integer', 'fractional', 'compensation_gain']
RUN = PROJECT / 'research-runs/alignment_gate_v1'
PRIOR = PROJECT / 'research-runs/order_gate_v1'


def hashes():
    paths = [Path(__file__), BASE/'run.py', BASE/'model.py', BASE/'video_io.py', BASE/'selection.py', BASE/'decide.py', PROJECT/'research-code/sampling.py']
    return {str(p): engine.digest(p) for p in paths}


def verify(run):
    lock = engine.read(run/'lock.json')
    assert hashes() == lock['code_hashes'], 'Code changed after freeze'
    assert engine.digest(run/'protocol.json') == lock['protocol_sha256']
    assert engine.digest(run/'manifest.json') == lock['manifest_sha256']
    return engine.read(run/'protocol.json')


def freeze():
    if RUN.exists():
        raise FileExistsError('Preserve existing run; no overwrite')
    cfg = engine.read(BASE/'protocol.json')
    cfg.update(experiment_id='alignment_gate_v1', input_run=str(PRIOR), models=ARMS,
               representation_map={m:m for m in ARMS}, cache_representations=ARMS,
               conditions={'clean':{}, 'jpeg70':{'quality':70}},
               scope='Exploratory mechanism diagnostic on reused development audit; no independent confirmation')
    cfg['flow']['mask'] = 'per-pixel intersection of correct, wrong_integer, fractional validity; identical for every arm'
    cfg['decision_gate'] = {
        'primary':['correct - wrong_integer', 'correct - fractional'],
        'minimum_effect':0.02, 'positive_seeds':2,
        'bootstrap':{'replicates':2000,'seed':20260912,'stratify':'source'},
        'pass':'Both primary deltas >= .02, both lower95 > 0, >=2 positive seeds each; independent-source replication still required',
        'secondary':['correct - raw', 'compensation_gain - correct', 'all jpeg70 results', 'mask and residual-statistics LR'],
        'no_audit_tuning':True,
        'failure':'Do not advance motion-mechanism claim or scale memory; preserve negative results'
    }
    cfg['controls'] = {
        'correct':'Farneback current-to-previous sampling estimate quantized to 1/32 pixel OpenCV interpolation table resolution; not ground-truth optical flow',
        'wrong_integer':'floor(flow) rolled spatially by half image on both axes + original per-pixel fractional(flow)',
        'fractional':'flow-floor(flow); one bilinear remap with same per-pixel fractional interpolation weights as correct, no integer motion',
        'raw':'unwarped previous frame, common mask; anchor only, not interpolation-matched',
        'compensation_gain':'abs(fractional residual)-abs(correct residual), channelwise signed local error reduction, common mask',
        'mask_probe':'8 features: temporal coverage mean/std/min/max and mean invalid fraction in four quadrants; LR C=1',
        'statistics_probe':'per-arm mean absolute, std of per-time mean absolute, RMS, 95th percentile; LR C=1',
        'limitations':'Wrong control changes integer displacement field spatial structure; equal weights do not equal sampled texture; fractional control retains subpixel motion; masks can still encode source. No exact-motion or causal claim.'
    }
    cfg['limitations'] = engine.read(BASE/'protocol.json')['limitations'][:6] + [
        'Same 595 videos and split as prior order gate; audit reused explicitly for mechanism exploration.',
        'No independent real source, unseen generator, semantic deduplication or true transmission validation.',
        'All five arms use the same 49,601 parameter bag network; gain is a hypothesis, not a novel-method claim.',
        'Bootstrap is video-level stratified; known groups checked unique, unknown ancestry remains unresolved.'
    ]
    RUN.mkdir(parents=True)
    engine.dump(RUN/'protocol.json', cfg)
    shutil.copyfile(PRIOR/'manifest.json', RUN/'manifest.json')
    rows = engine.read(RUN/'manifest.json')
    assert len(rows) == 595
    assert len({r['sample_id'] for r in rows}) == len(rows)
    assert len({r['sha256'] for r in rows}) == len(rows)
    assert len({r['group_id'] for r in rows}) == len(rows), 'Use grouped inference if repeated groups exist'
    for p in hashes():
        target = RUN/'code'/Path(p).relative_to(PROJECT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    engine.dump(RUN/'lock.json', {
        'code_hashes':hashes(), 'protocol_sha256':engine.digest(RUN/'protocol.json'),
        'manifest_sha256':engine.digest(RUN/'manifest.json'),
        'prior_manifest_sha256':engine.digest(PRIOR/'manifest.json'),
        'frozen_before_cache_and_training':True, 'python':sys.version, 'executable':sys.executable,
        'torch':torch.__version__, 'opencv':cv2.__version__, 'numpy':np.__version__,
        'cuda':torch.cuda.get_device_name(0), 'created_utc':engine.datetime.now(engine.timezone.utc).isoformat()
    })
    engine.event(RUN,stage='freeze',samples=len(rows))
    print('FROZEN', len(rows), 'videos; 15 neural fits; clean + jpeg70', flush=True)


def flow_controls(flow):
    flow=(np.rint(flow*32)/32).astype(np.float32)
    integer = np.floor(flow)
    fraction = flow-integer
    wrong = np.roll(integer, (flow.shape[0]//2, flow.shape[1]//2), axis=(0,1)) + fraction
    return {'correct':flow, 'wrong_integer':wrong, 'fractional':fraction}


def representations(bgr, cfg):
    f = cfg['flow']
    rgb = bgr[..., ::-1].astype(np.float32)/255
    gray = [cv2.cvtColor(x,cv2.COLOR_BGR2GRAY) for x in bgr]
    output = {m:[] for m in ARMS}
    masks=[]
    changed=[]
    for t in range(1,len(bgr)):
        flow = cv2.calcOpticalFlowFarneback(gray[t],gray[t-1],None,f['pyr_scale'],f['levels'],f['winsize'],f['iterations'],f['poly_n'],f['poly_sigma'],f['flags'])
        controls=flow_controls(flow)
        warps={k:warp_previous(rgb[t-1],v) for k,v in controls.items()}
        mask=np.logical_and.reduce([v[1] for v in warps.values()])
        residual={k:(rgb[t]-v[0])*mask[...,None] for k,v in warps.items()}
        residual['raw']=(rgb[t]-rgb[t-1])*mask[...,None]
        residual['compensation_gain']=np.abs(residual['fractional'])-np.abs(residual['correct'])
        for k in ARMS:output[k].append(residual[k])
        masks.append(mask)
        changed.append(float(np.mean(np.any(np.floor(controls['correct'])!=np.floor(controls['wrong_integer']),axis=-1))))
    masks=np.stack(masks)
    coverage=masks.mean((1,2)); h,w=masks.shape[1:]
    probe=[coverage.mean(),coverage.std(),coverage.min(),coverage.max()]
    probe += [1-masks[:,ys,xs].mean() for ys,xs in [(slice(0,h//2),slice(0,w//2)),(slice(0,h//2),slice(w//2,None)),(slice(h//2,None),slice(0,w//2)),(slice(h//2,None),slice(w//2,None))]]
    arrays={k:np.stack(v).transpose(0,3,1,2).astype(np.float16) for k,v in output.items()}
    assert all(np.isfinite(v).all() for v in arrays.values())
    assert masks.any(), 'Empty common support; stop instead of replacing sample'
    return arrays, probe, {'coverage_mean':float(coverage.mean()),'coverage_min':float(coverage.min()),'wrong_integer_changed_fraction':float(np.mean(changed))}


def cache():
    cfg=verify(RUN)
    dest=RUN/'cache';dest.mkdir()
    rows=engine.read(RUN/'manifest.json'); n=len(rows);s=cfg['sampling']['size']
    buffers={(c,m):np.lib.format.open_memmap(dest/f'{c}__{m}.npy',mode='w+',dtype=np.float16,shape=(n,7,3,s,s)) for c in cfg['conditions'] for m in ARMS}
    probes={c:[] for c in cfg['conditions']};quality=[]
    cv2.setNumThreads(1);started=time.perf_counter()
    for i,r in enumerate(rows):
        if time.perf_counter()-started>cfg['budget']['max_cache_seconds']:raise TimeoutError('Cache budget exceeded')
        assert engine.digest(r['path'])==r['sha256'], 'Source changed'
        bgr,q=decode(r,cfg)
        assert q['indices']==r['quality']['indices']
        item={'sample_id':r['sample_id'],'conditions':{}}
        for c in cfg['conditions']:
            arrays,probe,receipt=representations(corrupt(bgr,c,cfg,r['sample_id']),cfg)
            for k,a in arrays.items():buffers[(c,k)][i]=a
            probes[c].append(probe);item['conditions'][c]=receipt
        quality.append(item)
        if (i+1)%25==0:print('CACHE',i+1,'/',n,'seconds',round(time.perf_counter()-started,1),flush=True)
    for a in buffers.values():a.flush()
    buffers.clear()
    engine.dump(RUN/'mask_features.json',probes)
    engine.dump(RUN/'qc.json',{'rows':quality,'wall_seconds':time.perf_counter()-started,'exclusions':[]})
    engine.dump(RUN/'cache_lock.json',{'manifest_sha256':engine.digest(RUN/'manifest.json'),'files':{p.name:engine.digest(p) for p in dest.glob('*.npy')},'mask_features_sha256':engine.digest(RUN/'mask_features.json')})
    engine.event(RUN,stage='cache_complete',samples=n)


def probes():
    cfg=verify(RUN);rows=engine.read(RUN/'manifest.json')
    y=np.array([r['label_fake'] for r in rows]);fit=np.array([i for i,r in enumerate(rows) if r['role']=='fit'])
    assert engine.digest(RUN/'mask_features.json')==engine.read(RUN/'cache_lock.json')['mask_features_sha256']
    features={'mask':{k:np.array(v) for k,v in engine.read(RUN/'mask_features.json').items()}}
    for arm in ARMS:
        features[arm]={}
        for c in cfg['conditions']:
            a=engine.load_array(RUN,c,arm);values=[]
            for x in a:
                x=np.asarray(x,dtype=np.float32);ax=np.abs(x)
                values.append([ax.mean(),ax.mean((1,2,3)).std(),np.sqrt((x*x).mean()),np.quantile(ax,.95)])
            features[arm][c]=np.log1p(np.array(values))
    results=[];predictions=[];models={}
    for name,conditions in features.items():
        scaler=StandardScaler().fit(conditions['clean'][fit]);clf=LogisticRegression(C=1,max_iter=1000,random_state=17)
        clf.fit(scaler.transform(conditions['clean'][fit]),y[fit])
        models[name]={'coef':clf.coef_.tolist(),'intercept':clf.intercept_.tolist(),'scaler_mean':scaler.mean_.tolist(),'scaler_scale':scaler.scale_.tolist()}
        for c,x in conditions.items():
            p=clf.predict_proba(scaler.transform(x))[:,1]
            for role in ('fit','calibration','audit'):
                ix=np.array([i for i,r in enumerate(rows) if r['role']==role])
                results.append({'probe':name,'condition':c,'role':role,'n':len(ix),'auc':float(roc_auc_score(y[ix],p[ix]))})
            for i,r in enumerate(rows):predictions.append({'probe':name,'condition':c,'sample_id':r['sample_id'],'role':r['role'],'label_fake':int(y[i]),'prob_fake':float(p[i]),'features':x[i].tolist()})
    engine.dump(RUN/'probes.json',{'metrics':results,'predictions':predictions,'models':models,'fit_only_scaler_and_lr':True})


def evaluate():
    cfg=verify(RUN);trained=engine.read(RUN/'training_complete.json');rows=engine.read(RUN/'manifest.json')
    assert trained['manifest_sha256']==engine.digest(RUN/'manifest.json')
    if (RUN/'evaluation.json').exists():raise FileExistsError('No overwrite')
    y=np.array([r['label_fake'] for r in rows]);audit=np.array([i for i,r in enumerate(rows) if r['role']=='audit'])
    val=np.array([i for i,r in enumerate(rows) if r['role']=='calibration'])
    outputs=[];records=[];device=torch.device('cuda:0');bs=cfg['training']['batch_size']
    for fit in trained['results']:
        kind,seed=fit['kind'],fit['seed'];path=RUN/'training'/f'{kind}_seed{seed}'/'best.pt'
        assert engine.digest(path)==fit['checkpoint_sha256']
        net=VideoBaseline('aligned_bag').to(device);net.load_state_dict(torch.load(path,map_location=device,weights_only=True))
        vp=engine.predict(net,engine.load_array(RUN,'clean',kind),val,device,bs)
        grid=np.linspace(.01,.99,99);scores=[engine.balanced_accuracy_score(y[val],vp>=t) for t in grid]
        threshold=min((float(t) for t,s in zip(grid,scores) if abs(s-max(scores))<1e-12),key=lambda t:(abs(t-.5),t))
        for c in cfg['conditions']:
            p=engine.predict(net,engine.load_array(RUN,c,kind),audit,device,bs)
            outputs.append({'kind':kind,'seed':seed,'condition':c,'threshold':threshold,**engine.metrics(y[audit],p,threshold)})
            for i,prob in zip(audit,p):records.append({'kind':kind,'seed':seed,'condition':c,'sample_id':rows[i]['sample_id'],'group_id':rows[i]['group_id'],'source':rows[i]['source'],'label_fake':int(y[i]),'prob_fake':float(prob),'threshold':threshold})
        del net
    engine.dump(RUN/'predictions.json',records)
    engine.dump(RUN/'evaluation.json',{'results':outputs,'predictions_sha256':engine.digest(RUN/'predictions.json'),'manifest_sha256':engine.digest(RUN/'manifest.json'),'protocol_sha256':engine.digest(RUN/'protocol.json')})
    engine.event(RUN,stage='evaluation_complete',fits=len(trained['results']),predictions=len(records))
    print('EVALUATED',len(outputs),'model/seed/condition groups',flush=True)


def report():
    cfg=verify(RUN);rows=engine.read(RUN/'manifest.json');pred=engine.read(RUN/'predictions.json');ev=engine.read(RUN/'evaluation.json')['results']
    comparisons=[]
    for c in cfg['conditions']:
        for a,b in [('correct','wrong_integer'),('correct','fractional'),('correct','raw'),('compensation_gain','correct')]:
            result=paired(pred,rows,(a,b),c,cfg['decision_gate'])
            result['seed_deltas']=[next(r['auc'] for r in ev if r['kind']==a and r['seed']==s and r['condition']==c)-next(r['auc'] for r in ev if r['kind']==b and r['seed']==s and r['condition']==c) for s in cfg['seeds']]
            comparisons.append(result)
    primary=comparisons[:2]
    checks=[r['delta']>=.02 and r['paired_stratified_percentile95'][0]>0 and sum(d>0 for d in r['seed_deltas'])>=2 for r in primary]
    engine.dump(RUN/'decision.json',{'primary_checks':checks,'local_gate_pass':all(checks),'independent_replication_complete':False,'comparisons':comparisons,'next':'Independent-source replication required before any motion-mechanism claim' if all(checks) else 'Do not promote motion mechanism; inspect interpolation/mask/source confounds','audit_reused':True})
    lines=['# 对齐机制排假：开发实验','', '同一595条视频与既有划分；15次等参数训练，三个种子。audit已在前轮使用，本轮仅是探索性机制诊断。','', '| 输入 | Clean AUROC，种子均值±标准差 | JPEG70 AUROC，种子均值±标准差 |','|---|---:|---:|']
    for k in ARMS:
        fields=[]
        for c in cfg['conditions']:
            a=np.array([r['auc'] for r in ev if r['kind']==k and r['condition']==c]);fields.append(f'{a.mean():.4f} ± {a.std(ddof=1):.4f}')
        lines.append('| '+k+' | '+' | '.join(fields)+' |')
    lines+=['','| 比较 | 条件 | 先平均种子概率的AUROC差值 | 配对95%区间 |','|---|---|---:|---|']
    for r in comparisons:
        lo,hi=r['paired_stratified_percentile95'];lines.append(f"| {r['a']} − {r['b']} | {r['condition']} | {r['delta']:.4f} | [{lo:.4f}, {hi:.4f}] |")
    lines+=['',f'两项预设主比较通过情况：{checks}。每项要求差值≥0.02、区间下界>0、至少2/3种子为正；独立来源复现仍未完成。', '', '| 简单探针 | Clean audit AUROC | JPEG70 audit AUROC |','|---|---:|---:|']
    ps=engine.read(RUN/'probes.json')['metrics']
    for k in ['mask']+ARMS:
        a=[next(r['auc'] for r in ps if r['probe']==k and r['condition']==c and r['role']=='audit') for c in cfg['conditions']]
        lines.append(f'| {k} | {a[0]:.4f} | {a[1]:.4f} |')
    lines+=['','正确对应指估计光流，并非真值。错误对应仅打乱整数位移，小数部分逐像素保留；fractional对照仅保留小数位移。三者均进行一次双线性采样，使用相同插值权重和共同有效区域。raw仅作为未插值锚点。', '', '新假设compensation_gain输入为逐通道的绝对fractional残差减去绝对correct残差，检查局部运动补偿收益能否形成有用判别表示。未搜索融合权重或扩大网络。','', '这些对照仍不能彻底隔离运动因果：采样纹理不同、错误位移空间结构改变、小数位移仍含运动，共同掩码也可能泄露来源。高分mask探针只能说明捷径可用，不能证明CNN必然依赖它。低分同样不能排除复杂掩码捷径。','', '校准集选择checkpoint和阈值；探针标准化及拟合仅使用fit。JPEG70在裁剪缩放后逐帧施加，是固定压力检查，不是真实平台传播。区间按来源分层、视频配对bootstrap，条件于已训练模型，不涵盖未知同源关系和外部来源不确定性。','', '全部检查点、逐视频概率、特征、损失曲线、输入哈希、代码快照与资源测量均保留。当前没有独立真实来源、未见生成器或CCF-A突破证据。']
    (RUN/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    engine.dump(RUN/'artifact_hashes.json',{str(p.relative_to(RUN)):engine.digest(p) for p in RUN.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
    print('\n'.join(lines[:12]),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','cache','train','evaluate','probes','report']);args=parser.parse_args()
    engine.verify=verify;engine.current_code_hashes=hashes
    engine.VideoBaseline=lambda kind:VideoBaseline('aligned_bag')
    torch.set_num_threads(4)
    try:
        {'freeze':freeze,'cache':cache,'train':lambda:engine.train(RUN),'evaluate':evaluate,'probes':probes,'report':report}[args.stage]()
    except Exception as exc:
        if RUN.exists():engine.event(RUN,stage=args.stage,status='failed',error=repr(exc),traceback=engine.traceback.format_exc())
        raise


if __name__=='__main__':main()
