"""Compact executable evidence for the small CPU-only numerical checks."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import unittest

import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();root=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root),str(root/'tests')]
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in ('test_lag_support','test_rank_response'))
    stream=io.StringIO();start=time.monotonic()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    files=['forensics/lag_support.py','forensics/rank_response.py','tests/test_lag_support.py',
           'tests/test_rank_response.py','scripts/audit_actual_lag_support.py','scripts/check_numerical_mechanisms.py']
    report=dict(observed_utc=datetime.now(timezone.utc).isoformat(),status='pass' if result.wasSuccessful() else 'fail',
        tests_run=result.testsRun,seconds=time.monotonic()-start,python=platform.python_version(),numpy=np.__version__,
        compute='small in-memory CPU synthetic arrays',real_research_videos_read=0,gpu_used=False,
        detector_trained=False,server_experiment_executed=False,formal_claim_released=False,
        artifact_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
        failures=[dict(test=str(t),traceback=trace) for t,trace in result.failures+result.errors],test_log=stream.getvalue(),
        limits=['Tests verify numerical contracts and counterexamples, not detection efficacy or novelty.',
                'The actual-lag census requires server timestamps and remains unexecuted.',
                'The local rank component is not an end-to-end trained forensic algorithm.'])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','tests_run','seconds','server_experiment_executed')},indent=2))
    if not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':
    main()
