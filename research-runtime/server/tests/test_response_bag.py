import sys
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forensics.model import ResponseBag

torch.manual_seed(11)
x = torch.randn(2, 4, 3, 32, 32)
c = torch.stack((x + .1, x - .1), dim=1)
m = ResponseBag()
assert m(x).shape == (2,)
y = m(x, c)
assert y.shape == (2,) and torch.isfinite(y).all()
print('response bag integration invariants: PASS')
