"""Quality/timing check of fixed candidate video set; no classifier fitting."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from msrvtt_source_probe import RUN,save

cv2.setNumThreads(1)
plan=json.loads((RUN/'candidate_selection.json').read_text(encoding='utf-8'))
results=[]
for j,row in enumerate(plan['records']):
    path=RUN/'candidate_videos'/(row['video_id']+'.mp4')
    r=dict(video_id=row['video_id'],origin_id=row['source_origin_id'],category=row['category'],label_status='not_admitted',scope='candidate_quality_and_sampling_only')
    try:
        receipt=json.loads(path.with_suffix('.receipt.json').read_text(encoding='utf-8'))
        r['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        if r['sha256']!=receipt['sha256']:raise ValueError('Candidate SHA mismatch')
        cap=cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1])
        try:
            if not cap.isOpened():raise ValueError('Cannot open')
            n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=float(cap.get(cv2.CAP_PROP_FPS))
            if n<=0 or fps<=0:raise ValueError('Invalid metadata')
            duration=n/fps;w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            r.update(frame_count=n,fps=fps,duration=duration,width=w,height=h,modes={})
            modes={'native16':np.arange(max(0,(n-16)//2),max(0,(n-16)//2)+16)}
            for seconds,count in [(2,16),(1.5,12)]:
                if duration+1e-6<seconds or fps<8-1e-6:
                    r['modes'][f'{seconds}s_8fps']={'status':'ineligible_duration_or_rate'}
                else:modes[f'{seconds}s_8fps']=np.floor(((duration-seconds)/2+np.arange(count)/8)*fps+1e-8).astype(int)
            for mode,indices in modes.items():
                if len(set(indices.tolist()))!=len(indices)or indices[-1]>=n:
                    r['modes'][mode]={'status':'ineligible_indices'};continue
                pts=[];frame_hashes=[];black=[]
                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES,int(idx));ok,frame=cap.read()
                    if not ok:raise ValueError('Decode failed')
                    pts.append(float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000)
                    frame_hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
                    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                    black.append(float(gray.mean())<5 and float(gray.std())<5)
                r['modes'][mode]={'status':'ok'if np.all(np.diff(pts)>0)else'nonmonotonic_pts','indices':indices.tolist(),'pts':pts,
                    'observation_span':pts[-1]-pts[0],'unique_content_frames':len(set(frame_hashes)),'black_fraction':float(np.mean(black)),
                    'frame_sequence_sha256':hashlib.sha256(''.join(frame_hashes).encode()).hexdigest()}
            r['status']='ok'
        finally:cap.release()
    except Exception as exc:r.update(status='error',error=repr(exc))
    results.append(r)
    if(j+1)%16==0:print('QC',j+1,'/64 errors',sum(x['status']=='error'for x in results),flush=True)
summary={'selected':64,'opened_and_hashed_ok':sum(r['status']=='ok'for r in results),'modes':{},'accepted_for_training':False,
    'limitation':'Sampled decoding and metadata only; no full-content/ancestry/license or camera-origin acceptance.',
    'selection_sha256':hashlib.sha256((RUN/'candidate_selection.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'records':results}
for mode in ['native16','2s_8fps','1.5s_8fps']:
    values=[r.get('modes',{}).get(mode,{})for r in results]
    summary['modes'][mode]={'ok':sum(v.get('status')=='ok'for v in values),'sampled_black_clips':sum(v.get('black_fraction',0)>=.5 for v in values),'sampled_repeated_content_clips':sum(v.get('unique_content_frames',len(v.get('indices',[])))<len(v.get('indices',[]))for v in values)}
save('candidate_qc.json',summary)
print(json.dumps({k:v for k,v in summary.items()if k!='records'},indent=2))
