#!/usr/bin/env python3
"""
pia-web -- Python port of flamewave000/pia-web
Zero-dependency web UI for controlling PIA VPN via piactl.
Requires only Python 3 stdlib -- no npm, no pip.

Usage:
    ./pia-web.py                  Start server (default port 8042)
    ./pia-web.py --port 9090      Custom port
    ./pia-web.py --piactl /path   Custom path to piactl
    ./pia-web.py --help
"""

import argparse
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DEFAULT_PIACTL = "piactl"
DEFAULT_PORT   = 8042
DEFAULT_HOST   = "0.0.0.0"

# ── PIA wrapper ────────────────────────────────────────────────────────────
class PIA:
    def __init__(self, command: str):
        self.command = command

    def _run(self, *args) -> str:
        result = subprocess.run([self.command] + list(args), capture_output=True, text=True)
        return result.stdout.strip()

    @property
    def connection_state(self) -> str:
        return self._run("get", "connectionstate")

    @property
    def connected(self) -> bool:
        return self.connection_state == "Connected"

    @property
    def pub_ip(self) -> str:
        return self._run("get", "pubip") or "—"

    @property
    def vpn_ip(self) -> str:
        return self._run("get", "vpnip") or "—"

    @property
    def port_forward_status(self) -> str:
        return self._run("get", "portforward")

    @property
    def region(self) -> str:
        return self._run("get", "region")

    @region.setter
    def region(self, value: str):
        self._run("set", "region", value)

    @property
    def regions(self) -> list:
        return [r for r in self._run("get", "regions").splitlines() if r.strip()]

    @property
    def protocol(self) -> str:
        return self._run("get", "protocol")

    @protocol.setter
    def protocol(self, value: str):
        self._run("set", "protocol", value)

    @property
    def request_port_forward(self) -> bool:
        return self._run("get", "requestportforward").lower() == "true"

    @request_port_forward.setter
    def request_port_forward(self, value: bool):
        self._run("set", "requestportforward", "true" if value else "false")

    @property
    def allow_lan(self) -> bool:
        return self._run("get", "allowlan").lower() == "true"

    @allow_lan.setter
    def allow_lan(self, value: bool):
        self._run("set", "allowlan", "true" if value else "false")

    @property
    def debug_logging(self) -> bool:
        return self._run("get", "debuglogging").lower() == "true"

    @debug_logging.setter
    def debug_logging(self, value: bool):
        self._run("set", "debuglogging", "true" if value else "false")

    def connect(self):    self._run("connect")
    def disconnect(self): self._run("disconnect")

    def background(self, enable: bool):
        self._run("background", "enable" if enable else "disable")

    def reset_settings(self):
        self._run("resetsettings")


# ── Helpers ───────────────────────────────────────────────────────────────────
def state_color(state: str) -> str:
    return {
        "Connected":                "#22c55e",
        "Connecting":               "#f59e0b",
        "Reconnecting":             "#f59e0b",
        "DisconnectingToReconnect": "#f59e0b",
        "Interrupted":              "#f97316",
        "Disconnecting":            "#6b7280",
        "Disconnected":             "#ef4444",
    }.get(state, "#6b7280")

def pf_color(status: str) -> str:
    if status.isdigit(): return "#22c55e"
    return {"Attempting": "#f59e0b", "Failed": "#ef4444", "Unavailable": "#6b7280"}.get(status, "#6b7280")

def toggle_btn(label_on, label_off, state: bool, action_on: str, action_off: str) -> str:
    if state:
        return f'<form method="POST" action="{action_off}" onsubmit="spin()"><button class="btn btn-toggle-on">{label_on}</button></form>'
    else:
        return f'<form method="POST" action="{action_on}" onsubmit="spin()"><button class="btn btn-toggle-off">{label_off}</button></form>'


