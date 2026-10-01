# MD 自定义上游图片编辑 400：第二阶段只读排查请求

## 目的

请协助继续排查一笔通过 IntelAlloc/Sub2API `v0.2.8` 发起的图片编辑请求。

本轮只需要查询现有日志和链路追踪，不要重放请求，不要执行收费测试，不要修改线上配置，也不要输出完整 API Key、Authorization、prompt 原文、图片内容或 Base64。

## 当前已经确认的链路

```text
IntelAlloc
  POST https://backend.intelalloc.com/v1/images/edits
      ↓
Sub2API v0.2.8：API Key 账号分支
      ↓
MD 自定义上游
      ↓
是否继续调用第二级图片供应商：目前未知
```

这里的 `upstream` 只能说明 IntelAlloc/Sub2API 的直接上游是 MD，不能据此证明 MD 已经向第二级供应商发出了请求。

## 待查询请求

### IntelAlloc/Sub2API 侧关联信息

- 时间：`2026-09-24 15:52:53 +08:00`（约）
- 方法和路径：`POST /v1/images/edits`
- IntelAlloc `x-request-id`：`82dc9437-c4f2-4812-88ce-bbe9e6f5591b`
- IntelAlloc `x-client-request-id`：`63afd781-31e0-4449-a887-d0017d7f647b`
- Cloudflare `cf-ray`：`a400363fab747537-SEA`
- Sub2API 错误记录：`1997030`
- MD 侧已记录的上游 request ID：`b1176702-a74a-4087-ad13-aa8469eab11a`
- MD 侧记录的状态：`HTTP 400`
- MD 侧记录的耗时：约 `1337 ms`

如果 `b1176702-a74a-4087-ad13-aa8469eab11a` 是 MD 发往第二级供应商的 request ID，请明确标注；如果它只是 MD 内部请求 ID，也请明确说明，不要混用这两个概念。

### 账号和请求特征

- account：`MD`
- `account_id`：`20673`
- `api_key_id`：`4333`
- platform：`openai`
- account type：`apikey`
- request model：`gpt-image-2.5-flare`
- upstream model：`gpt-image-2.5-flare`
- 调度能力：`images-native`
- 接口：`/v1/images/edits`
- `multipart/form-data`：已确认
- 图片：用户提供的是单张 PNG，约 `1370×1148`、约 `1.9 MB`；MD 日志目前未独立记录这些元数据
- `n`：请求侧为 `1`
- `size`：`auto`
- `quality`：`auto`
- 失败请求 `stream`：`false`
- 审计文本长度：`71` 字符；这不是原始 prompt 字节数

## 本轮必须区分的三个结果

请不要笼统地返回“上游 400”，请明确属于以下哪一种：

1. MD 在解析、参数校验、图片校验或权限校验阶段本地返回 400，根本没有发出第二级请求；
2. MD 已经发出第二级请求，第二级返回 400，MD 将其原样或统一包装后返回；
3. MD 先调用了内部适配器，但适配器在发出 HTTP 请求前失败，随后由 MD 统一包装为 400。

如果仍无法区分，请明确写出“现有日志不可区分”，并指出缺少哪一条日志，而不要推断为权限问题或 Sub2API 缺陷。

## 请查询的日志内容

### 1. MD 入站解析摘要

请按上面的时间、账号、模型和接口定位 MD 入站记录，并只返回脱敏摘要：

- MD 入站 trace/request ID；
- 是否成功解析 multipart；
- Content-Type 是否包含 boundary，是否在 MD 侧重建 boundary；
- 文件 part 的字段名（例如 `image` 或 `image[]`）；
- 文件 part 数量；
- filename 是否存在（可只返回扩展名或是否存在）；
- MIME type；
- 字节数；
- 图片解码是否成功；
- 解码后的宽高和格式；
- prompt 是否存在、长度和 hash；
- `model`、`n`、`size`、`quality`、`stream`；
- 是否收到 `partial_images`、`background`、`output_format`；
- 请求体大小或 Content-Length；
- 是否命中图片审核、prompt 审计、大小限制、格式限制或能力校验。

请不要输出图片二进制、Base64、prompt 原文或完整请求体。

### 2. MD 是否产生了第二级出站调用

请通过同一个 MD trace/request ID 查询出站调用日志：

如果存在出站调用，请提供：

- 实际 host 和 path（Authorization 脱敏）；
- HTTP 方法；
- 出站 request ID；
- 出站 HTTP status；
- 出站响应 Content-Type；
- 出站耗时；
- 原始响应 body 的脱敏内容；
- `error.type`、`error.code`、`error.param`、`error.message`（如有）；
- MD 是否修改了错误 body、status 或字段；
- 是否发生重试、切换供应商或账号冷却。

如果没有出站调用，请明确提供：

- 没有出站调用的证据；
- 触发本地返回的校验名称或错误码；
- 失败字段的名称和类型；
- 触发校验的配置或能力判断（不要输出密钥）。

如果只能看到 MD 统一错误记录，不能证明有没有出站调用，请明确写“没有足够日志证明出站调用是否发生”。

