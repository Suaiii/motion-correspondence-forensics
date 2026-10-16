"""Portable manifests: identity and ancestry constraints precede feature extraction."""
import collections
import re
from .common import object_hash, safe_path, sha

ROLES={'fit','calibration','dev_audit','ood_dev','final_audit','profile'}
SCOPES={'development','final','historical','synthetic'}
FIELDS={'sample_id','path','sha256','label_fake','source','generator','task','source_group',
        'reference_group','prompt_group','ancestry_status','role','scope','dataset_revision','license'}


def audit(records,data_root=None,check_files=False):
    errors=[];seen={};hash_roles={};groups={};generators={};counts=collections.Counter()
    for r in records:
        sid=r.get('sample_id','?');missing=FIELDS-set(r)
        if missing:errors.append(f'{sid}: missing {sorted(missing)}');continue
        if sid in seen:errors.append(f'{sid}: duplicate sample ID')
        seen[sid]=r
        if r['role'] not in ROLES or r['scope'] not in SCOPES:errors.append(f'{sid}: invalid role/scope')
        if r['label_fake'] not in (0,1):errors.append(f'{sid}: invalid label')
        if not re.fullmatch('[0-9a-f]{64}',r['sha256']):errors.append(f'{sid}: invalid SHA256')
        if not all(isinstance(r[k],str) and r[k] for k in ('source','dataset_revision','license','source_group')):
            errors.append(f'{sid}: missing provenance')
        if r['ancestry_status'] not in ('verified','unknown'):errors.append(f'{sid}: ancestry status')
        if r['label_fake'] and (not r['generator'] or r['task'] not in ('T2V','I2V','V2V')):
            errors.append(f'{sid}: fake requires generator and task')
        if not r['label_fake'] and (r['generator'] is not None or r['task']!='real'):
            errors.append(f'{sid}: real metadata inconsistent')
        if r['scope']=='final' and r['role']!='final_audit':errors.append(f'{sid}: final samples cannot be used for development')
        if r['role']=='final_audit' and r['scope']!='final':errors.append(f'{sid}: final role requires final scope')
        if r['scope']=='historical' and r['role']!='profile':errors.append(f'{sid}: historical inputs are profile-only')
        if r['scope'] in ('development','final') and r['ancestry_status']!='verified':
            errors.append(f'{sid}: unknown ancestry cannot enter a confirmation-grade manifest')
        if r['sha256'] in hash_roles:errors.append(f'{sid}: duplicate bytes, including same-role duplicates')
        hash_roles[r['sha256']]=r['role']
        for field in ('source_group','reference_group','prompt_group'):
            if r[field]:groups.setdefault(('prompt' if field=='prompt_group' else 'entity',r[field]),set()).add(r['role'])
        if r['label_fake']:generators.setdefault(r['generator'],set()).add(r['role'])
        counts[f"{r['role']}/{r['source']}/{r['label_fake']}"]+=1
        try:
            path=safe_path(data_root or '.',r['path'])
            if check_files and (not path.is_file() or sha(path)!=r['sha256']):errors.append(f'{sid}: file absent or changed')
        except ValueError as e:errors.append(f'{sid}: {e}')
    for group,roles in groups.items():
        if len(roles)>1:errors.append(f'ancestry leakage {group}: {sorted(roles)}')
    for gen,roles in generators.items():
        if 'ood_dev' in roles and roles-{'ood_dev'}:errors.append(f'OOD generator reused: {gen}')
        if 'final_audit' in roles and roles-{'final_audit'}:errors.append(f'final generator reused: {gen}')
    return {'valid':not errors,'errors':errors,'counts':dict(counts),'n':len(records),
            'manifest_hash':object_hash(sorted(records,key=lambda r:r.get('sample_id','')))}


def require_valid(records,root=None,check_files=False):
    result=audit(records,root,check_files)
    if not result['valid']:raise ValueError('\n'.join(result['errors']))
    return result


def split_groups(records,seed=20260910):
    """Connected ancestry components; greedy 60/20/20 within source/label.

    Unknown ancestry stays blocked; supplied final/OOD/historical records are not reassigned.
    This creates development splits only, never invents generator holdouts.
    """
    parent=list(range(len(records)))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    lookup={}
    for i,r in enumerate(records):
        for field in ('sha256','source_group','reference_group','prompt_group'):
            if r.get(field):
                key=('entity' if field in ('source_group','reference_group') else field,r[field])
                if key in lookup:parent[find(i)]=find(lookup[key])
                else:lookup[key]=i
    components={}
    for i,r in enumerate(records):components.setdefault(find(i),[]).append(dict(r))
    output=[];assigned=collections.Counter();totals=collections.Counter((r['source'],r['label_fake']) for r in records if r['scope']=='development' and r['role']!='ood_dev')
    for group in sorted(components.values(),key=lambda g:object_hash([seed,sorted(r['sample_id'] for r in g)])):
        fixed=[r for r in group if r['scope']!='development' or r['role']=='ood_dev']
        if fixed:
            if len(fixed)!=len(group):raise ValueError('Development ancestry overlaps reserved data')
            output.extend(group);continue
        counts=collections.Counter((r['source'],r['label_fake']) for r in group)
        targets={'fit':.6,'calibration':.2,'dev_audit':.2}
        role=min(targets,key=lambda role:sum((assigned[(role,key)]+n)/(max(1,totals[key]*targets[role])) for key,n in counts.items()))
        for r in group:r['role']=role;output.append(r)
        for key,n in counts.items():assigned[(role,key)]+=n
    return sorted(output,key=lambda r:r['sample_id'])
