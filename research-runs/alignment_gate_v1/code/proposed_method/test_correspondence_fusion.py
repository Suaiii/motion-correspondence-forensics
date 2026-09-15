import torch
from correspondence_fusion import CorrespondenceFusion
def test_forward_backward():
    torch.manual_seed(0);m=CorrespondenceFusion(16,hidden=8);a=torch.randn(4,16,requires_grad=True);b=torch.randn(4,16,requires_grad=True);y=m(a,b);assert y.shape==(4,);y.square().mean().backward();assert torch.isfinite(a.grad).all()
def test_shape_guard():
    m=CorrespondenceFusion(4)
    try:m(torch.randn(2,4),torch.randn(2,3));assert False
    except ValueError:pass
for f in (test_forward_backward,test_shape_guard):f()
print('2 fusion tests passed')
