$ErrorActionPreference = 'Stop'
$recipePython = Get-Command python -ErrorAction SilentlyContinue
if ($recipePython) {
    & $recipePython.Source "$PSScriptRoot\server.py"
} else {
    $recipeRuntime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (-not (Test-Path -LiteralPath $recipeRuntime)) { throw '未找到 Python，请安装 Python 3.10 或更新版本。' }
    & $recipeRuntime "$PSScriptRoot\server.py"
}
