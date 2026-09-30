from __future__ import annotations

import httpx

from juliangip_mcp.source import JuliangIPSource, parse_proxy_line


def test_parse_juliangip_line_does_not_treat_remaining_seconds_as_username():
    record = parse_proxy_line("61.160.216.142:15652,180:proxy-user:proxy-pass")
    assert record is not None
    assert record.host == "61.160.216.142"
    assert record.port == 15652
    assert record.remaining_seconds == 180
    assert record.username == "proxy-user"
    assert record.password == "proxy-pass"
    assert ":180@" not in record.proxy_url


def test_parse_supported_variants():
    assert parse_proxy_line("1.2.3.4:8080")
    assert parse_proxy_line("1.2.3.4:8080,user:pass")
    assert parse_proxy_line("1.2.3.4:8080|user:pass")
    assert parse_proxy_line("http://user:pass@1.2.3.4:8080")
    assert parse_proxy_line("not-a-proxy") is None


def test_fetch_caches_provider_response(monkeypatch, tmp_path):
    monkeypatch.setenv("JULIANGIP_CONFIG_FILE", str(tmp_path / "credentials.json"))
    from juliangip_mcp.config import save_credentials
    save_credentials(trade_no="trade", sign="secret", refresh_sec=600)
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        request = httpx.Request("GET", url)
        return httpx.Response(200, text="1.2.3.4:8080,180:user:pass\n", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr("juliangip_mcp.source.profile_dir", lambda: tmp_path)
    source = JuliangIPSource()
    first = source.fetch(num=1)
    second = source.fetch(num=1)
    assert len(first) == len(second) == 1
    assert len(calls) == 1
    assert "secret" not in str(first[0].public())
