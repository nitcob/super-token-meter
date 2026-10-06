# Deploy — keep the data fresh on a schedule

The dashboard reads `claude_usage.json`; run `collect` on a timer so it stays current, and run
`super-token-meter serve` whenever you want to look. Pick your OS — **`scripts/install`**
(macOS/Linux) and **`scripts/install.ps1`** (Windows) set this up for you.

## macOS — launchd

`scripts/install` does it automatically. Manual:

1. Copy `launchd.plist.template` → `~/Library/LaunchAgents/com.supertokenmeter.collect.plist`
2. Replace the `__PYTHON__` / `__REPO__` / `__DATA__` placeholders with real paths.
3. `launchctl load -w ~/Library/LaunchAgents/com.supertokenmeter.collect.plist`

> Keep the repo **outside** `~/Desktop`, `~/Documents`, `~/Downloads` — macOS TCC blocks launchd there.

## Linux — user systemd

`scripts/install` writes these for you. Manual — `~/.config/systemd/user/super-token-meter.service`:

```ini
[Unit]
Description=Super Token Meter collector
[Service]
Type=oneshot
WorkingDirectory=/path/to/super-token-meter
# pass --data-dir explicitly: a systemd/launchd/Task-Scheduler job does NOT inherit your shell's STM_DATA_DIR
ExecStart=/usr/bin/python3 -m super_token_meter collect --data-dir %h/.super-token-meter/data
```

and `~/.config/systemd/user/super-token-meter.timer`:

```ini
[Unit]
Description=Run Super Token Meter collector every 15 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Persistent=true
[Install]
WantedBy=timers.target
```

then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now super-token-meter.timer
```

No systemd? Use cron: `*/15 * * * * cd /path/to/super-token-meter && python3 -m super_token_meter collect --data-dir $HOME/.super-token-meter/data`

## Windows — Task Scheduler

Run **`scripts/install.ps1`** in PowerShell (registers a 15-minute scheduled task). Manual:

```powershell
$repo = "C:\path\to\super-token-meter"
$py   = (Get-Command python).Source
$data = Join-Path $HOME ".super-token-meter\data"   # pass it explicitly — the task won't inherit STM_DATA_DIR
$action  = New-ScheduledTaskAction -Execute $py -Argument "-m super_token_meter collect --data-dir `"$data`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "SuperTokenMeter" -Action $action -Trigger $trigger -Description "Refresh usage data"
```

## View the dashboard (any OS)

```bash
python3 -m super_token_meter serve     # macOS / Linux
python  -m super_token_meter serve     # Windows
```
