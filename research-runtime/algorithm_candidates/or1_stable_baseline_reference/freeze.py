"""AL32 archival selection and exact config only, before the single numeric batch."""
import copy
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'research-runs/algorithm_search_20260918'
SOURCE=Path(__file__).resolve().parent
MAIN=Path('E:/aNB/TECH/脉冲神经网络')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def save(name,data):
    with (OUT/('AL32_'+name+'.json')).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n')


def main():
    order=MAIN/'research-plan/AL32_STABLE_BASELINE_INTEGRATION_CPU_20260919.md'
    assert sha(order)=='86ee01efe1b273a71f1c80f2a0e007a82f684f8cbfdb5c04141d64ed130a693d'
    previous=load('AL30_freeze.json')
    assert load('AL27_evidence.json')['gate_result']=='fail'
    assert load('AL30_evidence.json')['gate_result']=='pass'
    for category in ['inputs','dependencies','historical']:
        for p,digest in previous[category].items():
            assert sha(ROOT/p)==digest,(category,p)
    archive=load('AL25_evidence.json')
    field_ids=['positive_inner','negative_inner','near_cancellation']
    fields=[]
    for case_id in field_ids:
        case=next(c for c in archive['cases'] if c['id']==case_id)['result']
        selected=dict(id=case_id,evidence_role='archived_synthetic_filtered_field',
            common_support_shape=case['common_support_shape'],eta_float=case['eta_float'],
            q4_direct=case['q4_direct'],q4_compact_raw=case['q4_compact_raw'],z12=case['z12'],filters=[])
        for old_filter in case['filters']:
            item={k:copy.deepcopy(v) for k,v in old_filter.items() if k!='filtered_fields'}
            item['filtered_fields']={k:copy.deepcopy(old_filter['filtered_fields'][k]) for k in ['d_a','d_b','K']}
            item['expected_q_hex']=old_filter['q_direct'].hex()
            selected['filters'].append(item)
        fields.append(selected)
    old_inputs=load('AL30_inputs.json')
    panels=[copy.deepcopy(p) for p in old_inputs['panels'] if p['name'] in ['aligned','full_rank','symmetric']]
    assert [p['name'] for p in panels]==['aligned','full_rank','symmetric']
    assert all(p['case_role']=='known_regression' for p in panels)
    save('inputs',dict(field_source=dict(path=(OUT/'AL25_evidence.json').relative_to(ROOT).as_posix(),
                                       sha256=sha(OUT/'AL25_evidence.json'),case_ids=field_ids),
        panel_source=dict(path=(OUT/'AL30_inputs.json').relative_to(ROOT).as_posix(),
                          sha256=sha(OUT/'AL30_inputs.json'),names=[p['name'] for p in panels]),
        archived_fields=fields,abstract_panels=panels))
    m=[[1,1,2],[1,1,-2],[1,-1,0]]
    inverse=[['1/4','1/4','1/2'],['1/4','1/4','-1/2'],['1/4','-1/4','0']]
    g=[[6,-2,0],[-2,6,0],[0,0,2]]
    block=[[m[i%3][j%3] if i//3==j//3 else 0 for j in range(12)] for i in range(12)]
    metric=[[g[i%3][j%3] if i//3==j//3 else 0 for j in range(12)] for i in range(12)]
    w=['1','-2','1/2','0']
    gamma=[v for x in w for v in ['0',x,'0']]
    beta=[str(v*F(x)) for x in w for v in [1,1,-2]]
    save('config',dict(dtype='float64',native_threads=2,max_dimension=12,max_pairs=12,
        max_array_bytes=1048576,max_archived_filter_elements=54,tolerance=1e-12,
        filter_order=['identity','laplacian','sobel_x','sobel_y'],M=m,M_inverse=inverse,
        expected_MMt=g,B=block,expected_BBt=metric,weights=w,
        points=[dict(name='zero',gamma=['0']*12,expected_beta=['0']*12,expected_penalty='0'),
                dict(name='embedded_w',gamma=gamma,expected_beta=beta,expected_penalty='21/4000')],
        candidate_lambda='1/1000',free_lambda='1/6000',
        expected_old_gate=dict(AL27='fail',AL30='pass'),
        field_rK_policy='literal archived q_direct; float.hex equality',
        field_sum_policy='stored Hda plus stored Hdb, no refiltering',
        strict_numeric_certificate=False,real_AE_error_bound=None))
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in SOURCE.glob('*.py')}
    for suffix in ['inputs.json','config.json','protocol.md']:
        p=OUT/('AL32_'+suffix); inputs[p.relative_to(ROOT).as_posix()]=sha(p)
    historical=dict(previous['historical'])
    for p in list(OUT.glob('AL30_*'))+list((SOURCE.parent/'or1_head_accuracy_v2').glob('*.py')):
        if p.is_file(): historical[p.relative_to(ROOT).as_posix()]=sha(p)
    upstream=['research-plan/WORK_PLAN.md','research-plan/task-hermes/project.json',
        'research-plan/AL32_STABLE_BASELINE_INTEGRATION_CPU_20260919.md',
        'research-plan/reviews/AL29_STABLE_BASELINE_REVIEW_20260919.md',
        'research-plan/reviews/AL30_REVIEW_20260919.md']
    save('freeze',dict(created_at=datetime.now(timezone.utc).isoformat(),
        parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        inputs=inputs,dependencies=previous['dependencies'],historical=historical,
        upstream_at_freeze={str(MAIN/p):sha(MAIN/p) for p in upstream},
        new_numeric_arithmetic_or_objective_run=False,
        note='Commit every input/source and this receipt before new stable-coordinate arithmetic.'))


if __name__=='__main__':
    main()
