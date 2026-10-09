from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from .config import DEFAULT_API_URL, MASKED, load_credentials, save_credentials, settings_snapshot
from .pool import ProxyPool
from .source import JuliangIPError

mcp = FastMCP("JuliangIP Proxy API")


class SettingsReadResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_: dict[str, Any] = Field(alias="schema")
    values: dict[str, Any]
    layout: list[dict[str, Any]] = Field(default_factory=list)


class SettingsUpdateResult(BaseModel):
    values: dict[str, Any]


def _advertise_native_settings() -> None:
    original = mcp._mcp_server.create_initialization_options

    def create_initialization_options(notification_options: Any = None, experimental_capabilities: dict[str, dict[str, Any]] | None = None):
        capabilities = dict(experimental_capabilities or {})
        settings = dict(capabilities.get("openai/settings", {}))
        settings.setdefault("readTool", "juliangip_settings_read")
        settings.setdefault("updateTool", "juliangip_settings_update")
        capabilities["openai/settings"] = settings
        options = original(notification_options, capabilities)
        try:
            options.capabilities.extensions = {"openai/settings": settings}
        except (AttributeError, TypeError):
            pass
        return options

    mcp._mcp_server.create_initialization_options = create_initialization_options


_advertise_native_settings()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _error(exc: Exception) -> str:
    if isinstance(exc, JuliangIPError):
        return _json({"ok": False, "error": str(exc)})
    return _json({"ok": False, "error": str(exc)})


def _require_reveal(reveal_credentials: bool, confirm_reveal: bool) -> None:
    if reveal_credentials and not confirm_reveal:
        raise JuliangIPError("Credential output is disabled by default; set confirm_reveal=true together with reveal_credentials=true")


@mcp.tool(name="juliangip_settings_read", title="JuliangIP settings", description="Read local JuliangIP settings with the signature masked.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False), structured_output=True)
def juliangip_settings_read() -> SettingsReadResult:
    snapshot = settings_snapshot()
    return SettingsReadResult(schema_={"type": "object", "properties": {"trade_no": {"type": "string", "title": "trade_no", "minLength": 1}, "sign": {"type": "string", "title": "sign", "description": "JuliangIP extraction signature; masked after saving.", "minLength": 1}, "api_url": {"type": "string", "title": "Extraction API URL"}, "refresh_sec": {"type": "number", "title": "Refresh seconds"}, "max_uses": {"type": "integer", "title": "Max uses per IP"}}, "required": ["trade_no", "sign"]}, values={k: snapshot[k] for k in ("trade_no", "sign", "api_url", "refresh_sec", "max_uses")}, layout=[{"kind": "group", "title": "JuliangIP account", "items": [{"kind": "property", "property": "trade_no"}, {"kind": "property", "property": "sign"}, {"kind": "property", "property": "api_url"}, {"kind": "property", "property": "refresh_sec"}, {"kind": "property", "property": "max_uses"}]}])


@mcp.tool(name="juliangip_settings_update", title="Save JuliangIP settings", description="Save the JuliangIP order and signature from a settings page.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False), structured_output=True)
def juliangip_settings_update(set: dict[str, Any]) -> SettingsUpdateResult:
    allowed = {"trade_no", "sign", "api_url", "refresh_sec", "max_uses"}
    unknown = set.keys() - allowed
    if unknown:
        raise ValueError(f"Unsupported JuliangIP settings: {', '.join(sorted(unknown))}")
    current = load_credentials()
    provided_sign = set.get("sign")
    sign = current["sign"] if not provided_sign or provided_sign == MASKED else str(provided_sign)
    trade_no = set.get("trade_no") or current["trade_no"]
    save_credentials(trade_no=trade_no, sign=sign, api_url=str(set.get("api_url") or current["api_url"] or DEFAULT_API_URL), refresh_sec=float(set.get("refresh_sec") or current["refresh_sec"]), max_uses=int(set.get("max_uses") or current["max_uses"]))
    snapshot = settings_snapshot()
    return SettingsUpdateResult(values={k: snapshot[k] for k in ("trade_no", "sign", "api_url", "refresh_sec", "max_uses")})


@mcp.tool(name="juliangip_setup_local", title="Open JuliangIP local setup", description="Launch a one-shot localhost form for the JuliangIP order and signature. The form closes after saving.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
def juliangip_setup_local(open_browser: bool = True) -> str:
    from .setup_server import launch_setup_service
    try:
        return _json(launch_setup_service(open_browser=open_browser))
    except Exception as exc:
        return _error(exc)


@mcp.tool(name="juliangip_fetch_proxies", title="Fetch JuliangIP proxies", description="Fetch and cache a batch of JuliangIP HTTP proxies. Credentials are omitted unless explicitly revealed.")
def juliangip_fetch_proxies(num: int = 3, force: bool = False, reveal_credentials: bool = False, confirm_reveal: bool = False) -> str:
    try:
        _require_reveal(reveal_credentials, confirm_reveal)
        records = ProxyPool().records(num=num, force=force)
        return _json({"ok": True, "count": len(records), "proxies": [record.public(reveal_credentials=reveal_credentials) for record in records]})
    except Exception as exc:
        return _error(exc)


@mcp.tool(name="juliangip_get_proxy", title="Get a JuliangIP proxy", description="Select a healthy proxy using a single local pool binding. Credentials are omitted by default.")
def juliangip_get_proxy(force_refresh: bool = False, rotate: bool = False, preferred_proxy_id: str | None = None, reveal_credentials: bool = False, confirm_reveal: bool = False) -> str:
    try:
        _require_reveal(reveal_credentials, confirm_reveal)
        record = ProxyPool().pick(preferred_id=preferred_proxy_id, rotate=rotate, num=3, force=force_refresh)
        return _json({"ok": True, "proxy": record.public(reveal_credentials=reveal_credentials)})
    except Exception as exc:
        return _error(exc)


@mcp.tool(name="juliangip_mark_proxy", title="Mark proxy health", description="Record a proxy success or failure for cooling and rotation decisions.")
def juliangip_mark_proxy(proxy_id: str, ok: bool, hard: bool = False) -> str:
    try:
        return _json({"ok": True, "state": ProxyPool().mark(proxy_id, ok=ok, hard=hard)})
    except Exception as exc:
        return _error(exc)


@mcp.tool(name="juliangip_pool_status", title="JuliangIP pool status", description="Read proxy pool counts, cache age, cooling count, and rotation settings without exposing credentials.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def juliangip_pool_status() -> str:
    try:
        return _json({"ok": True, **ProxyPool().status()})
    except Exception as exc:
        return _error(exc)


@mcp.tool(name="juliangip_redact_proxy", title="Redact proxy URL", description="Return only the scheme, host, and port from a proxy URL; credentials are removed.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
def juliangip_redact_proxy(proxy_url: str) -> str:
    from .source import redact
    return _json({"ok": True, "proxy": redact(proxy_url)})


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
