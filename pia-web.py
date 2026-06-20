#!/usr/bin/env python3
"""
pia-web — Python port of flamewave000/pia-web
A zero-dependency web UI for controlling the PIA VPN client via piactl.
Requires only Python 3 (stdlib), which ships on all major Linux distros.

Usage:
    ./pia-web.py                  Start the server (HTTP on port 8080)
    ./pia-web.py --port 9090      Custom port
    ./pia-web.py --piactl /path   Custom path to piactl
    ./pia-web.py --help           Show help
"""

import argparse
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Default config ────────────────────────────────────────────────────────────
DEFAULT_PIACTL = "piactl"
DEFAULT_PORT   = 8080
DEFAULT_HOST   = "0.0.0.0"

# ── PIA wrapper ───────────────────────────────────────────────────────────────
class PIA:
    def __init__(self, command: str):
        self.command = command

    def _run(self, *args) -> str:
        result = subprocess.run(
            [self.command] + list(args),
            capture_output=True, text=True
        )
        return result.stdout.strip()

    @property
    def connected(self) -> bool:
        return self._run("get", "vpnip").lower() != "unknown"

    def connect(self):
        self._run("connect")

    def disconnect(self):
        self._run("disconnect")

    @property
    def region(self) -> str:
        return self._run("get", "region")

    @region.setter
    def region(self, value: str):
        self._run("set", "region", value)

    @property
    def regions(self) -> list:
        output = self._run("get", "regions")
        return [r for r in output.splitlines() if r.strip()]

    @property
    def port_forward(self) -> bool:
        return self._run("get", "portforward").lower() == "true"

    @port_forward.setter
    def port_forward(self, value: bool):
        self._run("set", "portforward", "true" if value else "false")


