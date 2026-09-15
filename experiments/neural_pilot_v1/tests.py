import unittest
import numpy as np
import torch
from model import VideoBaseline
from video_io import warp_previous


class PilotTests(unittest.TestCase):
    def test_warp_translation_direction(self):
        rng = np.random.default_rng(7)
        previous = rng.normal(size=(12,16,3)).astype(np.float32)
        current = np.roll(previous, 2, axis=1)
        flow = np.zeros((12,16,2), np.float32)
        flow[..., 0] = -2
        warped, valid = warp_previous(previous, flow)
        self.assertFalse(valid[:,:2].any())
        self.assertTrue(valid[:,2:].all())
        np.testing.assert_allclose(warped[:,2:], current[:,2:], atol=1e-6)

    def test_identity_warp(self):
        x = np.ones((9,11,3), np.float32)
        y, valid = warp_previous(x, np.zeros((9,11,2), np.float32))
        np.testing.assert_array_equal(y, x)
        self.assertTrue(valid.all())

    def test_temporal_parameter_match(self):
        a, b = VideoBaseline("raw_temporal"), VideoBaseline("aligned_temporal")
        self.assertEqual(sum(p.numel() for p in a.parameters()), sum(p.numel() for p in b.parameters()))

    def test_frame_baseline_order_invariant(self):
        torch.manual_seed(3)
        model = VideoBaseline("frame_mean").eval()
        x = torch.randn(2,4,3,32,32)
        with torch.no_grad():
            torch.testing.assert_close(model(x), model(x.flip(1)), atol=1e-6, rtol=1e-6)

    def test_finite_gradients_and_no_cross_clip_state(self):
        model = VideoBaseline("raw_temporal")
        x = torch.randn(2,4,3,32,32)
        y = model(x)
        y.sum().backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        model.eval()
        with torch.no_grad():
            a = model(x[:1]); model(x[1:]); b = model(x[:1])
            torch.testing.assert_close(a, b)


if __name__ == "__main__":
    torch.set_num_threads(2)
    unittest.main()
