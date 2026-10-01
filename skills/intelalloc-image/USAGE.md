# IntelAlloc Image Skill Usage

This guide is for Codex and WorkBuddy users who install the `intelalloc-image` skill. You can use natural language in English or Chinese; the host reads this skill and calls the bundled CLI for you. Normal replies follow the language of the request: English requests receive English guidance, Chinese requests receive Chinese guidance, and mixed requests use their dominant language.

## Quick Start

Install the `intelalloc-image` folder here:

- Codex on Windows: `C:\Users\<your-user>\.codex\skills\intelalloc-image`
- Codex on macOS: `~/.codex/skills/intelalloc-image`
- Codex on Linux: `~/.codex/skills/intelalloc-image`
- WorkBuddy on Windows: `C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image`
- WorkBuddy on macOS: `~/.workbuddy-ai/skills/intelalloc-image`

For direct CLI commands, use `python` on Windows and `python3` on macOS or Linux.

Restart or refresh Codex or WorkBuddy after installation.

Then generate an image directly, or configure a local key if an automatic runtime credential is unavailable:

```text
Use IntelAlloc to generate a futuristic city at night and save it to D:\out\city.png
```

## Help

Ask Codex or WorkBuddy naturally for IntelAlloc image help. A customer-facing answer should use plain language to describe creating images, editing images, using references, continuing from the latest result, batch processing, image size and quality, and save locations. It should not expose command names, flags, Python code, API endpoints, or internal configuration paths.

For example: “What can IntelAlloc do, what are the default image settings, and where will the result be saved?” The current host should explain that a result is saved automatically in the system Pictures folder under `IntelAlloc` when no location is specified. The user can simply describe a file or folder location in the request. Eligible GPT-series credentials are tried automatically; if none is available, the current host asks for an IntelAlloc GPT-series API key.

The bundled read-only help command remains available as a developer and troubleshooting reference. Its technical output should not be pasted into a normal customer reply.

## Natural-Language Examples

The examples in this section use Windows paths. On macOS or Linux, replace them with POSIX paths such as `~/Pictures/IntelAlloc/Codex` or `/path/to/input.png`.

Generate an image:

```text
Use IntelAlloc to generate a product poster and save it to D:\out\poster.png
```

Edit one image:

```text
Use IntelAlloc to edit D:\images\a.png into Japanese anime style and save it to D:\out\a_anime.png
```

Use the previous output:

```text
Edit the previous image into a cinematic poster and save it to D:\out\poster.png
```

Use a dragged image together with the previous output:

```text
Add the image I just dragged into the previous output, keep the overall style consistent, and save it to D:\out\result.png
```

```text
Use the image I just dragged in as a reference, edit the previous image into the same style, and save it to D:\out\result.png
```

Use a folder as reference images:

```text
Use images in D:\refs as references to generate a product poster and save it to D:\out\poster.png
```

Batch edit a folder:

```text
Batch edit images in D:\source into pixel art style and save outputs to D:\out
```

POSIX path examples for macOS and Linux:

```text
Use IntelAlloc to generate a product poster and save it to /path/to/poster.png
Use IntelAlloc to edit /path/to/source.png and save it to /path/to/watercolor.png
Use images in /path/to/refs as references to generate a poster and save it to /path/to/poster.png
Batch edit images in /path/to/source into pixel art style and save outputs to /path/to/out
```

## API Key Configuration

The skill works immediately after installation. Codex can identify its runtime host and model from the Codex session environment or `~/.codex/config.toml`; explicit runtime arguments are optional. WorkBuddy must pass `--runtime-host workbuddy` on every call and must also pass `--runtime-model <current-model-id>` for `generate`, `edit`, and `batch-edit`; when invoking the CLI directly, use the equivalent `INTELALLOC_RUNTIME_HOST` and `INTELALLOC_RUNTIME_MODEL` environment variables. Do not rely on the first `models.json` entry.

Automatic credentials are used only for GPT-series models:

- Codex: read `OPENAI_API_KEY` from `~/.codex/auth.json`.
- WorkBuddy: match the current model's `id` or `name` in `~/.workbuddy-ai/models.json`, then read `apiKey`.

