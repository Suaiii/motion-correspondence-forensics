#!/usr/bin/env bash
set -euo pipefail
# Run on the selected server, inside an explicitly selected project directory.
# This creates an isolated venv; it does not provision/start/stop a cloud instance.
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Select a Python >=3.11 server image"'
python3 -m venv "$project_dir/.venv"
"$project_dir/.venv/bin/python" -m pip install --upgrade pip
"$project_dir/.venv/bin/python" -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
"$project_dir/.venv/bin/python" -m pip install -e "$project_dir"
"$project_dir/.venv/bin/python" -m pip freeze > "$project_dir/environment-installed.txt"
printf '%s\n' 'Run doctor with the verified server data/cache roots before downloading videos.'
