# JuliangIP MCP · Codex Plugin

English | [简体中文](README.md)

An independent Codex plugin and stdio MCP server for authorized technical testing with JuliangIP proxies. It provides extraction, response parsing, local caching, health tracking and exit rotation, with setup/usage skills and a one-shot local configuration page. Signatures and proxy passwords are hidden by default. This community project is not affiliated with JuliangIP.

## Install with one sentence to your Agent

Send this to Codex:

> Install the JuliangIP plugin from https://github.com/guangfuhao/juliangip-mcp using its Codex marketplace, then run juliangip-setup to open the local configuration page. After saving, check local settings and pool status.

Requires Codex with plugin commands, Python 3.10+, and [uv](https://docs.astral.sh/uv/). Alternatively, run:

```sh
codex plugin marketplace add guangfuhao/juliangip-mcp
codex plugin add juliangip-mcp@juliangip-mcp
```

Start a new conversation after installation and ask the Agent to open JuliangIP setup. The repository includes `plugin.json`, `mcp.json`, setup/usage skills, and `.agents/plugins/marketplace.json`. The Agent performs installation; installing does not automatically buy or extract proxies.

## Official website and first-run setup

- [JuliangIP official website](https://www.juliangip.com/): sign in to your own account and obtain `trade_no` and `sign` from your order's extraction configuration.
- Default extraction endpoint: `http://v2.api.juliangip.com/company/postpay/getips`.

Call `juliangip_setup_local` on first use. It starts a separate temporary service bound only to `127.0.0.1` and returns a one-time browser link. Enter your order number (`trade_no`) and signature (`sign`); the service exits after saving, or after 10 minutes without completion. If the browser does not open automatically, ask the Agent to open the returned link.

Configuration is stored at `~/.config/juliangip-mcp/credentials.json` with owner-only `0600` permissions. Native settings-page availability depends on the Codex version; the local setup page works independently. Headless clients can supply `JULIANGIP_TRADE_NO`, `JULIANGIP_SIGN`, and optionally `JULIANGIP_API_URL` through a protected runtime environment. Do not put real values in prompts, commits, or installation commands.

The default extraction URL uses HTTP and transmits the order number and signature as GET parameters; use a trusted network. Change `api_url` only after confirming that your plan supports the alternative endpoint. Saving settings is local and does not authenticate upstream; the first actual extraction validates the order and signature.

## Example requests

- “Show JuliangIP local settings and pool status.” Reads local configuration and cache without extraction requests.
- “Fetch 3 JuliangIP proxies with redacted output.” Reuses valid cache where possible; a new extraction may consume plan quota.
- “Select a healthy proxy for this authorized test.” Reuses the current binding, then switches exits when the selection limit is reached.
- “Mark that proxy as a hard failure and select another healthy exit.” Cooling proxies are excluded from selection.

| Tool | Purpose |
| --- | --- |
| `juliangip_settings_read` / `juliangip_settings_update` | Read/save configuration with a masked signature |
| `juliangip_setup_local` | Launch the one-shot local setup page |
| `juliangip_fetch_proxies` | Extract/cache proxies; `force=true` requests a refresh |
| `juliangip_get_proxy` | Select a healthy exit, with `rotate` and `force_refresh` options |
| `juliangip_mark_proxy` | Record success, failure or hard-failure cooldown |
| `juliangip_pool_status` | Inspect cached, healthy, expired and cooling counts |
| `juliangip_redact_proxy` | Strip username/password from a proxy URL |

The plugin fixes `auth_type=2` and `pt=1`, and correctly parses formats such as `ip:port,remaining_seconds:user:pass`. Defaults: refresh interval 150 seconds, at most 3 selections per binding, failure threshold 2, cooldown 600 seconds. Remaining lifetime decreases with elapsed time. Expired or cooling records cannot be selected; an empty eligible pool returns an error until explicitly refreshed or cooled down.

Full proxy username, password and URL are returned only when both `reveal_credentials=true` and `confirm_reveal=true` are supplied. Default output contains redacted metadata. Pass credentials directly to your test program without displaying them in chat or logs. Cache files contain proxy authentication data and also use `0600` permissions.

The current implementation maintains one pool binding per local profile directory. It does not manage browsers, cookies, multiple browser identities, or system network settings. State files have no cross-process locking; do not share a directory between concurrent processes. Separate clients can use distinct `JULIANGIP_CONFIG_FILE` and `JULIANGIP_PROFILE_DIR` paths.

## Other MCP clients

```sh
git clone https://github.com/guangfuhao/juliangip-mcp.git
cd juliangip-mcp
uv sync
uv run juliangip-mcp
```

This runs a stdio MCP server. Configure an MCP client to launch `uv` with arguments `run --directory /absolute/path/to/juliangip-mcp juliangip-mcp`. To open the configuration page independently, run `uv run juliangip-setup-local`.

## Development and validation

```sh
uv sync --extra dev
uv run pytest -q
uv build
```

Tests use dummy credentials and mocked provider responses, never a real subscription. GitHub Actions tests and builds on Python 3.10/3.12. Releases include source archives and Python wheels; Codex users should use the repository marketplace for the complete plugin.

[MIT License](LICENSE). Report problems through [Issues](https://github.com/guangfuhao/juliangip-mcp/issues), with signatures, order numbers and proxy passwords removed.
