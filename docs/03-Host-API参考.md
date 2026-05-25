# 03 — Host API 参考

`bootstrap(hostApi)` 的 `hostApi` 是插件访问宿主的唯一正式入口。本页列出当前 v2 可用 API。

多数异步 Host API 成功时直接返回结果对象，失败时返回：

```javascript
{
  ok: false,
  error: {
    code: "permission_denied",
    message: "Permission denied for host API.",
    details: {}
  }
}
```

插件应显式判断 `result && result.ok === false`。

## 注册方法

| 方法 | 说明 | 权限 |
|------|------|------|
| `registerMessageHandler(descriptor)` | 注册消息处理器 | 无 |
| `registerCommandHandler(descriptor)` | 注册斜杠命令 | 无 |
| `registerRegexHandler(descriptor)` | 注册正则处理器 | 无 |
| `registerLlmHook(descriptor)` | 注册 LLM 流水线钩子 | 无 |
| `registerLifecycleHandler(descriptor)` | 注册生命周期钩子 | 无 |
| `registerTool(descriptor, handler?)` | 注册 LLM 工具 | 无 |
| `registerToolLifecycleHook(descriptor)` | 注册工具生命周期钩子 | 无 |
| `registerScheduledHandler(descriptor)` | 注册插件定时回调 | `schedule_manage` |
| `registerAgent(descriptor)` | 注册 Agent 能力 | `agent_run` |

生命周期快捷方法：

| 方法 | 等价于 |
|------|--------|
| `onPluginLoaded(descriptor)` | `registerLifecycleHandler({ hook: "on_plugin_loaded", ...descriptor })` |
| `onPluginUnloaded(descriptor)` | `registerLifecycleHandler({ hook: "on_plugin_unloaded", ...descriptor })` |
| `onPluginError(descriptor)` | `registerLifecycleHandler({ hook: "on_plugin_error", ...descriptor })` |

## 工具方法

### `log(level, message, metadata?)`

```javascript
hostApi.log("INFO", "普通信息");
hostApi.log("WARN", "警告");
hostApi.log("ERROR", "出错了", { detail: "..." });
```

`level` 可选：`"VERBOSE"` / `"DEBUG"` / `"INFO"` / `"WARN"` / `"ERROR"`。

### `getPluginMetadata()`

```javascript
const meta = hostApi.getPluginMetadata();
// {
//   pluginId,
//   installedVersion,
//   runtimeKind,
//   runtimeApiVersion,
//   runtimeBootstrap
// }
```

### `getSettings()` / `readSettings()` / `getPluginSettings()` / `getConfig()`

四个方法等价，读取宿主合并后的插件配置。

```javascript
const settings = hostApi.getSettings() || {};
const prefix = settings.greeting_prefix ?? "你好";
```

首次运行或用户未保存配置时可能返回 `{}`，务必提供默认值。

## 持久状态

`hostApi.storage.plugin` 是插件级持久状态，`hostApi.storage.session` 是当前会话级状态。

```javascript
await hostApi.storage.plugin.set("counter", 1);
const counter = hostApi.storage.plugin.get("counter", 0);
const keys = hostApi.storage.plugin.keys();
hostApi.storage.plugin.remove("counter");
hostApi.storage.plugin.clear("prefix:");
```

每个 scope 都支持：

| 方法 | 说明 |
|------|------|
| `get(key, defaultValue?)` | 读取值，缺失时返回默认值 |
| `set(key, value)` | 写入 JSON 可序列化值 |
| `remove(key)` | 删除单个 key |
| `keys(prefix?)` | 列出 key |
| `clear(prefix?)` | 清空 scope 或指定前缀 |

注意：

- key 会 trim，不能为空，长度不超过 128。
- value 必须可 JSON 序列化。
- `storage.session` 需要当前消息会话上下文；启动阶段无会话时不可用。

## 网络请求

### `hostApi.fetch(request)` / `hostApi.network.request(request)`

两个入口等价，网络请求必须走宿主代理。

权限：`network_request`。

```javascript
const response = await hostApi.fetch({
  url: "https://api.example.com/ping",
  method: "POST",
  headers: {
    "content-type": "application/json"
  },
  bodyText: JSON.stringify({ q: "hello" }),
  timeoutMs: 10000
});

if (response.ok === false) {
  hostApi.log("WARN", "network failed", { code: response.error.code });
} else {
  const data = JSON.parse(response.bodyText || "{}");
}
```

请求字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 必需，只支持 `http` / `https` |
| `method` | string | `GET` / `POST` / `PUT` / `PATCH` / `DELETE` / `HEAD`，默认 `GET` |
| `headers` | object | 字符串键值 |
| `bodyText` | string | 文本请求体 |
| `bodyBase64` | string | Base64 请求体，与 `bodyText` 互斥 |
| `timeoutMs` | number | 默认 10000，上限 15000 |

