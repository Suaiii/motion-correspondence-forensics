import copy
import sys
from pathlib import Path
import tempfile
import json
import unittest
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.composability_config import A,C,descriptor,cache_identity,candidate_training_specs,validate_candidate_training_specs,load_candidate_c_config
from forensics.composability import correspondence_response as np_response,six_frame_response,shift_permutation
from forensics.composability_torch import correspondence_response as th_response
from forensics.mechanism_sampling import choose_six,choose_centered_three
from forensics.local_composability import LocalComposability,make_candidate_control_models


class CandidateCChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.z=torch.from_numpy(np.random.default_rng(1029).normal(size=(1,3,256,8)).astype(np.float32))
        cls.g=torch.from_numpy(np.random.default_rng(1030).normal(size=(1,3,8)).astype(np.float32))

    def test_sampling_A_subset_and_VFR(self):
        fixtures=[np.arange(16)/10,np.arange(48)/24,np.arange(7)/4,
            np.cumsum(np.resize([.03,.05,.07,.04],60))]
        for pts in fixtures:
            ia,ma=choose_six(pts);ic,mc=choose_centered_three(pts)
            np.testing.assert_array_equal(ic,ia[[1,3,5]])
            np.testing.assert_allclose(mc['targets'],np.array(ma['targets'])[[1,3,5]],atol=1e-12)
            self.assertEqual(len(set(ic)),3)
            self.assertFalse(mc['real_source_joint_support_established'])
            shifted,_=choose_centered_three(pts+19)
            np.testing.assert_array_equal(shifted,ic)

    def test_sampler_ties_bounds_and_bad_pts(self):
        index,_=choose_centered_three(np.arange(9)*.2)
        np.testing.assert_array_equal(index,[2,4,7])
        at=np.array([0,.125,.375,.5,.625,.75,.875,1,1.125,1.25,1.375])
        _,m=choose_centered_three(at)
        self.assertAlmostEqual(max(abs(v) for v in m['timing_error']),.125)
        over=at.copy();over[1]-=2e-6;over[2]+=2e-6
        with self.assertRaisesRegex(ValueError,'error'):choose_centered_three(over)
        choose_centered_three(np.arange(6)*(1.5-.9e-6)/6)
        with self.assertRaisesRegex(ValueError,'duration'):
            choose_centered_three(np.arange(6)*(1.5-1.1e-6)/6)
        for pts in ([],[0,.2,.4],[0,1,2],[0,.5,.5,1.5],[0,np.nan,1.5],
                    [0,None,1.5],[0,np.inf,2],[[0,.5,1.5]],[0,1,.5,1.5]):
            with self.subTest(pts=pts),self.assertRaises(ValueError):choose_centered_three(pts)

    def test_C_numpy_torch_and_A_map_subset(self):
        for mode,n in [('temporal',1),('static',3),('anchor_static',1)]:
            r=th_response(self.z,candidate_id=C,branch_mode=mode)
            q=np_response(self.z[0].numpy(),candidate_id=C,branch_mode=mode)
            self.assertEqual(r['responses'].shape,(1,n,3,16,16))
            np.testing.assert_allclose(r['responses'][0],q['responses'],atol=2e-6)
            self.assertEqual(r['unique_affinity_matrices'],1 if mode=='anchor_static' else 3)
        six=np.random.default_rng(17).normal(size=(6,256,8))
        np.testing.assert_allclose(np_response(six[[1,3,5]],candidate_id=C)['responses'][0],
                                   six_frame_response(six)['responses'][5],atol=1e-12)

    def test_reject_padded_frames_and_wrong_map_protocol(self):
        padded=self.z.repeat(1,2,1,1)
        with self.assertRaises(ValueError):th_response(padded,candidate_id=C)
        model=LocalComposability(feature_dim=8,width=4,hidden=8,candidate_id=C)
        for changes in ({'candidate_id':A},{'frame_count':6},{'triplets':((2,1,0),)},
                        {'operator':dict(temperature=.2,grid=[16,16],scales=[1,2,4],interior_control=False)}):
            maps=th_response(self.z,candidate_id=C);maps.update(changes)
            with self.assertRaises(ValueError):model.classify_maps(maps,self.g)

    def test_all_three_semantic_vectors_retained_in_each_arm(self):
        models=make_candidate_control_models(29,feature_dim=8,width=4,hidden=8)
        expected=torch.nn.functional.normalize(self.g,dim=-1).mean(1)
        for mode,model in models.items():
            model.eval();seen=[]
            hook=model.classifier[0].register_forward_pre_hook(lambda module,args:seen.append(args[0].detach()))
            r=model(self.z,self.g);hook.remove()
            torch.testing.assert_close(seen[0][:,:8],expected)
            self.assertEqual(r['diagnostics']['frame_count'],3)
            if mode=='anchor_static':self.assertIn('diagnostic',r['diagnostics']['control_scope'])

    def test_full_capacity_independent_parameters_and_frozen_input_gradients(self):
        models=make_candidate_control_models(43)
        pointers=[]
        for model in models.values():
            self.assertEqual(sum(p.numel() for p in model.parameters()),217057)
            pointers.append({p.data_ptr() for p in model.parameters()})
        self.assertFalse(pointers[0]&pointers[1] or pointers[0]&pointers[2] or pointers[1]&pointers[2])
        for name,value in models['temporal'].state_dict().items():
            for mode in ('static','anchor_static'):
                torch.testing.assert_close(value,models[mode].state_dict()[name])
        for mode,model in make_candidate_control_models(43,feature_dim=8,width=4,hidden=8).items():
            z=self.z.clone().requires_grad_();g=self.g.clone().requires_grad_()
            model(z,g)['logits'].sum().backward()
            self.assertIsNone(z.grad);self.assertIsNone(g.grad)
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))

    def test_semantic_fallback_and_fixed_head_sensitivity(self):
        models=make_candidate_control_models(59,feature_dim=8,width=4,hidden=8)
        seen=[]
        for mode,model in models.items():
            model.eval();maps=th_response(self.z,candidate_id=C,branch_mode=mode)
            maps['support']=torch.zeros_like(maps['support'])
            maps['responses']=torch.full_like(maps['responses'],float('nan'))
            r=model.classify_maps(maps,self.g);seen.append(r['logits'])
            self.assertTrue(r['diagnostics']['semantic_fallback'].all())
        for item in seen[1:]:torch.testing.assert_close(item,seen[0])
        model=models['temporal'];before={k:v.clone() for k,v in model.state_dict().items()}
        result=model.fixed_branch_sensitivity(self.z,self.g)
        self.assertIn('not_retrained',result['scope'])
        for k,v in before.items():torch.testing.assert_close(v,model.state_dict()[k])

    def test_translation_null_logits_and_limited_scope(self):
        rng=np.random.default_rng(71);base=rng.normal(size=(256,8))
        indices=[shift_permutation((16,16),*offset)[0] for offset in [(0,0),(1,2),(2,3)]]
        z=torch.tensor(np.stack([base[i] for i in indices])[None],dtype=torch.float64)
        t=th_response(z,candidate_id=C);a=th_response(z,candidate_id=C,branch_mode='anchor_static')
        torch.testing.assert_close(t['responses'],a['responses'],atol=1e-12,rtol=0)
        models=make_candidate_control_models(71,feature_dim=8,width=4,hidden=8)
        for model in models.values():model.double().eval()
        torch.testing.assert_close(models['temporal'](z,self.g.double())['logits'],
            models['anchor_static'](z,self.g.double())['logits'],atol=1e-12,rtol=0)
        ti=th_response(z,candidate_id=C,interior_control=True)
        ai=th_response(z,candidate_id=C,branch_mode='anchor_static',interior_control=True)
        self.assertGreater(float((ti['responses']-ai['responses']).abs().max()),1e-6)
        arbitrary=torch.tensor(np.stack([base[rng.permutation(256)] for _ in range(3)])[None])
        ts=th_response(arbitrary,candidate_id=C);ss=th_response(arbitrary,candidate_id=C,branch_mode='anchor_static')
        self.assertGreater(float((ts['responses']-ss['responses']).abs().max()),1e-6)

    def test_checkpoint_identity_rejects_legacy_other_candidate_and_branch(self):
        models=make_candidate_control_models(17,feature_dim=8,width=4,hidden=8)
        model=models['temporal'];payload=model.checkpoint_payload()
        clone=LocalComposability(feature_dim=8,width=4,hidden=8,candidate_id=C)
        clone.load_compatible_checkpoint(payload)
        before={k:v.clone() for k,v in model.state_dict().items()}
        bad=[model.state_dict(),models['static'].checkpoint_payload(),
             LocalComposability(feature_dim=8,width=4,hidden=8).checkpoint_payload()]
        changed=copy.deepcopy(payload);changed['identity']['protocol']['sampler_sha256']='outdated';bad.append(changed)
        corrupt=copy.deepcopy(payload);corrupt['state_dict']['spatial.0.weight'].fill_(float('nan'));bad.append(corrupt)
        wrongshape=copy.deepcopy(payload);wrongshape['state_dict']['classifier.3.weight']=torch.zeros(1,99);bad.append(wrongshape)
        for item in bad:
            with self.assertRaises(ValueError):model.load_compatible_checkpoint(item)
        for k,v in before.items():torch.testing.assert_close(v,model.state_dict()[k])

    def test_cache_keys_bind_processing_frames_and_control_scope(self):
        p=dict(original_sha256='0'*64,processed_video_sha256='1'*64,backbone_sha256='2'*64,
            selected_indices=[1,3,5],selected_pts=[.25,.75,1.25],preprocessing={'resize':224},
            precision='float32',augmentation_identity='none')
        first=cache_identity(C,'temporal',p)['sha256']
        other=copy.deepcopy(p);other['preprocessing']['resize']=504
        keys=[cache_identity(C,mode,p)['sha256'] for mode in ['temporal','static','anchor_static']]
        keys += [cache_identity(C,'temporal',other)['sha256'],cache_identity(C,'temporal',p,True)['sha256']]
        self.assertEqual(len(set(keys)),5)
        self.assertEqual(first,cache_identity(C,'temporal',p)['sha256'])
        with self.assertRaises(ValueError):cache_identity(A,'temporal',p)
        other=copy.deepcopy(p);other['selected_pts'][1]=float('nan')
        with self.assertRaises(ValueError):cache_identity(C,'temporal',other)
        other=copy.deepcopy(p);other['selected_indices']=[5,3,1]
        with self.assertRaises(ValueError):cache_identity(C,'temporal',other)

    def test_training_rules_match_but_diagnostic_scope_differs(self):
        common=dict(data_manifest_sha256='fixture',split_sha256='fixture',seeds=[17],augmentations=['fixture'],
                    optimizer={'name':'not-run'},checkpoint_selection='calibration_only',head={'feature_dim':768,'width':32,'hidden':256})
        specs=candidate_training_specs(common,include_anchor=True)
        validate_candidate_training_specs(*specs)
        bad=copy.deepcopy(specs);bad[2]['protocol']['control_scope']='all_observed_frames_static_baseline'
        with self.assertRaises(ValueError):validate_candidate_training_specs(*bad)
        bad=copy.deepcopy(specs);bad[1]['head']['width']=64
        with self.assertRaises(ValueError):validate_candidate_training_specs(*bad)

    def test_checked_in_config_is_exact_and_not_training_authority(self):
        path=Path(__file__).resolve().parents[1]/'configs/candidate_c_centered3_v1.json'
        config=load_candidate_c_config(path)
        self.assertFalse(config['formal_training_authorized'])
        with tempfile.TemporaryDirectory() as temp:
            config['temperature']=.2;p=Path(temp)/'bad.json';p.write_text(json.dumps(config))
            with self.assertRaises(ValueError):load_candidate_c_config(p)


if __name__=='__main__':unittest.main()