WorkBuddy integration must set `INTELALLOC_RUNTIME_HOST=workbuddy` for every `generate`, `edit`, and `batch-edit` invocation, and must also set `INTELALLOC_RUNTIME_MODEL=<current-model-id>` for those image calls. The first valid model key is saved to `config.json` and then reused for all later requests until `configure --api-key` replaces it. Unknown hosts, unknown/non-GPT models, invalid files, and unmatched models fall back to manual configuration. Runtime model lookup is skipped while a skill key is already configured.

The platform-specific WorkBuddy CLI examples below include the correct skill path, shell, and Python command for each supported platform.

Use `--runtime-host workbuddy` for WorkBuddy `configure`, `show-config`, `last`, and `history` commands too, so each command uses WorkBuddy's separate state directory. Pass the current model ID whenever it is available. The host marker remains required after a key has been saved.

Save or update the API key later:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py configure --api-key "<your-api-key>"
```

Check the current configuration without revealing the full key:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py show-config
```

WorkBuddy on macOS:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py configure --runtime-host workbuddy --api-key "<your-api-key>"
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py show-config --runtime-host workbuddy
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py configure --runtime-host workbuddy --api-key "<your-api-key>"
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py show-config --runtime-host workbuddy
```

Local config is stored outside the skill folder and isolated by host:

```text
~/.codex/intelalloc-image/config.json
~/.workbuddy-ai/intelalloc-image/config.json
```

The key lookup order is single-request `--api-key`, `INTELALLOC_API_KEY`, the local `config.json` key, then the current eligible host-specific GPT credential. Once any key is present in `config.json`, it remains the active skill key until `configure --api-key` replaces it; model changes do not replace it. When no key is configured, resolve the current runtime and read the matching host credential on every request, saving the first successful automatic key. Host credential files are never modified.

`show-config` reports the detected host, model, GPT classification, automatic credential status, persisted automatic-key status and origin, and final key source without revealing any complete key.

Do not share either configuration file.

## Generate Images

Without `--output` or `--output-dir`, Codex saves a unique PNG to `~/Pictures/IntelAlloc/Codex` and WorkBuddy saves one to `~/Pictures/IntelAlloc/WorkBuddy`. The directory is created after a successful response. Use `--output` for an exact file path or `--output-dir` for a user-selected directory.

CLI form:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py generate --prompt "future city at night" --output "/path/to/city.png"
```

Codex on Windows:

```powershell
python C:\Users\<your-user>\.codex\skills\intelalloc-image\scripts\intelalloc_image.py generate --prompt "future city at night" --output "D:\out\city.png"
```

WorkBuddy on macOS:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py generate --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "future city at night" --output "/path/to/city.png"
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py generate --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "future city at night" --output "D:\out\city.png"
```

Before each request, the script prints the effective model, size, and quality:

```text
REQUEST_MODEL=gpt-image-2.5-flare
REQUEST_SIZE=auto
REQUEST_QUALITY=auto
```

Image edit requests use JSON by default, matching the verified `gen-image`
request path. JSON sends `images[].image_url` Data URLs. For compatibility or
diagnostics, select multipart explicitly with `--edit-protocol multipart`; it
sends files as `image[]`. The two protocols are never sent automatically in
sequence, so a 400 response does not trigger a second billable request.

It also prints request timing:

```text
REQUEST_STARTED_AT=...
REQUEST_FINISHED_AT=...
REQUEST_ELAPSED_SECONDS=...
```

When generation succeeds, the current host shows the output image and provides a clickable link to the complete saved directory path.

## Edit Images

Edit one local image:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --prompt "make this watercolor" --input "/path/to/source.png" --output "/path/to/watercolor.png"
```

Select the fallback multipart protocol for one request:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --edit-protocol multipart --prompt "make this watercolor" --input "/path/to/source.png" --output "/path/to/watercolor.png"
```

Set the persistent default with `configure --edit-protocol json` or
`configure --edit-protocol multipart`. A request-level `--edit-protocol`
overrides that setting. `batch-edit` accepts the same option.

WorkBuddy on macOS:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "make this watercolor" --input "/path/to/source.png" --output "/path/to/watercolor.png"
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "make this watercolor" --input "D:\images\source.png" --output "D:\out\watercolor.png"
```

