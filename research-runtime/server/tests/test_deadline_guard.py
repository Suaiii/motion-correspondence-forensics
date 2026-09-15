import sys
import errno
import unittest
import tempfile
from unittest.mock import patch
from datetime import datetime,timedelta
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from deadline_guard import phase,stop_registered,main,invoke_shutdown


class DeadlineTests(unittest.TestCase):
    def test_regular_shutdown_exec_is_unchanged(self):
        with patch('deadline_guard.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')) as run:
            result=invoke_shutdown('/usr/bin/shutdown')
            self.assertEqual(result['invocation'],['/usr/bin/shutdown'])
            self.assertEqual(run.call_count,1)

    def test_shebangless_provider_shutdown_uses_bash(self):
        with patch('deadline_guard.subprocess.run',side_effect=[OSError(errno.ENOEXEC,'Exec format error'),SimpleNamespace(returncode=0,stdout='stopped',stderr='')]) as run:
            result=invoke_shutdown('/usr/bin/shutdown')
            self.assertEqual(result['returncode'],0)
            self.assertEqual(result['invocation'],['/bin/bash','/usr/bin/shutdown'])
            self.assertEqual(run.call_args_list[1].args[0],['/bin/bash','/usr/bin/shutdown'])

    def test_missing_shutdown_is_not_masked_by_shell_fallback(self):
        with patch('deadline_guard.subprocess.run',side_effect=FileNotFoundError(errno.ENOENT,'not found')) as run:
            with self.assertRaises(FileNotFoundError):invoke_shutdown('/missing/shutdown')
            self.assertEqual(run.call_count,1)

    def test_deadline_boundaries(self):
        d=datetime.fromisoformat('2026-09-11T10:00:00+08:00')
        self.assertEqual(phase(d-timedelta(hours=2),d),'running')
        self.assertEqual(phase(d-timedelta(minutes=20),d),'no_new_jobs')
        self.assertEqual(phase(d-timedelta(minutes=10),d),'drain')
        self.assertEqual(phase(d-timedelta(minutes=1),d),'shutdown')
        self.assertEqual(phase(d,d),'shutdown')
        self.assertEqual(phase(d+timedelta(hours=4),d),'shutdown')
        self.assertEqual(phase(d-timedelta(hours=2),d,True),'shutdown')

    def test_corrupt_job_record_cannot_disable_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'job_bad.json').write_text('{bad json',encoding='utf-8')
            self.assertEqual(stop_registered(p),[])

    def test_status_write_failure_does_not_block_expired_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('sys.argv',['deadline_guard','--run-dir',tmp,'--deadline','2000-01-01T00:00:00+00:00','--dry-run']),patch('deadline_guard.save',side_effect=OSError('disk full')):
                main()


if __name__=='__main__':unittest.main()
