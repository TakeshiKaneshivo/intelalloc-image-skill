[English](README.md) ·
[简体中文](README.zh-CN.md) ·
[繁體中文](README.zh-TW.md)

# IntelAlloc Image Skill

本 skill 是 IntelAlloc 平臺專用的 Codex 與 WorkBuddy 生圖/改圖工具，用於讓 GPT 在 Codex 或 WorkBuddy 會話中穩定調用 IntelAlloc 的 image-2 模型，完成文本生圖、圖片編輯、參考圖編輯與連續追改等工作流。

IntelAlloc 平臺註冊連結：[https://backend.intelalloc.com/register?promo=JINGGE](https://backend.intelalloc.com/register?promo=JINGGE)

需要註冊邀請碼可以聯繫：takeshikaneshivo@gmail.com

這個 skill 給 Codex 與 WorkBuddy 用戶使用。安裝後，你不需要記 CLI 命令，直接用自然語言告訴 Codex 或 WorkBuddy 生成什麼圖、改哪張圖、輸出到哪裡即可。普通回覆會跟隨請求語言：英文請求使用英文，中文請求使用中文；混合語言請求按主要語言回覆。兩個宿主可以分別安裝 skill，並獨立保存各自的配置、歷史與預設輸出位置。

![IntelAlloc Codex 與 WorkBuddy 圖片工作流示範 1](docs/images/intelalloc-demo-1.png)

![IntelAlloc Codex 與 WorkBuddy 圖片工作流示範 2](docs/images/intelalloc-demo-2.png)

## 安裝

手動安裝時，下載：

```text
releases/intelalloc-image-release.zip
```

解壓後，再解壓裡面的 `intelalloc-image.zip`，把得到的 `intelalloc-image` 資料夾放到：

Windows 的 Codex：

```text
C:\Users\<用戶名>\.codex\skills\intelalloc-image
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
C:\Users\<用戶名>\.workbuddy-ai\skills\intelalloc-image
```

macOS WorkBuddy：

```text
~/.workbuddy-ai/skills/intelalloc-image
```

安裝後重啟或刷新 Codex 或 WorkBuddy。

## 幫助

直接對 Codex 或 WorkBuddy 說“IntelAlloc 圖片幫助”，或自然地詢問“可以生成與修改哪些圖片”“預設品質是多少”“圖片會保存到哪裡”。普通回覆會用中文說明生成、改圖、參考圖、批次處理、尺寸品質與保存位置，不要求用戶記憶命令，也不會展示內部路徑或密鑰配置命令。

未指定保存位置時，圖片會自動保存到系統圖片目錄下按宿主區分的 `IntelAlloc` 子目錄；也可以直接說“保存到某個檔案”或“保存到某個目錄”。系統會先嘗試使用符合條件的 GPT 系列模型憑據，無法自動使用時再請用戶提供 IntelAlloc GPT 系列 API key。

每個工作階段首張圖片成功後，宿主只提示一次目前模型、尺寸與品質。例如：

```text
模型：GPT Image 2.5 Flare；尺寸：`auto`；品質：`auto`。
如需查看完整配置，請直接輸入 `help`，系統會列出全部詳細尺寸、完整品質列表，以及可選模型和各自特點。
```

同一工作階段後續成功圖片不再重複提示。需要完整配置時，直接輸入 `help`，即可查看全部詳細尺寸、完整品質列表和可選模型特點。

下面的 Windows 範例使用 `D:\` 路徑；在 macOS 或 Linux 中請改用 `~/Pictures/IntelAlloc/Codex` 或 `/path/to/input.png` 這樣的 POSIX 路徑。

開發者或排障情境仍可使用隨技能附帶的只讀幫助命令查看技術細節；這些命令不屬於普通客戶的使用方式。

## API key 配置

安裝後無需初始化。本地還沒有 key 時，第一次正式生圖會檢查目前宿主與模型。只有確認是 GPT 系列模型時才自動讀取宿主憑據並保存到本地；否則請提供 IntelAlloc GPT 系列模型的 API key：

```text
配置 IntelAlloc API key：你的 key
```

只有 skill 尚未配置 key 時，Codex 才會在確認宿主與 GPT 模型後讀取 `~/.codex/auth.json` 的 `OPENAI_API_KEY`；Codex 可以通過會話環境或 `~/.codex/config.toml` 自動識別宿主與模型，也可以顯式傳入執行時參數。WorkBuddy 每次調用都必須注入 `INTELALLOC_RUNTIME_HOST=workbuddy`，圖片請求還必須注入 `INTELALLOC_RUNTIME_MODEL=<目前模型 ID>`。skill 會在 `~/.workbuddy-ai/models.json` 中匹配並保存對應 `apiKey`。保存後始終使用該 key，切換模型不會替換；只有手動配置新 key 才會覆蓋，且不會修改宿主憑據檔案。WorkBuddy 的 `configure`、`show-config`、`last` 與 `history` 也必須帶宿主標記。

## 生圖

未指定保存路徑時，Codex 會保存到 `~/Pictures/IntelAlloc/Codex`，WorkBuddy 會保存到 `~/Pictures/IntelAlloc/WorkBuddy`；批次編輯會在對應目錄中創建唯一批次目錄。請求成功後會展示圖片與指向完整實際保存目錄的可點擊連結。用戶提供檔案路徑或目錄時，始終使用客戶提供的路徑。

```text
用 IntelAlloc 生成一張未來城市夜景，輸出到 D:\out\city.png
```

```text
用 IntelAlloc 生成一張產品海報，輸出到 D:\out\poster.png
```

## 改圖

指定本地圖片路徑：

```text
用 IntelAlloc 把 D:\images\source.png 改成水彩風，輸出到 D:\out\watercolor.png
```

也可以直接把圖片檔案拖入 Codex 或 WorkBuddy，然後說：

```text
把我剛拖入來的圖片改成日系動畫風格，輸出到 D:\out\anime.png
```

如果目前宿主能取得拖入圖片的本地可讀路徑，就會直接使用這張圖。如果拖入圖片沒有可讀取路徑，目前宿主會要求你補充本地檔案路徑。

## 拖入圖片與上張圖聯動

如果你剛生成或編輯過一張圖，可以把新圖片拖入 Codex 或 WorkBuddy，並讓它與上張輸出圖一起參與編輯。

把拖入圖片內容新增到上一張輸出圖裡：

```text
把我剛拖入來的圖片內容新增到上張輸出圖裡，保持整體風格一致，輸出到 D:\out\result.png
```

把拖入圖片作為參考圖，修改上一張輸出圖：

```text
把我剛拖入來的圖片作為參考，基於上張圖改成相同風格，輸出到 D:\out\result.png
```

這裡的“上張圖 / 上張輸出圖”指同一臺裝置上最近一次成功生成或編輯保存的圖片。如果檔案被刪除，或是更換了裝置，需要重新指定圖片路徑。

## 目錄參考圖

把一個目錄裡的圖片作為參考，生成一張結果圖：

```text
讀取 D:\refs 裡的圖片作為參考，生成一張產品海報，輸出到 D:\out\poster.png
```

預設只讀取目錄目前層級的 `.png`、`.jpg`、`.jpeg`、`.webp`。如果要包含子目錄，需要明確說明。

## 批次編輯

把目錄裡的每張圖片分別編輯成獨立輸出：

```text
批次把 D:\source 裡的圖片改成像素風，輸出到 D:\out
```

## 圖片模型

預設模型是面向日常快速生成的 `gpt-image-2.5-flare`。需要更高生成和編輯品質時，可以明確要求切換到 `gpt-image-2.5-sunburst`；也可以明確選擇 `gpt-image-2` 作為相容備選。只有這三個模型可儲存為預設模型；模型切換後會保存為目前宿主後續請求的預設模型，直到再次更改。

## 尺寸與品質

預設尺寸和預設品質均為 `auto`。

每次請求都會顯示目前使用的模型、尺寸、品質、開始時間、結束時間與耗時。預設值不會改變，除非明確要求修改。

尺寸可使用 `auto`、常用預設或合法的 `WIDTHxHEIGHT`：寬高不超過 3840、均為 16 的倍數、比例不超過 3:1、總像素為 655,360 至 8,294,400。常用預設為：`1536x1024`（橫圖 / Landscape）、`1024x1536`（豎圖 / Portrait）、`1024x1024`（方圖 / Square）、`2048x1152`（高清橫圖 / HD Landscape）、`1152x2048`（高清豎圖 / HD Portrait）、`2048x2048`（高清方圖 / HD Square）、`3840x2160`（4K 橫圖 / 4K Landscape）、`2160x3840`（4K 豎圖 / 4K Portrait）。品質可選 `auto`、`low`、`medium`、`high`、`xhigh`、`max`。

GPT Image 2 僅支援 `auto`、`low`、`medium`、`high`；`xhigh` 和 `max` 會在傳送 API 請求前被拒絕。

模型特點：GPT Image 2（相容備選，不支援 `xhigh` 和 `max`）；GPT Image 2.5 Flare（速度快，適合日常生成）；GPT Image 2.5 Sunburst（面向更高品質生成與編輯）。

如果只想這一次變更尺寸或品質，可以直接說：

```text
用 IntelAlloc 生成一張 3840x2160 的海報，品質 high，輸出到 D:\out\poster.png
```

如果想修改之後所有請求的預設尺寸或品質，可以說：

```text
把 IntelAlloc 預設尺寸改成 auto，預設品質改成 high
```

macOS 與 Linux 路徑範例：

```text
用 IntelAlloc 生成一張產品海報，輸出到 /path/to/poster.png
用 IntelAlloc 把 /path/to/source.png 改成水彩風，輸出到 /path/to/watercolor.png
讀取 /path/to/refs 裡的圖片作為參考，生成一張產品海報，輸出到 /path/to/poster.png
批次把 /path/to/source 裡的圖片改成像素風，輸出到 /path/to/out
```

## 常見問題

- 缺少 API key：重新說 `配置 IntelAlloc API key：你的 key`。
- 宿主未知、模型未知或不是 GPT 系列：請提供 IntelAlloc GPT 系列模型的 API key；可執行 `show-config` 查看偵測結果。
- 拖入圖片無法讀取：提供圖片的本地檔案路徑。
- 上張圖不存在：重新指定輸入圖片，或先生成一張新圖。
- HTTP 502：後端或上游服務暫時不可用，稍後重試。
- Cloudflare 1010 / 403：執行 `show-config` 確認自動生成的 User-Agent 後重試；如果仍失敗，需要後端放行該 API 客戶端。
- 參考圖超過 16 張：縮小圖片範圍，或明確讓目前宿主只取 16 張。

請求失敗時，目前宿主會先顯示失敗原因，再提醒你重試或稍後再試，不會繼續做其他圖片操作。

## 安全與跨裝置

不要分享：

```text
~/.codex/intelalloc-image/config.json
~/.workbuddy-ai/intelalloc-image/config.json
~/.codex/auth.json
~/.workbuddy-ai/models.json
~/.codex/intelalloc-image/history.json
~/.workbuddy-ai/intelalloc-image/history.json
API key
生成的圖片
暫存檔
```

歷史記錄與“上張圖”只在目前裝置可靠，更換裝置後不會自動同步。
