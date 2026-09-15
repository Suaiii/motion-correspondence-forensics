import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from night_qc import worker


class NightQCTests(unittest.TestCase):
    def test_qc_on_existing_synthetic_fixture(self):
        project=Path(__file__).resolve().parents[3]
        fixture=project/'research-runs/server_runtime_validation_v5/data/0.avi'
        if not fixture.exists():self.skipTest('Run synthetic smoke fixture first')
        result=worker(({'sample_id':'synthetic:0','source':'synthetic_fixture'},str(fixture)))
        self.assertEqual(result['status'],'ok',result)
        self.assertEqual(result['scope'],'source-only quality/representation inspection')
        self.assertEqual(len(result['sampling']['indices']),16)
        self.assertTrue(result['representations']['interior']['first_pair_interpolation_weights_equal'])
        self.assertTrue(result['representations']['common']['first_pair_interpolation_weights_equal'])


if __name__=='__main__':unittest.main()
