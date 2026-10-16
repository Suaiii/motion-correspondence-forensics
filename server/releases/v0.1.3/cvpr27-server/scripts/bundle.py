"""Build a source-only deployment ZIP, excluding authentication and browser state."""
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.common import sha,write


def main(dest):
    root=Path(__file__).resolve().parents[1];dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise FileExistsError('Deployment snapshot already exists')
    allowed_configs={'mechanism.json','mechanism_expanded.json','study_scale.json','baselines.json','historical_exclusions.json','server.example.json'}
    files=[p for p in root.rglob('*') if p.is_file() and not any(x in p.parts for x in ('.venv','__pycache__','.git'))
        and (p.suffix in ('.py','.sh','.toml','.md') or p.parent==root/'configs' and p.name in allowed_configs)]
    manifest={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in sorted(files)}
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):z.write(p,arcname='cvpr27-server/'+str(p.relative_to(root)).replace('\\','/'))
        z.writestr('cvpr27-server/source_manifest.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None:raise ValueError('ZIP validation failed')
        import hashlib
        for rel,h in manifest.items():
            if hashlib.sha256(z.read('cvpr27-server/'+rel)).hexdigest()!=h:raise ValueError('Bundle source differs')
    write(dest.with_suffix('.json'),{'zip_sha256':sha(dest),'files':manifest,'contains_credentials':False,'uploaded_to_server':False})
    print('BUNDLE VERIFIED',len(files),'files',dest.stat().st_size,'bytes')


if __name__=='__main__':main(sys.argv[1])
