[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md)

# IntelAlloc Image Skill

本 skill 是 IntelAlloc 平台专用的 Codex 和 WorkBuddy 生图/改图工具，用于让 GPT 在 Codex 或 WorkBuddy 会话中稳定调用 IntelAlloc 的 image-2 模型，完成文本生图、图片编辑、参考图编辑和连续追改等工作流。

IntelAlloc 平台注册链接：[https://backend.intelalloc.com/register?promo=JINGGE](https://backend.intelalloc.com/register?promo=JINGGE)

需要注册邀请码可以联系：takeshikaneshivo@gmail.com

这个 skill 给 Codex 和 WorkBuddy 用户使用。安装后，你不需要记 CLI 命令，直接用自然语言告诉 Codex 或 WorkBuddy 生成什么图、改哪张图、输出到哪里即可。普通回复会跟随请求语言：英文请求使用英文，中文请求使用中文；混合语言请求按主要语言回复。两个宿主可以分别安装 skill，并独立保存各自的配置、历史和默认输出位置。

![IntelAlloc Codex 和 WorkBuddy 图片工作流演示 1](docs/images/intelalloc-demo-1.png)

![IntelAlloc Codex 和 WorkBuddy 图片工作流演示 2](docs/images/intelalloc-demo-2.png)

## 安装

手动安装时，下载：

```text
releases/intelalloc-image-release.zip
```

解压后，再解压里面的 `intelalloc-image.zip`，把得到的 `intelalloc-image` 文件夹放到：

Windows 的 Codex：

```text
C:\Users\<用户名>\.codex\skills\intelalloc-image
```

macOS 的 Codex：

```text
~/.codex/skills/intelalloc-image
```

Linux 的 Codex：

```text
~/.codex/skills/intelalloc-image
```

Windows WorkBuddy：

```text
C:\Users\<用户名>\.workbuddy-ai\skills\intelalloc-image
```

macOS WorkBuddy：

```text
~/.workbuddy-ai/skills/intelalloc-image
```

安装后重启或刷新 Codex 或 WorkBuddy。

## 帮助

直接对 Codex 或 WorkBuddy 说“IntelAlloc 图片帮助”，或自然地询问“可以生成和修改哪些图片”“默认质量是多少”“图片会保存到哪里”。普通回复会用中文说明生成、改图、参考图、批量处理、尺寸质量和保存位置，不要求用户记忆命令，也不会展示内部路径或密钥配置命令。

未指定保存位置时，图片会自动保存到系统图片目录下按宿主区分的 `IntelAlloc` 子目录；也可以直接说“保存到某个文件”或“保存到某个目录”。系统会先尝试使用符合条件的 GPT 系列模型凭据，无法自动使用时再请用户提供 IntelAlloc GPT 系列 API key。

每个会话首张图片成功后，宿主只提示一次当前模型、尺寸和质量。例如：

```text
模型：GPT Image 2.5 Flare；尺寸：`auto`；质量：`auto`。
如需查看完整配置，请直接输入 `help`，系统会列出全部详细尺寸、完整质量列表，以及可选模型和各自特点。
```

同一会话后续成功图片不再重复提示。需要完整配置时，直接输入 `help`，即可查看全部详细尺寸、完整质量列表和可选模型特点。

下面的 Windows 示例使用 `D:\` 路径；在 macOS 或 Linux 中请改用 `~/Pictures/IntelAlloc/Codex` 或 `/path/to/input.png` 这样的 POSIX 路径。

开发者或排障场景仍可使用随技能附带的只读帮助命令查看技术细节；这些命令不属于普通客户的使用方式。

## API key 配置

安装后无需初始化。本地还没有 key 时，第一次正式生图会检查当前宿主和模型。只有确认是 GPT 系列模型时才自动读取宿主凭据并保存到本地；否则请提供 IntelAlloc GPT 系列模型的 API key：

```text
配置 IntelAlloc API key：你的 key
```

只有 skill 尚未配置 key 时，Codex 才会在确认宿主和 GPT 模型后读取 `~/.codex/auth.json` 的 `OPENAI_API_KEY`；Codex 可以通过会话环境或 `~/.codex/config.toml` 自动识别宿主和模型，也可以显式传入运行时参数。WorkBuddy 每次调用都必须注入 `INTELALLOC_RUNTIME_HOST=workbuddy`，图片请求还必须注入 `INTELALLOC_RUNTIME_MODEL=<当前模型 ID>`。skill 会在 `~/.workbuddy-ai/models.json` 中匹配并保存对应 `apiKey`。保存后始终使用该 key，切换模型不会替换；只有手动配置新 key 才会覆盖，且不会修改宿主凭据文件。WorkBuddy 的 `configure`、`show-config`、`last` 和 `history` 也必须带宿主标记。

## 生图

未指定保存路径时，Codex 会保存到 `~/Pictures/IntelAlloc/Codex`，WorkBuddy 会保存到 `~/Pictures/IntelAlloc/WorkBuddy`；批量编辑会在对应目录中创建唯一批次目录。请求成功后会展示图片和指向完整实际保存目录的可点击链接。用户提供文件路径或目录时，始终使用客户提供的路径。

```text
用 IntelAlloc 生成一张未来城市夜景，输出到 D:\out\city.png
```

```text
用 IntelAlloc 生成一张产品海报，输出到 D:\out\poster.png
```

## 改图

指定本地图片路径：

```text
用 IntelAlloc 把 D:\images\source.png 改成水彩风，输出到 D:\out\watercolor.png
```

也可以直接把图片文件拖进 Codex 或 WorkBuddy，然后说：

```text
把我刚拖进来的图片改成日系动画风格，输出到 D:\out\anime.png
```

如果当前宿主能拿到拖入图片的本地可读路径，就会直接使用这张图。如果拖入图片没有可读取路径，当前宿主会要求你补充本地文件路径。

## 拖入图片和上张图联动

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

## 目录参考图

把一个目录里的图片作为参考，生成一张结果图：

```text
读取 D:\refs 里的图片作为参考，生成一张产品海报，输出到 D:\out\poster.png
```

默认只读取目录当前层级的 `.png`、`.jpg`、`.jpeg`、`.webp`。如果要包含子目录，需要明确说明。

## 批量编辑

把目录里的每张图片分别编辑成独立输出：

```text
批量把 D:\source 里的图片改成像素风，输出到 D:\out
```

## 图片模型

默认模型是面向日常快速生成的 `gpt-image-2.5-flare`。需要更高生成和编辑质量时，可以明确要求切换到 `gpt-image-2.5-sunburst`；也可以明确选择 `gpt-image-2` 作为兼容备选。只有这三个模型可保存为默认模型；模型切换后会保存为当前宿主后续请求的默认模型，直到再次更改。

## 尺寸和质量

默认尺寸和默认质量均为 `auto`。

每次请求都会显示当前使用的模型、尺寸、质量、开始时间、结束时间和耗时。默认值不会改变，除非明确要求修改。

尺寸可使用 `auto`、常用预设或合法的 `WIDTHxHEIGHT`：宽高不超过 3840、均为 16 的倍数、比例不超过 3:1、总像素为 655,360 至 8,294,400。常用预设为：`1536x1024`（横图 / Landscape）、`1024x1536`（竖图 / Portrait）、`1024x1024`（方图 / Square）、`2048x1152`（高清横图 / HD Landscape）、`1152x2048`（高清竖图 / HD Portrait）、`2048x2048`（高清方图 / HD Square）、`3840x2160`（4K 横图 / 4K Landscape）、`2160x3840`（4K 竖图 / 4K Portrait）。质量可选 `auto`、`low`、`medium`、`high`、`xhigh`、`max`。

GPT Image 2 仅支持 `auto`、`low`、`medium`、`high`；`xhigh` 和 `max` 会在发送接口请求前被拒绝。

模型特点：GPT Image 2（兼容备选，不支持 `xhigh` 和 `max`）；GPT Image 2.5 Flare（速度快，适合日常生成）；GPT Image 2.5 Sunburst（面向更高质量生成与编辑）。

如果只想这一次改变尺寸或质量，可以直接说：

```text
用 IntelAlloc 生成一张 3840x2160 的海报，质量 high，输出到 D:\out\poster.png
```

如果想修改以后所有请求的默认尺寸或质量，可以说：

```text
把 IntelAlloc 默认尺寸改成 auto，默认质量改成 high
```

macOS 和 Linux 路径示例：

```text
用 IntelAlloc 生成一张产品海报，输出到 /path/to/poster.png
用 IntelAlloc 把 /path/to/source.png 改成水彩风，输出到 /path/to/watercolor.png
读取 /path/to/refs 里的图片作为参考，生成一张产品海报，输出到 /path/to/poster.png
批量把 /path/to/source 里的图片改成像素风，输出到 /path/to/out
```

## 常见问题

- 缺 API key：重新说 `配置 IntelAlloc API key：你的 key`。
- 宿主未知、模型未知或不是 GPT 系列：请提供 IntelAlloc GPT 系列模型的 API key；可运行 `show-config` 查看检测结果。
- 拖入图片不可读：提供图片的本地文件路径。
- 上张图不存在：重新指定输入图片，或先生成一张新图。
- HTTP 502：后端或上游服务暂时不可用，稍后重试。
- Cloudflare 1010 / 403：运行 `show-config` 确认自动生成的 User-Agent 后重试；如果仍失败，需要后端放行该 API 客户端。
- 参考图超过 16 张：缩小图片范围，或明确让当前宿主只取 16 张。

请求失败时，当前宿主会先显示失败原因，再提醒你重试或稍后再试，不会继续做其它图片操作。

## 安全和跨设备

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
