import copy
import json
import sys
import tempfile
import unittest
import io
import zipfile
from unittest.mock import patch
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.common import safe_path,sha,read,write
from forensics.manifest import audit,split_groups
from forensics.controls import fields,pair,warp
from forensics import budget


def record(i,role='fit',label=0,scope='development'):
    return {'sample_id':f's{i}','path':f'v/{i}.mp4','sha256':f'{i:064x}','label_fake':label,
        'source':'fake' if label else 'real','generator':'generator' if label else None,'task':'T2V' if label else 'real',
        'source_group':f'original:{i}','reference_group':None,'prompt_group':None,'ancestry_status':'verified',
        'role':role,'scope':scope,'dataset_revision':'test-fixture','license':'synthetic'}


class ManifestTests(unittest.TestCase):
    def test_cross_platform_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in ('../x','/x','C:/x','C:x','foo\\bar'):
                with self.assertRaises(ValueError):safe_path(tmp,path)
            self.assertEqual(safe_path(tmp,'a/b').relative_to(Path(tmp)).as_posix(),'a/b')
    def test_duplicate_and_unknown_ancestry(self):
        a=record(1);b=record(2);b['sha256']=a['sha256']
        self.assertFalse(audit([a,b])['valid'])
        b['sha256']='2'*64;b['ancestry_status']='unknown'
        self.assertFalse(audit([a,b])['valid'])
    def test_reference_links_real_source(self):
        a=record(1);b=record(2,'dev_audit',1);b['reference_group']=a['source_group']
        self.assertFalse(audit([a,b])['valid'])
        assigned=split_groups([a,b])
        self.assertEqual(assigned[0]['role'],assigned[1]['role'])
        self.assertTrue(audit(assigned)['valid'])
    def test_final_and_ood_barriers(self):
        a=record(1,label=1);b=record(2,'final_audit',1,'final')
        self.assertFalse(audit([a,b])['valid'])
        b['role']='ood_dev';b['scope']='development'
        self.assertFalse(audit([a,b])['valid'])
        b['generator']='newgen';self.assertTrue(audit([a,b])['valid'])
    def test_historical_is_profile_only(self):
        a=record(1,scope='historical');self.assertFalse(audit([a])['valid'])
        a['role']='profile';a['ancestry_status']='unknown';self.assertTrue(audit([a])['valid'])
    def test_deterministic_grouped_split(self):
        rr=[record(i+1,label=i%2) for i in range(60)]
        a=split_groups(rr);b=split_groups(list(reversed(rr)))
        self.assertEqual(a,b);self.assertTrue(audit(a)['valid'])
        self.assertEqual({r['role'] for r in a},{'fit','calibration','dev_audit'})


class ControlTests(unittest.TestCase):
    def test_exact_opencv_interpolation_indices(self):
        f=np.random.default_rng(1).uniform(-25,25,(64,64,2)).astype(np.float32)
        actual,fraction,nulls,_=fields(f,12)
        yy,xx=np.mgrid[:64,:64].astype(np.float32)
        tables=[cv2.convertMaps(xx+v[...,0],yy+v[...,1],cv2.CV_16SC2)[1] for v in [actual,fraction]+nulls]
        for t in tables[1:]:np.testing.assert_array_equal(t,tables[0])
        self.assertLessEqual(abs(fraction).max(),.5)
    def test_known_translation_and_self_warp(self):
        previous=np.random.default_rng(4).random((64,64,3),dtype=np.float32);current=np.roll(previous,3,axis=1)
        flow=np.zeros((64,64,2),np.float32);flow[...,0]=-3
        values,q=pair(previous,current,flow)
        np.testing.assert_array_equal(values['correct'],0)
        self.assertGreater(abs(values['raw']).mean(),.1)
        zero,_=pair(previous,previous,np.zeros_like(flow))
        for v in zero.values():np.testing.assert_array_equal(v,0)
    def test_common_mask_and_clipping(self):
        p=np.random.default_rng(3).random((64,64,3),dtype=np.float32);f=np.full((64,64,2),30.2,np.float32)
        v,q=pair(p,p,f);self.assertEqual(q['clipped_fraction'],1.)
        self.assertEqual(v['correct'].shape,(3,32,32))
        vals,_=pair(p,p,f,support='common');valid=warp(p,fields(f)[0])[1]
        for a in vals.values():self.assertTrue((a[:,~valid]==0).all())
    def test_four_control_formula(self):
        rng=np.random.default_rng(7);p=rng.random((64,64,3),dtype=np.float32);c=rng.random((64,64,3),dtype=np.float32);f=rng.uniform(-5,5,(64,64,2)).astype(np.float32)
        v,_=pair(p,c,f)
        residual=v['concat'].reshape(5,3,32,32)
        np.testing.assert_allclose(v['multi_contrast'],np.abs(residual[1:]).mean(0)-np.abs(residual[0]),atol=1e-7)


