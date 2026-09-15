"""Mechanism-control tests, including OpenCV interpolation table equality."""
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from run_alignment import flow_controls, representations, engine, BASE, VideoBaseline
from video_io import warp_previous


class ControlsTest(unittest.TestCase):
    def test_actual_interpolation_weights_match(self):
        rng=np.random.default_rng(34)
        # Quantize away from half-table boundaries to isolate integer offsets.
        flow=rng.uniform(-8,8,(128,128,2)).astype(np.float32)
        yy,xx=np.mgrid[:128,:128].astype(np.float32)
        indices=[]
        for v in flow_controls(flow).values():
            _,weights=cv2.convertMaps(xx+v[...,0],yy+v[...,1],cv2.CV_16SC2)
            indices.append(weights)
        for w in indices[1:]:np.testing.assert_array_equal(w,indices[0])

    def test_translation_direction_and_residual(self):
        rng=np.random.default_rng(4);previous=rng.random((64,64,3)).astype(np.float32)
        current=np.roll(previous,3,axis=1)
        flow=np.zeros((64,64,2),np.float32);flow[...,0]=-3
        warped,mask=warp_previous(previous,flow)
        np.testing.assert_allclose((current-warped)[mask],0,atol=1e-6)
        self.assertFalse(mask[:,:3].any())

    def test_stationary_control_and_common_support(self):
        frame=np.random.default_rng(6).integers(0,256,(128,128,3),dtype=np.uint8)
        cfg=engine.read(BASE/'protocol.json')
        arrays,probe,q=representations(np.stack([frame]*8),cfg)
        self.assertEqual(len(probe),8)
        for a in arrays.values():
            self.assertEqual(a.shape,(7,3,128,128));self.assertTrue(np.isfinite(a).all())
        np.testing.assert_allclose(arrays['compensation_gain'],np.abs(arrays['fractional'].astype(np.float32))-np.abs(arrays['correct'].astype(np.float32)),atol=.001,rtol=0)
        self.assertEqual(sum(p.numel() for p in VideoBaseline('aligned_bag').parameters()),49601)

    def test_all_arms_share_intersection_mask(self):
        rng=np.random.default_rng(12)
        frames=rng.integers(0,256,(8,128,128,3),dtype=np.uint8)
        flow=np.zeros((128,128,2),np.float32)
        flow[:64,:,0]=-20.25;flow[64:,:,0]=10.5;flow[...,1]=3.25
        valid=np.logical_and.reduce([warp_previous(frames[0].astype(np.float32),v)[1] for v in flow_controls(flow).values()])
        self.assertTrue(valid.any());self.assertTrue((~valid).any())
        with patch('cv2.calcOpticalFlowFarneback',return_value=flow):
            arrays,probe,q=representations(frames,engine.read(BASE/'protocol.json'))
        for a in arrays.values():self.assertTrue((a.transpose(0,2,3,1)[:,~valid,:]==0).all())
        self.assertAlmostEqual(probe[0],valid.mean())


if __name__=='__main__':unittest.main()
