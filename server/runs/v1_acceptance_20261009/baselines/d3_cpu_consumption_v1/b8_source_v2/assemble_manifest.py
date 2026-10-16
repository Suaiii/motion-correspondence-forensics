"""Explicit frozen metadata join for a future selection; never open JPEG/model payloads."""
import argparse,hashlib,json
from pathlib import Path
from contract import ROOT,read_locked,digest,sha_file,validate_manifest
def read_jsonl(path,expected):
    p=Path(path)
    if sha_file(p)!=expected:raise ValueError('external_JSONL_SHA_mismatch:'+str(p))
    return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def main():
    p=argparse.ArgumentParser(description='Join coordinated typed selection, prepared index and frozen A7-style input records')
    for name in ['selection','prepared-index','input-records','environment','identity']:
        p.add_argument('--'+name,required=True);p.add_argument('--'+name+'-sha256',required=True)
    p.add_argument('--output',required=True);a=p.parse_args()
    selection=read_jsonl(a.selection,a.selection_sha256);prepared=read_jsonl(a.prepared_index,a.prepared_index_sha256);records=read_jsonl(a.input_records,a.input_records_sha256)
    environment=read_locked(a.environment,a.environment_sha256);identity=read_locked(a.identity,a.identity_sha256)
    prep={r['sample_id']:r for r in prepared};inputs={r['sample_id']:r for r in records if r.get('method')=='d3'}
    if len(prep)!=len(prepared):raise ValueError('duplicate_prepared_index_identity')
    members=[]
    for ordinal,r in enumerate(selection):
        sid=r['sample_id'];record=inputs[sid];binding=prep[sid]
        if record['input_sha256']!=r['source_sha256'] or binding['source_sha256']!=r['source_sha256']:raise ValueError('selection_prepared_record_source_SHA_disagreement')
        member=dict(r,ordinal=ordinal,prepared_folder=binding['prepared_folder'],prepared_frames=binding['prepared_frames'],
            input_record=record,input_record_sha256=digest(record))
        if 'timeline_evidence' in binding:member['timeline_evidence']=binding['timeline_evidence']
        members.append(member)
    manifest=dict(identity,version='d3_execution_manifest/1.0',status='frozen',fixture=False,method_id='d3',encoder_type='XCLIP-16',loss_type='l2',
        method_revision=json.loads((ROOT/'METHOD_IDENTITY.json').read_text())['author_commit'],track='native_reference',
        preprocessing_sha256=sha_file(ROOT/'PREPROCESS_IDENTITY.json'),selection_sha256=a.selection_sha256,
        dependency_versions=environment['dependency_versions'],cv2_provider=environment['cv2_provider'],expected_members=len(members),members=members)
    manifest['assembly_input_SHA']={'selection':a.selection_sha256,'prepared_index':a.prepared_index_sha256,'input_records':a.input_records_sha256,
        'environment':a.environment_sha256,'identity':a.identity_sha256}
    validate_manifest(manifest)
    out=Path(a.output).resolve()
    protected=[ROOT.parents[1]/s for s in ['baselines/input_contract_recovery_v1','baselines/sources/d3','fingerprint_cpu/author_input_parity_v1','data_audit/unified_release_candidate_v1']]
    if any(out.is_relative_to(x.resolve()) for x in protected):raise ValueError('assembly_output_cannot_write_old_sealed_input_namespaces')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'execution_manifest':str(out),'sha256':sha_file(out),'requested_members':len(members),
        'public_approved':sum(r['approved_public_candidate'] for r in members),'public_excluded_retained':sum(not r['approved_public_candidate'] for r in members),
        'new_scores_or_models':0}))
if __name__=='__main__':main()
