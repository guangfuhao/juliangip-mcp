from __future__ import annotations

import argparse
import html
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import DEFAULT_API_URL, save_credentials

_STYLE = "body{font:16px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:48px auto;padding:0 20px;color:#172033;background:#f7f9fc}main{background:#fff;border:1px solid #e3e8f0;border-radius:16px;padding:28px;box-shadow:0 8px 28px #17203312}h1{font-size:24px;margin:0 0 8px}p{line-height:1.5;color:#566176}label{display:block;font-weight:600;margin:18px 0 7px}input{box-sizing:border-box;width:100%;padding:11px 12px;border:1px solid #c9d2df;border-radius:9px;font-size:16px}button{margin-top:24px;padding:11px 16px;border:0;border-radius:9px;background:#1769e0;color:#fff;font-size:16px;font-weight:600;cursor:pointer}.hint{font-size:13px;color:#6b7585;margin-top:16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}"


def _page(message: str = "", success: bool = False) -> bytes:
    alert = f'<p style="color:{"#18794e" if success else "#b42318"}">{html.escape(message)}</p>' if message else ""
    if success:
        content = f"<h1>JuliangIP is configured</h1>{alert}<p>You can close this tab. The temporary local setup service has stopped.</p>"
    else:
        content = f"""
<h1>JuliangIP setup</h1>
<p>Enter the order and signature locally. This page is served only from this computer and the temporary service closes after saving.</p>
{alert}
<form method="post">
  <label for="trade_no">trade_no</label>
  <input id="trade_no" name="trade_no" autocomplete="off" required>
  <label for="sign">sign</label>
  <input id="sign" name="sign" type="password" autocomplete="off" required>
  <label for="api_url">Extraction API URL</label>
  <input id="api_url" name="api_url" value="{DEFAULT_API_URL}" autocomplete="url">
  <div class="grid">
    <div><label for="refresh_sec">Refresh seconds</label><input id="refresh_sec" name="refresh_sec" value="150" inputmode="numeric"></div>
    <div><label for="max_uses">Max uses per IP</label><input id="max_uses" name="max_uses" value="3" inputmode="numeric"></div>
  </div>
  <button type="submit">Save securely</button>
</form>
<p class="hint">auth_type=2 and pt=1 are fixed for the documented account/password proxy response. The signature is never displayed back to the page.</p>
"""
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>JuliangIP setup</title><style>{_STYLE}</style></head><body><main>{content}</main></body></html>".encode()


class _SetupServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple[str, int], access_token: str):
        super().__init__(address, _SetupHandler)
        self.access_token = access_token
        self.completed = False


class _SetupHandler(BaseHTTPRequestHandler):
    server: _SetupServer

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _authorized(self) -> bool:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        return secrets.compare_digest(query.get("setup", [""])[0], self.server.access_token)

    def _send(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        authorized = self._authorized()
        self._send(_page() if authorized else _page("This setup link is invalid or expired."), 200 if authorized else 404)

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._send(_page("This setup link is invalid or expired."), 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16 * 1024:
                raise ValueError("invalid form size")
            fields = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            trade_no = fields.get("trade_no", [""])[0].strip()
            sign = fields.get("sign", [""])[0].strip()
            api_url = fields.get("api_url", [DEFAULT_API_URL])[0].strip() or DEFAULT_API_URL
            refresh_sec = float(fields.get("refresh_sec", ["150"])[0])
            max_uses = int(fields.get("max_uses", ["3"])[0])
            save_credentials(trade_no=trade_no, sign=sign, api_url=api_url, refresh_sec=refresh_sec, max_uses=max_uses)
        except (OSError, ValueError, UnicodeDecodeError):
            self._send(_page("The configuration could not be saved locally."), 400)
            return
        self.server.completed = True
        self._send(_page("Configuration saved locally.", success=True))
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def _serve(timeout: int, open_browser: bool) -> int:
    setup_token = secrets.token_urlsafe(32)
    server = _SetupServer(("127.0.0.1", 0), setup_token)
    url = f"http://127.0.0.1:{server.server_port}/?setup={urllib.parse.quote(setup_token)}"
    rendezvous = f"/tmp/juliangip-setup-{os.getpid()}.url"
    with open(rendezvous, "w", encoding="utf-8") as handle:
        handle.write(url + "\n")
    os.chmod(rendezvous, 0o600)
    if open_browser:
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass

    def stop_on_timeout() -> None:
        time.sleep(timeout)
        if not server.completed:
            server.shutdown()

    threading.Thread(target=stop_on_timeout, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        try:
            os.unlink(rendezvous)
        except OSError:
            pass
    return 0


def launch_setup_service(*, open_browser: bool = True, timeout: int = 600) -> dict[str, Any]:
    process = subprocess.Popen([sys.executable, "-m", "juliangip_mcp.setup_server", "--serve", "--timeout", str(timeout), *(["--no-open"] if not open_browser else [])], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
    rendezvous = f"/tmp/juliangip-setup-{process.pid}.url"
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and not os.path.exists(rendezvous):
        time.sleep(0.03)
    if not os.path.exists(rendezvous):
        return {"started": False, "error": "The local setup service did not start."}
    with open(rendezvous, encoding="utf-8") as handle:
        url = handle.read().strip()
    try:
        os.unlink(rendezvous)
    except OSError:
        pass
    return {"started": True, "pid": process.pid, "url": url, "expires_in_seconds": timeout, "message": "Complete the local form; the service exits after saving."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if args.serve:
        return _serve(max(30, min(args.timeout, 3600)), not args.no_open)
    result = launch_setup_service(open_browser=not args.no_open, timeout=args.timeout)
    if result.get("started"):
        print(result["url"])
        return 0
    print(result["error"], file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
