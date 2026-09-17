"""Minimal candidate interface required by shared-plan RS04.

Input features come from a frozen external DINO extractor. This module does
not load/download a backbone, select a checkpoint, or claim forensic efficacy.
"""
import torch
from torch import nn
from copy import deepcopy
from .composability import branch_triplets
from .composability_torch import six_frame_response


class LocalComposability(nn.Module):
    def __init__(self,feature_dim=768,width=32,hidden=256,interior_control=False,branch_mode='temporal'):
        super().__init__()
        if min(feature_dim,width,hidden)<1:raise ValueError('Positive feature/head dimensions required')
        self.feature_dim=feature_dim;self.interior_control=interior_control
        branch_triplets(branch_mode);self.branch_mode=branch_mode
        self.spatial=nn.Sequential(nn.Conv2d(3,width,3,padding=1),nn.GELU(),
            nn.Conv2d(width,width,3,padding=1),nn.GELU())
        self.classifier=nn.Sequential(nn.LayerNorm(feature_dim+width),nn.Linear(feature_dim+width,hidden),
            nn.GELU(),nn.Dropout(.1),nn.Linear(hidden,1))

    def classify_maps(self,maps,global_tokens):
        if global_tokens.ndim!=3 or global_tokens.shape[1:]!=(6,self.feature_dim) or not torch.isfinite(global_tokens).all():
            raise ValueError('Expected finite global tokens [batch,6,feature_dim]')
        b=global_tokens.shape[0]
        if maps['responses'].shape!=(b,6,3,16,16) or maps['direct_js'].shape!=(b,6,16,16) or maps['support'].shape!=(b,6,16,16):
            raise ValueError('Unexpected correspondence-response map shape')
        support=maps['support'].bool()
        # Absolute JS is returned as a diagnostic/ablation, not a hidden input
        # to the calibrated-response candidate.
        image=maps['responses'].detach()
        if not torch.isfinite(image[support[:,:,None].expand_as(image)]).all():
            raise ValueError('Nonfinite response inside valid support')
        image=torch.where(support[:,:,None],image,torch.zeros_like(image))
        features=self.spatial(image.reshape(b*6,3,16,16)).reshape(b,6,-1,16,16)
        local=features.mean(dim=(-1,-2)).mean(dim=1)
        has_local=support.flatten(1).any(1)
        local=torch.where(has_local[:,None],local,torch.zeros_like(local))
        semantics=torch.nn.functional.normalize(global_tokens.detach(),dim=-1,eps=1e-12).mean(dim=1)
        logits=self.classifier(torch.cat([semantics,local],dim=1)).squeeze(-1)
        return dict(logits=logits,response_maps=maps['responses'],direct_js=maps['direct_js'],
            diagnostics=dict(support_fraction=support.float().mean((1,2,3)),
                semantic_fallback=~has_local,correspondence_entropies=maps['correspondence_entropies'],
                middle_probability_mass=maps['middle_probability_mass']))

    def forward(self,patch_tokens,global_tokens,branch_mode=None):
        if patch_tokens.shape!=(global_tokens.shape[0],6,256,self.feature_dim):
            raise ValueError('Expected frozen 16x16 patch tokens for six frames')
        selected=self.branch_mode if branch_mode is None else branch_mode
        maps=six_frame_response(patch_tokens.detach(),interior_control=self.interior_control,branch_mode=selected)
        result=self.classify_maps(maps,global_tokens)
        result['diagnostics']['branch_mode']=selected
        return result

    @torch.no_grad()
    def fixed_branch_sensitivity(self,patch_tokens,global_tokens):
        """No retraining: this output must not be labelled a static baseline."""
        if self.training or self.branch_mode!='temporal':
            raise ValueError('Sensitivity check requires an eval-mode temporal model')
        temporal=self(patch_tokens,global_tokens,branch_mode='temporal')
        static=self(patch_tokens,global_tokens,branch_mode='static')
        return dict(temporal_logits=temporal['logits'],static_branch_logits=static['logits'],
            logit_difference=static['logits']-temporal['logits'],
            scope='fixed_model_sensitivity_not_retrained_static_baseline')


def make_matched_control_models(seed,**head_options):
    """Fresh independent heads, identical initialization; no checkpoint reuse."""
    if 'branch_mode' in head_options:raise ValueError('The pair factory owns branch mode')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        temporal=LocalComposability(**head_options,branch_mode='temporal')
        static=LocalComposability(**head_options,branch_mode='static')
        static.load_state_dict(temporal.state_dict())
    return temporal,static


def matched_training_specs(common_recipe):
    """Prepare equal future training rules; does not freeze an actual experiment.

    Persist branch_mode alongside state_dict: weights alone cannot distinguish
    a trained static baseline from a temporal checkpoint.
    """
    required={'data_manifest_sha256','split_sha256','seeds','augmentations','optimizer','checkpoint_selection'}
    if not required.issubset(common_recipe) or 'branch_mode' in common_recipe:
        raise ValueError('Incomplete common recipe or overridden branch mode')
    specs=[dict(deepcopy(common_recipe),branch_mode=mode) for mode in ('temporal','static')]
    validate_matched_training_specs(*specs)
    return tuple(specs)


def validate_matched_training_specs(temporal,static):
    if temporal.get('branch_mode')!='temporal' or static.get('branch_mode')!='static':
        raise ValueError('Incorrect paired branch modes')
    if {k:v for k,v in temporal.items() if k!='branch_mode'}!={k:v for k,v in static.items() if k!='branch_mode'}:
        raise ValueError('Training data, seed, capacity, augmentation or selection rules differ')
