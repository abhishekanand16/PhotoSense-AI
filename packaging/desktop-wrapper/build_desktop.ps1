Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

& .\build_backend.ps1

Push-Location "src-tauri"
cargo tauri build --config tauri.conf.json
Pop-Location