Edit with multiple reference images:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --prompt "combine these references into a product poster" --input "/path/a.png" --input "/path/b.jpg" --output "/path/poster.png"
```

Supported input types are `.png`, `.jpg`, `.jpeg`, and `.webp`. One edit request supports at most 16 input images.

If you drag an image into Codex or WorkBuddy, the current host can use it directly only when it has a readable local file path. If the dragged image does not expose a path, provide the path manually.

Combine dragged images with the previous output:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --input "/path/dragged.png" --from-last --prompt "add the dragged image into the previous output and keep the overall style consistent" --output "/path/result.png"
```

You can repeat `--input` for multiple dragged images. `--from-last` appends the most recent successful IntelAlloc output as another edit input. The 16-image limit includes dragged images, directory images, and the previous output.

For multi-image edits, the CLI tries to optimize upload copies to reduce request size when Pillow is available. Original input images are never modified. If Pillow is missing or the optimized copy is not smaller, the CLI uploads the original bytes.

## Folder Reference Images

Use images in a folder as references for one output:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --prompt "use these references to make a poster" --input-dir "/path/to/refs" --output "/path/to/poster.png"
```

By default, only top-level files in the folder are used. Include subfolders only when needed:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --prompt "use these references" --input-dir "/path/to/refs" --recursive --output "/path/to/poster.png"
```

If the folder has more than 16 supported images, narrow the folder or explicitly limit the count:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --prompt "use these references" --input-dir "/path/to/refs" --limit 16 --output "/path/to/poster.png"
```

WorkBuddy on macOS folder-reference example:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "use these references" --input-dir "/path/to/refs" --output "/path/to/poster.png"
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "use these references" --input-dir "D:\refs" --output "D:\out\poster.png"
```

## Batch Edit A Folder

Without `--output-dir`, each batch creates a unique directory under the current host's default output directory. Supply `--output-dir` to use a specific directory.

Batch-edit each image in a folder into separate outputs:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py batch-edit --prompt "make each image pixel art" --input-dir "/path/to/source" --output-dir "/path/to/out"
```

Codex on Windows:

```powershell
python C:\Users\<your-user>\.codex\skills\intelalloc-image\scripts\intelalloc_image.py batch-edit --prompt "make each image pixel art" --input-dir "D:\source" --output-dir "D:\out"
```

WorkBuddy on macOS:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py batch-edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "make each image pixel art" --input-dir "/path/to/source" --output-dir "/path/to/out"
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py batch-edit --runtime-host workbuddy --runtime-model "<current-model-id>" --prompt "make each image pixel art" --input-dir "D:\source" --output-dir "D:\out"
```

## Continue From The Previous Image

Every successful generation or edit is recorded in host-specific local history:

```text
~/.codex/intelalloc-image/history.json
~/.workbuddy-ai/intelalloc-image/history.json
```

Codex commands below use the Codex history by default. WorkBuddy must include
`--runtime-host workbuddy` on `last`, `history`, and `--from-last` commands so
they read only WorkBuddy's history. The runtime model is not needed for the
read-only history commands, but image requests should also pass the exact
current model ID.

Show the latest output:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py last
```

Show recent history:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py history
```

WorkBuddy on macOS:

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py last --runtime-host workbuddy
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py history --runtime-host workbuddy
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py last --runtime-host workbuddy
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py history --runtime-host workbuddy
```

Edit from the latest output:

```bash
python3 ~/.codex/skills/intelalloc-image/scripts/intelalloc_image.py edit --from-last --prompt "make it cinematic" --output "/path/to/cinematic.png"
```

WorkBuddy on macOS (include the current model ID for this image request):

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --from-last --prompt "make it cinematic" --output "/path/to/cinematic.png"
```

WorkBuddy on Windows (PowerShell):

```powershell
python C:\Users\<your-user>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<current-model-id>" --from-last --prompt "make it cinematic" --output "D:\out\cinematic.png"
```

Natural language:

```text
Edit the previous image into a cinematic poster and save it to D:\out\cinematic.png
```

This works only on the same device, because history stores local file paths.

The history file is selected by the runtime host. A saved skill API key does
not remove the WorkBuddy host requirement, because the host also selects the
configuration, history, and default output directories.

