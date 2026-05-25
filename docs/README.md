# ElymBot 插件 v2 开发文档

适用于 `protocolVersion: 2`、运行时 `js_quickjs`、Host API `apiVersion: 1`、宿主版本 `0.4.0+`。

本指南面向 ElymBot Android Native 外部插件开发者。插件运行在 QuickJS 沙箱中，入口为 `export default async function bootstrap(hostApi)`，所有宿主交互都必须通过 `hostApi` 或事件对象完成。

## 当前边界

- 不支持 Node.js API：不要使用 `fs`、`path`、`require`、`process`、`Buffer`。
- 不允许插件直连宿主数据库；只能通过文档列出的 Host API 读取或写入受控数据。
- 网络能力必须走 `hostApi.fetch` / `hostApi.network.request`，并受权限、域名白名单和宿主网络策略限制。
- `hostApi.callLlm` / `hostApi.llm.generate` 与 Agent 内部 LLM 调用默认绕过插件 LLM hooks，避免递归触发。
- 当前不提供 Web API 注册、平台适配器注册、文本转图、HTML 渲染能力。
- 文档只使用 ElymBot v2 正式 API 名称，不提供旧框架风格别名。

## 文档索引

| 文件 | 内容 |
|------|------|
| [01-快速开始.md](01-快速开始.md) | 从零到可运行插件的最短路径 |
| [02-包结构与描述文件.md](02-包结构与描述文件.md) | 目录布局、`manifest.json`、`android-plugin.json`、权限和网络声明 |
| [03-Host-API参考.md](03-Host-API参考.md) | `hostApi` 上可用方法、返回结构和示例 |
| [04-处理器与钩子.md](04-处理器与钩子.md) | 消息 / 命令 / 正则 / LLM / 生命周期 / 定时 / Agent / 过滤器 |
| [05-配置与设置.md](05-配置与设置.md) | `_conf_schema.json`、`settings-schema.json` 与持久状态区别 |
| [06-资源与附件.md](06-资源与附件.md) | 静态资源、附件、富消息链和媒体 URI 规则 |
| [07-权限与安全边界.md](07-权限与安全边界.md) | Host API 权限表、安全限制和不支持能力 |
| [AGENT-PLUGIN-DEV-GUIDE.md](AGENT-PLUGIN-DEV-GUIDE.md) | 给 AI 编码代理使用的完整开发约束 |

## 最小环境

1. ElymBot 宿主应用，用于导入、启用、运行和调试插件。
2. 一个可用的文本编辑器。
3. 一个 ZIP 压缩工具。
4. Git / GitHub 环境。

## 推荐给编码代理的启动提示

```text
请先阅读 AGENT-PLUGIN-DEV-GUIDE.md，并严格按照其中的约束开发 ElymBot protocolVersion 2 插件。

要求：
1. 入口必须是 runtime/bootstrap.js 中的 export default async function bootstrap(hostApi)。
2. 只能使用文档列出的 hostApi 和事件对象能力，不允许修改宿主代码。
3. 如需网络、模型、消息、上下文、定时、流式输出、Agent 等能力，先在 manifest.json 声明对应权限。
4. 网络请求必须走 hostApi.fetch 或 hostApi.network.request，并在 android-plugin.json 的 network.allowedDomains 声明裸域名。
5. 如果宿主当前不支持某项核心能力，先说明限制，再给出可行降级方案。
6. 输出结果必须是可导入、可运行、可分发的 Android Native 外部插件目录。
```

## 模板插件

`helloworld` 模板是一个最小可导入、可执行、可配置的模板插件：

- Git 仓库：https://github.com/undertaker33/helloworld.git

模板覆盖命令处理、正则匹配、LLM 钩子、生命周期、配置读取等基础能力。开发需要 Host API 扩展能力时，请按本目录文档补充权限、网络白名单和对应调用代码。
