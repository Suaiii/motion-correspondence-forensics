"""Versioned local neural training pilot with pretraining locks and held-out reporting."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import random
import shutil
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
import torch
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, confusion_matrix, log_loss
from model import VideoBaseline
from video_io import decode, represent, corrupt

ROOT = Path(__file__).resolve().parent
SAMPLER = ROOT.parents[1] / "research-code" / "sampling.py"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def event(run, **payload):
    with (run / 'events.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(dict(time_utc=datetime.now(timezone.utc).isoformat(), **payload), ensure_ascii=False) + '\n')


def current_code_hashes():
    return {str(p): digest(p) for p in [ROOT/'run.py', ROOT/'model.py', ROOT/'video_io.py', SAMPLER]}


def prepare(run):
    if run.exists():
        raise FileExistsError('Refuse overwrite; create a fresh run directory')
    cfg = read(ROOT/'protocol.json')
    prior = Path(cfg['input_run'])
    # Preserve the historical role mapping; never reassign roles based on outcomes.
    receipt = read(prior/'probe_receipt.json')
    assert digest(prior/'observations.jsonl') == receipt['observations_sha256']
    rows = [json.loads(s) for s in (prior/'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) <= cfg['budget']['max_source_videos']
    assert len({r['group_id'] for r in rows}) == len(rows)
    assert len({r['sha256'] for r in rows}) == len(rows)
    run.mkdir(parents=True)
    shutil.copyfile(ROOT/'protocol.json', run/'protocol.json')
    for src in (ROOT/'run.py', ROOT/'model.py', ROOT/'video_io.py', SAMPLER):
        (run/'code').mkdir(exist_ok=True)
        shutil.copyfile(src, run/'code'/src.name)
    dump(run/'input_manifest.json', rows)
    env = ROOT.parents[1]/'research-runtime'/'environment.json'
    if env.exists():
        shutil.copyfile(env, run/'environment.json')
    dump(run/'lock.json', {'created_utc':datetime.now(timezone.utc).isoformat(),
        'code_hashes':current_code_hashes(), 'protocol_sha256':digest(run/'protocol.json'),
        'input_manifest_sha256':digest(run/'input_manifest.json'), 'torch':torch.__version__,
        'python':sys.version, 'python_executable':sys.executable,
        'scope':'explicit local development training; no confirmatory test',
        'main_thread':'01a055fc-51ee-7b00-824b-087fc85b70d5'})
    event(run, stage='prepare', samples=len(rows))
    print('PREPARED', len(rows), flush=True)


def verify(run):
    cfg, lock = read(run/'protocol.json'), read(run/'lock.json')
    assert digest(run/'protocol.json') == lock['protocol_sha256']
    assert digest(run/'input_manifest.json') == lock['input_manifest_sha256']
    assert current_code_hashes() == lock['code_hashes'], 'Code changed; create a new versioned run'
    return cfg


def cache(run):
    cfg = verify(run)
    if (run/'cache').exists():
        raise FileExistsError('Cache directory exists; no overwrite')
    (run/'cache').mkdir()
    if cfg.get('cache_source'):
        source=Path(cfg['cache_source'])
        prior_cfg=read(source/'protocol.json')
        for key in ('input_run','sampling','quality','flow','conditions','models'):
            assert cfg[key]==prior_cfg[key], f'Cache contract differs: {key}'
        assert digest(source/'input_manifest.json')==digest(run/'input_manifest.json')
        receipt=read(source/'cache_lock.json')
        assert digest(source/'manifest.json')==receipt['manifest_sha256']
        for filename,h in receipt['files'].items():
            assert digest(source/'cache'/filename)==h, filename
            os.link(source/'cache'/filename,run/'cache'/filename)
        for name in ('manifest.json','qc.json','cache_lock.json'):
            shutil.copyfile(source/name,run/name)
        dump(run/'cache_reuse.json',{'source':str(source),'mode':'read-only same-volume hardlinks','source_manifest_sha256':receipt['manifest_sha256'],'cache_stage_recomputed':False})
        event(run,stage='cache_reused',source=str(source))
        print('CACHE VERIFIED AND REUSED',receipt['rows'],'videos',flush=True)
        return
    rows = read(run/'input_manifest.json')
    buffers = {(c,m):[] for c in cfg['conditions'] for m in cfg['models']}
    kept, exclusions, failed = [], [], []
    started = time.perf_counter()
    cv2.setNumThreads(1)
    for i, row in enumerate(rows):
        if time.perf_counter()-started > cfg['budget']['max_cache_seconds']:
            failed.append({'sample_id':row['sample_id'], 'error':'cache time budget exceeded'})
            break
        # Confirm actual inputs still match the M0 asset audit before using them.
        if digest(row['path']) != row['sha256']:
            failed.append({'sample_id':row['sample_id'], 'error':'source file changed'})
            break
        if row['duration_sec'] < cfg['quality']['minimum_duration'] - 1e-8:
            exclusions.append({'sample_id':row['sample_id'], 'source':row['source'], 'role':row['role'], 'label_fake':row['label_fake'], 'reason':'insufficient_duration'})
            continue
        try:
            video, quality = decode(row, cfg)
            if quality['black_frame_fraction'] >= cfg['quality']['reject_if_black_frame_fraction_at_least']:
                exclusions.append({'sample_id':row['sample_id'], 'source':row['source'], 'role':row['role'], 'label_fake':row['label_fake'], 'reason':'black_frames', 'quality':quality})
                continue
            timing, coverages = {}, {}
            for condition in cfg['conditions']:
                tick = time.perf_counter()
                views, valid = represent(corrupt(video, condition, cfg, row['sample_id']), cfg)
                for model in cfg['models']:
                    buffers[(condition,model)].append(views[model].astype(np.float16))
                timing[condition] = time.perf_counter()-tick
                coverages[condition] = valid
            kept.append(dict(row, quality=quality, transform_seconds=timing, valid_warp_fraction=coverages))
        except Exception as exc:
            failed.append({'sample_id':row['sample_id'], 'error':repr(exc)})
            break
        if (i+1)%10 == 0:
            print(f'CACHE {i+1}/{len(rows)} kept={len(kept)} excluded={len(exclusions)}', flush=True)
    dump(run/'qc.json', {'kept':len(kept), 'exclusions':exclusions, 'failures':failed, 'wall_seconds':time.perf_counter()-started,
                          'policy':'quality rules frozen before model fitting; no replacements; all conditions share same IDs'})
    if failed:
        raise RuntimeError('Cache failed; see qc.json; fitting not permitted')
    for role in ['fit','calibration','audit']:
        for label in [0,1]:
            assert sum(r['role']==role and r['label_fake']==label for r in kept) >= 5
    dump(run/'manifest.json', kept)
    hashes = {}
    for (condition, model), values in buffers.items():
        filename = f'{condition}__{model}.npy'
        np.save(run/'cache'/filename, np.stack(values), allow_pickle=False)
        hashes[filename] = digest(run/'cache'/filename)
    dump(run/'cache_lock.json', {'manifest_sha256':digest(run/'manifest.json'), 'files':hashes,
                                'rows':len(kept), 'counts':dict(Counter(f"{r['role']}/{r['source']}" for r in kept))})
    event(run, stage='cache_complete', kept=len(kept), excluded=len(exclusions))
    print('CACHE COMPLETE', len(kept), 'videos', flush=True)


def load_array(run, condition, kind):
    return np.load(run/'cache'/f'{condition}__{kind}.npy', mmap_mode='r', allow_pickle=False)


def batch(array, indices, device):
    return torch.from_numpy(np.array(array[indices], dtype=np.float32)).to(device)


@torch.no_grad()
def predict(model, array, indices, device, batch_size):
    model.eval()
    result=[]
    for start in range(0,len(indices),batch_size):
        result.extend(torch.sigmoid(model(batch(array,indices[start:start+batch_size],device))).cpu().tolist())
    return np.array(result, dtype=float)


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True)


def train(run):
    cfg=verify(run)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; refuse unannounced CPU training fallback')
    receipt=read(run/'cache_lock.json')
    assert digest(run/'manifest.json') == receipt['manifest_sha256']
    for filename,h in receipt['files'].items():
        assert digest(run/'cache'/filename)==h, filename
    if (run/'training_complete.json').exists():
        raise FileExistsError('Training already completed')
    if (run/'training').exists():
        raise FileExistsError('Partial training exists; preserve it and use a fresh versioned run')
    (run/'training').mkdir()
    rows=read(run/'manifest.json')
    y=np.array([r['label_fake'] for r in rows],dtype=float)
    fit=np.array([i for i,r in enumerate(rows) if r['role']=='fit'])
    val=np.array([i for i,r in enumerate(rows) if r['role']=='calibration'])
    torch.set_num_threads(cfg['budget']['cpu_threads'])
    device=torch.device('cuda:0'); tc=cfg['training']; bs=tc['batch_size']
    total_start=time.perf_counter(); results=[]
    for kind in cfg['models']:
        array=load_array(run,'clean',kind)
        training_arrays={c:load_array(run,c,kind)for c in tc['train_conditions']}
        for seed in cfg['seeds']:
            seed_all(seed)
            dest=run/'training'/f'{kind}_seed{seed}';dest.mkdir()
            net=VideoBaseline(kind).to(device)
            optimizer=torch.optim.AdamW(net.parameters(),lr=tc['lr'],weight_decay=tc['weight_decay'])
            criterion=torch.nn.BCEWithLogitsLoss()
            best=float('inf'); best_epoch=0; best_val=None; history=[]
            torch.cuda.reset_peak_memory_stats()
            tick=time.perf_counter()
            for epoch in range(1,tc['epochs']+1):
                if time.perf_counter()-total_start>cfg['budget']['max_training_seconds']:
                    raise TimeoutError('Bounded pilot training budget exceeded')
                net.train(); order=np.random.permutation(fit); loss_sum=0
                for start in range(0,len(order),bs):
                    idx=order[start:start+bs]
                    condition=str(np.random.choice(tc['train_conditions']))
                    x=batch(training_arrays[condition],idx,device)
                    if np.random.random()<0.5:
                        x=x.flip(-1)
                    labels=torch.tensor(y[idx],dtype=torch.float32,device=device)
                    optimizer.zero_grad(set_to_none=True)
                    loss=criterion(net(x),labels)
                    if not torch.isfinite(loss):raise FloatingPointError('Nonfinite loss')
                    loss.backward()
                    norm=torch.nn.utils.clip_grad_norm_(net.parameters(),tc['gradient_clip'],error_if_nonfinite=True)
                    optimizer.step();loss_sum+=float(loss.detach())*len(idx)
                val_prob=predict(net,array,val,device,bs)
                val_loss=float(log_loss(y[val],val_prob,labels=[0,1]))
                row={'epoch':epoch,'train_bce':loss_sum/len(fit),'calibration_bce':val_loss,'calibration_auc':float(roc_auc_score(y[val],val_prob))}
                history.append(row)
                with (dest/'history.jsonl').open('a',encoding='utf-8') as handle:handle.write(json.dumps(row)+'\n')
                if val_loss < best:
                    best=val_loss;best_epoch=epoch;best_val=val_prob.copy()
                    torch.save({k:v.detach().cpu() for k,v in net.state_dict().items()},dest/'best.pt')
                if epoch==1 or epoch%5==0:
                    print(f'{kind} seed={seed} epoch={epoch:02d} train={row["train_bce"]:.4f} val={val_loss:.4f} val_auc={row["calibration_auc"]:.3f}',flush=True)
            fresh=VideoBaseline(kind).to(device)
            fresh.load_state_dict(torch.load(dest/'best.pt',map_location=device,weights_only=True))
            check=predict(fresh,array,val,device,bs)
            assert np.allclose(best_val,check,atol=1e-6,rtol=1e-6), 'Checkpoint reload predictions differ'
            stats={'kind':kind,'seed':seed,'params':sum(p.numel() for p in net.parameters()),'best_epoch':best_epoch,'best_calibration_bce':best,
                'first_train_bce':history[0]['train_bce'],'last_train_bce':history[-1]['train_bce'],
                'seconds':time.perf_counter()-tick,'peak_allocated_mb':torch.cuda.max_memory_allocated()/2**20,
                'checkpoint_sha256':digest(dest/'best.pt'),'checkpoint_reload_max_probability_error':float(np.max(np.abs(best_val-check))),
                'calibration_predictions':[{'sample_id':rows[i]['sample_id'],'label_fake':int(y[i]),'prob_fake':float(p)}for i,p in zip(val,check)]}
            dump(dest/'summary.json',stats);results.append(stats)
            event(run,stage='model_trained',kind=kind,seed=seed,best_epoch=best_epoch)
            del net,fresh,optimizer
            torch.cuda.empty_cache()
    dump(run/'training_complete.json',{'results':results,'wall_seconds':time.perf_counter()-total_start,'device':torch.cuda.get_device_name(0),
        'audit_results_used_for_training':False,'code_hashes':current_code_hashes(),'protocol_sha256':digest(run/'protocol.json'),'manifest_sha256':digest(run/'manifest.json')})
    print('ALL TRAINING COMPLETE',len(results),'fits',flush=True)


def metrics(y,p,t):
    pred=p>=t
    return {'n':len(y),'auc':float(roc_auc_score(y,p)), 'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'fake_recall':float(np.mean(pred[y==1])), 'real_recall':float(np.mean(~pred[y==0])),
            'bce':float(log_loss(y,p,labels=[0,1])),'confusion_matrix_real_fake':confusion_matrix(y,pred,labels=[0,1]).tolist()}


def evaluate(run):
    cfg=verify(run); trained=read(run/'training_complete.json'); rows=read(run/'manifest.json')
    assert trained['manifest_sha256']==digest(run/'manifest.json')
    if (run/'evaluation.json').exists():raise FileExistsError('Evaluation exists; no overwrite')
    y=np.array([r['label_fake']for r in rows]); audit=np.array([i for i,r in enumerate(rows)if r['role']=='audit'])
    val=np.array([i for i,r in enumerate(rows)if r['role']=='calibration'])
    outputs=[]; records=[];device=torch.device('cuda:0');bs=cfg['training']['batch_size']
    for fit in trained['results']:
        kind,seed=fit['kind'],fit['seed'];dest=run/'training'/f'{kind}_seed{seed}'
        assert digest(dest/'best.pt')==fit['checkpoint_sha256']
        seed_all(seed);net=VideoBaseline(kind).to(device)
        net.load_state_dict(torch.load(dest/'best.pt',map_location=device,weights_only=True))
        vp=predict(net,load_array(run,'clean',kind),val,device,bs)
        grid=np.linspace(.01,.99,cfg['threshold']['grid_count'])
        vals=[balanced_accuracy_score(y[val],vp>=t)for t in grid]
        threshold=min((float(t)for t,s in zip(grid,vals)if abs(s-max(vals))<1e-12),key=lambda t:(abs(t-.5),t))
        for condition in cfg['conditions']:
            array=load_array(run,condition,kind)
            p=predict(net,array,audit,device,bs)
            item={'kind':kind,'seed':seed,'condition':condition,'threshold':threshold,'checkpoint_sha256':fit['checkpoint_sha256'],**metrics(y[audit],p,threshold)}
            outputs.append(item)
            for i,prob in zip(audit,p):
                records.append({'kind':kind,'seed':seed,'condition':condition,'sample_id':rows[i]['sample_id'],'group_id':rows[i]['group_id'],
                                'source':rows[i]['source'],'label_fake':int(y[i]),'prob_fake':float(prob),'threshold':threshold})
        del net;torch.cuda.empty_cache()
    dump(run/'predictions.json',records)
    dump(run/'evaluation.json',{'results':outputs,'predictions_sha256':digest(run/'predictions.json'),
        'scope':'development pilot; every model/seed/condition reported; no inferential superiority claims',
        'protocol_sha256':digest(run/'protocol.json'),'manifest_sha256':digest(run/'manifest.json')})
    lines=['# 首轮神经网络训练结果','', '本轮为本地开发 pilot，不是论文主结果。全部模型从随机初始化训练，未下载预训练权重。', '',
           '| 模型 | 条件 | AUROC 均值±种子标准差 | BAcc 均值 |','|---|---|---:|---:|']
    for kind in cfg['models']:
        for condition in cfg['conditions']:
            selected=[r for r in outputs if r['kind']==kind and r['condition']==condition]
            auc=np.array([r['auc']for r in selected]); ba=np.mean([r['balanced_accuracy']for r in selected])
            lines.append(f'| {kind} | {condition} | {auc.mean():.4f} ± {auc.std(ddof=1):.4f} | {ba:.4f} |')
    lines+=['','第二版训练使用clean/JPEG70/gaussian5均匀批次采样和一致水平翻转，lr=0.0003、weight_decay=0.01。仍以clean开发校准集选checkpoint与阈值。两种退化已在训练出现，不称未见退化鲁棒性。audit未用于训练或本次调整；种子标准差不是数据集置信区间。',
            '',f'训练样本保留 {len(rows)} 条；分组计数：{dict(Counter(r["role"]for r in rows))}。质量剔除和原因见 qc.json，无替补样本。',
            '', 'raw_temporal 与 aligned_temporal 都是相同CNN+GRU，仅残差对齐不同，使用共同有效mask；frame_mean是逐帧CNN表征均值分类，容量不同，不能当作严格等参数时序对照。',
            '', 'clean为统一4fps、中心2秒、方形中心裁剪128px的开发输入；jpeg70和gaussian5是在空间预处理后生成的图像域压力条件，不是实际平台转码。',
            '', '剩余局限：只有Vript真实源与两种旧生成器；已有历史数据被检查；没有语义匹配、独立来源最终测试和全面内容去重。输入统一不保证彻底消除编码/重采样捷径。',
            '', '已保存逐视频概率、每轮损失、最优checkpoint、模型参数量、训练耗时、峰值显存及加载复核。这里只报告实际训练结果，不说明SNN优于ANN，也不作CCF-A可发表性结论。']
    (run/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    event(run,stage='evaluation_complete',fits=len(trained['results']),prediction_rows=len(records))
    print('\n'.join(lines[:13]),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','cache','train','evaluate']);p.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args();run=a.run_dir.resolve()
    assert run.drive.upper()=='E:' and Path(sys.executable).drive.upper()=='E:'
    assert Path(os.environ.get('TEMP','')).drive.upper()=='E:', 'Use E-drive runtime entry'
    try:
        {'prepare':prepare,'cache':cache,'train':train,'evaluate':evaluate}[a.command](run)
    except Exception as exc:
        if run.exists():event(run,stage=a.command,status='failed',error=repr(exc),traceback=traceback.format_exc())
        raise


if __name__=='__main__':main()