# ── HTML renderer ────────────────────────────────────────────────────────────
def render_page(pia: PIA) -> str:
    state     = pia.connection_state
    connected = pia.connected
    pub_ip    = pia.pub_ip
    vpn_ip    = pia.vpn_ip
    pf_status = pia.port_forward_status
    region    = pia.region
    regions   = pia.regions
    protocol  = pia.protocol
    rpf       = pia.request_port_forward
    allow_lan = pia.allow_lan
    debug_log = pia.debug_logging

    sc = state_color(state)
    pc = pf_color(pf_status)

    action_path  = "/dis" if connected else "/con"
    action_label = "Disconnect" if connected else "Connect"
    action_cls   = "btn-danger" if connected else "btn-success"

    pf_display = f"Port: {pf_status}" if pf_status.isdigit() else pf_status

    options_html = "\n".join(
        f'<option value="{r}" {"selected" if r == region else ""}>{r}</option>'
        for r in regions
    )
    proto_options = "\n".join(
        f'<option value="{p}" {"selected" if p == protocol else ""}>{p}</option>'
        for p in ["openvpn", "wireguard"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PIA Remote Web</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg:       #0f1117;
      --surface:  #1a1d27;
      --surface2: #212533;
      --border:   #2a2d3a;
      --text:     #e2e4ed;
      --muted:    #6b7280;
      --accent:   #6d28d9;
      --success:  #22c55e;
      --warning:  #f59e0b;
      --danger:   #ef4444;
      --radius:   0.5rem;
    }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100dvh; display: flex;
      align-items: center; justify-content: center; padding: 1.5rem;
    }}
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 2rem;
      width: 100%; max-width: 500px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }}
    .logo {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.75rem; }}
    .logo h1 {{ font-size: 1.25rem; font-weight: 600; letter-spacing: -0.01em; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.25rem; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 0.4rem;
      background: rgba(255,255,255,0.05); border: 1px solid var(--border);
      border-radius: 2rem; padding: 0.35rem 0.8rem;
      font-size: 0.8rem; font-weight: 500;
    }}
    .dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 1.25rem; }}
    .info-cell {{
      background: var(--surface2); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 0.6rem 0.75rem;
    }}
    .info-cell .label {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem; }}
    .info-cell .value {{ font-size: 0.85rem; font-weight: 500; font-family: monospace; word-break: break-all; }}
    .section-label {{ font-size: 0.75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.6rem; }}
    label {{ display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.35rem; }}
    select {{
      width: 100%; background: var(--bg); color: var(--text);
      border: 1px solid var(--border); border-radius: var(--radius);
      padding: 0.55rem 0.75rem; font-size: 0.9rem; cursor: pointer;
    }}
    select:focus {{ outline: 2px solid var(--accent); border-color: transparent; }}
    .row-form {{ display: flex; gap: 0.5rem; align-items: flex-end; margin-bottom: 1rem; }}
    .row-form select {{ margin-bottom: 0; flex: 1; }}
    .row-form .btn {{ width: auto; padding: 0.55rem 1.1rem; flex-shrink: 0; }}
    .btn {{
      display: block; width: 100%; padding: 0.6rem 1rem;
      border: none; border-radius: var(--radius);
      font-size: 0.9rem; font-weight: 600; cursor: pointer;
      transition: opacity 0.15s;
    }}
    .btn:hover {{ opacity: 0.82; }}
    .btn:active {{ opacity: 0.65; }}
    .btn-success {{ background: var(--success); color: #000; }}
    .btn-danger  {{ background: var(--danger);  color: #fff; }}
    .btn-primary {{ background: var(--accent);  color: #fff; }}
    .btn-ghost   {{ background: transparent; color: var(--muted); border: 1px solid var(--border); }}
    .btn-ghost:hover {{ color: var(--text); border-color: var(--text); opacity: 1; }}
    .btn-toggle-on  {{ background: rgba(34,197,94,0.15);  color: var(--success); border: 1px solid var(--success); }}
    .btn-toggle-off {{ background: rgba(107,114,128,0.1); color: var(--muted);   border: 1px solid var(--border); }}
    .toggle-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.75rem; }}
    .divider {{ border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }}
    .btn-reset {{ background: transparent; color: var(--danger); border: 1px solid var(--danger); margin-top: 0.5rem; font-size: 0.8rem; padding: 0.45rem; }}
    .spinner {{
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,0.6); align-items: center; justify-content: center; z-index: 99;
    }}
    .spinner.active {{ display: flex; }}
    .spin {{
      width: 44px; height: 44px;
      border: 4px solid var(--border); border-top-color: var(--accent);
      border-radius: 50%; animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
<div class="spinner" id="spinner"><div class="spin"></div></div>
<div class="card">
  <div class="logo">
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-label="PIA Web">
      <rect width="32" height="32" rx="8" fill="#6d28d9"/>
      <path d="M9 10h6a5 5 0 0 1 0 10H9V10z" fill="white" opacity="0.9"/>
      <rect x="9" y="22" width="4" height="4" rx="1" fill="white" opacity="0.9"/>
      <circle cx="23" cy="22" r="4" stroke="white" stroke-width="2" fill="none" opacity="0.9"/>
      <path d="M23 20v2l1.5 1.5" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
    </svg>
    <h1>PIA Remote Web</h1>
  </div>

  <div class="badge-row">
    <span class="badge"><span class="dot" style="background:{sc};box-shadow:0 0 5px {sc}"></span>{state}</span>
    <span class="badge"><span class="dot" style="background:{pc};box-shadow:0 0 5px {pc}"></span>PF: {pf_display}</span>
  </div>

  <div class="info-grid">
    <div class="info-cell"><div class="label">Public IP</div><div class="value">{pub_ip}</div></div>
    <div class="info-cell"><div class="label">VPN IP</div><div class="value">{vpn_ip}</div></div>
  </div>

  <form method="POST" action="/reg" onsubmit="spin()">
    <label for="regions">VPN Region</label>
    <div class="row-form">
      <select id="regions" name="region">{options_html}</select>
      <button type="submit" class="btn btn-primary">Set</button>
    </div>
  </form>

  <form method="POST" action="/proto" onsubmit="spin()">
    <label for="proto">Protocol</label>
    <div class="row-form">
      <select id="proto" name="protocol">{proto_options}</select>
      <button type="submit" class="btn btn-primary">Set</button>
    </div>
  </form>

  <hr class="divider">

  <div class="section-label">VPN Connection</div>
  <form method="POST" action="{action_path}" onsubmit="spin()">
    <button type="submit" class="btn {action_cls}">{action_label}</button>
  </form>

  <hr class="divider">

  <div class="section-label">Settings</div>
  <div class="toggle-grid">
    {toggle_btn("Port Forward ✓", "Port Forward", rpf, "/rpf/on", "/rpf/off")}
    {toggle_btn("Allow LAN ✓", "Allow LAN", allow_lan, "/lan/on", "/lan/off")}
    {toggle_btn("Background ✓", "Background", False, "/bg/on", "/bg/off")}
    {toggle_btn("Debug Log ✓", "Debug Log", debug_log, "/dbg/on", "/dbg/off")}
  </div>

  <hr class="divider">

  <div class="section-label">Danger Zone</div>
  <form method="POST" action="/reset" onsubmit="return confirm('Reset all daemon settings to defaults?')">
    <button type="submit" class="btn btn-reset">⚠ Reset Settings</button>
  </form>

</div>
<script>
  function spin() {{ document.getElementById('spinner').classList.add('active'); }}
</script>
</body>
</html>"""


# ── HTTP handler ────────────────────────────────────────────────────────────
def make_handler(pia: PIA):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[pia-web] {self.address_string()} {fmt % args}")

        def send_redirect(self, location="/"):
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def do_GET(self):
            if urlparse(self.path).path == "/":
                body = render_page(pia).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            path   = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", 0))
            params = parse_qs(self.rfile.read(length).decode())

            routes = {
                "/con":    lambda: pia.connect(),
                "/dis":    lambda: pia.disconnect(),
                "/rpf/on": lambda: setattr(pia, "request_port_forward", True),
                "/rpf/off":lambda: setattr(pia, "request_port_forward", False),
                "/lan/on": lambda: setattr(pia, "allow_lan", True),
                "/lan/off":lambda: setattr(pia, "allow_lan", False),
                "/bg/on":  lambda: pia.background(True),
                "/bg/off": lambda: pia.background(False),
                "/dbg/on": lambda: setattr(pia, "debug_logging", True),
                "/dbg/off":lambda: setattr(pia, "debug_logging", False),
                "/reset":  lambda: pia.reset_settings(),
            }

            if path == "/reg":
                region = params.get("region", [None])[0]
                if region: pia.region = region
            elif path == "/proto":
                proto = params.get("protocol", [None])[0]
                if proto: pia.protocol = proto
            elif path in routes:
                routes[path]()
            else:
                self.send_response(404); self.end_headers(); return

            self.send_redirect("/")

    return Handler


# ── Entry point ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="PIA Remote Web — zero-dependency Python port")
    parser.add_argument("--piactl", default=DEFAULT_PIACTL, help=f"Path to piactl (default: {DEFAULT_PIACTL})")
    parser.add_argument("--port",   type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument("--host",   default=DEFAULT_HOST, help=f"Host (default: {DEFAULT_HOST})")
    args = parser.parse_args()

    pia     = PIA(args.piactl)
    handler = make_handler(pia)

    print(f"[pia-web] Starting on http://{args.host}:{args.port}")
    print(f"[pia-web] piactl: {args.piactl}")
    print(f"[pia-web] Ctrl+C to stop.")

    server = HTTPServer((args.host, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[pia-web] Stopped.")

if __name__ == "__main__":
    main()
