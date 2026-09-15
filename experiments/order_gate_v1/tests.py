import unittest
import numpy as np
import torch
from selection import select
from model import VideoBaseline
from video_io import warp_previous


class GateTests(unittest.TestCase):
    def test_exact_parameter_match(self):
        counts=[sum(p.numel()for p in VideoBaseline(k).parameters())for k in ('raw_temporal','aligned_temporal','raw_bag','aligned_bag')]
        self.assertEqual(counts,[49601]*4)

    def test_bag_is_order_invariant(self):
        torch.manual_seed(9);model=VideoBaseline('aligned_bag').eval()
        x=torch.randn(2,7,3,32,32)
        with torch.no_grad():torch.testing.assert_close(model(x),model(x.flip(1)),atol=1e-6,rtol=1e-6)

    def test_both_readouts_have_gradients(self):
        for kind in ('raw_temporal','raw_bag'):
            model=VideoBaseline(kind);x=torch.randn(2,7,3,32,32);model(x).sum().backward()
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all()for p in model.parameters()))

    def test_no_group_overlap_with_pilot(self):
        rows=[{'real_file':f'E:/r/origin{i//2}-Scene-{i:04d}.mp4','fake_file':f'E:/f/{i}.mp4','fake_source':'opensora' if i%2==0 else 't2vz'}for i in range(1800)]
        prior=[{'path':'E:/r/origin0-Scene-0000.mp4','label_fake':0},{'path':'E:/f/2.mp4','label_fake':1}]
        result=select(rows,prior,7)
        self.assertEqual(len(result),600)
        self.assertFalse(any(r['group_id']=='vript:origin0'or r['path']=='E:/f/2.mp4'for r in result))
        self.assertEqual(result,select(rows,prior,7))

    def test_warp_sign(self):
        x=np.random.default_rng(1).normal(size=(9,13,3)).astype(np.float32)
        flow=np.zeros((9,13,2),np.float32);flow[...,0]=-2
        warped,mask=warp_previous(x,flow)
        np.testing.assert_allclose(warped[:,2:],np.roll(x,2,axis=1)[:,2:])
        self.assertFalse(mask[:,:2].any())


if __name__=='__main__':
    torch.set_num_threads(2)
    unittest.main()
