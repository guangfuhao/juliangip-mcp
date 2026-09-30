# juliangip-mcp

`juliangip-mcp` is a proxy-pool plugin for authorized technical testing with JuliangIP. It fetches extraction results, parses provider formats, caches records, tracks health, rotates exits, and redacts credentials by default. It contains no hard-coded order number or signature.

## One-sentence install

> Install and run `juliangip-mcp`; on first use open its local setup page to enter the JuliangIP `trade_no` and `sign`, then inspect the proxy pool status.

## Official links

- [JuliangIP official website](https://www.juliangip.com/)
- [JuliangIP API documentation](https://www.juliangip.com/)
- Default extraction API: `http://v2.api.juliangip.com/company/postpay/getips`

## First-run configuration

The extraction endpoint uses the order number `trade_no` and signature `sign`. When the current Codex local-plugin page only shows skills, `juliangip-setup` calls `juliangip_setup_local`, which starts a temporary form bound to `127.0.0.1`. After saving, the service exits and stores the signature in the current user's local configuration with `0600` permissions.

The plugin fixes `auth_type=2` (account/password proxy authorization) and `pt=1` (HTTP/HTTPS proxies) as required by the documented response format. `refresh_sec` defaults to 150 seconds and `max_uses` defaults to 3 to avoid using expired or overused exits.

Headless environments can use `JULIANGIP_TRADE_NO`, `JULIANGIP_SIGN`, and optionally `JULIANGIP_API_URL`. The signature is never written to source, README files, GitHub, logs, ordinary chat messages, or default tool output.

## Capabilities

- `juliangip_settings_read` / `juliangip_settings_update`: read or save settings with the signature masked;
- `juliangip_setup_local`: open the one-shot local setup page;
- `juliangip_fetch_proxies`: fetch and cache proxies, returning redacted metadata by default;
- `juliangip_get_proxy`: select a proxy using health and profile binding;
- `juliangip_mark_proxy`: record success, failure, or hard-failure cooldown;
- `juliangip_pool_status`: inspect cached, healthy, and cooling counts;
- `juliangip_redact_proxy`: remove username and password from a proxy URL.

Proxy username, password, and full URL are returned only when both `reveal_credentials=true` and `confirm_reveal=true` are supplied. Cache and state files use owner-only `0600` permissions.

## Safety boundaries

The signature is a quota credential and must never enter a repository or log. Fetching prefers the cache to avoid repeated billable extraction calls; use `force=true` only when the cache is empty, expired, or exhausted. Strict mode fails when no healthy proxy is available instead of silently falling back to a direct connection.

Chinese documentation: [README.md](README.md)
