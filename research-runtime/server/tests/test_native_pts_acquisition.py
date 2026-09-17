"""Local fixtures only; every subprocess boundary is mocked."""
import contextlib
import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1]/'scripts/acquire_native_pts.py'
spec = importlib.util.spec_from_file_location('pts_collector', FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ROOT = Path(__file__).resolve().parents[3]


class Probe:
    def __init__(self, argv, stdout, stderr, env, raw=None, error=b'', running=False):
        assert env['CUDA_VISIBLE_DEVICES'] == ''
        assert '-show_frames' in argv and '-read_intervals' not in argv
        stdout.write(json.dumps(raw or {'streams':[{'time_base':'1/10'}],
            'frames':[{'pts':0},{'pts':1}]}).encode())
        stderr.write(error)
        stdout.flush(); stderr.flush()
        self.returncode = None if running else 0

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9

    def wait(self):
        return self.returncode


class NativePTSChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root/'synthetic_source.bin'
        self.source.write_bytes(b'not media: immutable local source fixture')
        self.row = dict(sample_id='fixture',source='vript',source_sha256=m.sha(self.source),
            relative_path=self.source.name,origin_group='origin-1',ancestry_status='known_fixture',
            data_role='development_candidate')
        self.manifest = self.root/'manifest.json'
        m.write(self.manifest,dict(candidates=[self.row]))
        self.contract = m.read(ROOT/'research-runs/shared_plan_20260917/pts_acquisition_contract_draft.json')
        self.out = self.root/'out'
        self.out.mkdir()

    def test_exact_integer_ticks_and_rational_base(self):
        ticks = [9007199254740993,9007199254740994]
        r = m.normalized_pts(dict(streams=[dict(time_base='1/90000')],frames=[dict(pts=v) for v in ticks]))
        self.assertEqual(r['pts_ticks'],ticks)
        self.assertEqual(r['time_base_denominator'],90000)
        self.assertTrue(r['strictly_increasing_native_pts'])
        self.assertFalse(r['sampling_eligibility_evaluated'])

    def test_missing_native_pts_never_filled_by_best_effort(self):
        r = m.normalized_pts(dict(streams=[dict(time_base='1/10')],frames=[
            dict(pts='N/A',best_effort_timestamp=3),dict(pts=4)]))
        self.assertEqual(r['pts_ticks'],[None,4])
        self.assertEqual(r['best_effort_ticks'],[3,None])
        self.assertFalse(r['strictly_increasing_native_pts'])

    def test_duplicates_and_backward_order_preserved(self):
        r = m.normalized_pts(dict(streams=[dict(time_base='1/10')],frames=[dict(pts=v) for v in [4,4,2]]))
        self.assertEqual(r['pts_ticks'],[4,4,2])
        self.assertEqual(r['duplicate_pts'],1)
        self.assertEqual(r['nonincreasing_adjacent_pairs'],2)

    def test_malformed_probe_not_sampling_failure(self):
        for raw in ({'error':{'code':1}}, {'streams':[{'time_base':'1/10'}],'frames':[]},
                    {'streams':[{'time_base':'1/10'}],'frames':[{'pts':1.5}]},
                    {'streams':[{'time_base':'1/10'}],'frames':[{'pts':True}]},
                    {'streams':[{'time_base':'0/0'}],'frames':[{'pts':0}]}):
            with self.subTest(raw=raw), self.assertRaises((ValueError,KeyError)):
                m.normalized_pts(raw)

    def test_selection_order_and_origin_dedup(self):
        rows = [dict(self.row,sample_id=str(i),source_sha256=f'{i:064x}',origin_group=str(i//2)) for i in range(8)]
        a = m.select_rows({'candidates':rows},self.contract)
        b = m.select_rows({'candidates':rows[::-1]},self.contract)
        self.assertEqual(a,b)
        self.assertEqual([r['sample_id'] for r in a],['0','2','4','6'])

    def test_final_role_and_duplicate_id_rejected(self):
        for rows in ([dict(self.row,data_role='final_confirmation')],[self.row,self.row]):
            with self.assertRaises(ValueError):
                m.select_rows({'candidates':rows},self.contract)

    def test_draft_execute_refuses_before_any_process(self):
        c = self.root/'contract.json'; m.write(c,self.contract)
        with patch.object(m.subprocess,'Popen') as popen, patch.object(m.subprocess,'run') as run:
            with patch.object(m.sys,'argv',['collector','--contract',str(c),'--manifest',str(self.manifest),'--execute']):
                with self.assertRaisesRegex(SystemExit,'Execution refused'):
                    m.main()
            popen.assert_not_called(); run.assert_not_called()

    def test_dry_plan_does_not_read_original_media(self):
        self.source.unlink()
        c = self.root/'contract.json'; m.write(c,self.contract)
        capture = io.StringIO()
        with patch.object(m.subprocess,'Popen') as proc, contextlib.redirect_stdout(capture):
            with patch.object(m.sys,'argv',['collector','--contract',str(c),'--manifest',str(self.manifest)]):
                m.main()
        result = json.loads(capture.getvalue())
        self.assertFalse(result['probe_started']); proc.assert_not_called()

    def test_changed_source_refused_before_probe(self):
        self.source.write_bytes(b'changed fixture')
        with patch.object(m.subprocess,'Popen') as proc, self.assertRaisesRegex(ValueError,'digest'):
            m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
        proc.assert_not_called()

    def test_complete_resume_and_corruption_reprobe(self):
        with patch.object(m.subprocess,'Popen',side_effect=Probe) as proc:
            first = m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
            second = m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
            self.assertEqual(first['status'],'probe_complete')
            self.assertEqual(second['status'],'reused_verified_metadata')
            self.assertEqual(proc.call_count,1)
            next(self.out.rglob('normalized.json')).write_text('{}')
            m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
            self.assertEqual(proc.call_count,2)

    def test_error_stderr_never_promoted_to_complete(self):
        def factory(*args,**kwargs): return Probe(*args,**kwargs,error=b'decode error fixture')
        with patch.object(m.subprocess,'Popen',side_effect=factory):
            r = m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
        self.assertEqual(r['status'],'acquisition_failed')

    def test_resource_interruption_preserves_partial(self):
        def factory(*args,**kwargs): return Probe(*args,**kwargs,running=True)
        with patch.object(m.subprocess,'Popen',side_effect=factory),patch.object(m,'remaining',return_value=0):
            r = m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
        self.assertEqual(r['reason'],'resource_partial_not_video_quality_failure')
        self.assertTrue(list(self.out.rglob('probe.json')))

    def test_fast_process_over_metadata_cap_is_not_complete(self):
        self.contract['outputs']['server_metadata_max_bytes_proposed'] = 1
        with patch.object(m.subprocess,'Popen',side_effect=Probe):
            r = m.execute_one(self.row,self.root,self.out,self.contract,{},'NO_REAL_FFPROBE')
        self.assertEqual(r['reason'],'resource_partial_not_video_quality_failure')

    def test_paths_cannot_escape_server_root(self):
        for name in ('../escape',str(self.source)):
            with self.assertRaises(ValueError): m.within_root(self.root,name)

    def test_empty_outputs_are_not_reusable(self):
        p = self.out/'bad.receipt.json'
        m.write(p,dict(status='probe_complete',binding={},outputs=[]))
        self.assertFalse(m.reusable(p,{}))

    def test_bound_contract_and_known_cumulative_budget(self):
        c = copy.deepcopy(self.contract)
        c.update(status='adopted',execution_authorized=True,approved_by='TEST_FIXTURE',
            approval_receipt='TEST_FIXTURE',parent_gate_receipt='TEST_FIXTURE',existing_instance_receipt='TEST_FIXTURE',
            collector_sha256=m.sha(FILE))
        c['inputs']['source_manifest_sha256'] = m.sha(self.manifest)
        c['budget'].update(approved_batch_max_cny=1,current_hourly_rate_cny=1,
            approved_batch_max_hours=1,next_file_reserve_cny=.1,batch_allowance_receipt='TEST_FIXTURE',
            billing_started_utc=datetime.now(timezone.utc).isoformat())
        self.assertEqual(m.authorization_errors(c,self.manifest),[])
        c['budget']['actual_paid_cny'] = 6000
        self.assertIn('actual_paid_cny',m.authorization_errors(c,self.manifest))
        c['budget']['actual_paid_cny'] = float('nan')
        self.assertIn('actual_paid_cny',m.authorization_errors(c,self.manifest))


if __name__ == '__main__':
    unittest.main()
