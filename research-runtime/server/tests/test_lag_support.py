import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from forensics.lag_support import support_report, timing_vector


def row(name, source, label, pts):
    return dict(sample_id=name,source=source,label_fake=label,group=name,role='development',sampling={'pts':list(pts)})


class LagSupportTests(unittest.TestCase):
    def test_nominal_eight_hz_does_not_establish_common_support(self):
        target=np.arange(8)/8
        actual30=np.floor(target*30+.5)/30
        data=[row('real','real30',0,actual30),row('fake','fake8',1,target)]
        whole,_=support_report(data,'all_adjacent',.002)
        self.assertEqual(whole['real_fake_source_pairs'][0]['discrete_overlap_coefficient'],0)
        half,_=support_report(data,'half_second',.002)
        self.assertEqual(half['real_fake_source_pairs'][0]['discrete_overlap_coefficient'],1)

    def test_rounded_overlap_retains_continuous_difference(self):
        data=[row('r','real',0,np.arange(8)*.125125),row('f','fake',1,np.arange(8)*.125)]
        summary,_=support_report(data,'half_second',.002)
        pair=summary['real_fake_source_pairs'][0]
        self.assertEqual(pair['discrete_overlap_coefficient'],1)
        self.assertAlmostEqual(pair['largest_within_bin_mean_timing_difference'],.0005)

    def test_lag_filter_does_not_depend_on_label(self):
        pts=np.arange(8)*.13
        data=[row('r','real',0,pts),row('f','fake',1,pts)]
        summary,records=support_report(data,'half_second',.002)
        self.assertFalse(any(r['lag_eligible'] for r in records))
        self.assertIsNone(summary['real_fake_source_pairs'][0]['discrete_overlap_coefficient'])

    def test_origin_translation_is_ignored(self):
        pts=np.arange(8)*.125
        np.testing.assert_allclose(timing_vector({'pts':pts},'all_adjacent'),timing_vector({'pts':pts+791},'all_adjacent'))

    def test_cross_label_origin_counts_remain_groups(self):
        data=[row('r1','real',0,np.arange(8)/8),row('r2','real',0,np.arange(8)/8),row('f','fake',1,np.arange(8)/8)]
        for r in data:r['group']='same_origin'
        summary,_=support_report(data,'half_second',.002)
        self.assertEqual(summary['real_fake_source_pairs'][0]['supported_groups'],{'real':1,'fake':1})

    def test_refuse_bad_inputs_and_final_data(self):
        r=row('r','real',0,np.arange(8)/8)
        with self.assertRaises(ValueError):support_report([r,r],'half_second',.002)
        for pts in ([0]*8,[0,1,2,np.nan,4,5,6,7],list(range(7))):
            with self.assertRaises(ValueError):timing_vector({'pts':pts},'all_adjacent')
        with self.assertRaises(ValueError):support_report([dict(r,role='final_confirmation')],'half_second',.002)
        with self.assertRaises(ValueError):support_report([r],'half_second',0)


if __name__=='__main__':
    unittest.main()
