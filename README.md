# pia-web-python

A zero-dependency Python 3 port of [flamewave000/pia-web](https://github.com/flamewave000/pia-web).

Controls the PIA VPN client via `piactl` through a simple web UI. Requires only Python 3 (stdlib) — no npm, no pip, no package manager.

## Requirements

- Python 3.6+ (pre-installed on most Linux distros)
- `piactl` on your PATH (installed with the PIA desktop client)

## Install as a systemd service (Debian / Ubuntu)

```bash
curl -fsSL https://raw.githubusercontent.com/pcartwright81/pia-web-python/main/install.sh | sudo bash
```

Then open `http://<your-server-ip>:8042` in a browser.

To use a custom port:

```bash
curl -fsSL https://raw.githubusercontent.com/pcartwright81/pia-web-python/main/install.sh | sudo PORT=9090 bash
```

Manage the service:

```bash
sudo systemctl status pia-web
sudo systemctl restart pia-web
sudo systemctl stop pia-web
```

## Manual usage (no install)

```bash
chmod +x pia-web.py
./pia-web.py
```

```
Options:
  --port PORT       Port to listen on (default: 8042)
  --host HOST       Host to bind to (default: 0.0.0.0)
  --piactl PATH     Path to piactl binary (default: piactl)
```

## Features

| Feature | piactl command |
|---|---|
| VPN connection state (detailed) | `get connectionstate` |
| Public IP & VPN IP display | `get pubip` / `get vpnip` |
| Region selector | `get/set region` |
| Protocol selector (OpenVPN / WireGuard) | `get/set protocol` |
| Connect / Disconnect | `connect` / `disconnect` |
| Port Forward Port display | `get portforward` |
| Request port forward toggle | `set requestportforward` |
| Allow LAN toggle | `get/set allowlan` |
| Background mode toggle | `background enable/disable` |
| Debug logging toggle | `get/set debuglogging` |
| Reset daemon settings | `resetsettings` |

## Credits

Original Node.js version by [flamewave000](https://github.com/flamewave000/pia-web).