### 3. 如果存在 MD 出站 multipart，请比较实际转发结构

本次实际是 API Key 账号路径，不应默认按 OAuth/Codex 的 `images[].image_url` JSON 路径分析。请先确认 MD 的实际协议，再返回以下字段：

- 出站 Content-Type 和 boundary 是否重新生成；
- model；
- prompt 是否存在及长度/hash；
- 图片字段名和文件数量；
- filename 是否存在；
- 文件 MIME type；
- 文件字节数；
- 图片格式、宽高和解码结果；
- `n`、`size`、`quality`、`stream`；
- `partial_images`、`background`、`output_format` 是否被补入、删除或改写；
- MD 是否把 multipart 转成 JSON、Base64 或 `images[].image_url`；
- 出站 Content-Length；
- 第二级供应商实际收到的模型和图片数量。

只有在日志明确显示 MD 使用 JSON/Codex 适配器时，才需要进一步检查 `images[].image_url`；不能因为公开的其他 OAuth 路径存在该字段，就假定本次 API Key 请求也使用该路径。

## 成功和失败请求对比

请获取下列成功请求的 MD trace/request ID，然后与失败请求 `1997030` 逐字段对比。成功记录本身没有保存完整请求结构，不能用“产生 1 张图片”代替原始 `n` 或 multipart 元数据。

| 时间（北京时间） | 接口 | 结果 | 关联信息 |
|---|---|---|---|
| `2026-09-24 12:27:04` | `/v1/images/edits` | 成功，产出 1 张图片 | usage `10798967`，同 `account_id=20673`、`api_key_id=4333`、模型 `gpt-image-2.5-flare`，`stream=true` |
| `2026-09-24 15:49:54` | `/v1/images/edits` | 上游 400 | 同一 MD 账号，`stream=true` |
| `2026-09-24 15:52:53` | `/v1/images/edits` | 上游 400 | error record `1997030`，`stream=false`，MD 侧 request ID `b1176702-a74a-4087-ad13-aa8469eab11a` |
| `2026-09-24 16:01:29` | `/v1/images/generations` | 成功，产出 1 张图片 | usage `10804536`，同一 MD 账号 |

请重点比较：

- 是否为同一个 MD 入站适配器和同一个第二级 endpoint；
- 成功和失败时的文件 part 名称、数量、filename、MIME、字节数、宽高和解码结果；
- 图片 SHA-256 或其他内容 hash；
- prompt 长度和 hash；
- model、n、size、quality；
- stream 和其他可选参数；
- 入站 boundary 与 MD 出站 boundary；
- MD 是否在不同时间使用了不同的供应商、路由、能力配置或模型映射；
- 第二级供应商返回的原始 status、request ID 和 body 是否不同。

成功记录中的 `image_size=2K`、`image_size_source=default` 如果只是计费尺寸，不能当作上传图片宽高，也不能当作图片相同的证据。

特别注意：已经存在一笔同账号、同模型、同接口的成功编辑，因此不能仅凭生成接口成功或失败接口 400，就认定账号没有图片编辑权限。另有 `stream=true` 的编辑失败记录，因此也不能把 `stream=false` 单独定性为根因。

## 当前证据允许得出的结论

在 MD 内部日志不可见的情况下，只能确认：

1. IntelAlloc/Sub2API 已进入上游链路，并收到 MD 方向的 HTTP 400；
2. 目前不能区分 MD 本地校验、MD 适配器失败和第二级供应商返回后包装；
3. 当前没有证据证明账号没有编辑权限；
4. 当前没有证据证明 `size=auto`、`quality=auto`、`image[]`、`stream=false` 或 Sub2API `v0.2.8` 本身是根因；
5. 当前也没有足够证据证明 MD 是否正确识别为一个图片文件，或是否真的到达第二级图片供应商；
6. 已知上游正文只有：

```json
{"error":{"message":"Bad Request","type":"invalid_request_error"}}
```

不能从这段泛化正文推导出权限、余额、参数或图片格式的具体原因。

## 请按以下格式返回结果

```text
1. MD 本地校验 / MD 适配器失败 / 第二级供应商返回 / 仍无法区分：
2. MD 入站 trace/request ID：
3. 是否存在 MD 到第二级供应商的出站调用：是 / 否 / 无法确认
4. 若存在，第二级 endpoint、request ID、status、Content-Type、原始脱敏 body：
5. 若不存在，本地校验名称或失败字段：
6. MD 实际识别的图片字段名、文件数量、MIME、字节数、宽高：
7. MD 出站使用 multipart 还是 JSON；是否重建 boundary：
8. 成功 usage 10798967 与失败 record 1997030 的关键差异：
9. 是否有更具体的 error.code 或 error.param：
10. 当前可以确认的根因和仍不能确认的事项：
```

再次强调：无需提供完整 API Key、Authorization、prompt 原文、图片内容、Base64 或完整请求体；字段名、类型、长度、hash、状态码和 request ID 已足够继续定位。
