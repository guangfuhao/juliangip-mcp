# JuliangIP MCP · 巨量IP Codex 插件

[English](README.en.md) | 简体中文

面向已授权技术测试的独立 Codex 插件和 MCP 服务，支持巨量IP代理提取、格式解析、本地缓存、健康记录及出口轮换。内置配置技能和一次性本地配置页，默认隐藏签名与代理密码。这是社区项目，与巨量IP官方无隶属关系。

## 一句话让 Agent 安装

把下面这句话发给 Codex：

> 请从 https://github.com/guangfuhao/juliangip-mcp 安装 JuliangIP 插件，添加仓库中的 Codex marketplace，并运行 juliangip-setup 打开本地配置页；配置完成后检查本地设置和代理池状态。

需要支持插件命令的 Codex、Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)。也可以在终端执行：

```sh
codex plugin marketplace add guangfuhao/juliangip-mcp
codex plugin add juliangip-mcp@juliangip-mcp
```

安装后开启新会话，向 Agent 说“使用 JuliangIP setup 打开配置页”。插件包含 `plugin.json`、`mcp.json`、setup/usage 技能及 `.agents/plugins/marketplace.json`。安装方式由 Agent 执行；不会在安装时自动购买或提取代理。

## 官方入口与首次配置

- [巨量IP官方网站](https://www.juliangip.com/)：登录自己的账户，使用自己订单的提取配置取得 `trade_no` 和 `sign`。
- 默认提取地址：`http://v2.api.juliangip.com/company/postpay/getips`。

首次使用调用 `juliangip_setup_local`。它启动仅监听 `127.0.0.1` 的独立临时服务，并返回一次性浏览器链接；页面输入订单号 `trade_no` 与签名 `sign`，保存后服务自动退出。未保存时默认 10 分钟后退出。若浏览器没有自动打开，让 Agent 打开工具返回的链接。

配置默认保存在 `~/.config/juliangip-mcp/credentials.json`，文件权限为 `0600`。原生插件详情页是否显示设置取决于 Codex 版本，本地配置页可以独立使用。无图形界面的环境可以通过受保护的运行环境提供 `JULIANGIP_TRADE_NO`、`JULIANGIP_SIGN` 和可选的 `JULIANGIP_API_URL`，不要把真实值写进提示词、Git 提交或安装命令。

默认提取地址使用 HTTP，订单号与签名随 GET 请求传输；请在信任的网络中使用。只有确认套餐支持其他地址时才修改 `api_url`。本地保存不会向上游认证；首次实际提取才会验证订单与签名是否有效。

## 使用示例

- “查看 JuliangIP 本地设置和代理池状态。”——只读本地配置、缓存，不请求提取接口。
- “从 JuliangIP 提取 3 个代理，只显示脱敏信息。”——缓存可用时优先复用；需要新提取时可能消耗套餐额度。
- “选择一个健康代理用于本次授权测试。”——复用当前绑定，达到使用次数限制后选择其他出口。
- “把刚才的代理标记为硬失败，再换一个健康代理。”——进入冷却的代理不会继续被选中。

| 工具 | 用途 |
| --- | --- |
| `juliangip_settings_read` / `juliangip_settings_update` | 读取或保存设置，签名掩码显示 |
| `juliangip_setup_local` | 启动一次性本地配置页 |
| `juliangip_fetch_proxies` | 提取并缓存代理，`force=true` 请求刷新 |
| `juliangip_get_proxy` | 选择健康出口，支持 `rotate` 和 `force_refresh` |
| `juliangip_mark_proxy` | 记录成功、失败及硬失败冷却 |
| `juliangip_pool_status` | 查看缓存、健康、过期和冷却数量 |
| `juliangip_redact_proxy` | 移除代理 URL 中的用户名和密码 |

插件固定使用 `auth_type=2`、`pt=1`，正确解析 `ip:port,剩余秒:user:pass` 等文本格式。默认缓存刷新周期 150 秒、单次绑定最多选择 3 次、累计失败阈值 2 次、冷却 600 秒。剩余有效期随时间递减，过期或冷却中的出口不会被选择。没有可选出口时返回错误，需显式刷新或等待冷却。

只有同时传入 `reveal_credentials=true` 和 `confirm_reveal=true` 才返回代理用户名、密码和完整 URL；默认输出仅含脱敏元数据。用于测试程序时应直接传递这些凭据，避免在聊天或日志中展示。缓存包含代理认证信息，也使用 `0600` 权限。

当前实现为每个本地配置目录维护一个代理绑定；不管理浏览器、Cookie 或多个独立浏览器身份，也不修改系统网络设置。状态文件没有跨进程锁，不适合多个进程同时操作同一目录；需要隔离时分别设置 `JULIANGIP_CONFIG_FILE` 和 `JULIANGIP_PROFILE_DIR`。

## 其他 MCP 客户端

克隆后安装依赖，或通过 uv 启动：

```sh
git clone https://github.com/guangfuhao/juliangip-mcp.git
cd juliangip-mcp
uv sync
uv run juliangip-mcp
```

该命令运行 stdio MCP 服务，适用于支持 MCP 的 Agent。客户端的启动命令也可设为 `uv`，参数为 `run --directory /absolute/path/to/juliangip-mcp juliangip-mcp`。单独打开本地设置页：`uv run juliangip-setup-local`。

## 开发与验证

```sh
uv sync --extra dev
uv run pytest -q
uv build
```

测试使用虚拟凭据和模拟提取响应，不调用真实套餐。GitHub Actions 检查 Python 3.10/3.12 的测试和构建。Release 提供源码压缩包与 Python wheel；Codex 用户使用仓库 marketplace 安装完整插件。

[MIT License](LICENSE)。欢迎通过 [Issues](https://github.com/guangfuhao/juliangip-mcp/issues) 反馈，提交问题时请隐藏签名、订单号和代理密码。
