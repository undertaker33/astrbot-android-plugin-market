# ElymBot Plugin v2 — Agent Development Guide

Audience: AI coding agents that need to create an ElymBot Android Native external plugin without reading host app source code.

Target contract:

- `protocolVersion: 2`
- `runtime.kind: "js_quickjs"`
- `runtime.apiVersion: 1`
- bootstrap entry: `runtime/bootstrap.js`
- host version: `0.4.0+`

## 1. Non-Negotiable Runtime Rules

Plugins run in a QuickJS ES module sandbox.

Do:

- Export `default async function bootstrap(hostApi)`.
- Register all handlers, hooks, tools, schedules, and agents during `bootstrap`.
- Use only documented `hostApi` methods and event objects.
- Keep imports inside the `runtime/` tree.
- Package a complete plugin directory with `manifest.json`, `android-plugin.json`, and `runtime/bootstrap.js`.

Do not:

- Use Node.js APIs: `fs`, `path`, `require`, `process`, `Buffer`, npm packages.
- Modify host application code.
- Use old API names such as `activate(hostApi)`, `registerCommand(...)`, `onDecoratingResult(...)`, or `afterMessageSent(...)`.
- Directly access host databases, Android services, platform adapters, or local sockets.
- Invent aliases from other bot frameworks.

## 2. Required File Structure

```text
my-plugin/
├── manifest.json
├── android-plugin.json
├── _conf_schema.json
├── runtime/
│   ├── bootstrap.js
│   └── utils.js
├── schemas/
│   └── settings-schema.json
└── assets/
```

Only these are mandatory:

- `manifest.json`
- `android-plugin.json`
- `runtime/bootstrap.js`

## 3. manifest.json

```json
{
  "pluginId": "com.example.myplugin",
  "version": "1.0.0",
  "protocolVersion": 2,
  "author": "Your Name",
  "title": "My Plugin",
  "description": "Short description",
  "permissions": [],
  "minHostVersion": "0.4.0",
  "maxHostVersion": "",
  "sourceType": "LOCAL_FILE",
  "entrySummary": "What this plugin does",
  "riskLevel": "LOW"
}
```

`permissions` must exist. Leave it empty only when the plugin uses basic handler registration, logging, settings, and event replies. Add permission objects for controlled Host API access:

```json
{
  "permissionId": "network_request",
  "title": "Network requests",
  "description": "Allows the plugin to access allowed domains through host-proxied network requests.",
  "riskLevel": "MEDIUM",
  "required": true
}
```

Known permission IDs:

| permissionId | Enables |
|--------------|---------|
| `network_request` | `hostApi.fetch`, `hostApi.network.request` |
| `provider_read` | `hostApi.providers.list`, `hostApi.providers.models` |
| `send_message` | `hostApi.message.send` for plain text / attachments |
| `rich_message_send` | `hostApi.message.send({ chain })` |
| `conversation_read` | `hostApi.conversation.history` |
| `call_model` | `hostApi.callLlm`, `hostApi.llm.generate` |
| `context_compress` | `hostApi.context.compress` |
| `schedule_manage` | `hostApi.registerScheduledHandler` |
| `message_stream` | `hostApi.message.openStream` and stream operations |
| `agent_run` | `hostApi.registerAgent`, `hostApi.agent.run` |

## 4. android-plugin.json

```json
{
  "protocolVersion": 2,
  "runtime": {
    "kind": "js_quickjs",
    "bootstrap": "runtime/bootstrap.js",
    "apiVersion": 1
  },
  "config": {
    "staticSchema": "_conf_schema.json",
    "settingsSchema": "schemas/settings-schema.json"
  },
  "network": {
    "allowedDomains": ["api.example.com"]
  }
}
```

Rules:

- `runtime.bootstrap` must be a relative path under `runtime/`.
- Use forward slashes.
- `network.allowedDomains` must contain bare domains only, no scheme, path, or port.
- Network access also requires the `network_request` permission.

## 5. Bootstrap Template

