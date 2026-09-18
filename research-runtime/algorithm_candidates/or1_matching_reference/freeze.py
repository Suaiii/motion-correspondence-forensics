"""AL24 actual-input freeze; does not import matching or objective implementation."""
from datetime import datetime,timezone
from fractions import Fraction as F
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'research-runs/algorithm_search_20260918'
MAIN=Path('E:/aNB/TECH/脉冲神经网络')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def graph(name,pvalues,nvalues,selected,cost,status='supported_matching',ties=None):
    return dict(id=name,left=[dict(id=f'p{i+1}',b=[value]*12) for i,value in enumerate(pvalues)],
        right=[dict(id=f'n{i+1}',b=[value]*12) for i,value in enumerate(nvalues)],
        expected=dict(status=status,selected=selected,cardinality=len(selected),cost=cost,ties=ties if ties is not None else [selected]))


def main():
    cfg=json.loads((HERE/'config.json').read_text(encoding='utf-8'))
    work=MAIN/'research-plan/AL24_MATCHING_OBJECTIVE_CPU_20260919.md'
    if sha(work)!=cfg['work_order_sha256']:raise ValueError('Canonical AL24 order hash mismatch')
    diagonal=[['p1','n1'],['p2','n2']];cross=[['p1','n2'],['p2','n1']]
    graphs=[graph('G1',['0','-1/4'],['0','1/2'],cross,'5/16'),
        graph('G2',['0','1/4'],['0','1/4'],diagonal,'0'),
        graph('G3',['1','1'],['1','1'],diagonal,'0',ties=[diagonal,cross]),
        graph('G4',['1','1'],['0','0'],[],'0','no_training_support',ties=[[]])]
    duplicate=copy.deepcopy(graphs[2]);duplicate['id']='duplicate_ID';duplicate['left'][1]['id']='p1';duplicate['expected']={'exception':'MatchingInputError'}
    nonfinite=copy.deepcopy(graphs[0]);nonfinite['id']='nonfinite_b';nonfinite['left'][0]['b'][0]={'nonfinite':'nan'};nonfinite['expected']={'exception':'MatchingInputError'}
    q_values={'p1':['3','0','0','0'],'p2':['1','0','0','0'],'n1':['2','0','0','0'],'n2':['0','0','0','0']}
    objectives=[]
    for name,pairs,ds,sign,interval in [('M1',diagonal,['1','1'],'negative',[1,10]),('M2',cross,['3','-1'],'positive',[0,1])]:
        objectives.append(dict(id=name,pairs=pairs,differences=[[d,'0','0','0'] for d in ds],
            expected=dict(gradient_at_one_sign=sign,solution_open_interval=interval),
            relationship_to_G3='selected lexicographic pairing' if name=='M1' else 'predeclared alternate optimal tie; does not replace G3 selection'))
    objectives.append(dict(id='zero_difference',pairs=None,differences=[['0']*4,['0']*4],
        expected=dict(gradient_at_one_sign='positive',solution_exact=0),relationship_to_G3='Separate nonempty zero-difference mathematical control'))
    save(OUT/'AL24_inputs.json',dict(graphs=graphs,invalid_graphs=[duplicate,nonfinite],q_values=q_values,
        objectives=objectives,empty_support_control='Call scalar reference on the empty G4 pair table; expect no_training_support and no weights',
        standardization='Already standardized scalar repeated 12 times; no fitted mean/variance',
        source_labels='No real/generated labels or actual media features; p/n are abstract bipartition IDs'))
    paths=[HERE/'matching.py',HERE/'objective.py',HERE/'config.json',HERE/'freeze.py',HERE/'run.py',OUT/'AL24_inputs.json',OUT/'AL24_protocol.md']
    preserved={}
    for p in OUT.rglob('*'):
        if p.is_file() and p.relative_to(OUT).parts[0].startswith(('AL01','AL04','AL06','AL09','AL12','AL15','AL18')):
            preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    for name in ('or1_cpu','or1_numerics'):
        for p in (ROOT/'research-runtime/algorithm_candidates'/name).glob('*'):
            if p.is_file():preserved[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    import fractions
    deps=[Path(sys.executable),Path(fractions.__file__),Path(getattr(math,'__file__',sys.executable))]
    save(OUT/'AL24_freeze.json',dict(frozen_at=datetime.now(timezone.utc).isoformat(),candidate_calls_before_freeze=0,
        files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths},preserved=preserved,
        dependencies={str(p):sha(p) for p in deps},work_order_sha256=sha(work),
        AL23_review_sha256=sha(MAIN/'research-plan/reviews/AL23_MATCHING_OBJECTIVE_REVIEW_20260919.md'),
        expectations='Analytic matching outputs and derivative signs/brackets fixed before execution; no numerical root evaluated here'))
    print('AL24 frozen: four exact graphs, two input-error cases, three nonempty scalar objectives and empty-support control')

if __name__=='__main__':main()
