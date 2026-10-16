import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from forensics.operator_response import OperatorResponseEncoder

torch.manual_seed(7)
x = torch.randn(2, 4, 3, 16, 16, requires_grad=True)
controls = torch.stack((x.detach() + .2, x.detach() - .2, x.detach() + .4), dim=1)
model = OperatorResponseEncoder()
logit, feat = model(x, controls)
assert logit.shape == (2,) and feat.shape == (2, 12)
assert torch.isfinite(logit).all() and torch.isfinite(feat).all()
logit.mean().backward()
assert x.grad is not None and torch.isfinite(x.grad).all()
try:
    model(x, controls[:, :1])
except ValueError:
    pass
else:
    raise AssertionError('K=1 controls must be rejected')
print('operator response module invariants: PASS')