## Image Model

The default model is `gpt-image-2.5-flare` for fast everyday generation. Ask to switch to `gpt-image-2.5-sunburst` for quality-focused generation and editing, or explicitly choose `gpt-image-2` as a compatibility fallback. Only these three models can be saved as defaults. The selected model remains the default for future requests on the current host until changed again.

## Size And Quality

Default size and quality are both `auto`.

Common size presets:

```text
1536x1024 - Landscape
1024x1536 - Portrait
1024x1024 - Square
2048x1152 - HD Landscape
1152x2048 - HD Portrait
2048x2048 - HD Square
3840x2160 - 4K Landscape
2160x3840 - 4K Portrait
```

Supported qualities:

```text
auto
low
medium
high
xhigh
max
```

`gpt-image-2` supports only `auto`, `low`, `medium`, and `high`; `xhigh` and `max` are rejected before an API request.

Model characteristics:

```text
GPT Image 2 - compatibility fallback; does not support xhigh or max
GPT Image 2.5 Flare - fast, for everyday generation
GPT Image 2.5 Sunburst - higher-quality generation and editing
```

You can also use `auto` or a custom `WIDTHxHEIGHT`. Each edge must be at most 3840px and a multiple of 16px, the aspect ratio must not exceed 3:1, and total pixels must be 655,360 through 8,294,400.

Codex and WorkBuddy should not pass `--size` or `--quality` unless you explicitly request a size or quality. Neither host should change default size or quality unless you explicitly ask to change defaults.

Single request override:

```text
Use IntelAlloc to generate a 3840x2160 poster with high quality and save it to D:\out\poster.png
```

Change defaults for future requests:

```text
Set IntelAlloc default size to auto and default quality to high
```

## Output Display In Codex And WorkBuddy

After a successful generation or edit, the current host shows the generated image in the conversation and provides a clickable link to the complete saved directory path. Batch edits show the generated images and one link to the complete batch directory path.

Only the first successful image in each Codex or WorkBuddy conversation includes the settings reminder. English requests receive an English reminder; Chinese requests receive a Chinese reminder. The reminder states only the active model, size, and quality, then tells the user to enter `help`; it will list all detailed sizes, the complete quality list, and the available models with their characteristics. It does not list alternative models, positioning parentheses, or detailed size/quality options. Later successful images in the same conversation do not repeat this reminder.

## Common Errors

Missing API key:

```text
IntelAlloc API key is not configured.
```

Fix: configure your API key.

HTTP 502:

```text
HTTP 502
The API returned the following error:
...
Please try again later.
```

Meaning: the backend or upstream service is temporarily unavailable. The skill does not retry 502; try again later.

Cloudflare 1010:

```text
Access denied | backend.intelalloc.com used Cloudflare to restrict access
Error 1010
```

Run `show-config` to confirm the automatically generated device User-Agent, then retry. If it still fails, the backend Cloudflare rule likely needs to allow API clients for `/v1/images/*`.

Input image missing: provide a valid local path.

Too many input images: reduce the folder, use a smaller reference set, or explicitly limit to 16.

Invalid saved model:

```text
Unsupported persistent model: ...
```

