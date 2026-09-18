"""AL18 archive arithmetic review plus three targeted v2 interface checks."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path('E:/aNB/TECH/脉冲神经网络')
SOURCE=Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN=Path('research-runs/algorithm_search_20260918')
OUT=ROOT/'research-plan/reviews/AL18_ARCHIVE_REVIEW_20260919.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((SOURCE/RUN/name).read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=SOURCE)
def vec(values):return [F(v) for v in values]
def scalar_bound(payload,name):return F(payload['bounds'][name]['value'])
def within(x,interval):return F(interval[0])<=x<=F(interval[1])

def main():
    assert not OUT.exists()
    manifest=read('AL18_artifact_manifest.json');lock=read('AL18_freeze.json');v2lock=read('AL18_v2_interface_freeze.json')
    for item in manifest['files']:
        p=SOURCE/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    for frozen,commit in [(lock,'8ff3400'),(v2lock,'4a771f7')]:
        for path,want in frozen['files'].items():
            assert sha(SOURCE/path)==want
            assert hashlib.sha256(git('show',commit+':'+path)).hexdigest()==want
    for path,want in lock['preserved'].items():assert sha(SOURCE/path)==want
    for path,want in lock['dependencies'].items():assert sha(Path(path))==want
    for a,b in [('8ff3400','0546f63'),('0546f63','4a771f7'),('4a771f7','1e823fd')]:
        subprocess.check_call(['git','merge-base','--is-ancestor',a,b],cwd=SOURCE)
    evidence=read('AL18_evidence.json');inputs=read('AL18_inputs.json')['records']
    assert not evidence['failures'] and len(evidence['records'])==len(inputs)==147
    families=Counter();n2_calls=0
    for inp,row in zip(inputs,evidence['records']):
        assert inp['id']==row['id'] and row['passed'] and all(row['checks'].values())
        family=inp['family'];families[family]+=1;r=row['result'];payload=inp['payload'];h=F(inp['nominal_h'])
        assert r['status']==inp['expected']['status'] and r['origin_decision'] is None
        if family in (1,2,3):
            if family in (1,2):
                ab,ba=vec(payload['hat_ab']),vec(payload['hat_ba'])
                exact=[(a-b)/h**2 for a,b in zip(ab,ba)]
                bound=(scalar_bound(payload,'delta_ab')+scalar_bound(payload,'delta_ba'))/h**2+scalar_bound(payload,'rho_K')
                true_ab,true_ba=map(vec,inp['true_endpoints']);truth=[(a-b)/h**2 for a,b in zip(true_ab,true_ba)]
            else:
                obs={k:vec(v) for k,v in row['observations'].items()}
                exact=[(a-b)/h**2 for a,b in zip(obs['uab'],obs['uba'])]
                bound=4*F(inp['epsilon'])/h;truth=[F(0),F(0)]
                assert len(row['mock_probe_ledger'])==4
                for call in row['mock_probe_ledger']:
                    x,y,error=vec(call['input']),vec(call['output']),vec(call['additive_error'])
                    assert vec(call['ideal_identity_output'])==x
                    assert all(a+b==c for a,b,c in zip(x,error,y))
                    assert sum(x*x for x in error)<=F(call['bound'])**2
                    n2_calls+=1
                for dest,left,right in [('pa','x','ra0'),('pb','x','rb0'),('uab','pb','rab'),('uba','pa','rba')]:
                    assert obs[dest]==[(1-h)*a+h*b for a,b in zip(obs[left],obs[right])]
            assert vec(r['K_hat'])==exact and F(r['B_K'])==bound
            error=sum((a-b)**2 for a,b in zip(exact,truth));assert error<=bound**2
            assert row['bound_attained']==(error==bound**2)
        elif family==4:
            n4=row['N4'];assert F(n4['B_N'])==F(3,4096)
            assert vec(n4['numerator_interval'])==[F(0),F(1,1024)] and within(F(0),r['ratio_interval'])
        elif family==5:
            hn,hd=F(payload['hat_n']),F(payload['hat_d']);bn,bd=scalar_bound(payload,'B_N'),scalar_bound(payload,'B_D')
            lower=hd-bd;expected=bn/lower+abs(hn)*bd/(hd*lower)+scalar_bound(payload,'rho_q')
            assert F(r['B_q'])==expected
            truth=F(row['ratio_corner']['n'])/F(row['ratio_corner']['d'])
            assert abs(F(r['q_hat'])-truth)<=expected and within(truth,r['ratio_interval'])
            assert F(r['score']['B_score'])==expected
        elif family==6:
            if r['status']=='denominator_lower_not_positive':assert not r['interval_valid'] and 'ratio_interval' not in r
            else:assert vec(r['ratio_interval'])==[F(0),F(0)] and F(r['denominator_residual_energy_lower'])==0
        elif family==7:
            assert not r['interval_valid']
        elif family==8:
            assert F(row['repeat_gap'])==0 and r['status']=='uncertified_bound' and 'B_K' not in r
            assert F(row['known_bias_contract']['B_K'])==F(1,1024)/h**2
            assert within(F(0),row['known_bias_contract']['coordinate_intervals'][0])
    assert n2_calls==192
    assert evidence['calls']['public_contract_queries']==156 and evidence['calls']['repeat_endpoint_readouts']==6
    states=dict(Counter(row['result']['status'] for row in evidence['records']));assert states==evidence['state_counts']
    v2=read('AL18_v2_interface_evidence.json');assert not v2['failures'] and len(v2['records'])==24
    assert all(row['passed'] for row in v2['records'])
    assert v2['calls']['v2_public_contract_queries']==24 and not v2['calls']['original_147_replayed']
    source=SOURCE/'research-runtime/algorithm_candidates/or1_numerics/bounds_v2.py';source_sha=sha(source)
    assert source_sha=='7a16a0f3335d57ff22d1409c0a3cc77273a05f8fc76d5a558d6b044bf764c5a5'
    sys.path.insert(0,str(source.parent))
    spec=importlib.util.spec_from_file_location('al18_review_v2',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    valid=lambda v:dict(value=v,basis='analytic_mock')
    p1=dict(hat_n='1/4',hat_d='1/2',hat_q=float('nan'),bounds=dict(B_N=valid('0'),B_D=None,rho_q=valid('0'),rho_s=valid('0')))
    check1=mod.evaluate('N5',p1,'1/8','1e-12');assert check1['status']=='invalid_input' and not check1['interval_valid']
    obs={k:['0'] for k in ('x','ra0','rb0','pa','pb','rab','rba','uab','uba')}
    b={k:valid('1' if k in ('L_a','L_b') else '0') for k in ('eps_a0','eps_b0','eps_ab','eps_ba','L_a','L_b','rho_a','rho_b','rho_ab','rho_ba','rho_K')}
    p2=dict(observations=obs,bounds=b,hat_k=[float('nan')]);check2=mod.evaluate('N2',p2,'1/8','1e-12')
    assert check2['status']=='invalid_input' and not check2['interval_valid']
    p2['hat_k']=['1/64'];b['rho_K']=valid('1/64');check3=mod.evaluate('N2',p2,'1/8','1e-12')
    assert check3['K_hat']==(F(1,64),) and check3['coordinate_intervals']==[(F(0),F(1,32))]
    assert sha(source)==source_sha
    result=dict(task_id='AL18',reviewer='planagent',observed_at=datetime.now(timezone.utc).isoformat(),
        status='pass_scoped_archive_and_targeted_interface_review',manifest_files_verified=len(manifest['files']),
        preserved_files_verified=len(lock['preserved']),dependencies_verified=len(lock['dependencies']),
        v1_records_reviewed=147,v1_status_counts=states,v1_R_mocks=192,v1_endpoint_readouts=6,v1_contract_queries=156,
        v2_archived_targeted_queries=24,v2_full_v1_replay=False,reviewer_new_v2_queries=3,reviewer_previous_v1_queries=2,
        targeted_checks=dict(N5_nonfinite_before_unknown=check1['status'],N2_nonfinite_not_ignored=check2['status'],N2_supplied_nonzero_consumed=True),
        source_result_commit=git('rev-parse','1e823fd').decode().strip(),source_v1_sha256=sha(source.parent/'bounds.py'),source_v2_sha256=source_sha,
        audit_script_sha256=sha(Path(__file__)),scientific_breakthrough=False,
        limits=['No formal scientific replication','No real AE error or Lipschitz bound measured','v2 accepted for24 targeted regressions plus3 reviewer probes, not unrestricted API verification','Non-square norm path not exercised by fixed suite'])
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
