import importlib.util
from pathlib import Path
import numpy as np

p=Path(__file__).resolve().parents[1]/'scripts/time_matched_dino.py'
spec=importlib.util.spec_from_file_location('time_matched',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for fps,n in [(8,16),(10,16),(30,60)]:
    ix,q=m.choose(np.arange(n)/fps)
    assert len(set(ix))==8 and np.all(np.diff(ix)>0)
    assert np.allclose(np.diff(q['targets']),.125)
    assert max(abs(v) for v in q['timing_error'])<=.062501
try:m.choose(np.arange(8)/4)
except ValueError:pass
else:raise AssertionError('4fps source cannot supply eight unique 8Hz frames')
print('time-grid selection: PASS; actual native timing retained')
