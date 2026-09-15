import json,sys,traceback
from pathlib import Path
import numpy as np,cv2
HERE=Path('research-runs/alignment_gate_v1/code/experiments/alignment_gate_v1');sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent.parent/'order_gate_v1'))
import run_alignment as ra
from video_io import decode
P=json.loads(Path('research-runs/alignment_gate_v1/protocol.json').read_text());R=Path('research-runs/comgenvid_videos_20260914');src=json.loads((R/'receipt_balanced50.json').read_text())['records'];out=R/'correspondence_features_150.jsonl';done={}
if out.exists():
 for line in out.open(encoding='utf8'):
  try: x=json.loads(line);done[x['sha256']]=x
  except: pass
ra.np.float16=ra.np.float32
with out.open('a',encoding='utf8') as f:
 for i,x in enumerate(src):
  if x['sha256'] in done:continue
  try:
   cap=cv2.VideoCapture(x['path']);row={'path':x['path'],'fps':cap.get(cv2.CAP_PROP_FPS),'frame_count':int(cap.get(cv2.CAP_PROP_FRAME_COUNT))};cap.release();bgr,q=decode(row,P);arrays,probe,_=ra.representations(bgr,P);features={}
   for k,a in arrays.items():
    z=a.astype(np.float32); az=np.abs(z);features[k]=[float(np.log1p(v)) for v in [az.mean(),az.mean((1,2,3)).std(),np.sqrt((z*z).mean()),np.quantile(az,.95)]]
   rec={k:x[k] for k in ('filename','source_model','label_fake','sha256')};rec.update(quality=q,probe=probe,features=features);f.write(json.dumps(rec)+'\n');f.flush();print('OK',i+1,flush=True)
  except Exception as e: print('FAIL',i+1,type(e).__name__,flush=True)
print('DONE',len(done))
