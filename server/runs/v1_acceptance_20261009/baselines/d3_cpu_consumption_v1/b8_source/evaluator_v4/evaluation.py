"""C3 validated, explicitly registered evaluation v2; no data/science release."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import argparse,json,random
from collections import defaultdict
from admission import validate_rows,admission_metadata
import arithmetic_v1 as arithmetic
from support import validate_support,_bind_rows_admitted,_planned_admitted
IDENTITY=arithmetic.IDENTITY

def read_rows(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def auroc(rows):validate_rows(rows);return arithmetic.auroc(rows)
def average_precision(rows):validate_rows(rows);return arithmetic.average_precision(rows)
def generator_macro(rows):validate_rows(rows);return arithmetic.generator_macro(rows)
def calibrate(rows,target_fpr=.01):return arithmetic.calibrate(rows,target_fpr)
def split_violations(rows):validate_rows(rows);return arithmetic.split_violations(rows)

def cluster_interval(rows,repeats=2000,seed=20261009,support=None,expected_support_sha256=None):
    validate_rows(rows)
    if support is not None:
        validate_support(support,expected_support_sha256);_bind_rows_admitted(rows,support)
    return _cluster_admitted(rows,repeats,seed,support)

def _cluster_admitted(rows,repeats,seed,support):
    synthetic=any(r['fixture'] or r['ancestry_status']=='fixture' for r in rows) or bool(support and support['fixture'])
    registered=support is not None and support['status']=='frozen'
    identity={'fixture':synthetic,'registration':'frozen_expected_support' if registered else 'draft' if support else 'unregistered_descriptive','certified':False,'scientific_gate_passed':False}
    if support is not None and (support['status']=='draft' or _planned_admitted(rows,support)['status']!='complete'):return identity|{'status':'pending','reason':'incomplete_or_draft_base_support','ci95':None}
    if not rows:return identity|{'status':'no_observations','ci95':None}
    if any(r['ancestry_status'] not in {'verified','fixture'} for r in rows):return identity|{'status':'pending','reason':'unverified_ancestor_closure'}
    source_by_cluster=defaultdict(set)
    for r in rows:source_by_cluster[r['ancestor_id']].add(r['source_family'])
    if any(len(v)>1 for v in source_by_cluster.values()):return identity|{'status':'pending','reason':'cross_source_cluster_needs_global_resampling_contract'}
    strata=defaultdict(lambda:defaultdict(list))
    for r in rows:strata[r['source_family']][r['ancestor_id']].append(r)
    if repeats<1:return identity|{'status':'not_run'}
    expected=sorted({r['generator_family'] for r in rows if r['label_fake']==1})
    expected_cells={(r['generator_family'],r['source_family']) for r in rows if r['label_fake']==1}
    rng=random.Random(seed);draws=[];invalid=0
    for _ in range(repeats):
        sample=[]
        for source in sorted(strata):
            keys=sorted(strata[source])
            for key in rng.choices(keys,k=len(keys)):sample.extend(strata[source][key])
        if registered:
            outcome=_planned_admitted(sample,support,require_all_rows=False);x=outcome['main_generator_macro']['value']
            if x is None:invalid+=1;continue
        else:
            observed={(r['generator_family'],r['source_family']) for r in sample if r['label_fake']==1}
            if observed!=expected_cells:invalid+=1;continue
            outcome=arithmetic.generator_macro(sample);x=outcome['auroc']['value']
            if x is None or [g['generator_family'] for g in outcome['generators']]!=expected:invalid+=1;continue
        draws.append(x)
    draws.sort()
    def quantile(p):
        q=(len(draws)-1)*p;i=int(q);j=min(i+1,len(draws)-1)
        return draws[i]*(j-q)+draws[j]*(q-i) if i!=j else draws[i]
    return identity|{'status':'descriptive_fixture' if synthetic else 'computed_not_independent_review' if registered else 'unregistered_descriptive','n_clusters':len(source_by_cluster),'repeats':repeats,'invalid_repeats':invalid,'invalid_mass':invalid/repeats,'ci95':[quantile(.025),quantile(.975)] if draws and invalid==0 else None,'valid_only_ci95':[quantile(.025),quantile(.975)] if draws else None,'seed':seed,'reason':'invalid resamples suppress primary interval' if invalid else 'source-stratified ancestor-cluster percentile interval; all shared real outputs follow one draw'}

def evaluate(rows,lock=None,bootstrap=2000,support=None,expected_support_sha256=None):
    validate_rows(rows)
    if not rows and support is None:raise ValueError('empty_predictions_requires_expected_support_lock')
    if any(r['role'] in {'fit','calibration','final_confirmation'} for r in rows):raise ValueError('evaluation_requires_audit_role_final_remains_sealed')
    if rows and len({tuple(r[k] for k in IDENTITY) for r in rows})!=1:raise ValueError('evaluate_one_method_seed_track_processing_at_a_time')
    if rows and (len({r['role'] for r in rows})!=1 or len({r.get('cohort_id') for r in rows})!=1 or len({r.get('protocol_sha256') for r in rows})!=1):raise ValueError('evaluate_one_cohort_protocol_at_a_time')
    if len({r['input_sha256'] for r in rows})!=len(rows):raise ValueError('duplicate_bytes_in_evaluation_unit')
    if lock:arithmetic.check_threshold_lock(rows,lock)
    if support is not None:validate_support(support,expected_support_sha256);_bind_rows_admitted(rows,support)
    registration='unregistered_descriptive' if support is None else 'draft_unregistered_descriptive' if support['status']=='draft' else 'observed_subset_description_registered_inventory'
    observed={'registration':registration,'pooled_auroc':arithmetic.auroc(rows),'pooled_ap':arithmetic.average_precision(rows),'pooled_operating_point':arithmetic.operating_point(rows,lock),'generator_macro':arithmetic.generator_macro(rows),'ancestor_cluster_interval':_cluster_admitted(rows,bootstrap,20261009,None)}
    main=_planned_admitted(rows,support)
    main['ancestor_cluster_interval']=_cluster_admitted(rows,bootstrap,20261009,support) if support else {'status':'unregistered','ci95':None,'reason':'no_expected_support_lock','certified':False}
    groups=defaultdict(list)
    for r in rows:groups[(r['generator_family'],r['source_family'],r['processing_id'])].append(r)
    cells=[{'generator_family':g,'source_family':s,'processing_id':p,'n':len(rs),'n_fake':sum(r['label_fake'] for r in rs),'auroc':arithmetic.auroc(rs),'operating_point':arithmetic.operating_point(rs,lock)} for (g,s,p),rs in sorted(groups.items())]
    identity={k:rows[0][k] for k in IDENTITY} if rows else support.get('identity')
    cohort_id=rows[0].get('cohort_id') if rows else support.get('cohort',{}).get('cohort_id')
    protocol_sha256=rows[0].get('protocol_sha256') if rows else support.get('identity',{}).get('protocol_sha256')
    role=rows[0]['role'] if rows else support.get('cohort',{}).get('role')
    synthetic=any(r['fixture'] or r['ancestry_status']=='fixture' for r in rows) or bool(support and support['fixture'])
    admission=admission_metadata(rows);admission['synthetic_identity']=synthetic
    return {'version':'baseline_metrics/2.0','identity':identity,'cohort_id':cohort_id,'protocol_sha256':protocol_sha256,'role':role,'admission':admission,'n_videos':len(rows),'n_unique_bytes':len({r['input_sha256'] for r in rows}),'n_ancestor_clusters':len({r['ancestor_id'] for r in rows}),'positive_class':'fake','observed_support':observed,'planned_support':main,'single_class_cells':cells,'prediction_rows_sha256':arithmetic.digest(rows),'threshold_sha256':lock['sha256'] if lock else None,'fixture':synthetic,'scientific_gate_passed':False,'five_seed_interval_is_ancestor_ci':False}

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('calibrate');c.add_argument('--predictions',required=True);c.add_argument('--target-fpr',type=float,default=.01);c.add_argument('--output',required=True)
    e=sub.add_parser('evaluate');e.add_argument('--predictions',required=True);e.add_argument('--threshold-lock');e.add_argument('--bootstrap',type=int,default=2000);e.add_argument('--support-lock');e.add_argument('--support-sha256');e.add_argument('--output',required=True)
    args=p.parse_args()
    try:
        rows=read_rows(args.predictions)
        if args.command=='calibrate':result=calibrate(rows,args.target_fpr)
        else:
            if bool(args.support_lock)!=bool(args.support_sha256):raise ValueError('support_lock_and_external_sha256_required_together')
            lock=json.loads(Path(args.threshold_lock).read_text(encoding='utf-8-sig')) if args.threshold_lock else None
            support=json.loads(Path(args.support_lock).read_text(encoding='utf-8-sig')) if args.support_lock else None
            result=evaluate(rows,lock,args.bootstrap,support,args.support_sha256)
        out=Path(args.output)
        with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
        print(json.dumps({'output':str(out),'scientific_gate_passed':False}))
    except (ValueError,KeyError,TypeError) as error:
        print(json.dumps({'status':'rejected','error_type':type(error).__name__,'error':str(error)},ensure_ascii=False),file=sys.stderr);raise SystemExit(2)
if __name__=='__main__':main()
