# pia-web-python

A zero-dependency Python 3 port of [flamewave000/pia-web](https://github.com/flamewave000/pia-web).

Controls the PIA VPN client via `piactl` through a simple web UI. Requires only Python 3 (stdlib) — no npm, no pip, no package manager.

## Requirements

- Python 3.6+ (pre-installed on most Linux distros)
- `piactl` on your PATH (installed with the PIA desktop client)

## Usage

```bash
# Make executable
chmod +x pia-web.py

# Start with defaults (port 8080, piactl on PATH)
./pia-web.py

# Custom options
./pia-web.py --port 9090 --piactl /usr/local/bin/piactl

# Help
./pia-web.py --help
```

Then open `http://<your-server-ip>:8080` in a browser.

## Features

- Display connection status
- Display and change the selected region
- Connect / Disconnect the VPN
- Toggle port forwarding on/off
- Dark UI, no dependencies

## Credits

Original Node.js version by [flamewave000](https://github.com/flamewave000/pia-web).
