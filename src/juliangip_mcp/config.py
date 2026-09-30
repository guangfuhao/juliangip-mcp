from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MASKED = "••••••••"
DEFAULT_API_URL = "http://v2.api.juliangip.com/company/postpay/getips"
DEFAULT_PROFILE_DIR = Path.home() / ".config" / "juliangip-mcp"


def config_path() -> Path:
    return Path(os.getenv("JULIANGIP_CONFIG_FILE", "").strip() or (DEFAULT_PROFILE_DIR / "credentials.json")).expanduser()


def profile_dir() -> Path:
    return Path(os.getenv("JULIANGIP_PROFILE_DIR", "").strip() or DEFAULT_PROFILE_DIR).expanduser()


def load_credentials() -> dict[str, Any]:
    try:
        raw = json.loads(config_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "trade_no": str(os.getenv("JULIANGIP_TRADE_NO", "").strip() or raw.get("trade_no", "")).strip(),
        "sign": str(os.getenv("JULIANGIP_SIGN", "").strip() or raw.get("sign", "")).strip(),
        "api_url": str(os.getenv("JULIANGIP_API_URL", "").strip() or raw.get("api_url", DEFAULT_API_URL)).strip(),
        "auth_type": int(os.getenv("JULIANGIP_AUTH_TYPE", raw.get("auth_type", 2))),
        "pt": int(os.getenv("JULIANGIP_PT", raw.get("pt", 1))),
        "refresh_sec": float(os.getenv("JULIANGIP_REFRESH_SEC", raw.get("refresh_sec", 150))),
        "max_uses": int(os.getenv("JULIANGIP_MAX_USES", raw.get("max_uses", 3))),
        "fail_threshold": int(os.getenv("JULIANGIP_FAIL_THRESHOLD", raw.get("fail_threshold", 2))),
        "cooldown_sec": float(os.getenv("JULIANGIP_COOLDOWN_SEC", raw.get("cooldown_sec", 600))),
        "strict": str(os.getenv("JULIANGIP_STRICT", str(raw.get("strict", True)))).lower() in {"1", "true", "yes", "on"},
    }


def save_credentials(*, trade_no: str, sign: str, api_url: str = DEFAULT_API_URL, auth_type: int = 2, pt: int = 1, refresh_sec: float = 150, max_uses: int = 3, fail_threshold: int = 2, cooldown_sec: float = 600, strict: bool = True) -> None:
    trade_no, sign = trade_no.strip(), sign.strip()
    if not trade_no or not sign:
        raise ValueError("trade_no and sign are required")
    if auth_type != 2 or pt != 1:
        raise ValueError("JuliangIP plugin requires auth_type=2 and pt=1")
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"trade_no": trade_no, "sign": sign, "api_url": api_url.strip() or DEFAULT_API_URL, "auth_type": 2, "pt": 1, "refresh_sec": max(1, float(refresh_sec)), "max_uses": max(1, int(max_uses)), "fail_threshold": max(1, int(fail_threshold)), "cooldown_sec": max(1, float(cooldown_sec)), "strict": bool(strict)}, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def settings_snapshot() -> dict[str, Any]:
    c = load_credentials()
    return {"trade_no": c["trade_no"], "sign": MASKED if c["sign"] else "", "api_url": c["api_url"], "auth_type": c["auth_type"], "pt": c["pt"], "refresh_sec": c["refresh_sec"], "max_uses": c["max_uses"], "strict": c["strict"], "configured": bool(c["trade_no"] and c["sign"])}
