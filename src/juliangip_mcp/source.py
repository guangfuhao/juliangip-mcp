from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from .config import DEFAULT_API_URL, load_credentials, profile_dir

_IP = r"\d{1,3}(?:\.\d{1,3}){3}"
_PORT = r"\d{1,5}"
_PATTERNS = [
    re.compile(rf"^(?P<ip>{_IP}):(?P<port>{_PORT}),(?P<remaining>\d+):(?P<user>[^:]+):(?P<pwd>.+)$"),
    re.compile(rf"^(?P<ip>{_IP}):(?P<port>{_PORT}),(?P<user>[^:]+):(?P<pwd>.+)$"),
    re.compile(rf"^(?P<ip>{_IP}):(?P<port>{_PORT})\|(?P<user>[^:]+):(?P<pwd>.+)$"),
    re.compile(rf"^(?P<ip>{_IP}):(?P<port>{_PORT}):(?P<user>[^:]+):(?P<pwd>[^:]+)"),
    re.compile(rf"^(?P<ip>{_IP}):(?P<port>{_PORT})$"),
]


class JuliangIPError(RuntimeError):
    pass


def _valid_host_port(ip: str, port: str) -> bool:
    try:
        return 0 < int(port) <= 65535 and all(0 <= int(part) <= 255 for part in ip.split("."))
    except ValueError:
        return False


@dataclass
class ProxyRecord:
    proxy_id: str
    host: str
    port: int
    remaining_seconds: int | None
    username: str | None
    password: str | None
    fetched_at: float

    @property
    def server(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def proxy_url(self) -> str:
        if self.username is None:
            return self.server
        return urlunsplit(("http", f"{quote(self.username, safe='')}:{quote(self.password or '', safe='')}@{self.host}:{self.port}", "", "", ""))

    def public(self, *, reveal_credentials: bool = False) -> dict[str, Any]:
        result = {"proxy_id": self.proxy_id, "server": self.server, "remaining_seconds": self.remaining_seconds, "fetched_at": self.fetched_at}
        if reveal_credentials:
            result.update({"username": self.username, "password": self.password, "proxy_url": self.proxy_url})
        else:
            result["authenticated"] = self.username is not None
        return result


def proxy_id(proxy_url: str) -> str:
    import hashlib
    return hashlib.sha256(proxy_url.encode()).hexdigest()[:8]


def redact(proxy_url: str) -> str:
    try:
        parts = urlsplit(proxy_url)
        return f"{parts.scheme}://{parts.hostname or '?'}{':' + str(parts.port) if parts.port else ''}"
    except Exception:
        return "<invalid-proxy>"


def parse_proxy_line(line: str, *, fetched_at: float | None = None) -> ProxyRecord | None:
    line = (line or "").strip().strip('"').strip("'")
    if not line or line.startswith("#"):
        return None
    fetched_at = fetched_at or time.time()
    if "://" in line:
        parts = urlsplit(line)
        if parts.scheme not in {"http", "https"} or not parts.hostname or not parts.port:
            return None
        raw_url = line
        return ProxyRecord(proxy_id(proxy_url=raw_url), parts.hostname, parts.port, None, parts.username, parts.password, fetched_at)
    for index, pattern in enumerate(_PATTERNS):
        match = pattern.match(line)
        if not match:
            continue
        data = match.groupdict()
        if not _valid_host_port(data["ip"], data["port"]):
            return None
        remaining = int(data["remaining"]) if data.get("remaining") else None
        user, password = data.get("user"), data.get("pwd")
        raw = f"http://{quote(user, safe='')}:{quote(password, safe='')}@{data['ip']}:{data['port']}" if user is not None else f"http://{data['ip']}:{data['port']}"
        return ProxyRecord(proxy_id(raw), data["ip"], int(data["port"]), remaining, user, password, fetched_at)
    return None


class JuliangIPSource:
    def __init__(self, *, timeout: float = 15.0):
        self.credentials = load_credentials()
        self.timeout = timeout
        self.cache_path = profile_dir() / "proxy-cache.json"

    def _load_cache(self) -> tuple[list[ProxyRecord], float]:
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return [ProxyRecord(**item) for item in raw.get("records", [])], float(raw.get("fetched_at", 0))
        except (FileNotFoundError, OSError, ValueError, TypeError):
            return [], 0.0

    def _save_cache(self, records: list[ProxyRecord]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"records": [asdict(record) for record in records], "fetched_at": time.time()}
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(self.cache_path)
        self.cache_path.chmod(0o600)

    def fetch(self, *, num: int = 3, force: bool = False) -> list[ProxyRecord]:
        if num < 1 or num > 100:
            raise JuliangIPError("num must be between 1 and 100")
        cached, fetched_at = self._load_cache()
        refresh_sec = float(self.credentials.get("refresh_sec", 150))
        if not force and cached and time.time() - fetched_at < refresh_sec:
            return cached
        if not self.credentials.get("trade_no") or not self.credentials.get("sign"):
            raise JuliangIPError("Missing trade_no/sign. Run the local setup page or set JULIANGIP_TRADE_NO and JULIANGIP_SIGN.")
        params = {"auth_type": 2, "ip_remain": 1, "num": num, "pt": 1, "result_type": "text", "split": 1, "trade_no": self.credentials["trade_no"], "sign": self.credentials["sign"]}
        try:
            response = httpx.get(self.credentials.get("api_url", DEFAULT_API_URL), params=params, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            if cached:
                return cached
            raise JuliangIPError(f"JuliangIP extraction request failed: {type(exc).__name__}") from exc
        text = response.text.strip()
        if text.upper().startswith("ERROR"):
            if cached:
                return cached
            raise JuliangIPError("JuliangIP returned an error response")
        records = [record for line in text.splitlines() if (record := parse_proxy_line(line)) is not None]
        if not records:
            if cached:
                return cached
            raise JuliangIPError("JuliangIP returned no recognizable proxy records")
        self._save_cache(records)
        return records
