import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "research-code"))
from sampling import fixed_rate_plan

p = fixed_rate_plan(frame_count=8, source_fps=4, target_fps=4, window_sec=2)
assert p.indices == tuple(range(8))
assert len(set(p.indices)) == 8
try:
    fixed_rate_plan(frame_count=7, source_fps=4, target_fps=4, window_sec=2)
except ValueError:
    pass
else:
    raise AssertionError("short 4 fps video must be rejected")
print("4 fps sampling invariants: PASS")
