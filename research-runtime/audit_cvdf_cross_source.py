import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'research-runs/source_probe_20260914_cvdf'
a=json.loads((run/'candidate_annotation_audit.json').read_text(encoding='utf8'))
known=json.loads((ROOT/'research-plan/artifacts/cvpr27/real_source_id_candidates_20260911.json').read_text(encoding='utf8'))
all_ids=set(known.get('overlap_ids',[]))
ids={r.get('youtube_id') for r in a['records'] if r.get('youtube_id')}
hits=sorted(ids & all_ids)
out={'candidate_ids':sorted(ids),'known_shared_vript_hdvg_ids_hit':hits,'hit_count':len(hits),'cross_source_independence_verified':len(hits)==0,'ancestry_verified':False,'decision':'retain_as_provisional_external_real_probe' if not hits else 'exclude_hits_and_reaudit','basis':'filename-derived YouTube IDs; absence is not proof of content independence'}
(run/'cross_source_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(out,ensure_ascii=False,indent=2))
