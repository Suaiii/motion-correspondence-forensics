"""Explicit local, hash-checked weights only. These adapters do not download models."""
from functools import lru_cache
from pathlib import Path
import numpy as np
import torch
from .common import sha


@lru_cache(maxsize=1)
def raft(weights,expected_sha,device):
    if sha(weights)!=expected_sha:raise ValueError('RAFT weights changed')
    from torchvision.models.optical_flow import raft_small
    model=raft_small(weights=None,progress=False).to(device).eval()
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
    return model


def raft_flow(current,previous,weights,expected_sha,device):
    if current.shape[0]%8 or current.shape[1]%8:raise ValueError('RAFT inputs must be divisible by eight')
    def tensor(x):return torch.from_numpy(x[...,::-1].copy()).permute(2,0,1).unsqueeze(0).float().to(device)/127.5-1
    with torch.inference_mode():out=raft(weights,expected_sha,device)(tensor(current),tensor(previous))[-1]
    return out[0].permute(1,2,0).cpu().numpy()


def dinov2(repo,weights,expected_sha,device,variant='dinov2_vits14'):
    if not (Path(repo)/'hubconf.py').is_file() or sha(weights)!=expected_sha:raise ValueError('Local DINO code/weights missing or changed')
    if variant not in ('dinov2_vits14','dinov2_vitb14','dinov2_vitl14'):raise ValueError('Unsupported DINOv2 variant')
    model=torch.hub.load(str(repo),variant,source='local',pretrained=False).to(device).eval()
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
    for p in model.parameters():p.requires_grad_(False)
    return model


@torch.inference_mode()
def dino_features(model,bgr,device,batch_size=4):
    x=torch.from_numpy(bgr[...,::-1].copy()).permute(0,3,1,2).float()/255
    x=(x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]
    tokens=[]
    for batch in x.split(batch_size):tokens.append(model(batch.to(device)).float().cpu().numpy())
    return np.concatenate(tokens)
