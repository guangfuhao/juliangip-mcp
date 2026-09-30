---
name: juliangip-setup
description: Configure JuliangIP order and extraction signature after the plugin is installed.
---

# JuliangIP setup

Run this before fetching or selecting a proxy.

1. If the host exposes a native settings page, enter the JuliangIP `trade_no` and `sign` there.
2. Otherwise call `juliangip_setup_local` with `open_browser=true`. It starts a one-shot localhost form; the user enters the values there and the service exits after saving.
3. Keep `auth_type=2` and `pt=1`; the plugin enforces those documented settings for account/password proxy responses.
4. Confirm setup with `juliangip_pool_status` or a small `juliangip_fetch_proxies` call. Do not reveal credentials by default.

The signature is a quota credential. Never put it in chat, tool output, logs, repositories, screenshots, or commits. Headless environments can use `JULIANGIP_TRADE_NO`, `JULIANGIP_SIGN`, and `JULIANGIP_API_URL` from a secure environment.
