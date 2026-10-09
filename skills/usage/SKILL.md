---
name: juliangip-usage
description: Use the JuliangIP proxy pool safely for authorized technical tests.
---

# JuliangIP usage

Use the installed `juliangip-mcp` server after `juliangip-setup` has configured the order and signature.

Safe flow:

1. Call `juliangip_pool_status` to inspect cache and cooling counts.
2. Call `juliangip_fetch_proxies` with the smallest needed `num`; use `force=true` only when the cache is stale or empty.
3. Call `juliangip_get_proxy` to obtain a selection using the single local pool binding. It returns only redacted metadata by default. Set `force_refresh=true` only for an explicitly requested extraction; it can consume provider quota.
4. Call `juliangip_mark_proxy` after an authorized test reports success or failure.

The full username/password or proxy URL is returned only when both `reveal_credentials=true` and `confirm_reveal=true` are supplied. Never reveal proxy credentials in normal chat or logs. Keep `auth_type=2`, `pt=1`, `refresh_sec` below the provider's IP lifetime, and `max_uses` conservative. Do not call the provider repeatedly to probe quota.
