"""Mechanical verification by primary implementer, not independent scientific review."""
import json
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from run_alignment import RUN, PRIOR, ARMS, verify, engine, VideoBaseline


def main():
    cfg=verify(RUN)
    assert engine.digest(RUN/'manifest.json')==engine.digest(PRIOR/'manifest.json')
    receipts=engine.read(RUN/'artifact_hashes.json')
    for path,h in receipts.items():assert engine.digest(RUN/path)==h,path
    rows=engine.read(RUN/'manifest.json');train=engine.read(RUN/'training_complete.json');ev=engine.read(RUN/'evaluation.json');pred=engine.read(RUN/'predictions.json')
    assert len(train['results'])==15
    assert len(ev['results'])==30
    assert len(pred)==30*117
    assert all(r['params']==49601 for r in train['results'])
    y=np.array([r['label_fake'] for r in rows]);audit=np.array([i for i,r in enumerate(rows) if r['role']=='audit'])
    val=np.array([i for i,r in enumerate(rows) if r['role']=='calibration'])
    ids=[rows[i]['sample_id'] for i in audit]
    device=torch.device('cuda:0');torch.set_num_threads(4)
    maxerror=0.;recomputed=0
    for fit in train['results']:
        kind,seed=fit['kind'],fit['seed'];folder=RUN/'training'/f'{kind}_seed{seed}'
        assert engine.digest(folder/'best.pt')==fit['checkpoint_sha256']
        history=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
        assert len(history)==20
        assert min(history,key=lambda r:r['calibration_bce'])['epoch']==fit['best_epoch']
        net=VideoBaseline('aligned_bag').to(device);net.load_state_dict(torch.load(folder/'best.pt',map_location=device,weights_only=True))
        vp=engine.predict(net,engine.load_array(RUN,'clean',kind),val,device,8)
        grid=np.linspace(.01,.99,99);scores=[balanced_accuracy_score(y[val],vp>=t) for t in grid]
        threshold=min((float(t) for t,s in zip(grid,scores) if abs(s-max(scores))<1e-12),key=lambda t:(abs(t-.5),t))
        for c in cfg['conditions']:
            p=engine.predict(net,engine.load_array(RUN,c,kind),audit,device,8)
            saved={r['sample_id']:r for r in pred if r['kind']==kind and r['seed']==seed and r['condition']==c}
            assert set(saved)==set(ids)
            expected=np.array([saved[s]['prob_fake'] for s in ids])
            error=float(np.max(np.abs(p-expected)));maxerror=max(maxerror,error)
            assert error<1e-6
            record=next(r for r in ev['results'] if r['kind']==kind and r['seed']==seed and r['condition']==c)
            assert abs(record['threshold']-threshold)<1e-12
            assert abs(roc_auc_score(y[audit],p)-record['auc'])<1e-12
            assert abs(balanced_accuracy_score(y[audit],p>=threshold)-record['balanced_accuracy'])<1e-12
            # Independent AUROC implementation with explicit ties.
            a=p[y[audit]==1,None];b=p[y[audit]==0][None,:]
            pair_auc=float(((a>b)+.5*(a==b)).mean())
            assert abs(pair_auc-record['auc'])<1e-12
            recomputed+=1
        del net
        print('VERIFIED',kind,seed,flush=True)
    probes=engine.read(RUN/'probes.json');probe_error=0.
    for name,model in probes['models'].items():
        for c in cfg['conditions']:
            records=[r for r in probes['predictions'] if r['probe']==name and r['condition']==c]
            # The extractor uses float64 mask features, but float32 residual
            # statistics. StandardScaler preserves input dtype and rounds after
            # each in-place subtraction/division; replay both rounding points.
            x=np.array([r['features'] for r in records],dtype=np.float64 if name=='mask' else np.float32)
            z=x.copy();z-=np.array(model['scaler_mean']);z/=np.array(model['scaler_scale'])
            p=1/(1+np.exp(-(z@np.array(model['coef'])[0]+model['intercept'][0])))
            error=float(np.max(np.abs(p-np.array([r['prob_fake'] for r in records]))));probe_error=max(probe_error,error)
            assert error<1e-12,(name,c,error)
            for role in ('fit','calibration','audit'):
                ix=[i for i,r in enumerate(records) if r['role']==role]
                score=roc_auc_score([records[i]['label_fake'] for i in ix],p[ix])
                saved=next(r for r in probes['metrics'] if r['probe']==name and r['condition']==c and r['role']==role)
                assert abs(score-saved['auc'])<1e-12
    decision=engine.read(RUN/'decision.json')
    sr={r['sample_id']:r for r in rows if r['role']=='audit'};ordered=sorted(sr)
    labels=np.array([sr[s]['label_fake'] for s in ordered])
    strata=[np.array([i for i,s in enumerate(ordered) if sr[s]['source']==name]) for name in sorted({r['source'] for r in sr.values()})]
    for comp in decision['comparisons']:
        probs=[]
        for arm in (comp['a'],comp['b']):
            probs.append(np.array([np.mean([r['prob_fake'] for r in pred if r['sample_id']==s and r['kind']==arm and r['condition']==comp['condition']]) for s in ordered]))
        def auc_direct(p,ix):
            a=p[ix[labels[ix]==1],None];b=p[ix[labels[ix]==0]][None,:]
            return float(((a>b)+.5*(a==b)).mean())
        rng=np.random.default_rng(cfg['decision_gate']['bootstrap']['seed']);diff=[]
        for _ in range(cfg['decision_gate']['bootstrap']['replicates']):
            ix=np.concatenate([rng.choice(g,len(g),replace=True) for g in strata])
            diff.append(auc_direct(probs[0],ix)-auc_direct(probs[1],ix))
        np.testing.assert_allclose(np.quantile(diff,[.025,.975]),comp['paired_stratified_percentile95'],atol=1e-12,rtol=0)
        assert abs(auc_direct(probs[0],np.arange(len(ordered)))-auc_direct(probs[1],np.arange(len(ordered)))-comp['delta'])<1e-12
    checks=[r['delta']>=.02 and r['paired_stratified_percentile95'][0]>0 and sum(d>0 for d in r['seed_deltas'])>=2 for r in decision['comparisons'][:2]]
    assert checks==decision['primary_checks'] and all(checks)==decision['local_gate_pass']
    engine.dump(RUN/'verification.json',{'verdict':'passed','review_type':'primary_implementer_mechanical_recomputation','independent_scientific_review':False,'neural_metric_groups':recomputed,'checkpoint_reload_max_error':maxerror,'probe_probability_max_error':probe_error,'all_artifact_hashes_checked':len(receipts),'same_manifest_as_prior':True,'all_15_checkpoint_epochs_and_thresholds_reselected_from_calibration_only':True,'pairwise_auc_checked':True,'bootstrap_intervals_recomputed_by_pairwise_auc':len(decision['comparisons']),'decision_checks_recomputed':True,'verification_code_sha256':engine.digest(__file__)})
    print('VERIFICATION PASSED',recomputed,'groups, max error',maxerror,flush=True)


if __name__=='__main__':main()
