"""Read-only AL27 integrity and stopping-accuracy review; no optimizer imports."""
from datetime import datetime,timezone
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path('E:/aNB/TECH/脉冲神经网络')
SOURCE=Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN=Path('research-runs/algorithm_search_20260918')
OUT=ROOT/'research-plan/reviews/AL27_FAILURE_REVIEW_20260919.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((SOURCE/RUN/name).read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=SOURCE)
def dec(x):
    f=F(x);return D(f.numerator)/D(f.denominator)
def rank(a):
    m=[row[:] for row in a];i=0
    for j in range(len(m[0])):
        piv=next((k for k in range(i,len(m)) if m[k][j]),None)
        if piv is None:continue
        m[i],m[piv]=m[piv],m[i];v=m[i][j];m[i]=[x/v for x in m[i]]
        for k in range(len(m)):
            if k!=i:
                v=m[k][j];m[k]=[x-v*y for x,y in zip(m[k],m[i])]
        i+=1
        if i==len(m):break
    return i

def main():
    assert not OUT.exists()
    m=read('AL27_artifact_manifest.json');lock=read('AL27_freeze.json');ev=read('AL27_evidence.json');inputs=read('AL27_inputs.json')
    for name,entry in m['files'].items():
        p=SOURCE/name;assert sha(p)==entry['sha256'] and p.stat().st_size==entry['bytes']
        assert hashlib.sha256(git('show','505b001:'+name)).hexdigest()==entry['sha256']
    for name,want in lock['inputs'].items():assert sha(SOURCE/name)==want and hashlib.sha256(git('show','dc78269:'+name)).hexdigest()==want
    for name,want in lock['historical'].items():assert sha(SOURCE/name)==want
    for name,want in lock['dependencies'].items():assert sha(Path(name))==want
    assert ev['gate_result']=='fail' and len(ev['checks'])==69 and sum(bool(r['passed']) for r in ev['checks'])==68
    assert len(ev['failures'])==1 and ev['failures'][0]['check']=='full_rank/free/scalar_vector_agreement'
    transform=[[F(v) for v in row] for row in inputs['transform']];diags=[];gram_count=0
    for panel,stored in zip(inputs['panels'],ev['panels']):
        assert panel['name']==stored['name'];plus=[[F(v) for v in row] for row in panel['plus']];minus=[[F(v) for v in row] for row in panel['minus']]
        for row in plus+minus:
            for j in range(0,12,3):
                a,b,c=row[j:j+3];assert a>=0 and b>=0 and a*b>=c*c;gram_count+=1
        dz=[[a-b for a,b in zip(x,y)] for x,y in zip(plus,minus)]
        dq=[[sum((row[k]*transform[k][j] for k in range(12)),F(0)) for j in range(4)] for row in dz]
        expected_rank=(12,4) if panel['name']=='full_rank' else (4,4);assert (rank(dz),rank(dq))==expected_rank
        for name,rows in [('candidate',dq),('free',dz)]:
            result=stored['heads'][name];terminal=result['evaluations'][result['terminal_evaluation_id']]
            with localcontext() as ctx:
                ctx.prec=60;lam=D(1)/(D(1000) if name=='candidate' else D(6000));n=D(len(rows))
                x=[D.from_float(v) for v in terminal['parameters']];data=[[dec(v) for v in row] for row in rows]
                margins=[sum((a*b for a,b in zip(row,x)),D(0)) for row in data]
                weights=[D(1)/(D(1)+v.exp()) for v in margins]
                grad=[-sum((row[j]*s for row,s in zip(data,weights)),D(0))/n+2*lam*x[j] for j in range(len(x))]
                objective=sum(((D(1)+(-v).exp()).ln() for v in margins),D(0))/n+lam*sum((v*v for v in x),D(0))
                assert max(abs(v-D.from_float(a)) for v,a in zip(grad,terminal['gradient']))<D('1e-12')
                assert abs(objective-D.from_float(terminal['objective']))<D('1e-12')
                initial_exact=[-sum((row[j] for row in rows),F(0))/(2*len(rows)) for j in range(len(x))]
                first=result['evaluations'][0]
                assert all(abs(dec(v)-D.from_float(a))<D('1e-15') for v,a in zip(initial_exact,first['gradient']))
                diags.append(dict(panel=panel['name'],head=name,rank=rank(rows),terminal_gradient_l2_decimal=str(sum((v*v for v in grad),D(0)).sqrt()),
                                  objective_decimal=str(objective),initial_gradient_exact=[str(v) for v in initial_exact]))
    assert gram_count==192
    panel=next(p for p in ev['panels'] if p['name']=='full_rank');head=panel['heads']['free'];term=head['evaluations'][head['terminal_evaluation_id']]
    reference=panel['scalar_reference']['root'];error=max(abs(v-reference) for v in term['parameters'])
    assert term['gradient_l2']<=1e-10 and error>1e-9 and error==ev['failures'][0]['details']['max_abs_error']
    with localcontext() as ctx:
        ctx.prec=60;b=D.from_float(reference);scalar_derivative=-D(1)/4/(1+(b/4).exp())+b/250
        assert abs(scalar_derivative)<D('1e-14')
    result=dict(task_id='AL27',reviewed_at=datetime.now(timezone.utc).isoformat(),execution_status='done',gate_result='fail',reviewer='planagent',
        manifest_files_verified=len(m['files']),historical_files_verified=len(lock['historical']),dependencies_verified=len(lock['dependencies']),
        source_freeze_commit=git('rev-parse','dc78269').decode().strip(),source_result_commit=git('rev-parse','505b001').decode().strip(),
        checks_total=69,checks_passed=68,gram_conditions_exactly_checked=gram_count,independent_terminal_diagnostics=diags,
        failure=dict(coordinate_error=error,coordinate_limit=1e-9,gradient_l2=term['gradient_l2'],gradient_limit=1e-10,
                     head_mu_exact='1/3000',conditional_bound_from_original_gradient_limit='3/10000000',
                     precise_scalar_reference_derivative=str(scalar_derivative),
                     interpretation='Frozen gradient stopping threshold is not sufficient to guarantee frozen coordinate accuracy; execution followed stopping rule'),
        parameter_derived_future_gradient_budget=dict(target_parameter_error='1/1000000000',
            rule='min(1e-10, mu*target/2); half reserved for unknown gradient computation error if a formal guarantee is desired',
            candidate='1/1000000000000',free='1/6000000000000',formal_float_gradient_error_bound='unknown'),
        optimizer_or_objective_module_calls=0,scientific_OR1_refutation=False,scientific_breakthrough=False,
        audit_source_sha256=sha(Path(__file__)))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('gate_result','manifest_files_verified','historical_files_verified','checks_passed','failure','parameter_derived_future_gradient_budget')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
