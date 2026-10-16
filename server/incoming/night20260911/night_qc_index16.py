"""Post-hoc diagnostic prompted by strict two-second exclusions; not the primary gate."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import night_qc
import index16_decode

# Keep the existing worker, extraction and frozen selection; change only the decoder.
_original_worker=night_qc.worker


def worker(task):
    from forensics import video
    previous=video.decode
    video.decode=index16_decode.decode
    try:return _original_worker(task)
    finally:video.decode=previous


night_qc.worker=worker
night_qc.SAMPLING={'frames':16,'fps':None,'window_sec':None,'size':224,
    'mode':'center_16_native_frames','analysis_status':'posthoc_supplement; no primary-gate substitution'}

if __name__=='__main__':
    import argparse
    from forensics.common import read,write,sha
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--run-dir',type=Path,required=True)
    args,_=parser.parse_known_args();args.run_dir.mkdir(parents=True,exist_ok=True)
    receipt=args.run_dir/'supplement_code_hashes.json'
    code={'analysis':'posthoc native-frame diagnostic after strict time-window exclusions',
          'files':{Path(p).name:sha(p) for p in [__file__,night_qc.__file__,index16_decode.__file__]}}
    if receipt.exists():
        if read(receipt)!=code:raise ValueError('Supplement code changed; use a new run')
    else:write(receipt,code)
    night_qc.main()
