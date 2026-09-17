import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.composability import correspondence,js_rows,shift_permutation,response_from_matrices,six_frame_response
from forensics.mechanism_sampling import choose_six


class ComposabilityTests(unittest.TestCase):
    def setUp(self):self.rng=np.random.default_rng(1729)

    def stochastic(self,n):
        x=self.rng.random((n,n));return x/x.sum(1,keepdims=True)

    def test_soft_correspondence_normalizes_and_ignores_feature_scale(self):
        a=self.rng.normal(size=(16,12));b=self.rng.normal(size=(16,12))
        p=correspondence(a,b)
        np.testing.assert_allclose(p.sum(1),1)
        np.testing.assert_allclose(p,correspondence(a*3,b*.2),atol=1e-15)

    def test_js_identity_symmetry_and_disjoint_bound(self):
        a=np.eye(4);b=np.roll(a,1,axis=1)
        np.testing.assert_array_equal(js_rows(a,a),0)
        np.testing.assert_allclose(js_rows(a,b),np.log(2))
        np.testing.assert_array_equal(js_rows(a,b),js_rows(b,a))

    def test_known_permutations_compose_exactly(self):
        a=np.eye(9)[self.rng.permutation(9)];b=np.eye(9)[self.rng.permutation(9)]
        pert=np.roll(np.arange(9),1)
        result=response_from_matrices(a,b,a@b,[pert])
        np.testing.assert_array_equal(result['direct_js'],0)
        np.testing.assert_allclose(result['response'],np.log(2))

    def test_uniform_middle_correspondence_has_zero_perturbation_response(self):
        a=np.ones((16,16))/16;b=self.stochastic(16);c=self.stochastic(16)
        result=response_from_matrices(a,b,c,[self.rng.permutation(16) for _ in range(4)])
        np.testing.assert_allclose(result['response'],0,atol=1e-15)

    def test_consistent_middle_reindexing_invariance_including_perturbations(self):
        a,b,c=[self.stochastic(16) for _ in range(3)]
        perm=self.rng.permutation(16);reindex=self.rng.permutation(16);inverse=np.argsort(reindex)
        original=response_from_matrices(a,b,c,[perm])
        renamed=response_from_matrices(a[:,reindex],b[reindex],c,[inverse[perm[reindex]]])
        np.testing.assert_allclose(original['direct_js'],renamed['direct_js'],atol=1e-15)
        np.testing.assert_allclose(original['response'],renamed['response'],atol=1e-15)

    def test_one_sided_permutation_is_not_consistent_reindexing(self):
        a=np.eye(16);b=np.eye(16);p,_=shift_permutation((4,4),0,1)
        np.testing.assert_allclose(response_from_matrices(a,b,a,[p])['response'],np.log(2))
        np.testing.assert_array_equal(a[:,p]@b[p],a)

    def test_wraps_are_explicit_and_middle_support_removes_them(self):
        tokens=self.rng.normal(size=(6,16*16,8))
        full=six_frame_response(tokens)
        interior=six_frame_response(tokens,interior_control=True)
        self.assertEqual(full['responses'].shape,(6,3,16,16))
        np.testing.assert_allclose(full['wrapped_middle_fraction'][:,0],[1/16,2/16,4/16])
        self.assertEqual(interior['middle_support_fraction'],.25)
        self.assertTrue(np.isfinite(interior['responses']).all())
        self.assertFalse(np.allclose(full['responses'],interior['responses']))

    def test_missing_conditional_support_is_not_silently_valid(self):
        a=np.eye(4);keep=np.array([True,True,False,False])
        result=response_from_matrices(a,a,a,[np.arange(4)],keep)
        np.testing.assert_array_equal(result['support'],keep)
        self.assertTrue(np.isnan(result['response'][0,~keep]).all())

    def test_sampler_short_vc2_and_joint_lags(self):
        index,meta=choose_six(np.arange(16)/10)
        np.testing.assert_array_equal(index,[0,3,5,8,10,13])
        np.testing.assert_allclose(np.array(meta['joint_triplet_intervals'])[-2:],.5,atol=1e-15)
        self.assertFalse(np.allclose(np.array(meta['joint_triplet_intervals'])[:4],.25))
        self.assertEqual(meta['target_span_seconds'],1.25)
        self.assertAlmostEqual(meta['native_duration'],1.6)

    def test_sampler_minimum_duration_translation_and_no_repeats(self):
        pts=np.arange(6)/4
        index,meta=choose_six(pts)
        np.testing.assert_array_equal(index,np.arange(6))
        shifted,other=choose_six(pts+137)
        np.testing.assert_array_equal(index,shifted)
        np.testing.assert_allclose(meta['joint_triplet_intervals'],other['joint_triplet_intervals'])
        with self.assertRaises(ValueError):choose_six(np.arange(6)/5)
        with self.assertRaises(ValueError):choose_six(np.arange(6))

    def test_reject_malformed_probability_and_permutation_inputs(self):
        a=np.eye(4)
        with self.assertRaises(ValueError):js_rows(a*2,a)
        with self.assertRaises(ValueError):response_from_matrices(a,a,a,[np.zeros(4,dtype=int)])
        with self.assertRaises(ValueError):correspondence(a,a,temperature=0)
        with self.assertRaises(ValueError):six_frame_response(np.zeros((8,16,4)),grid=(4,4),scales=(1,))


if __name__=='__main__':unittest.main()
