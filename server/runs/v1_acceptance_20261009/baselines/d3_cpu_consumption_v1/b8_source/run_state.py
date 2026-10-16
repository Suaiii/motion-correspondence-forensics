"""Owned atomic receipts/journal. Successful resume requires identical full lock."""
import json,os,time,traceback
from pathlib import Path
from contract import digest,sha_file
def write_json(path,value):
    p=Path(path);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def append(path,value):
    if Path(path).name=='events.jsonl':value['event_sha256']=digest({k:v for k,v in value.items() if k!='event_sha256'})
    with Path(path).open('a',encoding='utf-8') as f:
        f.write(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def file_bytes(root):
    total=0
    for p in Path(root).rglob('*'):
        try:
            if p.is_file() and not p.is_symlink():total+=p.stat().st_size
        except FileNotFoundError:pass
    return total
def journal(path,identity,members):
    p=Path(path);valid=[];latest={};tail=b''
    if not p.exists():return latest
    raw=p.read_bytes();parts=raw.splitlines(keepends=True)
    for n,line in enumerate(parts):
        try:event=json.loads(line.decode('utf-8'))
        except (ValueError,UnicodeDecodeError):
            if n!=len(parts)-1:raise ValueError('invalid_middle_journal_no_silent_truncation')
            tail=line;break
        if event.get('event_sha256')!=digest({k:v for k,v in event.items() if k!='event_sha256'}):raise ValueError('journal_event_checksum_changed')
        i=event['ordinal']
        if type(i) is not int or not 0<=i<len(members):raise ValueError('journal_ordinal_outside_frozen_denominator')
        m=members[i]
        if event['run_identity_sha256']!=identity or event['sample_id']!=m['sample_id'] or event['source_sha256']!=m['source_sha256']:raise ValueError('journal_identity_or_source_changed')
        if event['status']=='success':
            pred=event['prediction']
            if pred['input_sha256']!=m['source_sha256'] or pred['fixture'] or pred['ancestry_status']!='unknown':raise ValueError('invalid_success_resume_row')
            if event['input_record_sha256']!=m['input_record_sha256']:raise ValueError('resume_input_record_changed')
        elif event['status']!='failed':raise ValueError('journal_status_unknown')
        valid.append(event);latest[i]=event
    if tail or (parts and not parts[-1].endswith(b'\n')):
        old=sha_file(p);archive=p.with_name('events.interrupted.'+old+'.jsonl');os.replace(p,archive)
        for event in valid:append(p,event)
        if not p.exists():p.touch()
        write_json(p.parent/('RECOVERY.'+old+'.json'),{'original_SHA':old,'archive':archive.name,'valid_events_recovered':len(valid),
            'invalid_tail_bytes':len(tail),'old_bytes_preserved':True,'no_score_or_success_invented':True})
    return latest
def materialize(root,identity,members,latest):
    root=Path(root);ledger=root/'RESULT_LEDGER.jsonl.tmp';pred=root/'predictions.jsonl.tmp'
    successes=failures=0
    with ledger.open('w',encoding='utf-8') as lf,pred.open('w',encoding='utf-8') as pf:
        for i,m in enumerate(members):
            e=latest.get(i);status=e['status'] if e else 'pending'
            row={'ordinal':i,'sample_id':m['sample_id'],'source_sha256':m['source_sha256'],'role':m['role'],'status':status,
                'run_identity_sha256':identity,'event_sha256':digest(e) if e else None,'denominator_member':True}
            if status=='success':successes+=1;pf.write(json.dumps(e['prediction'],ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
            elif status=='failed':failures+=1;row['failure']=e['error']
            lf.write(json.dumps(row,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    os.replace(ledger,root/'RESULT_LEDGER.jsonl');os.replace(pred,root/'predictions.jsonl')
    summary={'expected_members':len(members),'successful':successes,'failed':failures,'pending':len(members)-successes-failures,
        'ordered_full_denominator_ledger':True,'predictions_contain_true_successes_only':True,
        'all_failed_or_pending_remain_in_expected_support':True,'run_identity_sha256':identity,'scientific_gate_passed':False,
        'resume_skips_only_locked_successes':True,'failure_retry_requires_explicit_flag':True,'updated_unix':time.time()}
    write_json(root/'RUN_SUMMARY.json',summary);return summary

def failure(identity,i,m,stage,error):
    return {'run_identity_sha256':identity,'ordinal':i,'sample_id':m['sample_id'],'source_sha256':m['source_sha256'],
        'input_record_sha256':m['input_record_sha256'],'status':'failed','stage':stage,
        'error':{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},'observed_unix':time.time()}
