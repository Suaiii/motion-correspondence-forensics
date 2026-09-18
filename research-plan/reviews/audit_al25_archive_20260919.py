"""Independent exact convolution audit of AL25 archives; no research imports."""
from datetime import datetime,timezone
from fractions import Fraction as F
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path('E:/aNB/TECH/脉冲神经网络')
SOURCE=Path('D:/SUAI/codex/worktree/662f/脉冲神经网络')
RUN=Path('research-runs/algorithm_search_20260918')
OUT=ROOT/'research-plan/reviews/AL25_ARCHIVE_REVIEW_20260919.json'
KERNELS={'laplacian':([[0,1,0],[1,-4,1],[0,1,0]],4),
         'sobel_x':([[-1,0,1],[-2,0,2],[-1,0,1]],8),
         'sobel_y':([[-1,-2,-1],[0,0,0],[1,2,1]],8)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((SOURCE/RUN/name).read_text(encoding='utf-8'))
def git(*args):return subprocess.check_output(['git',*args],cwd=SOURCE)
def flat(x):
    if isinstance(x,list):return [v for child in x for v in flat(child)]
    return [F(x)]
def correlate(field,name):
    values=[]
    for t in range(2):
        for y in range(1,4):
            for x in range(1,4):
                for c in range(3):
                    if name=='identity':values.append(F(field[t][y][x][c]))
                    else:
                        k,den=KERNELS[name]
                        values.append(sum((F(field[t][y+dy-1][x+dx-1][c])*k[dy][dx] for dy in range(3) for dx in range(3)),F(0))/den)
    assert len(values)==54
    return values
def product(a,b):return sum((x*y for x,y in zip(a,b)),F(0))/54

def main():
    assert not OUT.exists()
    manifest=read('AL25_artifact_manifest.json');lock=read('AL25_freeze.json')
    for f in manifest['files']:
        p=SOURCE/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
    for name,want in lock['files'].items():
        assert sha(SOURCE/name)==want and hashlib.sha256(git('show','53cfb0b:'+name)).hexdigest()==want
    for name,want in lock['preserved'].items():assert sha(SOURCE/name)==want
    for name,want in lock['dependency_files'].items():assert sha(Path(name))==want
    subprocess.check_call(['git','merge-base','--is-ancestor','53cfb0b','de3fe06'],cwd=SOURCE)
    data=read('AL25_inputs.json');ev=read('AL25_evidence.json');assert not ev['failures'] and len(ev['cases'])==7
    eta=F(1,10**12);tol=F(1,10**12);checked_arrays=0;normals=[];cancellation=None
    for case,row in zip(data['records'],ev['cases']):
        assert case['id']==row['id'] and all(row['checks'].values())
        r=row['result'];fields=case['fields'];assert r['common_support_elements']==54 and r['common_support_shape']==[2,3,3,3]
        expected_K=[[[[F(fields['d_a'][t][y][x][c])-F(fields['d_b'][t][y][x][c]) for c in range(3)] for x in range(5)] for y in range(5)] for t in range(2)]
        full=fields|{'K':expected_K};energies=[]
        for rec in r['filters']:
            f={name:correlate(arr,rec['filter']) for name,arr in full.items()}
            for name,values in f.items():
                assert flat(rec['filtered_fields'][name])==values
                checked_arrays+=1
            n=product(f['K'],f['K']);ea=product(f['v_a'],f['v_a']);eb=product(f['v_b'],f['v_b'])
            a=product(f['d_a'],f['d_a']);b=product(f['d_b'],f['d_b']);c=product(f['d_a'],f['d_b']);den=ea+eb+eta
            assert n==a+b-2*c
            exact={'N':n,'E_a':ea,'E_b':eb,'D':den,'A':a,'B':b,'C':c}
            if case['mode']=='normal':
                assert all(abs(F(rec[k])-v)<=tol for k,v in exact.items())
                assert abs(F(rec['q_direct'])-n/den)<=tol and abs(F(rec['q_compact_raw'])-n/den)<=tol
            assert (rec['C']<0)==(c<0)
            assert rec['AE_error_bound_status']=='unknown' and rec['source_decision'] is None
            assert rec['q_compact_raw']==rec['z'][0]+rec['z'][1]-2*rec['z'][2]
            energies.append(str(n))
            if case['mode']!='normal' and rec['filter']=='identity':
                assert n==F(1,2**55) and F(rec['N'])==n and rec['q_direct']>0
                cancellation=dict(exact_N=str(n),exact_q=str(n/den),q_direct=rec['q_direct'],q_compact_raw=rec['q_compact_raw'],
                    direct_minus_compact=rec['q_direct']-rec['q_compact_raw'],scope='Observed binary64 operation-order loss, not extra source information')
        normals.append(dict(id=case['id'],exact_N=energies))
    assert checked_arrays==140 and cancellation is not None
    assert len(ev['invalid_inputs'])==3 and all(r['passed'] and r['filter_applications']==0 for r in ev['invalid_inputs'])
    assert ev['calls']=={'readout_attempts':10,'successful_readouts':7,'rejected_inputs':3,'synthetic_field_filter_applications':140,'mean_products':168,'actual_AE_or_probe_calls':0,'AL15_core_calls':0}
    result=dict(task_id='AL25',reviewer='planagent',observed_at=datetime.now(timezone.utc).isoformat(),
        status='pass_fixed_fields_and_declared_tensor_contract',manifest_files_verified=len(manifest['files']),
        preserved_files_verified=len(lock['preserved']),dependency_hashes_verified=len(lock['dependency_files']),
        source_freeze_commit=git('rev-parse','53cfb0b').decode().strip(),source_result_commit=git('rev-parse','de3fe06').decode().strip(),
        exact_signed_arrays_reviewed=checked_arrays,exact_N_by_case=normals,cancellation=cancellation,
        original_readout_calls_replayed=0,review_arithmetic='stdlib Fraction convolution on stored inputs only; no NumPy/candidate imports',
        scientific_breakthrough=False,AE_error_bounds='unknown',
        limitations=['Seven fixed maximum-shape fields only','v_b is zero in every frozen field; nonzero E_b not numerically covered','Mock time slots duplicated; not temporal mechanism evidence','17-frame/BCTHW/media/model pipeline not implemented','Float operation-order differences cannot be counted as algorithmic information gain'],
        audit_source_sha256=sha(Path(__file__)))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
