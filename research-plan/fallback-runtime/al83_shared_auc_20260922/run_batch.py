from __future__ import annotations
from fractions import Fraction
from datetime import datetime
import hashlib,json,sys
from pathlib import Path
from core import INVALID,validate_scores,validate_weights,paired_summary
from reference import summary as reference_summary

HERE=Path(__file__).resolve().parent;OUT=HERE/'run_v5';CFG=HERE/'config.json'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_new(p,obj):
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def fixture():
    records=[
      {'sample_id':'p0','ancestor_id':'A','label':1,'generator':'g1'},
      {'sample_id':'p1','ancestor_id':'B','label':1,'generator':'g1'},
      {'sample_id':'n2','ancestor_id':'A','label':0,'generator':None},
      {'sample_id':'n3','ancestor_id':'B','label':0,'generator':None},
      {'sample_id':'p4','ancestor_id':'C','label':1,'generator':'g2'},
      {'sample_id':'n5','ancestor_id':'D','label':0,'generator':None},]
    base={0:Fraction(4),1:Fraction(3),2:Fraction(1),3:Fraction(3),4:Fraction(5),5:Fraction(2)}
    candidate={};baseline={}
    names=['p0','p1','n2','n3','p4','n5']
    for method,target in [('candidate',candidate),('baseline',baseline)]:
      for tag,shift in [('diagnostic_a',Fraction(0)),('diagnostic_b',Fraction(1,2))]:
       target[tag]={names[i]:base[i]+(shift if method=='candidate' else 0) for i in range(6)}
    return records,candidate,baseline
def main():
    if OUT.exists():raise FileExistsError('run_v5 exists; preserve')
    OUT.mkdir();cfg=json.loads(CFG.read_bytes());records,candidate,baseline=fixture();scores={'candidate':candidate,'baseline':baseline}
    freeze={'task_id':'AL83','version':'v5','frozen_at':datetime.now().astimezone().isoformat(timespec='milliseconds'),'source_sha256':{p.name:sha(p) for p in [CFG,HERE/'core.py',HERE/'reference.py',HERE/'run_batch.py']},'config_sha256':sha(CFG),'records_hash':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),'previous_failed_runs':['run_v1','run_v2','run_v3','run_v4']};write_new(HERE/'freeze_v5.json',freeze)
    checks=[];fails=[];rows=[]
    def check(name,ok,**detail):checks.append({'name':name,'passed':bool(ok),**detail});fails.extend([] if ok else [name])
    schemes={'all_one':{r['sample_id']:1 for r in records},'ancestor_A_double':{r['sample_id']:(2 if r['ancestor_id']=='A' else 1) for r in records},'ancestor_C_zero':{r['sample_id']:(0 if r['ancestor_id']=='C' else 1) for r in records},'all_zero':{r['sample_id']:0 for r in records}}
    for name,weights in schemes.items():
      try:
       validate_weights(records,weights);validate_scores(records,scores,cfg['methods'],cfg['score_tags']); actual,deltas=paired_summary(records,scores,weights,cfg['methods'],cfg['score_tags'],cfg['generators']); oracle,od=reference_summary(records,scores,weights,cfg['methods'],cfg['score_tags'],cfg['generators']);ok=actual==oracle and deltas==od;check(name+'/reference',ok,actual=str(actual),oracle=str(oracle),deltas=[None if x is None else str(x) for x in deltas]);rows.append({'scheme':name,'actual':str(actual),'oracle':str(oracle),'deltas':[None if x is None else str(x) for x in deltas]})
      except Exception as exc:check(name+'/execution',False,error=repr(exc))
    # Fixed expected all-one results and W^2-visible numerator witness.
    all_one=schemes['all_one'];actual,deltas=paired_summary(records,scores,all_one,cfg['methods'],cfg['score_tags'],cfg['generators']);check('all_one_expected_tag_a',str(deltas[0])=='7/24',observed=None if deltas[0] is None else str(deltas[0]));check('all_one_expected_tag_b',str(deltas[1])=='0',observed=None if deltas[1] is None else str(deltas[1]));check('shared_ancestor_weight_changes_pair_denominator',rows[1]['deltas']!=rows[0]['deltas'])
    # Invalid full group is null rather than dropped.
    broken={method:{tag:dict(vals) for tag,vals in table.items()} for method,table in scores.items()};del broken['candidate']['diagnostic_a']['p4'];
    try:
      validate_scores(records,broken,cfg['methods'],cfg['score_tags']);check('missing_score_rejected',False)
    except ValueError as exc:check('missing_score_rejected',str(exc)=='score_keys',error=str(exc))
    # Invalid generator support should be null, not a narrowed macro.
    rec_invalid=[r for r in records if r['generator']!='g2' or r['label']==0];m,dlt=paired_summary(rec_invalid,{'candidate':candidate,'baseline':baseline},all_one,cfg['methods'],cfg['score_tags'],cfg['generators']);check('missing_generator_group_is_invalid',all(v['macro'] is INVALID for v in m['candidate'].values()))
    evidence={'task_id':'AL83','version':cfg['version'],'freeze_sha256':sha(HERE/'freeze_v5.json'),'source_sha256':freeze['source_sha256'],'record_hash':freeze['records_hash'],'rows':rows,'checks':checks,'failures':fails,'software_pass':not fails,'previous_failed_runs':['run_v1','run_v2','run_v3','run_v4'],'scope':'synthetic shared-negative ancestor-weighted point estimand only; no CI/bootstrap/model/media/server/GPU','resources':{'threads':1,'network':0,'media':0,'server':0,'gpu':0}}
    write_new(OUT/'evidence.json',evidence);print(json.dumps({'software_pass':evidence['software_pass'],'checks':len(checks),'failures':fails},ensure_ascii=False));return 0 if evidence['software_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
