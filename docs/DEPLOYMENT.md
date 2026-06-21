# nanoclaw-finance — Local Daemon Deployment (macOS)

## Current Setup
- Runs via launchd (macOS), not systemd (Linux) — this machine is macOS
- Production directory: /opt/agents/nanoclaw-finance/
- Service definition: deploy/com.nanoclaw.finance.plist
- Logs: /opt/agents/nanoclaw-finance/logs/

## Commands
- Load:    launchctl load ~/Library/LaunchAgents/com.nanoclaw.finance.plist
- Unload:  launchctl unload ~/Library/LaunchAgents/com.nanoclaw.finance.plist
- Status:  launchctl list | grep nanoclaw
- Logs:    tail -f /opt/agents/nanoclaw-finance/logs/heartbeat.log

## Verified
- [x] Survives terminal closure
- [x] Auto-restarts on crash (KeepAlive)
- [x] .env permissions hardened to 600
- [x] Logs writing correctly with no unexpected errors

## Migration to Linux/systemd (future)
When deployed to a real cloud VM:
- com.nanoclaw.finance.plist → nanoclaw-finance.service
- launchctl load/unload → systemctl start/stop
- KeepAlive → Restart=always
- StandardOutPath/StandardErrorPath → journalctl, or explicit log redirection
