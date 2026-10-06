# scripts/install.ps1 -- Super Token Meter (Windows): set up the per-user data dir and a
#                        15-minute collector schedule via Task Scheduler. Local-first: no
#                        admin, no network, no API key.
# Run:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "python not found - install Python 3.9+ (https://python.org)"; exit 1 }

$data = if ($env:STM_DATA_DIR) { $env:STM_DATA_DIR } else { Join-Path $HOME ".super-token-meter\data" }
New-Item -ItemType Directory -Force -Path $data | Out-Null

Write-Host "[install] repo:   $repo"
Write-Host "[install] python: $py"
Write-Host "[install] data:   $data"

$action  = New-ScheduledTaskAction  -Execute $py -Argument "-m super_token_meter collect --data-dir `"$data`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "SuperTokenMeter" -Action $action -Trigger $trigger -Force `
  -Description "Super Token Meter collector (refresh usage data every 15 min)" | Out-Null
Write-Host "[install] scheduled task 'SuperTokenMeter' registered (every 15 min)."

& $py -m super_token_meter collect --data-dir $data
Write-Host "[install] Done. View the dashboard any time with:  python -m super_token_meter serve --data-dir `"$data`""