The local configuration contains a model that is no longer allowed. Choose one of
`gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, or `gpt-image-2` with
`configure --model`, then retry the request. The skill does not silently replace
the saved model.

For any generation/editing request failure, the current host should show the returned failure reason first, then remind the user to retry or try again later. It should not claim an image was saved or attempt another image operation unless the user asks.

## Cross-Device Notes

The skill folder can be the same on every device.

Each device needs its own:

- API key configuration only when an automatic runtime credential is unavailable
- local output paths
- local history
- optional User-Agent override if that device hits Cloudflare rules

Do not share:

```text
~/.codex/intelalloc-image/config.json
~/.workbuddy-ai/intelalloc-image/config.json
~/.codex/auth.json
~/.workbuddy-ai/models.json
~/.codex/intelalloc-image/history.json
~/.workbuddy-ai/intelalloc-image/history.json
API keys
generated images
temporary files
```

The phrase "previous image" only works on the same device where that image was generated and still exists.

## 中文完整使用说明

这个 skill 给 Codex 和 WorkBuddy 用户使用。安装后，你可以直接用中文告诉 Codex 或 WorkBuddy 要生成什么图、修改哪张图、输出到哪里。宿主会读取这个 skill，并调用内置脚本完成请求。

### 安装

把 `intelalloc-image` 文件夹放到当前宿主的 skills 目录：

- Windows 的 Codex：`C:\Users\<你的用户名>\.codex\skills\intelalloc-image`
- macOS 的 Codex：`~/.codex/skills/intelalloc-image`
- Linux 的 Codex：`~/.codex/skills/intelalloc-image`

Windows WorkBuddy：`C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image`

macOS WorkBuddy：`~/.workbuddy-ai/skills/intelalloc-image`

直接运行 CLI 命令时，Windows 使用 `python`，macOS 或 Linux 使用 `python3`。

如果你下载的是 `intelalloc-image-release.zip`，先解压它，再解压里面的 `intelalloc-image.zip`，把得到的 `intelalloc-image` 文件夹放到上面的目录。安装后重启或刷新 Codex 或 WorkBuddy。

### 帮助

直接对 Codex 或 WorkBuddy 说“IntelAlloc 图片帮助”，或自然地询问“可以生成和修改哪些图片”“默认设置是什么”“结果会保存在哪里”。普通回复会用自然语言介绍生成图片、修改图片、参考图、继续处理上一张图片、批量处理、尺寸质量和保存位置，不要求用户记忆命令，也不会展示内部路径或密钥配置命令。

未指定保存位置时，结果会自动保存到系统图片目录下按宿主区分的 `IntelAlloc` 子目录；用户也可以直接说出要保存的文件或目录。系统会先尝试使用符合条件的 GPT 系列模型凭据，无法自动使用时再请用户提供 IntelAlloc GPT 系列 API key。

开发者或排障时仍可使用随技能附带的只读帮助命令查看技术细节；这些命令不是普通客户需要使用的方式。

### API key 配置

安装后无需初始化。Codex 可以通过 Codex 会话环境或 `~/.codex/config.toml` 自动识别宿主和模型，也可以显式传入运行时参数。WorkBuddy 每次调用必须传入 `--runtime-host workbuddy`；`generate`、`edit` 和 `batch-edit` 还必须传入 `--runtime-model <当前模型 ID>`，直接运行 CLI 时也可以使用对应的 `INTELALLOC_RUNTIME_HOST` 和 `INTELALLOC_RUNTIME_MODEL` 环境变量。不能默认使用 `models.json` 的第一项。

只有 GPT 系列模型才会自动读取凭据：

- Codex：读取 `~/.codex/auth.json` 的 `OPENAI_API_KEY`。
- WorkBuddy：在 `~/.workbuddy-ai/models.json` 中匹配当前模型的 `id` 或 `name`，读取对应的 `apiKey`。

WorkBuddy 集成每次 `generate`、`edit` 和 `batch-edit` 调用都必须注入 `INTELALLOC_RUNTIME_HOST=workbuddy` 和 `INTELALLOC_RUNTIME_MODEL=<当前模型 ID>`。第一次成功读取的模型 key 会保存到 `config.json`，之后一直使用，直到用户手动配置新 key。宿主未知、模型未知或非 GPT、文件无效、模型匹配失败时，改走手动配置；已有 skill key 时跳过运行时模型读取。

WorkBuddy 的每个图片命令也可直接传入运行时参数。

macOS WorkBuddy：

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py generate --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..."
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..." --input "/path/to/input.png"
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py batch-edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..." --input-dir "/path/to/images"
```

Windows WorkBuddy（PowerShell）：

```powershell
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py generate --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..."
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..." --input "D:\images\input.png"
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py batch-edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --prompt "..." --input-dir "D:\images"
```

WorkBuddy 调用 `configure`、`show-config`、`last` 和 `history` 时也必须传入 `--runtime-host workbuddy`，以使用 WorkBuddy 独立的状态目录；可以取得当前模型 ID 时一并传入。保存 key 后仍然必须传入宿主标记。

如果没有可用 key，请提供 IntelAlloc GPT 系列模型的 API key：

```text
配置 IntelAlloc API key：你的 key
```

