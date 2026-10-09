from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from juliangip_mcp.config import MASKED, config_path, save_credentials
from juliangip_mcp.server import juliangip_fetch_proxies, juliangip_get_proxy, juliangip_settings_update


def test_masked_signature_is_preserved(monkeypatch, tmp_path):
    monkeypatch.setenv('JULIANGIP_CONFIG_FILE', str(tmp_path / 'credentials.json'))
    save_credentials(trade_no='test-order', sign='dummy-secret')
    result = juliangip_settings_update({'sign': MASKED, 'max_uses': 5})
    assert result.values['sign'] == MASKED
    assert json.loads(config_path().read_text())['sign'] == 'dummy-secret'
    assert config_path().stat().st_mode & 0o777 == 0o600


def test_reveal_requires_both_flags():
    for tool in (juliangip_fetch_proxies, juliangip_get_proxy):
        result = json.loads(tool(reveal_credentials=True))
        assert result['ok'] is False
        assert 'confirm_reveal' in result['error']


def test_local_setup_saves_and_exits(tmp_path):
    # Own subprocess, no browser. Always reap it, including assertion failures.
    env = dict(os.environ, JULIANGIP_CONFIG_FILE=str(tmp_path / 'credentials.json'))
    process = subprocess.Popen([sys.executable, '-m', 'juliangip_mcp.setup_server', '--serve', '--no-open', '--timeout', '30'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rendezvous = Path(f'/tmp/juliangip-setup-{process.pid}.url')
    try:
        deadline = time.monotonic() + 5
        while not rendezvous.exists() and time.monotonic() < deadline:
            time.sleep(0.03)
        assert rendezvous.exists()
        assert rendezvous.stat().st_mode & 0o777 == 0o600
        url = rendezvous.read_text().strip()
        with pytest.raises(HTTPError) as unauthorized:
            urlopen(url.split('?')[0], timeout=2)
        assert unauthorized.value.code == 404
        with urlopen(url, timeout=2) as response:
            assert b'type="password"' in response.read()
        request = Request(url, data=urlencode({'trade_no': 'test-order', 'sign': 'dummy-secret'}).encode(), method='POST')
        with urlopen(request, timeout=2) as response:
            body = response.read()
            assert b'configured' in body
            assert b'dummy-secret' not in body
        assert process.wait(timeout=5) == 0
        saved = tmp_path / 'credentials.json'
        assert json.loads(saved.read_text())['sign'] == 'dummy-secret'
        assert saved.stat().st_mode & 0o777 == 0o600
        assert not rendezvous.exists()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        rendezvous.unlink(missing_ok=True)