```javascript
export default async function bootstrap(hostApi) {
  hostApi.log("INFO", "[my-plugin] loaded");

  hostApi.registerCommandHandler({
    key: "my-plugin.ping",
    command: "ping",
    aliases: [],
    groupPath: [],
    priority: 0,
    metadata: {},
    handler(event) {
      event.replyText("pong");
    },
  });
}
```

Use ES modules only:

```javascript
import { helper } from "./utils.js";
```

Never use `require`.

## 6. hostApi Reference

### Registration

| Method | Purpose |
|--------|---------|
| `registerMessageHandler(descriptor)` | Message handler before command matching |
| `registerCommandHandler(descriptor)` | Slash command |
| `registerRegexHandler(descriptor)` | Regex matcher |
| `registerLlmHook(descriptor)` | LLM pipeline hook |
| `registerLifecycleHandler(descriptor)` | Lifecycle hook |
| `registerTool(descriptor, handler?)` | LLM tool |
| `registerToolLifecycleHook(descriptor)` | Tool lifecycle hook |
| `registerScheduledHandler(descriptor)` | Scheduled callback |
| `registerAgent(descriptor)` | Agent capability |

Lifecycle shortcuts:

- `onPluginLoaded(descriptor)`
- `onPluginUnloaded(descriptor)`
- `onPluginError(descriptor)`

### Utilities

```javascript
hostApi.log("INFO", "message", { key: "value" });
const meta = hostApi.getPluginMetadata();
const settings = hostApi.getSettings() || {};
```

Settings aliases:

- `readSettings()`
- `getPluginSettings()`
- `getConfig()`

### Storage

```javascript
hostApi.storage.plugin.set("counter", 1);
const counter = hostApi.storage.plugin.get("counter", 0);
const keys = hostApi.storage.plugin.keys();
hostApi.storage.plugin.remove("counter");
hostApi.storage.plugin.clear("prefix:");
```

`hostApi.storage.session` has the same methods, but requires a current conversation context.

## 7. Controlled Host APIs

Most controlled Host APIs return a plain value on success and this shape on failure:

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

Always check `result && result.ok === false`.

### Network

```javascript
const response = await hostApi.fetch({
  url: "https://api.example.com/ping",
  method: "POST",
  headers: { "content-type": "application/json" },
  bodyText: JSON.stringify({ q: "hello" }),
  timeoutMs: 10000
});
```

Equivalent:

```javascript
await hostApi.network.request({ url: "https://api.example.com/ping" });
```

Limits:

- `http` / `https` only.
- Domain must match `android-plugin.json.network.allowedDomains`.
- Localhost, private IPs, `.local`, `.internal`, and `.lan` are blocked.
- Response body limit is 1 MB.
- Timeout is capped at 15000 ms.

### Providers

```javascript
const providers = await hostApi.providers.list();
const models = await hostApi.providers.models({ providerId: providers[0].providerId });
```

### Message Send

```javascript
const receipt = await hostApi.message.send({
  text: "Hello from plugin",
  markdown: false
});
```

The target is always the current conversation. If `conversationId` is provided, it must match the current event conversation.

Rich message chain:

```javascript
await hostApi.message.send({
  chain: [
    { type: "text", text: "Image:" },
    { type: "image", uri: "plugin://package/assets/welcome.png", mimeType: "image/png" },
    { type: "mention", userId: "123456", label: "user" },
    { type: "reply", messageId: "message-1" },
    { type: "card", title: "Title", text: "Summary", url: "https://example.com" }
  ]
});
```

Media URIs for `message.send` must be one of:

- `plugin://package/...`
- `plugin://workspace/...`
- `content://com.elymbot.android.fileprovider/...`
- `https://...`

### Message Stream

```javascript
const stream = await hostApi.message.openStream({ markdown: true });

if (stream.ok === false) {
  return event.replyText(`stream failed: ${stream.error.code}`);
}

await stream.append("first chunk");
await stream.replace("replacement text");
await stream.close();
```

Limits: 120 seconds, 128 chunks, 64 KB text.

### Conversation History

