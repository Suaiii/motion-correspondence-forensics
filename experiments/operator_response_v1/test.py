import numpy as np
from run import features
rng=np.random.default_rng(17); base=rng.normal(size=(7,3,16,16)).astype('float32'); noise=rng.normal(scale=.1,size=base.shape).astype('float32')
x=features(base,base+noise,base-noise)
assert np.isfinite(x).all() and x.shape==(12,)
assert np.isfinite(features(base,base,base)).all()
print('operator_response synthetic invariants: PASS')
