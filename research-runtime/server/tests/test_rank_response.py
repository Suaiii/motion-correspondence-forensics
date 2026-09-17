import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.rank_response import displacement_orbit,bilinear_target,orbit_rank,local_response,local_histograms


class RankResponseTests(unittest.TestCase):
    def test_fractional_weights_and_integer_lengths_are_shared(self):
        flow=np.random.default_rng(11).uniform(-3,3,(9,9,2));ops=displacement_orbit(flow)
        frac=flow-np.floor(flow)
        np.testing.assert_allclose(ops-np.floor(ops),np.broadcast_to(frac,ops.shape),atol=1e-14)
        lengths=(np.floor(ops)**2).sum(-1)
        np.testing.assert_array_equal(lengths,np.broadcast_to(lengths[0],lengths.shape))

    def test_analytic_translation_bilinear_surface(self):
        yy,xx=np.mgrid[:24,:24]
        target=np.stack([xx+2*yy,3*xx-yy,.1*xx*yy],-1).astype(float)
        flow=np.zeros((24,24,2));flow[...,0]=1.25;flow[...,1]=2.5
        reference=np.stack([xx+1.25+2*(yy+2.5),3*(xx+1.25)-(yy+2.5),.1*(xx+1.25)*(yy+2.5)],-1)
        warped,valid=bilinear_target(target,flow)
        np.testing.assert_allclose(warped[valid],reference[valid],atol=1e-12)
        response=local_response(reference,target,flow)
        self.assertGreater(response['support'].mean(),.5)
        np.testing.assert_allclose(response['rank'][response['support']],.9375)

    def test_common_positive_affine_photometric_change(self):
        yy,xx=np.mgrid[:16,:16];target=np.stack([xx,yy,xx*yy],-1).astype(float)
        flow=np.broadcast_to([1.2,.3],(16,16,2))
        reference=np.stack([xx+1.2,yy+.3,(xx+1.2)*(yy+.3)],-1)
        a=local_response(reference,target,flow);b=local_response(reference*3+7,target*3+7,flow)
        np.testing.assert_array_equal(a['rank'],b['rank'])

    def test_monotone_error_transform_and_orbit_neutrality(self):
        rng=np.random.default_rng(21);errors=rng.integers(0,8,(8,5,7)).astype(float)
        np.testing.assert_array_equal(orbit_rank(errors),orbit_rank(errors**3+2))
        np.testing.assert_allclose(np.mean([orbit_rank(errors,k) for k in range(8)],0),.5)

    def test_zero_integer_motion_has_no_invented_response(self):
        x=np.random.default_rng(9).normal(size=(16,16,3));flow=np.zeros((16,16,2))+.2
        result=local_response(x,x,flow)
        np.testing.assert_array_equal(result['rank'],.5)
        self.assertEqual(result['diagnostics']['nontrivial_orbit_fraction'],0)

    def test_support_does_not_wrap_or_hide_norm_mismatch(self):
        x=np.ones((8,8,1));flow=np.broadcast_to([3.2,.8],(8,8,2))
        result=local_response(x,x,flow)
        self.assertFalse(result['support'][0,0])
        self.assertGreater(result['diagnostics']['max_total_displacement_norm_change'],0)
        self.assertFalse(result['diagnostics']['applied_operator_magnitude_matched'])
        empty=local_response(x,x,np.ones((8,8,2))*20)
        self.assertFalse(empty['support'].any())
        np.testing.assert_array_equal(empty['rank'],.5)

    def test_integer_mode_really_matches_applied_motion_magnitudes(self):
        yy,xx=np.mgrid[:24,:24];image=np.stack([xx,yy,xx*yy],-1).astype(float)
        flow=np.random.default_rng(4).uniform(-3,3,(24,24,2))
        result=local_response(image,image,flow,integer_only=True)
        self.assertTrue(result['diagnostics']['applied_operator_magnitude_matched'])
        self.assertEqual(result['diagnostics']['max_total_displacement_norm_change'],0)
        self.assertLessEqual(result['diagnostics']['quantization_l2_error_max'],np.sqrt(.5))

    def test_quantization_does_not_create_signal_for_subpixel_motion(self):
        image=np.random.default_rng(18).normal(size=(16,16,3));flow=np.broadcast_to([-.2,.3],(16,16,2))
        original=local_response(image,image,flow)
        quantized=local_response(image,image,flow,integer_only=True)
        self.assertGreater(original['diagnostics']['max_total_displacement_norm_change'],1)
        np.testing.assert_array_equal(quantized['rank'],.5)
        self.assertAlmostEqual(quantized['diagnostics']['quantization_l2_error_max'],np.sqrt(.13))

    def test_local_readout_retains_arrangement_and_empty_coverage(self):
        a=np.zeros((8,8));a[4:]=1;b=np.indices((8,8)).sum(0)%2;mask=np.ones((8,8),bool)
        ha,_=local_histograms(a,mask);hb,_=local_histograms(b,mask)
        self.assertFalse(np.array_equal(ha,hb))
        np.testing.assert_allclose(ha.sum((0,1)),hb.sum((0,1)))
        empty,cov=local_histograms(a,np.zeros_like(mask))
        self.assertEqual(empty.sum(),0);self.assertEqual(cov.sum(),0)

    def test_reject_nonfinite_and_shape_errors(self):
        with self.assertRaises(ValueError):displacement_orbit(np.ones((2,2,3)))
        with self.assertRaises(ValueError):orbit_rank(np.array([[np.nan],[0.]]))
        with self.assertRaises(ValueError):local_histograms(np.zeros((7,7)),np.ones((7,7),bool))


if __name__=='__main__':
    unittest.main()
