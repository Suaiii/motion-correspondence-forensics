"""Read-only inventory of saved evidence bundles; no extraction or pickle loading."""
import json
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'research-runs'/'overnight_20260911'
for name in ['dino_checkpoint_v1.zip','real_and_closeout_checkpoint_v1.zip','gpu_checkpoint_raft_v1.zip']:
    with zipfile.ZipFile(root/name)as z:
        items=z.infolist()
        arrays=[i for i in items if i.filename.endswith(('.npy','.npz'))]
        candidates=[i for i in items if any(x in i.filename.lower()for x in ['summary','manifest','overview','audit','index.json'])and i.file_size<200000]
        print(json.dumps({'archive':name,'entries':len(items),'array_count':len(arrays),'array_examples':[(i.filename,i.file_size)for i in arrays[:2]],'summary_candidates':[(i.filename,i.file_size)for i in candidates[:10]],'top_level':[i.filename for i in items if '/'not in i.filename]},ensure_ascii=False))
        # One provenance record, selected by path only.
        records=[i for i in items if '/records/'in i.filename and i.filename.endswith('.json')]
        if records:
            obj=json.loads(z.read(records[0]))
            print('record example:',json.dumps(obj,ensure_ascii=False)[:6500])
