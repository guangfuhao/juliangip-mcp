# juliangip-mcp

`juliangip-mcp` 是面向已授权技术测试的巨量IP代理池插件，负责提取链接调用、响应解析、磁盘缓存、代理池健康状态、出口轮换和脱敏输出。它不包含任何硬编码订单号或签名。

## 一句话安装

> 安装并运行 `juliangip-mcp` 插件；首次使用打开本地配置页输入巨量IP `trade_no` 和 `sign`，然后查询代理池状态。

## 官方入口

- [巨量IP官方网站](https://www.juliangip.com/)
- [巨量IP API 接入文档](https://www.juliangip.com/)
- 提取 API 默认地址：`http://v2.api.juliangip.com/company/postpay/getips`

## 首次配置

巨量IP提取接口使用订单号 `trade_no` 和签名 `sign`。当前 Codex 本地插件页如果只显示技能，`juliangip-setup` 会调用 `juliangip_setup_local`，启动只监听 `127.0.0.1` 的临时配置页。输入配置并保存后服务自动关闭，签名写入当前用户的本地配置并设置为 `0600`。

插件固定使用文档要求的 `auth_type=2`（账号密码鉴权）和 `pt=1`（HTTP/HTTPS 代理）。`refresh_sec` 默认 150 秒，`max_uses` 默认 3；这两个值用于避免继续使用临近过期或已经高频使用的出口。

无图形界面的环境使用 `JULIANGIP_TRADE_NO`、`JULIANGIP_SIGN` 和可选的 `JULIANGIP_API_URL`。签名不会写入代码、README、GitHub、日志、普通聊天消息或默认工具输出。

## 能力

- `juliangip_settings_read` / `juliangip_settings_update`：读取或保存设置，签名始终掩码；
- `juliangip_setup_local`：启动一次性本地配置页；
- `juliangip_fetch_proxies`：提取并缓存代理，默认只返回脱敏信息；
- `juliangip_get_proxy`：按健康度和绑定关系选择代理；
- `juliangip_mark_proxy`：记录成功、失败和硬失败冷却；
- `juliangip_pool_status`：查看缓存数量、健康数量和冷却数量；
- `juliangip_redact_proxy`：移除代理 URL 中的用户名和密码。

只有同时传入 `reveal_credentials=true` 和 `confirm_reveal=true` 时，提取或选择工具才会返回代理用户名、密码和完整 URL。代理写入缓存和状态文件时采用 `0600` 权限。

## 安全边界

签名等同于套餐额度钥匙，不能写入仓库或日志。提取调用会优先使用缓存，避免每次测试重复计费；`force=true` 只应在缓存为空、过期或代理池耗尽时使用。严格模式下没有健康代理会直接报错，不会静默回退直连。

English documentation: [README.en.md](README.en.md)
