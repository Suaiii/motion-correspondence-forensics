"""Synthetic-image integration of existing frozen DINO with the new head."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.backbones import dinov2,dino_patch_features
from forensics.local_composability import LocalComposability


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();started=time.monotonic();torch.set_num_threads(4);torch.manual_seed(1729)
    rev='7764ea0f912e53c92e82eb78a2a1631e92725fc8'
    expected='0b8b82f85de91b424aded121c7e1dcc2b7bc6d0adeea651bf73a13307fad8c73'
    repo=a.base/'models'/('dinov2-'+rev);weights=a.base/'models/dinov2_vitb14_pretrain.pth'
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==rev
    assert not subprocess.check_output(['git','-C',str(repo),'diff','--name-only'],text=True).strip()
    torch.backends.cuda.matmul.allow_tf32=False;torch.cuda.reset_peak_memory_stats()
    model=dinov2(str(repo),str(weights),expected,'cuda',variant='dinov2_vitb14')
    yy,xx=np.mgrid[:224,:224]
    frame=np.stack([(xx*3+yy)%256,(yy*5)%256,((xx//14+yy//14)%2)*255],axis=-1).astype(np.uint8)
    frames=np.repeat(frame[None],6,axis=0)
    extracted=dino_patch_features(model,frames,'cuda')
    assert extracted['patch_tokens'].shape==(6,256,768) and extracted['global_tokens'].shape==(6,768)
    assert not any(p.requires_grad for p in model.parameters())
    head=LocalComposability().cuda().eval()
    with torch.no_grad():
        output=head(torch.from_numpy(extracted['patch_tokens'])[None].cuda(),torch.from_numpy(extracted['global_tokens'])[None].cuda())
    assert output['logits'].shape==(1,) and torch.isfinite(output['logits']).all()
    assert output['response_maps'].shape==(1,6,3,16,16) and torch.isfinite(output['response_maps']).all()
    root=Path(__file__).resolve().parents[1]
    sources=['forensics/backbones.py','forensics/common.py','forensics/local_composability.py',
             'forensics/composability.py','forensics/composability_torch.py','scripts/check_backbone_composability.py']
    result=dict(status='pass',plan_version='cvpr27-20260917-v1',seconds=time.monotonic()-started,
        model_revision=rev,weights_sha256=expected,precision=extracted['precision'],
        input='six identical synthetic 224x224 BGR frames, no real research video',
        patch_shape=list(extracted['patch_tokens'].shape),global_shape=list(extracted['global_tokens'].shape),
        response_shape=list(output['response_maps'].shape),finite_logit=True,
        trainable_backbone_parameters=0,trainable_head_parameters=sum(p.numel() for p in head.parameters()),
        peak_gpu_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
        static_synthetic_direct_js_mean=float(output['direct_js'].mean()),
        static_synthetic_response_absolute_mean=float(output['response_maps'].abs().mean()),
        source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources},
        optimizer_steps=0,real_data_efficacy_measured=False,formal_gate_passed=False,
        limits=['Untrained head: a finite score is only an interface check.',
                'No video decoder or actual-PTS census in this check; not the required 100-video profile.'])
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
