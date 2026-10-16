import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def write(path,value,replace=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not replace:raise FileExistsError(path)
    temp=path.with_name(path.name+'.partial')
    with temp.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
        f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def safe_path(root,relative):
    root=Path(root).resolve();p=PurePosixPath(relative)
    if '\\' in relative or p.is_absolute() or PureWindowsPath(relative).drive or '..' in p.parts or not p.parts:
        raise ValueError('Expected a root-relative POSIX path: '+relative)
    dest=(root/str(p)).resolve()
    if not dest.is_relative_to(root):raise ValueError('Path escapes root')
    return dest


def code_hashes():
    root=Path(__file__).parent
    return {p.name:sha(p) for p in sorted(root.glob('*.py'))}


@contextlib.contextmanager
def exclusive(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:f.write(str(os.getpid()))
    try:yield
    finally:path.unlink()


def event(root,stage,**data):
    path=Path(root)/'events.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(time_utc=now(),stage=stage,**data),ensure_ascii=False,allow_nan=False)+'\n')
