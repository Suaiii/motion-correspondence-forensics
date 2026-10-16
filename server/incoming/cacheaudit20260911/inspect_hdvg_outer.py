"""Decode already-CRC-checked 7z metadata; refuse every payload read."""
import argparse
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys


class HeaderOnly(io.RawIOBase):
    def __init__(self, regions, size): self.regions=regions;self.size=size;self.pos=0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if not 0<=pos<=self.size:raise ValueError('Metadata seek outside archive')
        self.pos=pos;return pos
    def read(self,n=-1):
        if self.pos==self.size:return b''
        if n<0 or n>1024*1024:raise ValueError('Unbounded payload read refused')
        for start,data in self.regions:
            offset=self.pos-start
            if 0<=offset<len(data) and offset+n<=len(data):
                self.pos+=n;return data[offset:offset+n]
        raise ValueError('Archive payload read refused at '+str(self.pos))


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    root=a.run_dir;target=root/'archive_tools_py7zr_1_1_3'
    if not target.exists():
        env=dict(os.environ,PIP_CONFIG_FILE=os.devnull)
        for key in ('PIP_INDEX_URL','PIP_EXTRA_INDEX_URL'):env.pop(key,None)
        subprocess.run([sys.executable,'-m','pip','install','--index-url','https://pypi.org/simple',
                        '--target',str(target),'--report',str(root/'archive_tools_install.json'),'py7zr==1.1.3'],
                       check=True,timeout=240,env=env)
    sys.path.insert(0,str(target));import py7zr
    probe=root/'hdvg_header_probe_v1';info=json.loads((probe/'header_info.json').read_text())
    f=HeaderOnly([(0,(probe/'start_header.bin').read_bytes()),
                  (info['next_header_global_offset'],(probe/'next_header.bin').read_bytes())],
                 info['next_header_global_offset']+info['next_header_size'])
    with py7zr.SevenZipFile(f,'r') as archive:
        files=[{'name':x.filename,'compressed_bytes':x.compressed,'uncompressed_bytes':x.uncompressed,
                'is_directory':x.is_directory} for x in archive.list()]
        # These structural fields come from parsed metadata; no stream extraction.
        folders=archive.header.main_streams.unpackinfo.folders
        result={'files':files,'compression_blocks':len(folders),
                'coders':[[{'method_hex':c['method'].hex(),'properties_hex':(c.get('properties') or b'').hex()} for c in folder.coders] for folder in folders],
                'payload_read':False,'py7zr_version':py7zr.__version__,
                'limitations':'Only outer archive metadata. No video or nested RAR index extracted; no full archive SHA verified.'}
    result['tool_environment']={d.metadata['Name']:d.version for d in importlib.metadata.distributions(path=[str(target)])}
    (probe/'outer_archive_info.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
