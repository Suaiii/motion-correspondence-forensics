import torch
from nuisance_adversarial import AlignmentNuisanceAdversarial,grad_reverse

def test_shapes_and_backward():
    torch.manual_seed(0); m=AlignmentNuisanceAdversarial(32); x=torch.randn(5,32,requires_grad=True)
    o=m(x); assert o['fake_logit'].shape==(5,); assert o['nuisance_pred'].shape==(5,8)
    loss=o['fake_logit'].mean()+o['nuisance_pred'].square().mean(); loss.backward(); assert torch.isfinite(x.grad).all()

def test_gradient_reversal_direction():
    x=torch.tensor([[2.0]],requires_grad=True); y=grad_reverse(x,0.5); y.sum().backward(); assert torch.allclose(x.grad,torch.tensor([[-.5]]))