class BudgetTests(unittest.TestCase):
    def test_budget_caps_and_real_overspend(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json';budget.init(p)
            budget.reserve(p,'x','profile',10,5,0,'quoted-provider-price')
            with self.assertRaises(ValueError):budget.reserve(p,'y','profile',100,5,0,'quote')
            with self.assertRaises(ValueError):budget.reserve(p,'y','method',181,1,0,'quote')
            with self.assertRaises(ValueError):budget.reserve(p,'y','profile',float('nan'),1,0,'quote')
            budget.settle(p,'x',60,11,'bill-123');self.assertTrue(read(p)['entries'][0]['over_reservation'])
            with self.assertRaises(ValueError):budget.admit(p,'x','run','profile')
    def test_exclusive_reservation_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ledger.json';budget.init(p);budget.reserve(p,'x','mechanism',10,5,0,'quote')
            budget.admit(p,'x','run_a','mechanism')
            with self.assertRaises(ValueError):budget.admit(p,'x','run_b','mechanism')


class ArchiveTests(unittest.TestCase):
    def test_remote_index_and_selected_member(self):
        from forensics.data import remote_zip
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_STORED) as z:
            z.writestr('video/selected.txt','selected');z.writestr('large.bin',b'x'*(2*2**20));z.writestr('../escape.txt','unsafe')
        blob=payload.getvalue()
        class Response(io.BytesIO):
            status=206
        def serve(request,timeout):
            start,end=map(int,request.get_header('Range').split('=')[1].split('-'))
            r=Response(blob[start:end+1]);r.headers={'Content-Range':f'bytes {start}-{end}/{len(blob)}'};return r
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);catalog=root/'catalog.json';write(catalog,{'repositories':[{'repo':'fixture/data','revision':'a'*40,'files':[{'path':'archive.zip','size':len(blob),'lfs':{'oid':'b'*64}}]}]})
            with patch('urllib.request.urlopen',side_effect=serve):
                index=remote_zip(catalog,'fixture/data','archive.zip',output=root/'index.json')
                self.assertLess(index['transferred_bytes'],len(blob)//10)
                remote_zip(catalog,'fixture/data','archive.zip',members=['video/selected.txt'],data_root=root/'data',max_gib=.01)
                self.assertEqual((root/'data/video/selected.txt').read_text(),'selected')
                self.assertFalse((root/'data/large.bin').exists())
                receipt=read(root/'data/video/selected.txt.receipt.json');self.assertFalse(receipt['full_archive_hash_verified'])
                with self.assertRaises(ValueError):remote_zip(catalog,'fixture/data','archive.zip',members=['../escape.txt'],data_root=root/'data',max_gib=.01)
    def test_no_full_body_fallback(self):
        from forensics.data import RangeReader
        class Response(io.BytesIO):
            status=200;headers={}
        with patch('urllib.request.urlopen',return_value=Response(b'not-a-range')):
            with self.assertRaises(ValueError):RangeReader('https://example.test/pinned',20).read(5)


class LossTests(unittest.TestCase):
    def test_selection_cannot_drop_all_tokens(self):
        import torch
        from forensics.model import selective_consistency
        clean=torch.tensor([[[1.,0.],[1.,0.],[0.,1.],[0.,1.]]],requires_grad=True)
        degraded=torch.tensor([[[1.,.1],[1.,.2],[1.,0.],[1.,0.]]],requires_grad=True)
        loss=selective_consistency(clean,degraded);loss.backward()
        self.assertIsNone(clean.grad)
        self.assertTrue((degraded.grad[:,:2].abs().sum(-1)>0).all())
        self.assertTrue((degraded.grad[:,2:]==0).all())


if __name__=='__main__':unittest.main()