key 优先级为单次 `--api-key`、`INTELALLOC_API_KEY`、本地 `config.json`、当前符合条件的宿主凭据。只要 `config.json` 已有 key，后续始终使用它，切换模型也不会替换；只有用户手动配置新 key 才会覆盖。没有 key 时，每次请求都会解析当前宿主和模型并读取对应凭据，首次成功读取后保存。直接提供 `sk-...` key 后，skill 会保存该 key 并立即重试原请求，且不会回显完整 key。不会修改宿主凭据文件。`show-config` 只显示脱敏后的 key、模型匹配结果、来源和自动保存状态。

### 继续处理上一张图片

成功生成或编辑的记录保存在当前宿主的本地历史文件中：Codex 使用 `~/.codex/intelalloc-image/history.json`，WorkBuddy 使用 `~/.workbuddy-ai/intelalloc-image/history.json`。WorkBuddy 执行 `last`、`history` 或带 `--from-last` 的图片命令时，必须传入 `--runtime-host workbuddy`，避免读取 Codex 的历史；图片命令还必须传入准确的 `--runtime-model <当前模型 ID>`。`last` 和 `history` 只读历史，不要求模型参数。

WorkBuddy 命令示例：

macOS WorkBuddy：

```bash
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py last --runtime-host workbuddy
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py history --runtime-host workbuddy
python3 ~/.workbuddy-ai/skills/intelalloc-image/scripts/intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --from-last --prompt "改成电影感" --output "/path/to/cinematic.png"
```

Windows WorkBuddy（PowerShell）：

```powershell
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py last --runtime-host workbuddy
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py history --runtime-host workbuddy
python C:\Users\<你的用户名>\.workbuddy-ai\skills\intelalloc-image\scripts\intelalloc_image.py edit --runtime-host workbuddy --runtime-model "<当前模型 ID>" --from-last --prompt "改成电影感" --output "D:\out\cinematic.png"
```

保存 key 后仍然必须传入 WorkBuddy 宿主标记，因为它同时决定配置、历史和默认输出目录。

### 生图

