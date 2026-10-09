from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from .config import load_credentials, profile_dir, write_private_json
from .source import JuliangIPError, JuliangIPSource, ProxyRecord


class ProxyPool:
    def __init__(self):
        self.credentials = load_credentials()
        self.state_path = profile_dir() / "proxy-state.json"
        self.binding_path = profile_dir() / "proxy-binding.json"
        self.source = JuliangIPSource()

    def _state(self) -> dict[str, dict[str, float | int]]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (FileNotFoundError, OSError, ValueError):
            return {}

    def _save_state(self, state: dict[str, dict[str, float | int]]) -> None:
        write_private_json(self.state_path, state)

    def _binding(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.binding_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (FileNotFoundError, OSError, ValueError):
            return {}

    def _save_binding(self, binding: dict[str, Any]) -> None:
        write_private_json(self.binding_path, binding)

    def records(self, *, force: bool = False, num: int = 3) -> list[ProxyRecord]:
        return self.source.fetch(num=num, force=force)

    def pick(self, *, preferred_id: str | None = None, rotate: bool = False, num: int = 3, force: bool = False) -> ProxyRecord:
        records = self.records(num=num, force=force)
        if not records:
            raise JuliangIPError("No proxy records available")
        state = self._state()
        now = time.time()
        available = [record for record in records if
                     float(state.get(record.proxy_id, {}).get("cooldown_until", 0)) <= now
                     and (record.remaining_at(now) is None or record.remaining_at(now) > 0)]
        by_id = {record.proxy_id: record for record in available}
        binding = self._binding()
        bound_id = binding.get("proxy_id")
        if not rotate and preferred_id in by_id:
            bound_id = preferred_id
        if not rotate and bound_id in by_id and int(binding.get("uses", 0)) < int(self.credentials.get("max_uses", 3)):
            chosen = by_id[bound_id]
        else:
            if bound_id and (rotate or int(binding.get("uses", 0)) >= int(self.credentials.get("max_uses", 3))):
                # Do not randomly reselect the same exhausted/bound exit.
                available = [record for record in available if record.proxy_id != bound_id]
            if not available:
                if self.credentials.get("strict", True):
                    raise JuliangIPError("All proxy records are cooling down or expired; strict mode refuses an unsafe fallback")
                raise JuliangIPError("No healthy proxy available; refresh the pool explicitly")
            chosen = random.choice(available)
        uses = int(binding.get("uses", 0)) + 1 if binding.get("proxy_id") == chosen.proxy_id and not rotate else 1
        self._save_binding({"proxy_id": chosen.proxy_id, "uses": uses, "bound_at": time.time()})
        entry = state.setdefault(chosen.proxy_id, {"fails": 0, "oks": 0, "cooldown_until": 0.0, "last_used": 0.0})
        entry["last_used"] = now
        self._save_state(state)
        return chosen

    def mark(self, proxy_id: str, *, ok: bool, hard: bool = False) -> dict[str, Any]:
        state = self._state()
        entry = state.setdefault(proxy_id, {"fails": 0, "oks": 0, "cooldown_until": 0.0, "last_used": 0.0})
        if ok:
            entry["oks"] = int(entry.get("oks", 0)) + 1
            entry["fails"] = 0
            entry["cooldown_until"] = 0.0
        else:
            entry["fails"] = int(entry.get("fails", 0)) + 1
            if hard or int(entry["fails"]) >= int(self.credentials.get("fail_threshold", 2)):
                entry["cooldown_until"] = time.time() + float(self.credentials.get("cooldown_sec", 600))
        self._save_state(state)
        return {"proxy_id": proxy_id, "ok": ok, "fails": entry["fails"], "oks": entry["oks"], "cooldown_until": entry["cooldown_until"]}

    def status(self) -> dict[str, Any]:
        records, fetched_at = self.source._load_cache()
        now = time.time()
        state = self._state()
        cooling = sum(1 for record in records if float(state.get(record.proxy_id, {}).get("cooldown_until", 0)) > now)
        expired = sum(1 for record in records if record.remaining_at(now) == 0)
        healthy = sum(1 for record in records if record.remaining_at(now) != 0 and float(state.get(record.proxy_id, {}).get("cooldown_until", 0)) <= now)
        return {"cached_records": len(records), "healthy_records": healthy, "expired_records": expired, "cooling_records": cooling, "cache_age_seconds": round(now - fetched_at, 2) if fetched_at else None, "strict": bool(self.credentials.get("strict", True)), "max_uses": int(self.credentials.get("max_uses", 3))}