```javascript
const history = await hostApi.conversation.history({
  limit: 20,
  includeAttachments: false
});
```

The target is the current conversation only. `limit` is capped at 100.

For QQ group conversations, history reads the host-maintained public group
message history, not the bot LLM conversation context. Group-user session
isolation only affects bot context; group analysis and statistics plugins read
the public `group:<groupId>` history. The result only covers messages already
received and deposited by the host QQ runtime. Current history records may not
carry a separate real sender id; group sender information is primarily encoded
in the returned `text` prefix.

### Direct LLM

```javascript
const result = await hostApi.callLlm({
  providerId: "provider-main",
  modelId: "model-main",
  systemPrompt: "Be concise.",
  messages: [
    { role: "user", text: "Summarize this" }
  ],
  temperature: 0.2,
  topP: 0.9,
  maxTokens: 256
});
```

Equivalent model endpoint:

```javascript
await hostApi.llm.generate({ providerId, modelId, messages });
```

Direct LLM calls bypass plugin LLM hooks by default. Do not expect these calls to trigger `registerLlmHook`.

Allowed message roles for direct LLM calls: `system`, `user`, `assistant`.

### Context Compression

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

This reads current conversation history and uses host LLM compression. It also bypasses plugin LLM hooks.

## 8. Handler and Hook Patterns

### Command

```javascript
hostApi.registerCommandHandler({
  key: "my-plugin.echo",
  command: "echo",
  handler(event) {
    event.replyText(event.remainingText || "");
  },
});
```

Command event helpers:

- `event.replyText(text)`
- `event.replyResult(payload)`
- `event.stopPropagation()`

### Message

```javascript
hostApi.registerMessageHandler({
  key: "my-plugin.observe",
  handler(event) {
    hostApi.log("INFO", `message: ${event.rawText}`);
  },
});
```

### Regex

```javascript
hostApi.registerRegexHandler({
  key: "my-plugin.regex",
  pattern: "^echo\\s+(.+)",
  flags: ["i"],
  handler(event) {
    hostApi.log("INFO", `regex matched: ${event.groups[0] || ""}`);
    event.stopPropagation();
  },
});
```

### Filters

Use `filters` for composition:

```javascript
filters: {
  allOf: [
    { eventMessageType: "group" },
    {
      anyOf: [
        { platformAdapterType: "onebot" },
        { platformAdapterType: "qq" }
      ]
    },
    { not: { permissionType: "blocked" } }
  ]
}
```

Compatible legacy filters:

```javascript
declaredFilters: [
  "event_message_type:group",
  "platform_adapter_type:onebot",
  "permission_type:send_message",
  "custom_filter:my_filter"
]
```

Never put both `declaredFilters` and `filters` on the same registration.

### LLM Hooks

```javascript
hostApi.registerLlmHook({
  hook: "on_decorating_result",
  key: "my-plugin.decorate",
  priority: 100,
  handler({ result }) {
    result.appendText("\n-- plugin footer");
  },
});
```

Supported hooks:

- `on_waiting_llm_request`
- `on_llm_request`
- `on_llm_response`
- `on_decorating_result`
- `after_message_sent`

Use `registerLlmHook`. Do not use `onDecoratingResult` or `afterMessageSent` shortcut APIs; they are not part of the v2 public surface.

### Scheduled Handler

```javascript
hostApi.registerScheduledHandler({
  key: "daily-summary",
  cron: "0 9 * * *",
  handler: async (event) => {
    await hostApi.message.send({ text: "Daily summary" });
  }
});
```

or:

```javascript
hostApi.registerScheduledHandler({
  key: "run-once",
  runAt: Date.now() + 60000,
  handler: async () => {}
});
```

`cron` and `runAt` are mutually exclusive.

If the scheduled callback sends messages, opens streams, or reads history, also declare the corresponding permissions such as `send_message`, `message_stream`, or `conversation_read`.

### Tool

```javascript
hostApi.registerTool({
  name: "lookup",
  description: "Lookup data",
  inputSchema: {
    type: "object",
    properties: { query: { type: "string" } },
    required: ["query"]
  },
  handler: async (args) => {
    return { status: "success", text: `hit:${args.payload.query}` };
  }
});
```

