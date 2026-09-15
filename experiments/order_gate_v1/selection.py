"""Source-prefix-disjoint expansion excluding the first pilot's source groups."""
import random
import re
from collections import defaultdict
from pathlib import Path


def prefix(path):
    return re.sub(r'-Scene-\d+$', '', Path(path).stem)


def select(rows, prior, seed):
    old_real = {prefix(r['path']) for r in prior if r['label_fake']==0}
    old_fake = {r['path'] for r in prior if r['label_fake']==1}
    real=defaultdict(set);fakes={'opensora':set(),'t2vz':set()}
    for r in rows:
        key=prefix(r['real_file'])
        if key not in old_real:real[key].add(r['real_file'])
        if r['fake_source'] in fakes and r['fake_file'] not in old_fake:
            fakes[r['fake_source']].add(r['fake_file'])
    rng=random.Random(seed);keys=sorted(real);rng.shuffle(keys)
    if len(keys)<300:raise ValueError('Insufficient fresh real source prefixes')
    result=[]
    real_roles=['fit']*180+['calibration']*60+['audit']*60
    for key,role in zip(keys[:300],real_roles):
        result.append({'path':rng.choice(sorted(real[key])),'label_fake':0,'source':'vript','group_id':'vript:'+key,'role':role})
    for generator,pool in fakes.items():
        pool=sorted(pool);rng.shuffle(pool)
        if len(pool)<150:raise ValueError('Insufficient fresh fake files')
        roles=['fit']*90+['calibration']*30+['audit']*30
        for path,role in zip(pool[:150],roles):
            result.append({'path':path,'label_fake':1,'source':generator,'group_id':generator+':'+Path(path).stem,'role':role})
    for i,r in enumerate(result):r['sample_id']=f'X{i:04d}'
    assert len({r['group_id']for r in result})==len(result)
    assert len({r['path']for r in result})==len(result)
    return result