返回字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | number | HTTP 状态码 |
| `headers` | object | 响应头 |
| `bodyText` | string | UTF-8 文本体 |
| `bodyBase64` | string | Base64 响应体 |
| `contentType` | string | 响应 Content-Type |
| `elapsedMs` | number | 耗时 |

限制：

- 需要 `android-plugin.json` 的 `network.allowedDomains` 命中目标 host。
- 不允许本地、私有网段和内网域名。
- 响应体上限为 1 MB。
- 每插件最多 4 个并发网络请求。

## Provider 查询

### `hostApi.providers.list()`

权限：`provider_read`。

```javascript
const providers = await hostApi.providers.list();
```

返回 Provider 摘要数组：

```javascript
{
  providerId: "provider-main",
  displayName: "Main Provider",
  enabled: true,
  capabilities: ["chat"],
  defaultModelId: "model-main",
  modelCount: 1
}
```

### `hostApi.providers.models({ providerId })`

权限：`provider_read`。

```javascript
const models = await hostApi.providers.models({ providerId: "provider-main" });
```

返回模型摘要数组：

```javascript
{
  modelId: "model-main",
  displayName: "Main Model",
  capabilities: ["chat"],
  contextWindow: 8192,
  supportsToolCalling: true,
  supportsStreaming: true
}
```

## 当前会话消息

### `hostApi.message.send(request)`

权限：

- 普通 `text` / `attachments`：`send_message`。
- 使用 `chain` 富消息链：`rich_message_send`。

```javascript
const receipt = await hostApi.message.send({
  text: "来自插件的消息",
  markdown: false
});
```

返回：

```javascript
{
  conversationId: "conversation-current",
  platformAdapterType: "app_chat",
  receiptIds: ["receipt-1"],
  messageLength: 6,
  warnings: []
}
```

约束：

- 只能发送到当前会话。
- `conversationId` 可省略；如传入，必须与当前事件会话一致。
- `text` 和 `attachments` 不能同时为空。

### 富消息链

```javascript
await hostApi.message.send({
  chain: [
    { type: "text", text: "看图：" },
    { type: "image", uri: "plugin://package/assets/welcome.png", alt: "欢迎图", mimeType: "image/png" },
    { type: "mention", userId: "123456", label: "用户" },
    { type: "reply", messageId: "message-1" },
    { type: "card", title: "标题", text: "摘要", url: "https://example.com" }
  ]
});
```

支持 segment：

| type | 字段 |
|------|------|
| `text` | `text` |
| `image` | `uri`、`alt?`、`mimeType?` |
| `file` | `uri`、`name?`、`mimeType?` |
| `mention` | `userId`、`label?` |
| `reply` | `messageId` |
| `card` | `title`、`text?`、`url?` |

媒体 `uri` 只允许 `plugin://package/...`、`plugin://workspace/...`、宿主 file provider `content://com.elymbot.android.fileprovider/...` 或 `https://...`。

## 流式输出

### `hostApi.message.openStream({ markdown? })`

权限：`message_stream`。

```javascript
const stream = await hostApi.message.openStream({ markdown: true });

if (stream.ok === false) {
  return event.replyText(`无法打开流：${stream.error.code}`);
}

await stream.append("第一段");
await stream.append("\n第二段");
await stream.replace("完整替换文本");
await stream.close();
```

返回 stream 对象：

| 字段 / 方法 | 说明 |
|------|------|
| `streamId` | 流 ID |
| `platformMode` | `Editable` / `Chunked` / `FinalOnClose` |
| `receiptId` | 平台回执，可能为空 |
| `append(text)` | 追加文本 |
| `replace(text)` | 替换当前流文本 |
| `close()` | 关闭并完成 |
| `fail(message)` | 失败结束 |

限制：最长 120 秒、最多 128 个 chunk、累计文本最多 64 KB。应用内聊天优先走可编辑消息；QQ 等平台可能退化为 close 时发送最终文本。

## 当前会话历史

### `hostApi.conversation.history(request?)`

权限：`conversation_read`。

```javascript
const history = await hostApi.conversation.history({
  limit: 20,
  includeAttachments: false
});
```

请求字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `limit` | number | 默认 20，上限 100 |
| `beforeMessageId` | string | 从指定消息之前继续分页 |
| `includeAttachments` | boolean | 是否返回附件引用 |
| `conversationId` | string | 可省略；如传入必须等于当前会话 |

QQ 群场景说明：