Avoid reserved prefixes for plugin tool names:

- `mcp.`
- `skill.`
- `web.`
- `active.`
- `ctx.`
- `context.`

### Agent

```javascript
hostApi.registerAgent({
  key: "research-agent",
  systemPrompt: "Use tools when useful.",
  tools: ["lookup"],
  model: {
    providerId: "provider-main",
    modelId: "model-main"
  },
  handler: async ({ input, agent }) => {
    return await agent.run(input);
  }
});
```

Invoke it:

```javascript
const result = await hostApi.agent.run({
  key: "research-agent",
  input: "question",
  maxToolCalls: 8,
  maxDepth: 8,
  timeoutMs: 30000,
  maxTokens: 32768,
  maxCostMicros: 5000000
});
```

Agent LLM/tool loops are host-controlled and bypass plugin LLM hooks.

## 9. Configuration

`_conf_schema.json` defines data:

```json
{
  "greeting_prefix": {
    "type": "string",
    "description": "Greeting prefix",
    "hint": "Text before the name",
    "default": "Hello",
    "section": "general"
  }
}
```

Read it:

```javascript
const settings = hostApi.getSettings() || {};
const prefix = settings.greeting_prefix ?? "Hello";
```

`schemas/settings-schema.json` defines UI:

```json
{
  "title": "Settings",
  "sections": [
    {
      "sectionId": "general",
      "title": "General",
      "fields": [
        {
          "fieldType": "text_input",
          "fieldId": "greeting_prefix",
          "label": "Greeting prefix",
          "defaultValue": "Hello"
        }
      ]
    }
  ]
}
```

Supported field types:

- `toggle`
- `text_input`
- `select`

## 10. Attachments and Assets

For command replies, relative paths are allowed:

```javascript
event.replyResult({
  text: "Image:",
  attachments: [
    { source: "assets/welcome.png", mimeType: "image/png", label: "welcome" }
  ]
});
```

For `hostApi.message.send`, use safe `uri` values:

```javascript
await hostApi.message.send({
  text: "Image:",
  attachments: [
    { uri: "plugin://package/assets/welcome.png", mimeType: "image/png" }
  ]
});
```

## 11. Unsupported Capabilities

Do not implement or document these as available:

- Web API registration.
- Platform adapter registration.
- Direct database access.
- Text-to-image Host API.
- HTML rendering Host API.
- Arbitrary filesystem access.
- Node.js/npm runtime.
- Old framework-style public aliases.

If a requested plugin feature needs one of these, state the limitation and propose a fallback using current ElymBot APIs.

## 12. Delivery Checklist

Before delivery, verify:

```text
[ ] manifest.json exists at plugin root.
[ ] android-plugin.json exists at plugin root.
[ ] protocolVersion is 2 in both files.
[ ] runtime.kind is "js_quickjs".
[ ] runtime.bootstrap points under runtime/.
[ ] runtime/bootstrap.js exports default async function bootstrap(hostApi).
[ ] No Node.js APIs, CommonJS, npm imports, or host source imports are used.
[ ] All controlled Host APIs have matching manifest permissions.
[ ] Network calls declare network_request and android-plugin.json network.allowedDomains.
[ ] Direct LLM / context compression / Agent assumptions mention hook bypass if relevant.
[ ] Message sends target only the current conversation.
[ ] Rich message media URIs use allowed schemes.
[ ] ZIP root contains manifest.json directly, not an extra parent folder.
```

## 13. Minimal Complete Example

```javascript
export default async function bootstrap(hostApi) {
  hostApi.log("INFO", "example loaded");

  hostApi.registerCommandHandler({
    key: "example.ping",
    command: "ping",
    handler(event) {
      event.replyText("pong");
    },
  });

  hostApi.registerLlmHook({
    hook: "on_decorating_result",
    key: "example.footer",
    priority: 100,
    handler({ result }) {
      result.appendText("\n-- from example plugin");
    },
  });
}
```
