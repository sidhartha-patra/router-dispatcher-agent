$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

Push-Location $root
& $python -m router_dispatcher_agent run 'Research zero-downtime rollout practices and include citations.' --json-output
& $python -m router_dispatcher_agent run 'Debug this failing unit test and stack trace.' --json-output
& $python -m router_dispatcher_agent run 'Book a release review meeting tomorrow.' --auto-approve --json-output
Pop-Location
