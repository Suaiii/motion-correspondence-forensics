"""A repeated-frame counterexample: soft correspondences need not be idempotent."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.composability import correspondence,six_frame_response


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    theta=np.arange(16)*2*np.pi/16
    features=np.stack([np.cos(theta),np.sin(theta)],axis=1)
    tokens=np.repeat(features[None],6,axis=0)
    matrix=correspondence(features,features,temperature=.1)
    result=six_frame_response(tokens,grid=(4,4),scales=(1,))
    defect=float(np.max(np.abs(matrix@matrix-matrix)))
    direct=float(result['direct_js'].mean());response=float(result['responses'].mean())
    assert np.array_equal(tokens[0],tokens[-1]) and defect>1e-8 and direct>1e-8
    assert np.max(np.abs(result['responses']))>1e-8
    report=dict(plan_version='cvpr27-20260917-v1',status='counterexample_confirmed',
        input='six identical frames; 4x4 grid of unit circle feature vectors; not a real video',
        temperature=.1,scales=[1],max_soft_correspondence_idempotence_defect=defect,
        direct_js_mean=direct,response_mean=response,response_absolute_max=float(np.abs(result['responses']).max()),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        core_sha256=hashlib.sha256((Path(__file__).resolve().parents[1]/'forensics/composability.py').read_bytes()).hexdigest(),
        interpretation='Nonzero composition error and calibrated spatial response can occur without any temporal change.',
        recommendation='Add a repeated-frame/static-patch control before attributing detection gains to a temporal mechanism.',
        limitations=['Toy feature algebra, not an efficacy experiment or a rejection of the candidate.',
                    'Do not claim that nonzero JS alone establishes temporal inconsistency or forgery.'],
        formal_gate_passed=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
