from fractions import Fraction
from datetime import datetime
import hashlib, json, sys
from pathlib import Path
from core import INVALID, macro
from reference import macro_ref

HERE=Path(__file__).resolve().parent; OUT=HERE/'run_v1'; CFG=HERE/'config.json'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_new(p,obj):
    if p.exists(): raise FileExistsError(p)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def fixture():
    labels={0:1,1:1,2:0,3:0,4:1,5:0}; gen={0:'g1',1:'g1',2:'g1',3:'g1',4:'g2',5:'g2'}
    candidate={0:Fraction(4),1:Fraction(3),2:Fraction(1),3:Fraction(3),4:Fraction(5),5:Fraction(2)}
    baseline={0:Fraction(3),1:Fraction(2),2:Fraction(2),3:Fraction(4),4:Fraction(4),5:Fraction(2)}
    return labels,gen,candidate,baseline
def main():
    if OUT.exists(): raise FileExistsError('run_v1 exists; no overwrite')
    OUT.mkdir(); cfg=json.loads(CFG.read_bytes()); source=[CFG,HERE/'core.py',HERE/'reference.py',HERE/'run_batch.py']
    freeze={'task_id':'AL81','frozen_at':datetime.now().astimezone().isoformat(timespec='milliseconds'),'source_sha256':{p.name:sha(p) for p in source},'config_sha256':sha(CFG)}
    write_new(HERE/'freeze.json',freeze)
    labels,gen,candidate,baseline=fixture(); rows=[];checks=[];failures=[]
    weights_sets={'all_one':{i:Fraction(1) for i in labels},'ancestor_A_double':{0:Fraction(2),1:Fraction(2),2:Fraction(2),3:Fraction(2),4:Fraction(1),5:Fraction(1)},'g2_positive_zero':{0:Fraction(1),1:Fraction(1),2:Fraction(1),3:Fraction(1),4:Fraction(0),5:Fraction(1)},'all_zero':{i:Fraction(0) for i in labels}}
    for name,w in weights_sets.items():
        c=macro(candidate,labels,gen,w); b=macro(baseline,labels,gen,w); cr=macro_ref(candidate,labels,gen,w); br=macro_ref(baseline,labels,gen,w)
        ok=(c is INVALID and cr is None) or (c is not INVALID and c==cr); checks.append({'name':name+'/candidate_reference','passed':ok,'observed':None if c is INVALID else str(c),'reference':None if cr is None else str(cr)})
        ok2=(b is INVALID and br is None) or (b is not INVALID and b==br); checks.append({'name':name+'/baseline_reference','passed':ok2,'observed':None if b is INVALID else str(b),'reference':None if br is None else str(br)})
        if not ok: failures.append(checks[-2]['name'])
        if not ok2: failures.append(checks[-1]['name'])
        rows.append({'weight':name,'candidate':None if c is INVALID else str(c),'baseline':None if b is INVALID else str(b),'invalid':c is INVALID or b is INVALID})
    perm={i:5-i for i in labels}; p2={i:candidate[perm[i]] for i in labels}; l2={i:labels[perm[i]] for i in labels}; g2={i:gen[perm[i]] for i in labels}; checks.append({'name':'identity_reindex','passed':macro(candidate,labels,gen,weights_sets['all_one'])==macro(p2,l2,g2,weights_sets['all_one'])}); checks.append({'name':'all_zero_invalid','passed':macro(candidate,labels,gen,weights_sets['all_zero']) is INVALID})
    evidence={'task_id':'AL81','version':cfg['version'],'freeze_sha256':sha(HERE/'freeze.json'),'source_sha256':freeze['source_sha256'],'rows':rows,'checks':checks,'failures':failures,'software_pass':not failures,'scope':'synthetic point estimand only; no CI/bootstrap/model/media/server/GPU','resources':{'network':0,'models':0,'media':0,'server':0,'gpu':0,'threads':1}}
    write_new(OUT/'evidence.json',evidence); print(json.dumps({'software_pass':evidence['software_pass'],'checks':len(checks),'failures':failures},ensure_ascii=False))
if __name__=='__main__': main()