# ── HTML renderer ─────────────────────────────────────────────────────────────
def render_page(pia: PIA) -> str:
    connected    = pia.connected
    region       = pia.region
    regions      = pia.regions
    port_forward = pia.port_forward

    status_color = "#22c55e" if connected else "#ef4444"
    status_text  = "Connected" if connected else "Disconnected"
    action_path  = "/dis" if connected else "/con"
    action_label = "Disconnect" if connected else "Connect"
    action_cls   = "btn-danger" if connected else "btn-success"

    pf_color  = "#22c55e" if port_forward else "#6b7280"
    pf_text   = "Enabled" if port_forward else "Disabled"
    pf_action = "/pf/off" if port_forward else "/pf/on"
    pf_label  = "Disable Port Forward" if port_forward else "Enable Port Forward"
    pf_cls    = "btn-outline-danger" if port_forward else "btn-outline-success"

    options_html = "\n".join(
        f'<option value="{r}" {"selected" if r == region else ""}>{r}</option>'
        for r in regions
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
      --border:   #2a2d3a;
      --text:     #e2e4ed;
      --muted:    #6b7280;
      --accent:   #6d28d9;
      --success:  #22c55e;
      --danger:   #ef4444;
      --radius:   0.5rem;
    }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.75rem;
    }}
    .logo svg {{ flex-shrink: 0; }}
    .logo h1 {{
      font-size: 1.25rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}
    .status-row {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      border-radius: 2rem;
      padding: 0.4rem 0.9rem;
      font-size: 0.875rem;
      font-weight: 500;
    }}
    .dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
    }}
    .dot-vpn {{ background: {status_color}; box-shadow: 0 0 6px {status_color}; }}
    .dot-pf  {{ background: {pf_color};     box-shadow: 0 0 6px {pf_color}; }}
    label {{
      display: block;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 0.4rem;
    }}
    select {{
      width: 100%;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0.6rem 0.75rem;
      font-size: 0.95rem;
      margin-bottom: 1rem;
      cursor: pointer;
    }}
    select:focus {{ outline: 2px solid var(--accent); border-color: transparent; }}
    .btn {{
      display: block;
      width: 100%;
      padding: 0.65rem 1rem;
      border: none;
      border-radius: var(--radius);
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s;
    }}
    .btn:hover {{ opacity: 0.85; }}
    .btn:active {{ opacity: 0.7; }}
    .btn-primary         {{ background: var(--accent);  color: #fff; }}
    .btn-success         {{ background: var(--success); color: #000; }}
    .btn-danger          {{ background: var(--danger);  color: #fff; }}
    .btn-outline-success {{
      background: transparent;
      color: var(--success);
      border: 1px solid var(--success);
    }}
    .btn-outline-danger {{
      background: transparent;
      color: var(--danger);
      border: 1px solid var(--danger);
    }}
    .divider {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 1.25rem 0;
    }}
    .region-row {{
      display: flex;
      gap: 0.5rem;
      align-items: flex-end;
    }}
    .region-row select {{ margin-bottom: 0; flex: 1; }}
    .region-row .btn {{ width: auto; padding: 0.6rem 1.2rem; }}
    .section-label {{
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 0.75rem;
    }}
    .spinner {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      align-items: center;
      justify-content: center;
      z-index: 99;
    }}
    .spinner.active {{ display: flex; }}
    .spin {{
      width: 44px; height: 44px;
      border: 4px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
<div class="spinner" id="spinner"><div class="spin"></div></div>
<div class="card">

  <!-- Logo -->
  <div class="logo">
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="PIA Web">
      <rect width="32" height="32" rx="8" fill="#6d28d9"/>
      <path d="M9 10h6a5 5 0 0 1 0 10H9V10z" fill="white" opacity="0.9"/>
      <rect x="9" y="22" width="4" height="4" rx="1" fill="white" opacity="0.9"/>
      <circle cx="23" cy="22" r="4" stroke="white" stroke-width="2" fill="none" opacity="0.9"/>
      <path d="M23 20v2l1.5 1.5" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
    </svg>
    <h1>PIA Remote Web</h1>
  </div>

  <!-- Status badges -->
  <div class="status-row">
    <div class="status-badge">
      <span class="dot dot-vpn"></span>
      <span>VPN: {status_text}</span>
    </div>
    <div class="status-badge">
      <span class="dot dot-pf"></span>
      <span>Port Forward: {pf_text}</span>
    </div>
  </div>

  <!-- Region selector -->
  <form method="POST" action="/reg" onsubmit="spin()">
    <label for="regions">VPN Region</label>
    <div class="region-row">
      <select id="regions" name="region">{options_html}</select>
      <button type="submit" class="btn btn-primary">Set</button>
    </div>
  </form>

  <hr class="divider">

  <!-- Connect / Disconnect -->
  <div class="section-label">VPN Connection</div>
  <form method="POST" action="{action_path}" onsubmit="spin()">
    <button type="submit" class="btn {action_cls}">{action_label}</button>
  </form>

  <hr class="divider">

  <!-- Port Forwarding -->
  <div class="section-label">Port Forwarding</div>
  <form method="POST" action="{pf_action}" onsubmit="spin()">
    <button type="submit" class="btn {pf_cls}">{pf_label}</button>
  </form>

</div>
<script>
  function spin() {{
    document.getElementById('spinner').classList.add('active');
  }}
</script>
</body>
</html>"""


# ── HTTP handler ──────────────────────────────────────────────────────────────
def make_handler(pia: PIA):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[pia-web] {self.address_string()} {fmt % args}")

        def send_redirect(self, location="/"):
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = render_page(pia).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            raw    = self.rfile.read(length).decode()
            params = parse_qs(raw)

            if parsed.path == "/reg":
                region = params.get("region", [None])[0]
                if region:
                    pia.region = region
                self.send_redirect("/")

            elif parsed.path == "/con":
                pia.connect()
                self.send_redirect("/")

            elif parsed.path == "/dis":
                pia.disconnect()
                self.send_redirect("/")

            elif parsed.path == "/pf/on":
                pia.port_forward = True
                self.send_redirect("/")

            elif parsed.path == "/pf/off":
                pia.port_forward = False
                self.send_redirect("/")

            else:
                self.send_response(404)
                self.end_headers()

    return Handler


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="PIA Remote Web — zero-dependency Python port of pia-web"
    )
    parser.add_argument("--piactl", default=DEFAULT_PIACTL,
                        help=f"Path to piactl binary (default: {DEFAULT_PIACTL})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Host to bind to (default: {DEFAULT_HOST})")
    args = parser.parse_args()

    pia = PIA(args.piactl)
    handler = make_handler(pia)

    print(f"[pia-web] Starting server on http://{args.host}:{args.port}")
    print(f"[pia-web] Using piactl at: {args.piactl}")
    print(f"[pia-web] Press Ctrl+C to stop.")

    server = HTTPServer((args.host, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[pia-web] Stopped.")


if __name__ == "__main__":
    main()
