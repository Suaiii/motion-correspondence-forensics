import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import balanced_accuracy_score
from .common import read,write,sha,object_hash,safe_path
from .pipeline import verify_lock,checked_index,metrics
from .controls import represent


def probes(run,cache_root):
    cfg,records=verify_lock(run);index=checked_index(run,cache_root)
    selected=[r for r in records if r['sample_id'] in index['retained'] and r['role']!='final_audit']
    y=np.array([r['label_fake'] for r in selected]);fit=[i for i,r in enumerate(selected) if r['role']=='fit']
    calibration=[i for i,r in enumerate(selected) if r['role']=='calibration']
    features={};names=['nuisance']+cfg['arms']
    for c in cfg['conditions']:
        features[c]={name:[] for name in names}
        for r in selected:
            item=index['items'][r['sample_id']+'/'+c]
            with np.load(safe_path(cache_root,item['path']),allow_pickle=False) as a:
                it=iter(a['flow']);views,q=represent(a['frames'],cfg['controls'],lambda *_:next(it))
            values=np.array([[v[k] for k in sorted(v)] for v in q])
            features[c]['nuisance'].append(np.concatenate([values.mean(0),values.std(0)]))
            for arm in cfg['arms']:
                x=views[arm];ax=np.abs(x)
                features[c][arm].append([ax.mean(),ax.mean((1,2,3)).std(),np.sqrt((x*x).mean()),np.quantile(ax,.95)])
        features[c]={k:np.asarray(v,dtype=np.float64) for k,v in features[c].items()}
    predictions=[];models={};scores=[]
    for name in names:
        scaler=StandardScaler().fit(features['clean'][name][fit])
        clf=LogisticRegression(C=1,max_iter=1000,random_state=17).fit(scaler.transform(features['clean'][name][fit]),y[fit])
        cp=clf.predict_proba(scaler.transform(features['clean'][name][calibration]))[:,1]
        cy=y[calibration];grid=np.linspace(.01,.99,99);grid_scores=[balanced_accuracy_score(cy,cp>=t) for t in grid]
        tau=min((float(t) for t,s in zip(grid,grid_scores) if abs(s-max(grid_scores))<1e-12),key=lambda t:(abs(t-.5),t))
        tau_fpr=float(np.nextafter(np.quantile(cp[cy==0],.99,method='higher'),np.inf))
        models[name]={'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coef':clf.coef_.tolist(),'intercept':clf.intercept_.tolist(),
            'threshold':tau,'threshold_calibration_fpr01':tau_fpr}
        for c in cfg['conditions']:
            p=clf.predict_proba(scaler.transform(features[c][name]))[:,1]
            for role in ('calibration','dev_audit','ood_dev'):
                ix=[i for i,r in enumerate(selected) if r['role']==role]
                if ix:scores.append({'probe':name,'condition':c,'role':role,**metrics([selected[i] for i in ix],p[ix],tau,tau_fpr)})
            for r,x,v in zip(selected,features[c][name],p):predictions.append({'sample_id':r['sample_id'],'probe':name,'condition':c,'features':x.tolist(),'prob_fake':float(v)})
    write(Path(run)/'probes.json',{'models':models,'predictions':predictions,'metrics':scores,'fit_only_scaling':True,'scope':'development diagnostic; nuisance probe combines mask, motion, phase and texture'})


