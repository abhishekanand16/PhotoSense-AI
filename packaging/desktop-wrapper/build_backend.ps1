Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

python -m PyInstaller backend.spec --clean --noconfirm --distpath "src-tauri/bin" --workpath "build"
