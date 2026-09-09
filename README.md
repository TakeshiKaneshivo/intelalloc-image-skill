[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md)

# IntelAlloc Image Skill

Codex and WorkBuddy skill for generating and editing images through the IntelAlloc image API.

This repository supports English and Chinese users. Install the skill and talk to Codex or WorkBuddy naturally. Before image generation, it checks the runtime host and model before selecting an API key.

## IntelAlloc Platform

`intelalloc-image` is built specifically for the IntelAlloc platform. It supports both Codex and WorkBuddy workflows, enabling GPT to call IntelAlloc's image-2 model reliably for image generation, image editing, reference-image workflows, and iterative follow-up edits. Codex and WorkBuddy can install the skill independently and keep their local configuration, history, and default output locations separate.

IntelAlloc registration: [https://backend.intelalloc.com/register?promo=JINGGE](https://backend.intelalloc.com/register?promo=JINGGE)

Need an invitation code? Contact takeshikaneshivo@gmail.com.

![IntelAlloc Codex and WorkBuddy image workflow demo 1](docs/images/intelalloc-demo-1.png)

![IntelAlloc Codex and WorkBuddy image workflow demo 2](docs/images/intelalloc-demo-2.png)

## Quick Start

After installing the skill, ask Codex or WorkBuddy to generate an image directly:

```text
Use IntelAlloc to generate a futuristic city at night and save it to D:\out\city.png
```

When no save path is specified, Codex saves unique PNGs under `~/Pictures/IntelAlloc/Codex` and WorkBuddy saves them under `~/Pictures/IntelAlloc/WorkBuddy`. Successful requests display the image and a clickable link to the complete saved directory path.

## Help

Ask Codex or WorkBuddy naturally for IntelAlloc image help. A normal customer-facing answer should describe the available image creation, editing, reference-image, batch, size, quality, and save-location options in plain language. It should not display command names, flags, Python code, API endpoints, or internal configuration paths.

For example, you can say: “I want to learn what IntelAlloc can do, the default image quality, and where images are saved.” The current host should answer in natural language, explain that images are saved automatically in a host-specific folder under `IntelAlloc` when no location is given, and explain that an eligible GPT-series key is tried automatically before asking the user for a key.

The bundled read-only help command remains available for developers and troubleshooting; it is an internal technical reference and should not be pasted into an ordinary customer reply.

If the first request is not running on a confirmed GPT model with an eligible host credential, provide an IntelAlloc GPT-series model key locally:

```text
Configure IntelAlloc API key: <your-api-key>
```

Edit an image:

```text
Use IntelAlloc to edit D:\images\source.png into watercolor style and save it to D:\out\watercolor.png
```

Drag an image file into Codex or WorkBuddy and edit it:

```text
Use the image I just dragged in and turn it into watercolor style, then save it to D:\out\watercolor.png
```

Use a dragged image together with the previous output:

```text
Add the image I just dragged into the previous output, keep the overall style consistent, and save it to D:\out\result.png
```

```text
Use the image I just dragged in as a reference, edit the previous image into the same style, and save it to D:\out\result.png
```

## Install

### Install From GitHub Path

Use this skill path:

```text
skills/intelalloc-image
```

If using Codex skill installer, install from:

```text
https://github.com/<your-user>/intelalloc-image-skill/tree/main/skills/intelalloc-image
```

Replace `<your-user>` with the GitHub account or organization that owns this repository.

### Manual Install

Download:

```text
releases/intelalloc-image-release.zip
```

Unzip it, then unzip the inner `intelalloc-image.zip`.

Place the extracted `intelalloc-image` folder here:

Codex on Windows:

```text
C:\Users\<user>\.codex\skills\intelalloc-image
```

Codex on macOS:

```text
~/.codex/skills/intelalloc-image
```

Codex on Linux:

```text
~/.codex/skills/intelalloc-image
```

WorkBuddy on Windows:

```text
C:\Users\<user>\.workbuddy-ai\skills\intelalloc-image
```

WorkBuddy on macOS:

```text
~/.workbuddy-ai/skills/intelalloc-image
```

WorkBuddy integrations on Windows and macOS use the corresponding `.workbuddy-ai/skills/intelalloc-image` directory under the user's home directory. For direct CLI commands, use `python` on Windows and `python3` on macOS or Linux.

Restart or refresh Codex or WorkBuddy after installation.

## Common Prompts

Without a specified save path, Codex saves generated and edited images under `~/Pictures/IntelAlloc/Codex`, while WorkBuddy uses `~/Pictures/IntelAlloc/WorkBuddy`; batch edits use a unique subdirectory there. A user-provided file path or directory always takes precedence.

The Windows examples below use `D:\` paths. On macOS or Linux, use POSIX paths such as `~/Pictures/IntelAlloc/Codex` or `/path/to/input.png` instead.

### WorkBuddy Runtime Contract

WorkBuddy must provide the host on every skill command so configuration, history, and default output paths stay isolated:

```text
INTELALLOC_RUNTIME_HOST=workbuddy
```

For `generate`, `edit`, and `batch-edit`, it must also provide the exact active model ID:

```text
INTELALLOC_RUNTIME_MODEL=<current-model-id>
```

The same host marker is required for `configure`, `show-config`, `last`, and `history`; the model marker may be included when available. This remains required after an API key has been saved.

Generate:

```text
Use IntelAlloc to generate a product poster and save it to D:\out\poster.png
```

Edit one image:

```text
Use IntelAlloc to edit D:\images\a.png into Japanese anime style and save it to D:\out\a_anime.png
```

Use dragged images:

```text
Use the images I just dragged in as references to generate a product poster and save it to D:\out\poster.png
```

Use a folder as references:

```text
Use images in D:\refs as references to generate a product poster and save it to D:\out\poster.png
```

Batch edit a folder:

```text
Batch edit images in D:\source into pixel art style and save outputs to D:\out
```

Specify size or quality only when you want to override the default for that request:

```text
Use IntelAlloc to generate a 3840x2160 poster with high quality and save it to D:\out\poster.png
```

POSIX path examples for macOS and Linux:

```text
Use IntelAlloc to generate a product poster and save it to /path/to/poster.png
Use IntelAlloc to edit /path/to/source.png and save it to /path/to/watercolor.png
Use images in /path/to/refs as references to generate a poster and save it to /path/to/poster.png
Batch edit images in /path/to/source into pixel art style and save outputs to /path/to/out
```

## Image Model

The default model is `gpt-image-2.5-flare`, optimized for fast everyday generation. Ask to switch to `gpt-image-2.5-sunburst` for higher-quality generation and editing, or explicitly select `gpt-image-2` as a compatibility fallback. Only these three models can be saved as a default. A selected model remains the default for future requests on the current host until changed again.

## Size And Quality

Default size and quality are both `auto`.

Each request reports the active model, size, quality, start time, finish time, and elapsed seconds. Defaults are not changed unless you explicitly ask to change them.

Common size presets:

```text
1536x1024, 1024x1536, 1024x1024
2048x1152, 1152x2048, 2048x2048
3840x2160, 2160x3840
```

You can also use `auto` or any valid custom `WIDTHxHEIGHT`: each edge is at most 3840px and a multiple of 16px, the aspect ratio is at most 3:1, and total pixels are 655,360 through 8,294,400.

Supported qualities:

```text
auto, low, medium, high, xhigh, max
```

GPT Image 2 supports only `auto`, `low`, `medium`, and `high`; `xhigh` and `max` are rejected before an API request.

## Common Issues

- Missing API key: provide an IntelAlloc GPT-series model API key with `Configure IntelAlloc API key: <your-api-key>`.
- Automatic credentials are used only for a first request on confirmed GPT-series models without a local key. A successful automatic key is saved locally until manually replaced. Use `show-config` to inspect the detected host, model, GPT classification, saved automatic-key state, and key source without revealing the full key.
- Dragged image has no readable local path: provide the local image path manually.
- Previous output is missing: generate or edit an image first, or provide a local input path.
- Cloudflare 1010 / 403: run `show-config` to confirm the automatically generated User-Agent, then retry. If it still fails, the backend access rule may need to allow this API client.
- HTTP 502: the backend or upstream service is temporarily unavailable. Retry later.
- Image path does not exist: provide a readable local file path.
- More than 16 reference images: reduce the folder or explicitly ask the current host to limit to 16 images.

When an API request fails, the current host shows the returned failure reason first and reminds you to retry or try again later.

## Safety And Devices

Codex reads `OPENAI_API_KEY` from `~/.codex/auth.json` only when no skill key is configured and the current host and model are confirmed as Codex + GPT. WorkBuddy must provide `INTELALLOC_RUNTIME_HOST=workbuddy` on every call and `INTELALLOC_RUNTIME_MODEL=<current-model-id>` for image calls; when no skill key exists, the skill reads the matching GPT model's `apiKey` from `~/.workbuddy-ai/models.json`, saves it locally, and then keeps using it until manual replacement. Once a skill key is configured, model changes do not replace it. Unknown/non-GPT contexts use local manual configuration. Skill state is host-specific: Codex uses `~/.codex/intelalloc-image/` and WorkBuddy uses `~/.workbuddy-ai/intelalloc-image/`. This includes `config.json` and `history.json`; `last` and `--from-last` never cross hosts. Unknown hosts retain the legacy Codex state path and the legacy `~/Pictures/IntelAlloc` default output directory. User-specified output paths remain unchanged.

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
