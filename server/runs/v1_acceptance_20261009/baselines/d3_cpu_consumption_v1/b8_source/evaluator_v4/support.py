"""Score-free frozen row/cell support, fixed shared real pools and coverage."""
from collections import defaultdict
from admission import frozen_validator
import arithmetic_v1 as A

def validate_support(s,expected_sha256):
    if expected_sha256 is None:raise ValueError('expected_support_sha256_required')
    v=frozen_validator('support_schema_v2.json');errors=list(v.iter_errors(s))
    if errors:raise ValueError('support_schema_validation_failed:'+errors[0].message)
    content=dict(s);declared=content.pop('sha256')
    if A.digest(content)!=declared or declared!=expected_sha256:raise ValueError('support_lock_hash_changed')
    if s['status']=='draft':return s
    if s['cohort']['role'] not in ('development_audit','held_generator_audit','external_audit'):raise ValueError('support_requires_audit_cohort_final_sealed')
    ids=[r['sample_id'] for r in s['sample_manifest']]
    if len(set(ids))!=len(ids):raise ValueError('duplicate_support_sample_id')
    manifest={r['sample_id']:r for r in s['sample_manifest']};owners={};used=set();cells=set();cell_ids=set()
    if len({r['input_sha256'] for r in manifest.values()})!=len(manifest):raise ValueError('duplicate_support_input_bytes')
    for r in manifest.values():
        if r['fixture']!=s['fixture'] or (r['ancestry_status']=='fixture' and not r['fixture']):raise ValueError('support_fixture_identity_conflict')
        if (r['label_fake']==0)!=(r['generator_family']=='real'):raise ValueError('support_label_generator_conflict')
    for poolid,p in s['real_pools'].items():
        for sample in p['sample_ids']:
            if sample not in manifest:raise ValueError('support_real_pool_unmaterialized')
            r=manifest[sample]
            if r['label_fake']!=0 or r['source_family']!=p['source_family']:raise ValueError('support_real_pool_identity_conflict')
            if sample in owners:raise ValueError('real_sample_multiple_pool_ids_use_one_shared_pool')
            owners[sample]=poolid;used.add(sample)
    fake_owner={};used_pools=set()
    for c in s['cells']:
        key=(c['generator_family'],c['source_family'])
        if key in cells or c['cell_id'] in cell_ids:raise ValueError('duplicate_support_cell')
        cells.add(key);cell_ids.add(c['cell_id'])
        p=s['real_pools'].get(c['real_pool_id'])
        if p is None or p['source_family']!=c['source_family']:raise ValueError('support_same_source_real_pool_required')
        used_pools.add(c['real_pool_id'])
        for sample in c['fake_sample_ids']:
            if sample not in manifest:raise ValueError('support_fake_ids_unmaterialized')
            r=manifest[sample]
            if r['label_fake']!=1 or (r['generator_family'],r['source_family'])!=key:raise ValueError('support_fake_cell_identity_conflict')
            if sample in fake_owner:raise ValueError('fake_sample_multiple_cells')
            fake_owner[sample]=c['cell_id'];used.add(sample)
    if used!=set(manifest) or used_pools!=set(s['real_pools']):raise ValueError('support_unused_manifest_or_real_pool')
    excluded={e['sample_id'] for e in s['exclusions']}
    if len(excluded)!=len(s['exclusions']) or excluded&set(manifest):raise ValueError('support_exclusion_conflict')
    return s

def _bind_rows_admitted(rows,s):
    if s['status']=='draft':
        if any(r['fixture']!=s['fixture'] for r in rows):raise ValueError('support_prediction_fixture_identity_mismatch')
        return
    manifest={r['sample_id']:r for r in s['sample_manifest']}
    for r in rows:
        for k,v in s['identity'].items():
            if r.get(k)!=v:raise ValueError('support_prediction_identity_mismatch:'+k)
        if r['role']!=s['cohort']['role'] or r.get('cohort_id')!=s['cohort']['cohort_id'] or r['evaluation_unit']!=s['cohort']['evaluation_unit']:raise ValueError('support_prediction_cohort_mismatch')
        if r['fixture']!=s['fixture']:raise ValueError('support_prediction_fixture_identity_mismatch')
        if r['sample_id'] in manifest:
            m=manifest[r['sample_id']]
            for k,v in m.items():
                if r.get(k)!=v:raise ValueError('support_prediction_sample_identity_mismatch:'+k)