def cluster_strata(records):
    parent=list(range(len(records)));lookup={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,r in enumerate(records):
        for field in ('source_group','reference_group','prompt_group'):
            if r.get(field):
                key=('prompt' if field=='prompt_group' else 'entity',r[field])
                if key in lookup:parent[find(i)]=find(lookup[key])
                else:lookup[key]=i
    groups={}
    for i in range(len(records)):groups.setdefault(find(i),[]).append(i)
    strata={}
    for g in groups.values():
        signature=tuple(sorted({(records[i]['source'],records[i]['label_fake']) for i in g}))
        strata.setdefault(signature,[]).append(g)
    return list(strata.values())


def paired_comparison(records,predictions,a,b,conditions,seeds,replicates=2000):
    records=sorted(records,key=lambda r:r['sample_id']);ids=[r['sample_id'] for r in records]
    lookup={(r['sample_id'],r['arm'],r['condition'],r['seed']):r['prob_fake'] for r in predictions}
    if len(lookup)!=len(predictions):raise ValueError('Duplicate prediction identities')
    def vector(arm,c,seed=None):
        return np.array([np.mean([lookup[(sid,arm,c,s)] for s in (seeds if seed is None else [seed])]) for sid in ids])
    values={(arm,c):vector(arm,c) for arm in (a,b) for c in conditions}
    def macro(ix,p):
        rr=[records[i] for i in ix]
        return metrics(rr,p[ix],.5,.5)['macro_auc']
    def delta(ix):return float(np.mean([macro(ix,values[a,c])-macro(ix,values[b,c]) for c in conditions]))
    whole=np.arange(len(records));observed=delta(whole);strata=cluster_strata(records);rng=np.random.default_rng(20260910)
    draws=[]
    for _ in range(replicates):
        ix=np.concatenate([g[j] for g in strata for j in rng.integers(0,len(g),len(g))]);draws.append(delta(ix))
    seed_deltas=[float(np.mean([macro(whole,vector(a,c,s))-macro(whole,vector(b,c,s)) for c in conditions])) for s in seeds]
    return {'a':a,'b':b,'delta':observed,'ci95':np.quantile(draws,[.025,.975]).tolist(),'seed_deltas':seed_deltas,
        'conditions':conditions,'bootstrap_replicates':replicates,'bootstrap_unit':'connected source/reference/prompt cluster; source-label signature stratified'}


def decide(run):
    cfg,rows=verify_lock(run)
    if cfg['controls']['support']!='interior' or cfg['stage']=='smoke':raise ValueError('Only new-data interior research can pass mechanism gate')
    dev=read(Path(run)/'evaluation_dev_audit.json');ood=read(Path(run)/'evaluation_ood_dev.json')
    comparisons=[]
    for role,ev in [('dev_audit',dev),('ood_dev',ood)]:
        ids={r['sample_id'] for r in ev['predictions']};selected=[r for r in rows if r['sample_id'] in ids]
        for control in ('wrong','fractional'):
            c=paired_comparison(selected,ev['predictions'],'correct',control,cfg['conditions'],cfg['seeds'],cfg['bootstrap_replicates'])
            c['role']=role;comparisons.append(c)
    required_positive=int(np.ceil(len(cfg['seeds'])*cfg.get('positive_seed_fraction',2/3)))
    local=all(c['delta']>=.02 and c['ci95'][0]>0 and sum(d>0 for d in c['seed_deltas'])>=required_positive for c in comparisons[:2])
    outside=all(c['delta']>0 for c in comparisons[2:])
    write(Path(run)/'mechanism_gate.json',{'passed':local and outside,'local_passed':local,'ood_positive':outside,
        'required_positive_seeds':required_positive,
        'scope':'development','comparisons':comparisons,'configuration_sha256':sha(Path(run)/'config.json'),
        'evidence':{'development':sha(Path(run)/'evaluation_dev_audit.json'),'ood':sha(Path(run)/'evaluation_ood_dev.json')},
        'next':'minimum_method' if local and outside else 'one_selective_consistency_diagnostic_only'})


def verify_predictions(run):
    cfg,rows=verify_lock(run);byid={r['sample_id']:r for r in rows};groups=0
    for path in Path(run).glob('evaluation_*.json'):
        ev=read(path)
        if ev['config_hash']!=sha(Path(run)/'config.json') or ev['manifest_hash']!=sha(Path(run)/'manifest.json'):raise ValueError('Evaluation provenance differs')
        for item in ev['metrics']:
            p=[r for r in ev['predictions'] if all(r[k]==item[k] for k in ('arm','seed','condition'))]
            if len({r['sample_id'] for r in p})!=len(p):raise ValueError('Duplicate predictions')
            rr=[byid[r['sample_id']] for r in p]
            for r,expected in zip(p,rr):
                if r['label_fake']!=expected['label_fake'] or expected['role']!=ev['role']:raise ValueError('Label/role changed')
            summary=read(Path(run)/'training'/f"{item['arm']}_{item['seed']}"/'summary.json')
            actual=metrics(rr,[r['prob_fake'] for r in p],summary['threshold'],summary['threshold_calibration_fpr01'])
            for k in ('auc','macro_auc','worst_generator_auc','bacc','ece_10_equal_width'):
                if abs(actual[k]-item[k])>1e-12:raise ValueError('Metric mismatch '+k)
            y=np.array([r['label_fake'] for r in p]);v=np.array([r['prob_fake'] for r in p]);a=v[y==1,None];b=v[y==0][None,:]
            if abs(float(((a>b)+.5*(a==b)).mean())-item['auc'])>1e-12:raise ValueError('Pairwise AUROC mismatch')
            groups+=1
    if not groups:raise ValueError('No evaluated groups')
    receipt={'verdict':'passed','metric_groups':groups,'method':'saved-prediction and pairwise metric recomputation',
        'independent_scientific_review':False,'checkpoint_inference_replayed':False,'code_hash':sha(__file__)}
    write(Path(run)/'verification.json',receipt)
    return receipt
