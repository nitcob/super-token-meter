# Linux: run the collector on a timer (user systemd)

Create `~/.config/systemd/user/super-token-meter.service`:

```ini
[Unit]
Description=Super Token Meter collector (refresh usage data)

[Service]
Type=oneshot
WorkingDirectory=/path/to/super-token-meter
ExecStart=/usr/bin/python3 -m super_token_meter collect
```

And `~/.config/systemd/user/super-token-meter.timer`:

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

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now super-token-meter.timer
```

`scripts/install` writes these for you (substituting the real paths). Serve the dashboard with
`python3 -m super_token_meter serve` whenever you want to look. On Windows, use Task Scheduler to
run `python -m super_token_meter collect` every 15 minutes from the repo folder.
