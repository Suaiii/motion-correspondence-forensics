"""Future metadata-only dependency/source descriptor; does not import cv2 or models."""
import argparse,base64,csv,importlib.metadata,importlib.util,json,sys
from pathlib import Path
from contract import DEPS,CV2_DISTRIBUTIONS,sha_file
def describe(provider,paths):
    for path in reversed(paths):sys.path.insert(0,path)
    if provider not in CV2_DISTRIBUTIONS:raise ValueError('explicit_supported_cv2_distribution_required')
    dist=importlib.metadata.distribution(provider);spec=importlib.util.find_spec('cv2')
    if not spec or not spec.origin:raise ValueError('cv2_module_source_missing')
    origin=Path(spec.origin).resolve();files=list(dist.files or []);byreal={Path(dist.locate_file(p)).resolve():str(p) for p in files}
    if origin not in byreal:raise ValueError('cv2_actual_module_not_claimed_by_explicit_distribution')
    records=[p for p in files if str(p).endswith('.dist-info/RECORD')]
    if len(records)!=1:raise ValueError('one_cv2_distribution_RECORD_required')
    record_path=Path(dist.locate_file(records[0]));native={}
    for f in files:
        name=str(f).replace('\\','/')
        if name.startswith('cv2/') and Path(name).suffix in ['.pyd','.so']:native[name]=sha_file(Path(dist.locate_file(f)))
    if not native:raise ValueError('cv2_native_extension_not_in_distribution')
    # Prove installed core bytes agree with the selected distribution RECORD, even if another alias is present.
    declared={r[0]:r[1] for r in csv.reader(record_path.read_text(encoding='utf-8').splitlines()) if len(r)>1}
    locked={byreal[origin]:sha_file(origin),**native}
    for rel,h in locked.items():
        claim=declared.get(rel,'')
        if claim!='sha256='+base64.urlsafe_b64encode(bytes.fromhex(h)).decode().rstrip('='):raise ValueError('installed_cv2_core_not_selected_distribution_RECORD:'+rel)
    versions={n:importlib.metadata.version(n) for n in DEPS+[provider]}
    return {'dependency_versions':versions,'cv2_provider':{'distribution':provider,'version':dist.version,
        'module_relative_path':byreal[origin],'module_source_sha256':locked[byreal[origin]],
        'distribution_record_sha256':sha_file(record_path),'native_extensions':native},
        'source_location_description':str(origin),'cv2_imported':False,'torch_or_model_imported':False,
        'use':'copy dependency_versions and cv2_provider into coordinated frozen execution manifest; current descriptor is not a model test'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--cv2-distribution',required=True,choices=sorted(CV2_DISTRIBUTIONS));p.add_argument('--dependency-path',action='append',default=[]);a=p.parse_args()
    print(json.dumps(describe(a.cv2_distribution,a.dependency_path),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
