"""Read at most 1MiB of public author metadata; never fetch video content."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request


def prefix(url, n):
    request=urllib.request.Request(url,headers={'Range':'bytes=0-%d'%(n-1)})
    with urllib.request.urlopen(request,timeout=20) as response:
        info={'status':response.status,'content_range':response.headers.get('Content-Range'),
              'content_length':response.headers.get('Content-Length'),'content_type':response.headers.get('Content-Type')}
        data=response.read(n)
    return data,info


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    file_id='1BNv6HvlI-ieG4Hk3yD5My74ESBG_p6EW'
    url='https://drive.google.com/uc?export=download&id='+file_id
    data,info=prefix(url,65536)
    if b'<html' in data[:200].lower():
        (a.output_dir/'download_interstitial.html').write_bytes(data)
        found=re.search(rb'name="uuid" value="([^"]+)"',data)
        if not found:raise ValueError('No public download form; stop without video acquisition')
        url='https://drive.usercontent.google.com/download?'+urllib.parse.urlencode({
            'id':file_id,'export':'download','confirm':'t','uuid':found.group(1).decode()})
    data,info=prefix(url,1024*1024)
    (a.output_dir/'metadata_prefix.bin').write_bytes(data)
    text=data.decode('utf-8',errors='strict');decoder=json.JSONDecoder();pos=0;records=[]
    while pos<len(text) and text[pos].isspace():pos+=1
    if pos==len(text) or text[pos]!='{':raise ValueError('Metadata prefix is not a JSON object')
    pos+=1
    while pos<len(text):
        while pos<len(text) and (text[pos].isspace() or text[pos]==','):pos+=1
        if pos>=len(text) or text[pos]=='}':break
        try:
            key,pos=decoder.raw_decode(text,pos)
            while pos<len(text) and text[pos].isspace():pos+=1
            if text[pos]!=':':raise ValueError('Expected metadata key separator')
            pos+=1
            while pos<len(text) and text[pos].isspace():pos+=1
            value,pos=decoder.raw_decode(text,pos)
        except (json.JSONDecodeError,IndexError):break
        records.append({'video_id_key':key,'metadata':value})
    (a.output_dir/'complete_prefix_records.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    result={'public_drive_file_id':file_id,'bytes_read':len(data),'prefix_sha256':hashlib.sha256(data).hexdigest(),
            'response':info,'complete_video_records':len(records),'sample_rule':'prefix availability probe only; not random sample',
            'full_metadata_downloaded':False,'videos_downloaded':0,
            'example_schema':list(records[0]['metadata']) if records else []}
    (a.output_dir/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