- `conversation.history` 读取的是宿主沉淀的当前群公共消息历史，不是 bot LLM 对话上下文。
- 群聊隔离只影响 bot 对话上下文；群分析、统计等插件仍读取 `group:<群号>` 的公共群历史。
- 公共群历史只包含宿主 QQ runtime 已接收并写入的消息；历史写入生效前、宿主未接收、未绑定到启用 bot 的消息不会补齐。
- 当前历史消息的 `senderId` 受宿主会话模型限制，真实发言人主要体现在 `text` 前缀中。

返回：

```javascript
{
  conversationId: "conversation-current",
  messages: [
    {
      messageId: "message-latest",
      role: "user",
      senderId: "user-1",
      messageType: "FriendMessage",
      text: "hello",
      timestampEpochMillis: 1710000000000,
      attachmentRefs: []
    }
  ]
}
```

## LLM 调用

### `hostApi.callLlm(request)` / `hostApi.llm.generate(request)`

两个入口都调用宿主模型。权限：`call_model`。

```javascript
const result = await hostApi.callLlm({
  providerId: "provider-main",
  modelId: "model-main",
  systemPrompt: "你是一个简洁助手。",
  messages: [
    { role: "user", text: "总结这句话" }
  ],
  temperature: 0.2,
  topP: 0.9,
  maxTokens: 256,
  tools: [
    {
      name: "lookup",
      description: "查询信息",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string" }
        }
      }
    }
  ]
});
```

请求限制：

- `providerId` 和 `modelId` 必须存在且可用。
- `messages` 至少一条，role 只支持 `system` / `user` / `assistant`。
- `temperature` 范围 `0..2`。
- `topP` 范围 `0..1`。
- `maxTokens` 范围 `1..32768`。

返回：

```javascript
{
  text: "模型回复",
  finishReason: "stop",
  providerId: "provider-main",
  modelId: "model-main",
  usage: {
    promptTokens: 10,
    completionTokens: 20,
    totalTokens: 30,
    inputCostMicros: 0,
    outputCostMicros: 0,
    currencyCode: ""
  },
  toolCalls: []
}
```

该调用默认绕过插件 LLM hooks，不会触发本插件或其他插件注册的 LLM pipeline hook。

## 上下文压缩

### `hostApi.context.compress(request)`

权限：`context_compress`。

```javascript
const compressed = await hostApi.context.compress({
  providerId: "provider-main",
  modelId: "model-main",
  maxTokens: 512,
  limit: 50,
  targetLanguage: "zh-CN",
  outputLength: "short"
});
```

请求字段：

| 字段 | 说明 |
|------|------|
| `conversationId` | 可省略；如传入必须等于当前会话 |
| `providerId` / `modelId` | 必需 |
| `maxTokens` | 默认 1200，宿主裁剪到 `64..8192` |
| `limit` | 默认 50，范围 `1..100` |
| `targetLanguage` | 可选输出语言 |
| `outputLength` | 可选长度提示 |

返回：

```javascript
{
  summary: "压缩后的上下文",
  sourceMessageCount: 12,
  truncated: false,
  usage: {}
}
```

上下文压缩使用宿主 LLM 服务，同样绕过插件 LLM hooks。

## 定时回调

### `hostApi.registerScheduledHandler(descriptor)`

详见 [04-处理器与钩子](04-处理器与钩子.md#定时回调)。

权限：`schedule_manage`。

## Agent

### `hostApi.registerAgent(descriptor)`

注册当前插件拥有的 Agent。

权限：`agent_run`。

```javascript
hostApi.registerAgent({
  key: "research-agent",
  systemPrompt: "你是一个研究助手。",
  model: { providerId: "provider-main", modelId: "model-main" },
  tools: ["lookup"],
  handler: async ({ input, agent }) => {
    return await agent.run(input);
  }
});
```

### `hostApi.agent.run(request)`

调用已注册 Agent。

权限：`agent_run`。

```javascript
const result = await hostApi.agent.run({
  key: "research-agent",
  input: "帮我查一下上下文",
  maxToolCalls: 8,
  maxDepth: 8,
  timeoutMs: 30000,
  maxTokens: 32768,
  maxCostMicros: 5000000
});
```

返回：

```javascript
{
  succeeded: true,
  text: "Agent 输出",
  providerId: "provider-main",
  modelId: "model-main",
  usage: {},
  toolCallCount: 1,
  durationMs: 1234,
  failureCode: ""
}
```

Agent 内部 LLM / tool loop 由宿主控制，默认绕过插件 LLM hooks。插件工具名称不能伪装成 `mcp.`、`skill.`、`web.`、`active.`、`ctx.`、`context.` 等宿主保留来源。
