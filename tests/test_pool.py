from __future__ import annotations

from juliangip_mcp.config import save_credentials
from juliangip_mcp.pool import ProxyPool
from juliangip_mcp.source import ProxyRecord


def test_pool_marks_and_reports_health(monkeypatch, tmp_path):
    monkeypatch.setenv("JULIANGIP_CONFIG_FILE", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("JULIANGIP_PROFILE_DIR", str(tmp_path))
    save_credentials(trade_no="trade", sign="secret", fail_threshold=1, cooldown_sec=600)
    pool = ProxyPool()
    record = ProxyRecord("abc12345", "1.2.3.4", 8080, 180, "u", "p", 0)
    monkeypatch.setattr(pool.source, "fetch", lambda **kwargs: [record])
    selected = pool.pick()
    assert selected.proxy_id == "abc12345"
    state = pool.mark("abc12345", ok=False, hard=True)
    assert state["cooldown_until"] > 0
    status = pool.status()
    assert status["cooling_records"] == 0  # status reads cache, not the mocked source
