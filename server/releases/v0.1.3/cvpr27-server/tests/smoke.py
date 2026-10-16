"""End-to-end synthetic video test and exact epoch-boundary resume check."""
import copy
import sys
from pathlib import Path
import cv2
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics import pipeline,statistics
from forensics import materialize
from forensics.common import read,write,sha
from test_runtime import record


def main(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False);data=root/'data';data.mkdir();cache=root/'cache'
    cfg=read(Path(__file__).resolve().parents[1]/'configs/mechanism.json')
    cfg.update(stage='smoke',seeds=[17],arms=['correct'],workers=0,cpu_threads=2,minimum_per_class=2,minimum_retained_total=0,bootstrap_replicates=20)
    cfg['sampling']['size']=64;cfg['conditions']=['clean','h264_23'];cfg['training'].update(epochs=2,batch_size=2)
    rr=[]
    for i in range(18):
        role=['fit','calibration','dev_audit'][i//6];label=i%2;path=data/f'{i}.avi'
        writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'FFV1'),8,(64,64))
        if not writer.isOpened():raise RuntimeError('FFV1 fixture writer unavailable')
        base=np.random.default_rng(i).integers(30,225,(64,64,3),dtype=np.uint8)
        for t in range(16):writer.write(np.roll(base,t if label else 2*t,axis=1))
        writer.release();r=record(i+1,role,label,'synthetic');r.update(path=path.name,sha256=sha(path));rr.append(r)
    baseline=root/'uninterrupted';resumed=root/'resumed'
    pipeline.prepare(baseline,cfg,rr);pipeline.extract(baseline,data,cache)
    index=pipeline.checked_index(baseline,cache)
    before=pipeline.Inputs(rr,index,cache,'correct',cfg)[0][0]
    materialize.materialize(baseline,cache,'correct',workers=2)
    after=pipeline.Inputs(rr,pipeline.checked_index(baseline,cache),cache,'correct',cfg)[0][0]
    if not torch.equal(before,after):raise AssertionError('Materialization changed model inputs')
    pipeline.train(baseline,cache,'cpu','correct',17)
    pipeline.evaluate(baseline,cache,'cpu');statistics.probes(baseline,cache);statistics.verify_predictions(baseline)
    pipeline.prepare(resumed,cfg,rr);pipeline.extract(resumed,data,cache)
    pipeline.train(resumed,cache,'cpu','correct',17,epochs_this_call=1)
    if (resumed/'training/correct_17/summary.json').exists():raise AssertionError('Paused fit marked complete')
    pipeline.train(resumed,cache,'cpu','correct',17)
    first=torch.load(baseline/'training/correct_17/epoch_002.pt',weights_only=False,map_location='cpu')
    second=torch.load(resumed/'training/correct_17/epoch_002.pt',weights_only=False,map_location='cpu')
    for key in first['model']:
        if not torch.equal(first['model'][key],second['model'][key]):raise AssertionError('Resume changed model '+key)
    pipeline.evaluate(resumed,cache,'cpu');statistics.verify_predictions(resumed)
    a=read(baseline/'evaluation_dev_audit.json')['predictions'];b=read(resumed/'evaluation_dev_audit.json')['predictions']
    if a!=b:raise AssertionError('Resume predictions differ')
    materialize.purge(baseline,cache,'correct')
    restored=pipeline.Inputs(rr,pipeline.checked_index(baseline,cache),cache,'correct',cfg)[0][0]
    if not torch.equal(before,restored):raise AssertionError('Purging derived cache changed fallback inputs')
    try:pipeline.evaluate(resumed,cache,'cpu',role='final_audit')
    except FileNotFoundError:pass
    else:raise AssertionError('Final data accessed without release')
    write(root/'validation.json',{'passed':True,'scope':'synthetic software validation only','videos':18,
        'full_video_h264_before_sampling':True,'epochs':2,'resume_model_bitwise_equal':True,
        'resume_predictions_equal':True,'metric_groups':2,'final_release_required':True,
        'parallel_materialized_inputs_bitwise_equal':True,'derived_cache_purge_preserves_original_inputs':True})
    print('SYNTHETIC END-TO-END AND RESUME PASSED',flush=True)


if __name__=='__main__':main(sys.argv[1])