def _planned_admitted(rows,s,require_all_rows=True):
    """Internal admitted multiset kernel; bootstrap skips original row completeness."""
    if s is None:return {'status':'unregistered','main_generator_macro':A.undefined('no_expected_support_lock'),'coverage':None}
    if s['status']=='draft':return {'status':'draft','main_generator_macro':A.undefined('support_draft_not_frozen'),'coverage':{'blocking_gaps':s['blocking_gaps']}}
    byid=defaultdict(list)
    for r in rows:byid[r['sample_id']].append(r)
    expected={r['sample_id'] for r in s['sample_manifest']};observed=set(byid)
    missing=sorted(expected-observed) if require_all_rows else []
    unexpected=sorted(observed-expected)
    declared_cells={(c['generator_family'],c['source_family']) for c in s['cells']}
    unplanned_cells=sorted({(r['generator_family'],r['source_family']) for r in rows if r['label_fake']==1}-declared_cells)
    required_real_ids={x for p in s['real_pools'].values() for x in p['sample_ids']}
    unexpected_real=sorted(r['sample_id'] for r in rows if not r['label_fake'] and r['sample_id'] not in required_real_ids)
    cell_reports=[];gen=defaultdict(list);class_failures=[]
    for c in s['cells']:
        fake=[r for sample in c['fake_sample_ids'] for r in byid[sample]]
        pool=s['real_pools'][c['real_pool_id']]
        real=[r for sample in pool['sample_ids'] for r in byid[sample]]
        if not fake and not real:state='both_classes_absent'
        elif not fake:state='fake_class_absent'
        elif not real:state='real_class_absent'
        else:state='both_classes_present'
        absent=sorted(set(c['fake_sample_ids']+pool['sample_ids'])-observed) if require_all_rows else []
        metric=A.auroc(fake+real)
        cell_reports.append({'cell_id':c['cell_id'],'generator_family':c['generator_family'],'source_family':c['source_family'],'real_pool_id':c['real_pool_id'],'expected_fake_rows':len(c['fake_sample_ids']),'expected_real_rows':len(pool['sample_ids']),'observed_fake_rows':len(fake),'observed_real_rows':len(real),'class_support':state,'missing_sample_ids':absent,'observed_subset_auroc':metric,'complete_required_rows':not absent})
        if state!='both_classes_present':class_failures.append(c['cell_id'])
        gen[c['generator_family']].append(metric['value'])
    complete=not (missing or unexpected or unplanned_cells or unexpected_real or class_failures)
    generators=[]
    for g,vals in sorted(gen.items()):
        x=A.value(sum(vals)/len(vals)) if all(x is not None for x in vals) else A.undefined('incomplete_planned_source_cells')
        generators.append({'generator_family':g,'source_cells':len(vals),'observed_subset_macro':x})
    if complete:
        vals=[g['observed_subset_macro']['value'] for g in generators];main=A.value(sum(vals)/len(vals))
    else:main=A.undefined('incomplete_or_unplanned_expected_support')
    coverage={'missing_required_sample_ids':missing,'unexpected_sample_ids':unexpected,'unexpected_fake_cells':[list(k) for k in unplanned_cells],'unexpected_real_sample_ids':unexpected_real,'single_or_zero_class_cells':class_failures,'cells':cell_reports,'shared_real_pools':{k:{'expected_rows':len(v['sample_ids']),'consumers':[c['cell_id'] for c in s['cells'] if c['real_pool_id']==k]} for k,v in s['real_pools'].items()}}
    return {'status':'complete' if complete else 'incomplete','support_sha256':s['sha256'],'main_generator_macro':main,'coverage':coverage,'generators':generators,'definition':'frozen generator families equal-weighted; within generator frozen source cells equal-weighted; shared real IDs reused with one bootstrap draw'}
