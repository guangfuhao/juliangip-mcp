from __future__ import annotations

import time

import pytest

from juliangip_mcp.config import save_credentials
from juliangip_mcp.pool import ProxyPool
from juliangip_mcp.source import JuliangIPError, ProxyRecord


def test_pool_marks_and_reports_health(monkeypatch, tmp_path):
    monkeypatch.setenv("JULIANGIP_CONFIG_FILE", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("JULIANGIP_PROFILE_DIR", str(tmp_path))
    save_credentials(trade_no="trade", sign="secret", fail_threshold=1, cooldown_sec=600)
    pool = ProxyPool()
    record = ProxyRecord("abc12345", "1.2.3.4", 8080, 180, "u", "p", time.time())
    pool.source._save_cache([record])
    monkeypatch.setattr(pool.source, "fetch", lambda **kwargs: [record])
    selected = pool.pick()
    assert selected.proxy_id == "abc12345"
    state = pool.mark("abc12345", ok=False, hard=True)
    assert state["cooldown_until"] > 0
    status = pool.status()
    assert status["cooling_records"] == 1
    assert status["healthy_records"] == 0
    with pytest.raises(JuliangIPError):
        pool.pick()  # A bound proxy must not bypass its cooldown.


def test_rotation_and_max_uses_choose_a_different_exit(monkeypatch, tmp_path):
    monkeypatch.setenv("JULIANGIP_CONFIG_FILE", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("JULIANGIP_PROFILE_DIR", str(tmp_path))
    save_credentials(trade_no="trade", sign="secret", max_uses=2)
    pool = ProxyPool()
    records = [ProxyRecord(str(i), f"1.2.3.{i}", 8080, 180, "u", "p", time.time()) for i in (1, 2)]
    calls = []
    def fetch(**kwargs):
        calls.append(kwargs)
        return records
    monkeypatch.setattr(pool.source, "fetch", fetch)
    first = pool.pick()
    assert pool.pick().proxy_id == first.proxy_id
    third = pool.pick(force=True)
    assert third.proxy_id != first.proxy_id
    assert calls[-1]["force"] is True
    assert pool.pick(rotate=True).proxy_id == first.proxy_id


def test_expired_bound_proxy_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("JULIANGIP_CONFIG_FILE", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("JULIANGIP_PROFILE_DIR", str(tmp_path))
    pool = ProxyPool()
    record = ProxyRecord("expired", "1.2.3.4", 8080, 10, "u", "p", time.time() - 20)
    pool.source._save_cache([record])
    pool._save_binding({"proxy_id": "expired", "uses": 1})
    monkeypatch.setattr(pool.source, "fetch", lambda **kwargs: [record])
    with pytest.raises(JuliangIPError):
        pool.pick()
    assert pool.status()["expired_records"] == 1
