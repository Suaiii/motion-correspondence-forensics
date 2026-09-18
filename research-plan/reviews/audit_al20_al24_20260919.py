"""Archive and independent arithmetic review, with no research module imports."""
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib,json,subprocess
from pathlib import Path

ROOT=Path('E:/aNB/TECH/脉冲神经网络')
SOURCE=Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN=Path('research-runs/algorithm_search_20260918')
OUT=ROOT/'research-plan/reviews/AL20_AL24_ARCHIVE_REVIEW_20260919.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((SOURCE/RUN/name).read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=SOURCE)
def vec(values):return tuple(F(x) for x in values)
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))

def main():
    assert not OUT.exists()
    counts={}
    for task in ('AL20','AL24'):
        m=read(task+'_artifact_manifest.json')
        for item in m['files']:
            p=SOURCE/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
        counts[task]=len(m['files'])
        lock=read(task+'_freeze.json')
        for name,want in lock['files'].items():
            assert sha(SOURCE/name)==want
            assert hashlib.sha256(git('show','bef69a4:'+name)).hexdigest()==want
        for name,want in lock.get('preserved',{}).items():assert sha(SOURCE/name)==want
        for name,want in lock.get('dependencies',{}).items():assert sha(Path(name))==want
    subprocess.check_call(['git','merge-base','--is-ancestor','bef69a4','e5ae5e6'],cwd=SOURCE)
    a=read('AL20_trace_audit.json');assert not a['failures'] and len(a['traces'])==3
    archive={r['id']:r['result'] for r in read('AL15_evidence.json')['evaluations']}
    for row in a['traces']:
        r=archive[row['trace_id']];h=F(r['h']);n=r['dimension']
        da=tuple((F(a)-F(b)-F(c)+F(d))/h for a,b,c,d in zip(r['ra_pb'],r['pb'],r['ra'],r['x']))
        db=tuple((F(a)-F(b)-F(c)+F(d))/h for a,b,c,d in zip(r['rb_pa'],r['pa'],r['rb'],r['x']))
        k=tuple(x-y for x,y in zip(da,db))
        assert da==vec(row['d_a']) and db==vec(row['d_b']) and k==vec(r['K'])
        A,B,C=dot(da,da)/n,dot(db,db)/n,dot(da,db)/n
        assert dot(k,k)/n==A+B-2*C
        denominator=(dot(vec(r['v_a']),vec(r['v_a']))+dot(vec(r['v_b']),vec(r['v_b'])))/n+F(r['eta_mean'])
        assert (A+B-2*C)/denominator==F(row['q_exact'])
        assert all(row['checks'].values())
    T=[vec(row) for row in a['T']]
    gram=[[sum((row[i]*row[j] for row in T),F(0)) for j in range(4)] for i in range(4)]
    assert all(gram[i][j]==(6 if i==j else 0) for i in range(4) for j in range(4))
    b=read('AL24_evidence.json');assert not b['failures'] and len(b['graphs'])==6 and len(b['objectives'])==3
    expected={'G1':([['p1','n2'],['p2','n1']],2,F(5,16),1),'G2':([['p1','n1'],['p2','n2']],2,F(0),1),'G3':([['p1','n1'],['p2','n2']],2,F(0),2),'G4':([],0,F(0),1)}
    for row in b['graphs']:
        assert row['passed'] and all(row['checks'].values())
        if row['id'] in expected:
            pairs,cardinality,cost,ties=expected[row['id']];r=row['result']
            assert r['selected_pairs']==pairs and r['cardinality']==cardinality and F(r['total_squared_RMS_cost'])==cost
            assert len(r['all_max_cardinality_min_cost_ties'])==ties
            assert r['q_accessed'] is False and r['standardization_performed'] is False
    diagnostics=[]
    for row in b['objectives']:
        assert row['passed'] and all(row['checks'].values())
        r=row['solver']['solution'];t=D.from_float(r['w'][0]);ds=[D(str(v[0])) for v in row['differences']]
        with localcontext() as ctx:
            ctx.prec=60;lam=D('0.001');n=D(len(ds))
            gradient=-sum((v/(1+(t*v).exp()) for v in ds),D(0))/n+2*lam*t
            hessian=sum((v*v*(t*v).exp()/(1+(t*v).exp())**2 for v in ds),D(0))/n+2*lam
            value=sum(((1+(-t*v).exp()).ln() for v in ds),D(0))/n+lam*t*t
            assert abs(gradient-D.from_float(r['gradient'][0]))<D('1e-12')
            assert abs(hessian-D.from_float(r['hessian'][0][0]))<D('1e-12')
            assert abs(value-D.from_float(r['value']))<D('1e-12')
            assert all(v==0 for v in r['w'][1:])
            diagnostics.append(dict(id=row['id'],solution_first_coordinate=str(t),decimal_gradient=str(gradient),decimal_hessian_00=str(hessian),
                scope='60-digit arithmetic diagnostic of archived candidate points, not optimizer replay or rigorous interval certificate'))
    assert b['calls']=={'matching_queries':6,'scalar_solver_queries':4,'value_gradient_hessian_evaluations':100,'probe':0,'model':0}
    result=dict(tasks=['AL20','AL24'],reviewer='planagent',observed_at=datetime.now(timezone.utc).isoformat(),
        status='pass_in_declared_mathematics_and_small_reference_scope',manifest_files_verified=counts,
        freeze_commit=git('rev-parse','bef69a4').decode().strip(),result_commit=git('rev-parse','e5ae5e6').decode().strip(),
        AL20_exact_trace_checks=3,AL20_cross_terms_in_checked_traces_all_zero=all(F(r['mean_cross_energy'][2])==0 for r in a['traces']),
        T_gram='6I verified exactly',AL24_graphs_and_negative_records=6,AL24_objective_point_diagnostics=diagnostics,
        research_calls_replayed=0,model_or_media_or_gpu=False,scientific_breakthrough=False,
        scope='No additional scientific inputs or fitted models; original traces and matched tiny cases only',
        remaining_limits=['Actual four-filter tensor readout pending','Three AL20 trace checks are not independent real samples; two share the same numerical setup','AL24 covers2x2 graphs and a one-dimensional subproblem, not large matching or general4D fitting','No actual detection benefit or innovative mechanism established'],
        audit_source_sha256=sha(Path(__file__)))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
