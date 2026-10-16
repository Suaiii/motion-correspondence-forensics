"""AL145: locked dense DINO baseline gate for video_evidence_v1.

This delegates to the path-based adapter and writes a small run receipt. It is
an evidence gate for AL146, not a mechanism claim.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--selection',type=Path,required=True)
    ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--features',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True); ap.add_argument('--adapter',type=Path,default=Path(__file__).with_name('video_evidence_dense_adapter.py'))
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    cmd=[sys.executable,str(a.adapter),'train','--selection',str(a.selection),'--manifest',str(a.manifest),'--features',str(a.features),'--output',str(a.output)]
    result=subprocess.run(cmd,capture_output=True,text=True)
    (a.output/'adapter.stdout.txt').write_text(result.stdout,encoding='utf-8')
    (a.output/'adapter.stderr.txt').write_text(result.stderr,encoding='utf-8')
    receipt={'status':'complete' if result.returncode==0 else 'failed','returncode':result.returncode,
             'command':cmd,'selection_sha256':sha(a.selection),'manifest_sha256':sha(a.manifest),
             'adapter_sha256':sha(a.adapter),'features_lock_sha256':sha(a.features/'lock.json') if (a.features/'lock.json').exists() else None,
             'formal_gate_passed':False,'scope':'strong dense baseline gate; no mechanism acceptance'}
    (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if result.returncode: raise SystemExit(result.returncode)
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__': main()
