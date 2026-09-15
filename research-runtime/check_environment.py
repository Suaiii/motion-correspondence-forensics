import importlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
report = {
    "time_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.executable, "python_version": sys.version,
    "platform": platform.platform(),
    "disk_free_gb": round(shutil.disk_usage(root).free / 2**30, 2),
    "caches": {k: os.environ.get(k) for k in ["TEMP", "TMP", "XDG_CACHE_HOME", "TORCH_HOME", "HF_HOME", "HF_HUB_CACHE", "MPLCONFIGDIR", "PIP_CACHE_DIR", "CUDA_CACHE_PATH", "TRITON_CACHE_DIR", "TORCH_EXTENSIONS_DIR", "NUMBA_CACHE_DIR", "PYTHONPYCACHEPREFIX", "UV_CACHE_DIR"]},
    "packages": {},
}
for name in ["numpy", "cv2", "sklearn", "torch"]:
    try:
        mod = importlib.import_module(name)
        report["packages"][name] = {"version": mod.__version__, "path": mod.__file__}
        if name == "torch":
            report["cuda"] = {"available": mod.cuda.is_available(), "build": mod.version.cuda}
            if mod.cuda.is_available():
                p = mod.cuda.get_device_properties(0)
                report["cuda"].update(name=p.name, vram_bytes=p.total_memory)
    except Exception as exc:
        report["packages"][name] = {"error": repr(exc)}
assert all(Path(v).drive.upper() == "E:" for v in report["caches"].values())
assert Path(sys.executable).drive.upper() == "E:"
path = root / "environment.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
