import json
import subprocess
import tempfile
from pathlib import Path
import cv2
import numpy as np


class QualityExclusion(ValueError):pass


def command(args,timeout=180):
    result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr[-3000:])
    return result.stdout


def decode(path,cfg):
    # Decode PTS rather than treating a nominal frame rate as a VFR guarantee.
    probe=json.loads(command(['ffprobe','-v','error','-select_streams','v:0','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
    pts=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
    if len(pts)<2 or not np.isfinite(pts).all() or not (np.diff(pts)>0).all():raise ValueError('Invalid decoded PTS')
    duration=pts[-1]-pts[0]+np.median(np.diff(pts))
    if duration+1e-6<cfg['window_sec']:raise QualityExclusion('short_video')
    n=round(cfg['window_sec']*cfg['fps']);targets=pts[0]+(duration-cfg['window_sec'])/2+np.arange(n)/cfg['fps']
    indices=np.searchsorted(pts,targets,side='right')-1
    if indices.min()<0 or len(set(indices))!=n:raise QualityExclusion('repeated_or_insufficient_frames')
    cap=cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);frames=[]
    try:
        for index in indices:
            if not cap.set(cv2.CAP_PROP_POS_FRAMES,int(index)):raise RuntimeError('seek failed')
            ok,frame=cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1!=index:raise RuntimeError('decode index mismatch')
            h,w=frame.shape[:2];side=min(h,w)
            frame=frame[(h-side)//2:(h+side)//2,(w-side)//2:(w+side)//2]
            frames.append(cv2.resize(frame,(cfg['size'],cfg['size']),interpolation=cv2.INTER_AREA))
    finally:cap.release()
    bgr=np.stack(frames);gray=np.stack([cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in bgr])
    black=float(np.mean((gray.mean((1,2))<5)&(gray.std((1,2))<5)))
    if black>=.5:raise QualityExclusion('black_frames')
    return bgr,{'indices':indices.tolist(),'pts':pts[indices].tolist(),'duration':float(duration),'black_fraction':black}


RECIPES={
    'clean':[],
    'h264_23':['-c:v','libx264','-crf','23'],
    'scale075_h264_28':['-vf','scale=trunc(iw*0.75/2)*2:trunc(ih*0.75/2)*2:flags=bicubic','-c:v','libx264','-crf','28'],
    'h265_32':['-c:v','libx265','-crf','32'],
    'scale05_h265_32':['-vf','scale=trunc(iw*0.5/2)*2:trunc(ih*0.5/2)*2:flags=lanczos','-c:v','libx265','-crf','32'],
    'fps12_h264_28':['-vf','fps=12','-c:v','libx264','-crf','28'],
}


def load_condition(path,condition,cfg,scratch):
    if condition not in RECIPES:raise ValueError('Unknown full-video transform')
    if condition=='clean':return decode(path,cfg)
    Path(scratch).mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch,prefix='transform-') as tmp:
        target=Path(tmp)/'view.mp4'
        cmd=['ffmpeg','-v','error','-nostdin','-i',str(path),'-map','0:v:0','-an','-map_metadata','-1',*RECIPES[condition],'-pix_fmt','yuv420p','-threads','2',str(target)]
        command(cmd)
        frames,q=decode(target,cfg);q['transform_arguments']=cmd[cmd.index('-map'): -1]
        return frames,q


def flows(frames):
    gray=[cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in frames]
    return np.stack([cv2.calcOpticalFlowFarneback(gray[t],gray[t-1],None,.5,3,15,3,5,1.2,0) for t in range(1,len(gray))])
