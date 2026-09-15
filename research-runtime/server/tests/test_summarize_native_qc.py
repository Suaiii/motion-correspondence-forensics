import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('summary', Path(__file__).resolve().parents[1] / 'scripts/summarize_native_qc.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SummaryTest(unittest.TestCase):
    def test_cross_source_identity_and_incomplete_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'records').mkdir()
            def save(name, value):
                (root / name).write_text(json.dumps(value), encoding='utf-8')
            for source in ('ms', 'vc2'):
                save('records/' + source + '.json', {
                    'sample_id': source, 'source': source, 'status': 'ok',
                    'file_sha256': source, 'sampled_frame_sha256': ['shared'] * 16,
                    'phash_three_frames': ['candidate'] * 3,
                })
                save('extraction_' + source + '.json', {})
            save('qc_lock.json', {'requested': 2})
            complete = {'complete': True, 'requested': 2, 'completed': 2,
                        'counts': {'ms': {'ok': 1}, 'vc2': {'ok': 1}}}
            save('qc_summary.json', complete)
            result, groups = module.summarize(root)
            self.assertEqual(result['duplicate_counts']['file_sha256']['groups'], 0)
            self.assertEqual(result['duplicate_counts']['sampled_frame_sha256']['cross_source_groups'], 1)
            self.assertEqual(len(groups['phash_three_frames'][0]['members']), 2)
            self.assertFalse(result['classification_metrics_computed'])
            complete['complete'] = False
            save('qc_summary.json', complete)
            with self.assertRaisesRegex(ValueError, 'not completed'):
                module.summarize(root)
            complete['complete'] = True
            save('qc_summary.json', complete)
            (root / 'records/vc2.json').unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete record coverage'):
                module.summarize(root)


if __name__ == '__main__':
    unittest.main()
