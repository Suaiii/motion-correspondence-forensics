param(
    [Parameter(Mandatory=$true)][string]$Script,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$ScriptArgs
)
$ErrorActionPreference = 'Stop'
$runtimeRoot = $PSScriptRoot
if ([IO.Path]::GetPathRoot($runtimeRoot) -ne 'E:\') { throw 'Research runtime must remain on E:' }
$locations = @{
    TEMP = 'tmp'; TMP = 'tmp'; TMPDIR = 'tmp';
    XDG_CACHE_HOME = 'cache'; TORCH_HOME = 'cache\torch';
    HF_HOME = 'cache\huggingface'; HF_HUB_CACHE = 'cache\huggingface\hub';
    MPLCONFIGDIR = 'cache\matplotlib'; PIP_CACHE_DIR = 'cache\pip';
    CUDA_CACHE_PATH = 'cache\cuda'; TRITON_CACHE_DIR = 'cache\triton';
    TORCH_EXTENSIONS_DIR = 'cache\torch_extensions'; NUMBA_CACHE_DIR = 'cache\numba';
    PYTHONPYCACHEPREFIX = 'cache\pycache'; UV_CACHE_DIR = 'cache\uv'
}
foreach ($name in $locations.Keys) {
    $destination = Join-Path $runtimeRoot $locations[$name]
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    [Environment]::SetEnvironmentVariable($name, $destination, 'Process')
}
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:WANDB_MODE = 'disabled'
$env:OMP_NUM_THREADS = '4'
$env:MKL_NUM_THREADS = '4'
$env:OPENBLAS_NUM_THREADS = '4'
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
$pythonExe = 'E:\AAGenvid\.conda_envs\d3_cuda\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Expected E-drive Python is missing' }
$resolvedScript = (Resolve-Path -LiteralPath $Script).Path
if ([IO.Path]::GetPathRoot($resolvedScript) -ne 'E:\') { throw 'Research script must be on E:' }
& $pythonExe $resolvedScript @ScriptArgs
if ($LASTEXITCODE -ne 0) { throw "Research command failed: $LASTEXITCODE" }