下面的 Windows 示例使用 `D:\` 路径；在 macOS 或 Linux 中请改用 `~/Pictures/IntelAlloc/Codex` 或 `/path/to/input.png` 这样的 POSIX 路径。

未指定输出文件或目录时，Codex 会自动保存唯一 PNG 到 `~/Pictures/IntelAlloc/Codex`，WorkBuddy 会保存到 `~/Pictures/IntelAlloc/WorkBuddy`；目录会在成功生成后创建。指定文件路径时使用该文件路径，指定目录时使用该目录。

```text
用 IntelAlloc 生成一张未来城市夜景，输出到 D:\out\city.png
```

```text
用 IntelAlloc 生成一张产品海报，输出到 D:\out\poster.png
```

### 改图

指定本地图片路径：

```text
用 IntelAlloc 把 D:\images\source.png 改成水彩风，输出到 D:\out\watercolor.png
```

也可以直接把图片文件拖进 Codex 或 WorkBuddy，然后说：

```text
把我刚拖进来的图片改成日系动画风格，输出到 D:\out\anime.png
```

如果当前宿主能拿到拖入图片的本地可读路径，就会直接使用这张图。如果拖入图片没有可读取路径，当前宿主会要求你补充本地文件路径。

### 拖入图片和上张图联动

如果你刚生成或编辑过一张图，可以把新图片拖进 Codex 或 WorkBuddy，并让它和上张输出图一起参与编辑。

把拖入图片内容添加到上一张输出图里：

```text
把我刚拖进来的图片内容添加到上张输出图里，保持整体风格一致，输出到 D:\out\result.png
```

把拖入图片作为参考图，修改上一张输出图：

```text
把我刚拖进来的图片作为参考，基于上张图改成同样风格，输出到 D:\out\result.png
```

这里的“上张图 / 上张输出图”指同一台设备上最近一次成功生成或编辑保存的图片。如果文件被删除，或者换了设备，需要重新指定图片路径。

### 目录参考图

把一个目录里的图片作为参考，生成一张结果图：

```text
读取 D:\refs 里的图片作为参考，生成一张产品海报，输出到 D:\out\poster.png
```

默认只读取目录当前层级的 `.png`、`.jpg`、`.jpeg`、`.webp`。如果要包含子目录，需要明确说明。

### 批量编辑

未指定输出目录时，每个批次都会在当前宿主的默认输出目录下创建唯一目录。指定输出目录时使用客户提供的目录。

把目录里的每张图片分别编辑成独立输出：

```text
批量把 D:\source 里的图片改成像素风，输出到 D:\out
```

macOS 和 Linux 路径示例：

```text
用 IntelAlloc 生成一张产品海报，输出到 /path/to/poster.png
用 IntelAlloc 把 /path/to/source.png 改成水彩风，输出到 /path/to/watercolor.png
读取 /path/to/refs 里的图片作为参考，生成一张产品海报，输出到 /path/to/poster.png
批量把 /path/to/source 里的图片改成像素风，输出到 /path/to/out
```

### 图片模型

默认模型是面向日常快速生成的 `gpt-image-2.5-flare`。需要更高生成和编辑质量时，可以明确要求切换到 `gpt-image-2.5-sunburst`；也可以明确选择 `gpt-image-2` 作为兼容备选。只有这三个模型可保存为默认模型；模型切换后会保存为当前宿主后续请求的默认模型，直到再次更改。

### 尺寸和质量

默认尺寸和默认质量均为 `auto`。

每次请求都会显示当前使用的模型、尺寸、质量、开始时间、结束时间和耗时。尺寸可使用 `auto` 或合法的 `WIDTHxHEIGHT`：宽高不超过 3840、均为 16 的倍数、比例不超过 3:1、总像素为 655,360 至 8,294,400。质量可选 `auto`、`low`、`medium`、`high`、`xhigh`、`max`。

GPT Image 2 仅支持 `auto`、`low`、`medium`、`high`；`xhigh` 和 `max` 会在发送接口请求前被拒绝。

只修改本次请求的尺寸或质量：

```text
用 IntelAlloc 生成一张 3840x2160 的海报，质量 high，输出到 D:\out\poster.png
```

修改以后所有请求的默认尺寸或质量：

```text
把 IntelAlloc 默认尺寸改成 auto，默认质量改成 high
```

### 输出图片展示

生成或编辑成功后，当前宿主会在会话里直接展示输出图片，并提供指向完整实际保存目录的可点击链接。批量编辑时，会展示生成图片列表和一个指向完整批次目录的链接。

每个 Codex 或 WorkBuddy 会话仅在首张成功图片后提示一次当前模型、尺寸和质量，然后明确告诉用户直接输入 `help`；系统会列出全部详细尺寸、完整质量列表，以及可选模型和各自特点。中文请求返回中文提示，例如：`模型：GPT Image 2.5 Flare；尺寸：auto；质量：auto。` 后接：如需查看完整配置，请直接输入 `help`，系统会列出全部详细尺寸、完整质量列表，以及可选模型和各自特点。首次提示不再列出候选模型、定位括号或详细尺寸/质量选项；英文请求返回对应英文提示。该提示不会写入配置或历史，同一会话后续成功图片不再重复。

### 常见问题

- 缺 API key：重新说 `配置 IntelAlloc API key：你的 key`。
- 拖入图片不可读：提供图片的本地文件路径。
- 上张图不存在：重新指定输入图片，或先生成一张新图。
- HTTP 502：后端或上游服务暂时不可用，稍后重试。
- Cloudflare 1010 / 403：运行 `show-config` 确认自动生成的 User-Agent 后重试；如果仍失败，需要后端放行该 API 客户端。
- 参考图超过 16 张：缩小图片范围，或明确让当前宿主只取 16 张。

请求失败时，当前宿主会先显示失败原因，再提醒你重试或稍后再试，不会继续做其它图片操作。

### 安全和跨设备

不要分享：

```text
~/.codex/intelalloc-image/config.json
~/.workbuddy-ai/intelalloc-image/config.json
~/.codex/auth.json
~/.workbuddy-ai/models.json
~/.codex/intelalloc-image/history.json
~/.workbuddy-ai/intelalloc-image/history.json
API key
生成图片
临时文件
```

历史记录和“上张图”只在当前设备可靠，换设备后不会自动同步。
