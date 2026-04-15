# ElymBot 插件上架说明

  该文档负责说明如何上架和安装插件

  当前宿主支持三种插件安装方式：

  - 本地zip
  - 直链包
  - 仓库安装

  ## 1. ZIP打包

  zip 根目录必须直接包含 `manifest.json` 和 `android-plugin.json`。

  正确结构：

  ```text
  plugin.zip
    manifest.json
    android-plugin.json
    _conf_schema.json
    runtime/bootstrap.js
    runtime/...
    config/...
    schemas/...
    assets/...
    memes/...
  ```

  建议不要把这些内容打进发布 zip：

  ```text
  .git/
  build/
  dist/
  node_modules/
  tests/
  *.log
  ```

  **<u>容易出错的点:</u>**

  1. 错误结构是把整层目录一起打进 zip：

     ```text
     plugin.zip
       your-plugin/
         manifest.json
         android-plugin.json
         runtime/bootstrap.js
     ```

     这会导致宿主在压缩包根目录找不到 `manifest.json`。

  2. zip 内部路径必须使用 `/`，不要依赖 Windows 风格 `\`

  

  ## 2.如果要走市场分发

  1. 维护独立插件仓库
  2. 生成插件 zip
  3. 把 zip 上传到 GitHub Release
  4. 克隆或fork中央仓库，在仓库`/plugins`目录下新增/更新一个JSON文件
  5. pr回中央仓库等待审核
  6. 审核通过后，安卓客户端从中央 Raw 市场源拉取条目

  JSON文件格式如下：

  ```json
  {
    "pluginId": "io.github.example.my_plugin",
    "title": "My Plugin",
    "author": "your-name",
    "description": "Android Native v2 plugin description.",
    "entrySummary": "Short summary shown in the Android market.",
    "repoUrl": "https://github.com/<owner>/<plugin-repo>",
    "scenarios": [
      "Scenario one",
      "Scenario two"
    ],
    "versions": [
      {
        "version": "0.1.0",
        "packageUrl": "https://github.com/<owner>/<plugin-repo>/releases/download/v0.1.0/my-plugin-v0.1.0.zip",
        "protocolVersion": 2,
        "minHostVersion": "0.3.0",
        "maxHostVersion": "",
        "permissions": [],
        "changelog": "Initial Android Native plugin market release."
      }
    ]
  }
  ```

  - `pluginId`：插件的唯一身份标识,必须和插件 `manifest.json` 一致。
  - `title`：插件显示名称。
  - `author`：插件作者名称。
  - `description`：插件的完整说明。
  - `entrySummary`：插件入口摘要，一句话描述插件能干什么。
  - `repoUrl`：插件独立仓库首页地址。
  - `scenarios`：插件适用场景列表。
  - `version`：版本列表，推荐把最新版本放在最前面。
  - `packageUrl`：这个版本对应的插件 zip 下载地址，在GitHub Release页面右键压缩包获取，必须是可直接下载 zip 的 URL。
  - `protocolVersion`：插件协议版本，当前只能填2。
  - `minHostVersion`：这个插件版本要求的最低宿主版本，建议填你当前使用的版本
  - `maxHostVersion`：这个插件版本允许的最高宿主版本，空字符串表示当前没有设置上限。
  - `permissions`：这个插件版本声明的权限列表，如果没有额外权限要求，可以为空数组。
  - `changelog`：这个版本的变更说明。

  你可能会在主仓库中看到类似 `"publishedAt": 1775459798000` 的字段,但这里给出的JSON中没有，这是正常的，该字段合并pr时由系统自动填写。

  

  ### 提交上架流程

  插件作者没有中央仓库直接推送权限时，按这个流程做：

  1. 完成插件仓库开发、测试、打包、Release。
  2. 复制 GitHub Release zip 下载链接。
  3. fork 或 clone 中央市场仓库。
  4. 新建或更新 `plugins/<pluginId>.json`。
  5. 提交 PR 到中央市场仓库。
  6. 等待中央仓库维护者审核、合并并生成 `catalog.json`。

  

  插件作者提交 PR 时，通常只需要改：

  ```text
  plugins/<pluginId>.json
  ```

  插件作者提交示例：

  ```bash
  git status
  git add plugins/<pluginId>.json
  git commit -m "Add <pluginId> plugin"
  git push -u origin add-<pluginId>
  ```

  然后在 GitHub 页面创建 PR，目标仓库选择：

  ```text
  undertaker33/ElymBot-plugin-market
  ```

  目标分支选择：

  ```text
  main
  ```

  

  ## 3.仅走直链分发或zip分发

  直链：你只需要一个可下载的 zip URL，用户选择直链包地址安装时，宿主会直接下载并尝试导入这个包。

  zip：直接发zip给用户，用户选择本地zip安装即可

  

  ## 4. 上架检查清单

  插件作者发布前检查：

  - `manifest.json` 存在。
  - `android-plugin.json` 存在。
  - `android-plugin.json` 的 `runtime.bootstrap` 指向真实文件。
  - `manifest.json` 的 `pluginId`、`version`、`protocolVersion`、`minHostVersion` 正确。
  - zip 根目录直接包含 `manifest.json` 和 `android-plugin.json`。
  - 插件仓库已经推送到 GitHub。
  - GitHub Release 已发布。
  - `packageUrl` 是 zip 下载链接，不是 Release 页面链接。
  - 已准备好 `plugins/<pluginId>.json`。

  中央仓库维护者合并前检查：

  - 中央市场 `plugins/<pluginId>.json` 文件名和 `pluginId` 一致。
  - `versions[0].protocolVersion` 为 `2`。
  - `packageUrl` 可访问，最终返回 `200 OK`。
  - 已重新生成并提交 `catalog.json`。
  - 远端 raw catalog 能看到新插件。

  安卓端验证：

  - 安卓端刷新市场后能看到插件卡片。

  

  ## 5.注意事项

  ### 不要把 Release 页面当成 zip 直链

  错误：

  ```text
  https://github.com/your-name/your-repo/releases/tag/v1.0.0
  ```

  正确直链应该类似：

  ```text
  https://github.com/your-name/your-repo/releases/download/v1.0.0/plugin.zip
  ```

  ### `pluginId` 不稳定

  如果你改了 `pluginId`，宿主会把它当成另一个插件。

  这会直接影响：

  - 已安装状态识别
  - 市场状态对齐
  - 更新检测

  ### zip 根目录结构错误

  如果 `manifest.json` 不在压缩包根目录，宿主会导入失败。



## 6. 发布新版本

发布新版本时不要删除旧版本。

插件作者负责：

1. 修改插件代码。
2. 更新 `manifest.json` 里的 `version`。
3. 重新打 zip。
4. Git 提交并推送。
5. 创建新的 GitHub Release，例如 `v0.2.0`，上传新 zip。

插件作者没有中央仓库权限时：

1. 更新 `plugins/<pluginId>.json`。
2. 在 `versions` 数组最前面追加新版本。
3. 提交 PR 给中央仓库。

中央仓库维护者负责：

1. 打开 `plugins/<pluginId>.json`。
2. 在 `versions` 数组最前面追加新版本。
3. 重新生成 `catalog.json`。
4. 提交并推送。

示例：

```json
"versions": [
  {
    "version": "0.2.0",
    "packageUrl": "https://github.com/<owner>/<plugin-repo>/releases/download/v0.2.0/my-plugin-v0.2.0.zip",
    "protocolVersion": 2,
    "minHostVersion": "0.3.0",
    "maxHostVersion": "",
    "permissions": [],
    "changelog": "Add new features."
  },
  {
    "version": "0.1.0",
    "packageUrl": "https://github.com/<owner>/<plugin-repo>/releases/download/v0.1.0/my-plugin-v0.1.0.zip",
    "protocolVersion": 2,
    "minHostVersion": "0.3.0",
    "maxHostVersion": "",
    "permissions": [],
    "changelog": "Initial release."
  }
]
```

---

## 
