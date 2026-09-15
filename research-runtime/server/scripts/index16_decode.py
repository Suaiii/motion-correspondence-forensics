"""Diagnostic fixed native-frame budget; preserves PTS and never invents physical timing."""
import json
import cv2
import numpy as np


def decode(path,cfg):
    from forensics.video import command,QualityExclusion
    probe=json.loads(command(['ffprobe','-v','error','-select_streams','v:0','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
    pts=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
    n=cfg['frames']
    if len(pts)<n:raise QualityExclusion('fewer_than_16_native_frames')
    if not np.isfinite(pts).all() or not (np.diff(pts)>0).all():raise ValueError('invalid_native_pts')
    start=(len(pts)-n)//2;indices=np.arange(start,start+n)
    cap=cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);frames=[]
    try:
        # Sequential decoding avoids using container frame-rate hints for random seeking.
        for i in range(int(indices[-1])+1):
            ok,frame=cap.read()
            if not ok:raise ValueError('native_sequence_decode_failed')
            if i>=start:
                h,w=frame.shape[:2];side=min(h,w)
                crop=frame[(h-side)//2:(h+side)//2,(w-side)//2:(w+side)//2]
                frames.append(cv2.resize(crop,(cfg['size'],cfg['size']),interpolation=cv2.INTER_AREA))
    finally:cap.release()
    bgr=np.stack(frames);gray=np.stack([cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in bgr])
    black=float(np.mean((gray.mean((1,2))<5)&(gray.std((1,2))<5)))
    if black>=.5:raise QualityExclusion('black_frames')
    return bgr,{'indices':indices.tolist(),'pts':pts[indices].tolist(),'dt':np.diff(pts[indices]).tolist(),
        'duration':float(pts[-1]-pts[0]+np.median(np.diff(pts))),
        'sampling_mode':'center_16_native_frames_no_time_resampling','black_fraction':black,
        'caveat':'Equal frame count does not equal matched physical time or motion magnitude'}
