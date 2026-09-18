"""Review new accuracy budget without rerunning old or repaired optimizers."""
from datetime import datetime,timezone
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,subprocess
from audit_al27_failure_20260919 import rank,dec

ROOT=Path('E:/aNB/TECH/脉冲神经网络')
SOURCE=Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN=Path('research-runs/algorithm_search_20260918')
OUT=ROOT/'research-plan/reviews/AL30_ARCHIVE_REVIEW_20260919.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((SOURCE/RUN/name).read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=SOURCE)

def main():
    assert not OUT.exists()
    m=read('AL30_artifact_manifest.json');lock=read('AL30_freeze.json');ev=read('AL30_evidence.json');inputs=read('AL30_inputs.json')
    old=read('AL27_evidence.json');old_inputs=read('AL27_inputs.json')
    assert old['gate_result']=='fail' and ev['gate_result']=='pass' and ev['old_AL27_gate_result']=='fail'
    assert ev['gradient_rounding_error_bound'] is None and ev['parameter_error_certified'] is False
    for name,item in m['files'].items():
        p=SOURCE/name;assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes']
        assert hashlib.sha256(git('show','24933a6:'+name)).hexdigest()==item['sha256']
    for name,want in lock['inputs'].items():assert sha(SOURCE/name)==want and hashlib.sha256(git('show','1fa8bb8:'+name)).hexdigest()==want
    for name,want in lock['historical'].items():assert sha(SOURCE/name)==want
    for name,want in lock['dependencies'].items():assert sha(Path(name))==want
    src=SOURCE/'research-runtime/algorithm_candidates'
    assert (src/'or1_head_reference/objective.py').read_bytes()==(src/'or1_head_accuracy_v2/objective.py').read_bytes()
    assert len(ev['checks'])==94 and all(r['passed'] for r in ev['checks']) and not ev['failures']
    for p,q in zip(old_inputs['panels'],inputs['panels'][:3]):
        assert all(p[k]==q[k] for k in ('name','plus','minus')) and q['case_role']=='known_regression'
    assert inputs['panels'][3]['name']=='full_rank_scale' and inputs['panels'][3]['case_role']=='new_prespecified_scale_control'
    transform=[[F(v) for v in row] for row in inputs['transform']];diagnostics=[];grams=0
    for p,stored in zip(inputs['panels'],ev['panels']):
        assert p['name']==stored['name']
        plus=[[F(v) for v in row] for row in p['plus']];minus=[[F(v) for v in row] for row in p['minus']]
        for row in plus+minus:
            for j in range(0,12,3):a,b,c=row[j:j+3];assert a>=0 and b>=0 and a*b>=c*c;grams+=1
        dz=[[a-b for a,b in zip(x,y)] for x,y in zip(plus,minus)]
        dq=[[sum((row[k]*transform[k][j] for k in range(12)),F(0)) for j in range(4)] for row in dz]
        assert (rank(dz),rank(dq))==((12,4) if p['name'].startswith('full_rank') else (4,4))
        if p['name']=='full_rank_scale':
            assert dz==[[F(i==j,8) for j in range(12)] for i in range(12)]
        for name,data in [('candidate',dq),('free',dz)]:
            head=stored['heads'][name];contract=head['stopping_contract'];lam=F(1,1000 if name=='candidate' else 6000)
            mu=2*lam;tau=min(F(1,10**10),mu*F(1,10**9)/2)
            assert F(contract['mu_exact'])==mu and F(contract['tau_exact'])==tau
            assert contract['tau_float']==min(1e-10,(2*float(lam))*1e-9/2)
            assert contract['gradient_rounding_error_bound'] is None and contract['parameter_error_certified'] is False
            term=head['evaluations'][head['terminal_evaluation_id']];assert head['status']=='gradient_l2_tolerance' and term['gradient_l2']<=contract['tau_float']
            with localcontext() as ctx:
                ctx.prec=60;x=[D.from_float(v) for v in term['parameters']];rows=[[dec(v) for v in row] for row in data];n=D(len(rows));reg=dec(lam)
                margins=[sum((a*b for a,b in zip(row,x)),D(0)) for row in rows];sig=[D(1)/(1+v.exp()) for v in margins]
                grad=[-sum((row[j]*s for row,s in zip(rows,sig)),D(0))/n+2*reg*x[j] for j in range(len(x))]
                value=sum(((1+(-v).exp()).ln() for v in margins),D(0))/n+reg*sum((v*v for v in x),D(0))
                assert max(abs(g-D.from_float(a)) for g,a in zip(grad,term['gradient']))<D('1e-12')
                assert abs(value-D.from_float(term['objective']))<D('1e-12')
                if stored.get('scalar_reference'):
                    root=stored['scalar_reference']['root']
                    expected=([root]*4 if name=='candidate' else [root,root,-2*root]*4) if p['name']=='aligned' else ([0.0]*4 if name=='candidate' else [root]*12)
                    assert max(abs(a-b) for a,b in zip(term['parameters'],expected))<=1e-9
                diagnostics.append(dict(panel=p['name'],head=name,gradient_l2_decimal=str(sum((v*v for v in grad),D(0)).sqrt()),
                    objective_decimal=str(value),scope='High-precision arithmetic diagnostic of archived points, not a certified bound or optimizer rerun'))
    assert grams==288
    old_panel=next(p for p in old['panels'] if p['name']=='full_rank')['heads']['free']
    new_panel=next(p for p in ev['panels'] if p['name']=='full_rank')['heads']['free']
    assert old_panel['evaluations'][:5]==new_panel['evaluations'][:5]
    assert old_panel['iterations']==4 and new_panel['iterations']==5
    assert old_panel['evaluations'][4]['gradient_l2']>new_panel['stopping_contract']['tau_float']
    output=dict(task_id='AL30',reviewed_at=datetime.now(timezone.utc).isoformat(),reviewer='planagent',gate_result='pass',old_AL27_gate_result='fail',
        manifest_files_verified=len(m['files']),historical_files_verified=len(lock['historical']),dependencies_verified=len(lock['dependencies']),
        solver_math_source_byte_identical=True,known_regression_panels=3,new_prespecified_panels=1,exact_Gram_checks=grams,archived_checks=94,
        independent_terminal_diagnostics=diagnostics,original_prefix_evaluations_unchanged=5,
        extra_step_cause='Unified new stopping criterion; old step4 residual exceeds new threshold',
        solver_or_model_replayed=False,parameter_error_certified=False,scientific_breakthrough=False,
        freeze_commit=git('rev-parse','1fa8bb8').decode().strip(),result_commit=git('rev-parse','24933a6').decode().strip(),
        audit_source_sha256=sha(Path(__file__)))
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('gate_result','old_AL27_gate_result','manifest_files_verified','historical_files_verified','known_regression_panels','new_prespecified_panels','exact_Gram_checks','original_prefix_evaluations_unchanged')},indent=2))

if __name__=='__main__':main()
