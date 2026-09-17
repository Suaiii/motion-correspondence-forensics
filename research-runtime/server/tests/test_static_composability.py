import sys
from pathlib import Path
import unittest
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.composability import six_frame_response as numpy_response,STATIC_TRIPLETS
from forensics.composability_torch import six_frame_response
from forensics.local_composability import make_matched_control_models,matched_training_specs,validate_matched_training_specs


class StaticControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.tokens=np.random.default_rng(713).normal(size=(1,6,256,8)).astype(np.float32)

    def setUp(self):torch.manual_seed(713)

    def test_static_uses_each_of_six_distinct_frames_and_matches_reference(self):
        z=torch.from_numpy(self.tokens)
        actual=six_frame_response(z,branch_mode='static')
        expected=numpy_response(self.tokens[0],branch_mode='static')
        self.assertEqual(actual['triplets'],STATIC_TRIPLETS)
        np.testing.assert_allclose(actual['responses'][0],expected['responses'],atol=2e-6)
        for i in range(6):
            single=np.repeat(self.tokens[0,i:i+1],6,axis=0)
            target=numpy_response(single)['responses'][0]
            np.testing.assert_allclose(actual['responses'][0,i],target,atol=2e-6)
        self.assertFalse(torch.allclose(actual['responses'][:,0],actual['responses'][:,5]))

    def test_static_frame_permutation_is_equivariant_then_unordered(self):
        z=torch.from_numpy(self.tokens);order=torch.tensor([5,2,1,4,0,3])
        a=six_frame_response(z,branch_mode='static');b=six_frame_response(z[:,order],branch_mode='static')
        torch.testing.assert_close(b['responses'],a['responses'][:,order])
        _,head=make_matched_control_models(71,feature_dim=8,width=4,hidden=8);head.eval()
        globals_=torch.randn(1,6,8)
        torch.testing.assert_close(head(z,globals_)['logits'],head(z[:,order],globals_[:,order])['logits'])

    def test_identical_frames_make_static_and_temporal_branches_equal(self):
        z=torch.from_numpy(self.tokens[:,0:1]).repeat(1,6,1,1)
        a=six_frame_response(z);b=six_frame_response(z,branch_mode='static')
        torch.testing.assert_close(a['responses'],b['responses'])

    def test_same_parameter_count_and_initialization_but_independent_storage(self):
        temporal,static=make_matched_control_models(17)
        self.assertEqual(sum(p.numel() for p in temporal.parameters()),217057)
        self.assertEqual(sum(p.numel() for p in static.parameters()),217057)
        for (n,a),(m,b) in zip(temporal.named_parameters(),static.named_parameters()):
            self.assertEqual(n,m);torch.testing.assert_close(a,b);self.assertNotEqual(a.data_ptr(),b.data_ptr())
        self.assertEqual(temporal.branch_mode,'temporal');self.assertEqual(static.branch_mode,'static')

    def test_fixed_replacement_retains_all_six_semantics_and_weights(self):
        temporal,_=make_matched_control_models(29,feature_dim=8,width=4,hidden=8);temporal.eval()
        z=torch.from_numpy(self.tokens);globals_=torch.randn(1,6,8)
        captured=[]
        hook=temporal.classifier[0].register_forward_pre_hook(lambda module,args: captured.append(args[0].detach().clone()))
        before={k:v.clone() for k,v in temporal.state_dict().items()}
        result=temporal.fixed_branch_sensitivity(z,globals_);hook.remove()
        expected=torch.nn.functional.normalize(globals_,dim=-1).mean(1)
        self.assertEqual(len(captured),2)
        for features in captured:torch.testing.assert_close(features[:,:8],expected)
        for k,v in before.items():torch.testing.assert_close(v,temporal.state_dict()[k])
        self.assertIn('not_retrained',result['scope'])
        self.assertTrue(torch.isfinite(result['logit_difference']).all())
        temporal.train()
        with self.assertRaises(ValueError):temporal.fixed_branch_sensitivity(z,globals_)

    def test_static_head_gradients_and_frozen_input_boundary(self):
        _,static=make_matched_control_models(43,feature_dim=8,width=4,hidden=8)
        z=torch.from_numpy(self.tokens.copy()).requires_grad_();globals_=torch.randn(1,6,8,requires_grad=True)
        static(z,globals_)['logits'].sum().backward()
        self.assertIsNone(z.grad);self.assertIsNone(globals_.grad)
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in static.parameters()))

    def test_empty_static_support_uses_same_semantic_fallback(self):
        temporal,static=make_matched_control_models(59,feature_dim=8,width=4,hidden=8)
        temporal.eval();static.eval();globals_=torch.randn(1,6,8)
        maps=six_frame_response(torch.from_numpy(self.tokens),branch_mode='static')
        maps['support']=torch.zeros_like(maps['support']);maps['responses']=torch.full_like(maps['responses'],float('nan'))
        a=temporal.classify_maps(maps,globals_);b=static.classify_maps(maps,globals_)
        torch.testing.assert_close(a['logits'],b['logits']);self.assertTrue(b['diagnostics']['semantic_fallback'].all())

    def test_training_rule_mismatch_is_rejected(self):
        common=dict(data_manifest_sha256='synthetic-fixture',split_sha256='fixture-split',seeds=[17,29],
            augmentations=['same-fixture'],optimizer={'name':'placeholder-not-frozen'},checkpoint_selection='calibration_only',width=32)
        a,b=matched_training_specs(common);validate_matched_training_specs(a,b)
        b['checkpoint_selection']='last_epoch'
        with self.assertRaises(ValueError):validate_matched_training_specs(a,b)
        self.assertEqual(a['checkpoint_selection'],'calibration_only')

    def test_compute_difference_is_recorded_not_assumed_equal(self):
        z=torch.from_numpy(self.tokens)
        temporal=six_frame_response(z);static=six_frame_response(z,branch_mode='static')
        self.assertEqual(temporal['unique_affinity_matrices'],11)
        self.assertEqual(static['unique_affinity_matrices'],6)
        self.assertEqual(temporal['responses'].shape,static['responses'].shape)

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):six_frame_response(torch.from_numpy(self.tokens),branch_mode='first_frame_only')


if __name__=='__main__':unittest.main()
