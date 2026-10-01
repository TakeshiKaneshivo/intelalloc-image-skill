#!/usr/bin/env python3
"""IntelAlloc image generation/editing CLI for the Codex skill."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as _dt
import json
import mimetypes
import os
import pathlib
import platform
import random
import re
import ssl
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_GENERATIONS_ENDPOINT = "https://backend.intelalloc.com/v1/images/generations"
DEFAULT_EDITS_ENDPOINT = "https://backend.intelalloc.com/v1/images/edits"
DEFAULT_MODEL = "gpt-image-2.5-flare"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "auto"
DEFAULT_PARTIAL_IMAGES = 3
DEFAULT_BACKGROUND = "auto"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_N = 1
DEFAULT_EDIT_PROTOCOL = "json"
SUPPORTED_ENDPOINT_SCHEMES = {"http", "https"}
SUPPORTED_EDIT_PROTOCOLS = {"json", "multipart"}
CODEX_CLI_VERSION = "0.77.0"
MIN_OUTPUT_IMAGES = 1
MAX_OUTPUT_IMAGES = 10
SUPPORTED_PARTIAL_IMAGE_COUNTS = set(range(0, 4))
SUPPORTED_BACKGROUNDS = {"auto", "opaque", "transparent"}
SUPPORTED_OUTPUT_FORMATS = {"png", "jpeg", "webp"}
MAX_INPUT_IMAGES = 16
MAX_RETRY_COUNT = 2
REQUEST_TIMEOUT_SECONDS = 60 * 60
HISTORY_LIMIT = 100
UPLOAD_OPTIMIZE_MAX_EDGE = 2048
UPLOAD_OPTIMIZE_JPEG_QUALITY = 85
UPLOAD_OPTIMIZE_MIN_BYTES = 512 * 1024

COMMON_SIZES = {
    "1536x1024",
    "1024x1536",
    "1024x1024",
    "2048x1152",
    "1152x2048",
    "2048x2048",
    "3840x2160",
    "2160x3840",
}
COMMON_SIZE_LABELS = (
    ("1536x1024", "横图", "Landscape"),
    ("1024x1536", "竖图", "Portrait"),
    ("1024x1024", "方图", "Square"),
    ("2048x1152", "高清横图", "HD Landscape"),
    ("1152x2048", "高清竖图", "HD Portrait"),
    ("2048x2048", "高清方图", "HD Square"),
    ("3840x2160", "4K 横图", "4K Landscape"),
    ("2160x3840", "4K 竖图", "4K Portrait"),
)
SUPPORTED_QUALITIES = {"auto", "low", "medium", "high", "xhigh", "max"}
PERSISTENT_MODELS = {
    "gpt-image-2.5-flare",
    "gpt-image-2.5-sunburst",
    "gpt-image-2",
}
GPT_IMAGE_2_MODEL = "gpt-image-2"
GPT_IMAGE_2_UNSUPPORTED_QUALITIES = {"xhigh", "max"}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_EDGE = 3840
MIN_IMAGE_PIXELS = 655_360
MAX_IMAGE_PIXELS = 8_294_400
MAX_IMAGE_ASPECT_RATIO = 3
GPT_IMAGE_2_5_MIGRATION_VERSION = 1
MODEL_MIGRATION_KEY = "gpt_image_2_5_model_migration"
SIZE_MIGRATION_KEY = "gpt_image_2_5_size_migration"
QUALITY_MIGRATION_KEY = "gpt_image_2_5_quality_migration"

HELP_TEXT = """IntelAlloc Image Help / IntelAlloc 图片帮助

Generate and edit / 生图与改图:
  generate --prompt \"...\"             Generate one image / 生成单张图片
  edit --prompt \"...\" --input <file> Edit an image / 编辑图片
  batch-edit --prompt \"...\" --input-dir <dir>
                                      Edit a directory / 批量编辑目录

Size / 分辨率:
  Request override: --size <size>      One request only / 仅当前请求
  Persistent default: configure --default-size <size>
                                      Save a default / 保存默认值
  Default / 默认值: {default_size}
  Supported / 支持: auto or WIDTHxHEIGHT / auto 或 WIDTHxHEIGHT
  Common presets / 常用预设:
{sizes}
  Custom limits / 自定义限制: each edge <= 3840, multiples of 16, ratio <= 3:1,
                         total pixels 655360-8294400

Quality / 质量:
  Request override: --quality auto|low|medium|high|xhigh|max
  Persistent default: configure --default-quality <quality>
  Default / 默认值: {default_quality}
  Supported / 支持: {qualities}
  GPT Image 2: auto|low|medium|high only / 仅支持 auto|low|medium|high

Streaming previews / 中间预览:
  Request override: --partial-images 0|1|2|3 / 仅当前请求
  Persistent default: configure --default-partial-images <count>
  Default / 默认值: {partial_images}

Background / 背景:
  Request override: --background auto|opaque|transparent / 仅当前请求
  Persistent default: configure --default-background <value>
  Default / 默认值: {background}

Output format / 输出格式:
  Request override: --output-format png|jpeg|webp / 仅当前请求
  Persistent default: configure --default-output-format <format>
  Default / 默认值: {output_format}

Final image count / 最终图片数量:
  Request override: --n <count> / 仅当前请求
  Persistent default: configure --default-n <count>
  Default / 默认值: {n}
  Supported / 支持: {min_n}-{max_n}; all returned images are saved / 全部返回图片都会保存

Edit protocol / 编辑协议:
  Default / 默认值: {edit_protocol}
  Request override: --edit-protocol json|multipart / 仅当前请求
  Persistent default: configure --edit-protocol json|multipart / 保存默认值
  JSON uses images[].image_url; multipart uses image[] / JSON 使用 images[].image_url；multipart 使用 image[]

Models / 模型:
  GPT Image 2: compatibility fallback; no xhigh or max / 兼容备选；不支持 xhigh 或 max
  GPT Image 2.5 Flare: fast, for everyday generation / 速度快，适合日常生成
  GPT Image 2.5 Sunburst: higher-quality generation and editing / 面向更高质量生成与编辑

API key / API key:
  Automatic credentials are checked for eligible Codex or WorkBuddy GPT runtimes.
  符合条件的 Codex 或 WorkBuddy GPT 运行环境会自动读取凭据。
  Manual setup: configure --api-key \"<your IntelAlloc GPT key>\"
  手动设置：configure --api-key \"<你的 IntelAlloc GPT key>\"

Output / 保存:
  Codex: saves under ~/Pictures/IntelAlloc/Codex
  WorkBuddy: saves under ~/Pictures/IntelAlloc/WorkBuddy
  Unknown host: keeps ~/Pictures/IntelAlloc
  Codex：保存到 ~/Pictures/IntelAlloc/Codex
  WorkBuddy：保存到 ~/Pictures/IntelAlloc/WorkBuddy
  未知宿主：保留 ~/Pictures/IntelAlloc
  --output <file>       Save to a file; extension follows the format / 保存到指定文件；扩展名跟随格式
  --output-dir <dir>    Save in a directory / 保存到指定目录

Diagnostics / 诊断:
  show-config            Show settings with a masked key / 查看脱敏配置
  last                   Show the latest output / 查看最近图片
""".format(
    default_size=DEFAULT_SIZE,
    sizes="\n".join(
        "    {0} - {1} / {2}".format(size, zh_label, en_label)
        for size, zh_label, en_label in COMMON_SIZE_LABELS
    ),
    default_quality=DEFAULT_QUALITY,
    partial_images=DEFAULT_PARTIAL_IMAGES,
    background=DEFAULT_BACKGROUND,
    output_format=DEFAULT_OUTPUT_FORMAT,
    n=DEFAULT_N,
    min_n=MIN_OUTPUT_IMAGES,
    max_n=MAX_OUTPUT_IMAGES,
    edit_protocol=DEFAULT_EDIT_PROTOCOL,
    qualities=", ".join(sorted(SUPPORTED_QUALITIES)),
)


@dataclasses.dataclass
class UploadImage:
    source_path: pathlib.Path
    upload_path: pathlib.Path
    filename: str
    content_type: str
    optimized: bool
    original_bytes: int
    upload_bytes: int
    cleanup: bool = False


def normalized_arch(machine: Optional[str] = None) -> str:
    value = (machine or platform.machine() or "").lower()
    if value in {"amd64", "x86_64"}:
        return "x86_64"
    if value in {"arm64", "aarch64"}:
        return "arm64"
    return value or "unknown"


def collect_platform_info() -> Dict[str, str]:
    return {
        "system": platform.system() or "",
        "release": platform.release() or "",
        "version": platform.version() or "",
        "machine": platform.machine() or "",
        "python": sys.version.split()[0],
    }


def build_default_user_agent(info: Optional[Dict[str, str]] = None) -> str:
    info = info or collect_platform_info()
    system = info.get("system") or platform.system() or "Unknown"
    release = info.get("release") or platform.release() or ""
    version = info.get("version") or platform.version() or ""
    arch = normalized_arch(info.get("machine"))
    if system == "Windows":
        os_label = "Windows " + (version or release or "unknown")
        terminal = "WindowsTerminal"
    elif system == "Darwin":
        os_label = "macOS " + (release or version or "unknown")
        terminal = "Terminal"
    elif system == "Linux":
        os_label = "Linux " + (release or version or "unknown")
        terminal = "Terminal"
    else:
        os_label = system + ((" " + (release or version)) if (release or version) else "")
        terminal = "Terminal"
    return "codex_cli_rs/{0} ({1}; {2}) {3}".format(CODEX_CLI_VERSION, os_label, arch, terminal)


class CliError(Exception):
    """Expected user-facing CLI error."""


class ApiResponseError(Exception):
    """API response error whose body should be shown to the user verbatim."""

    def __init__(self, body: str, status: Optional[int] = None):
        super().__init__(body)
        self.body = body
        self.status = status


def storage_host_name(runtime_host: str) -> str:
    """Map a recognized host to its state directory; keep legacy state for unknown hosts."""
    return "workbuddy" if str(runtime_host).strip().lower() == "workbuddy" else "codex"


def config_dir(runtime_host: str = "unknown") -> pathlib.Path:
    host = storage_host_name(runtime_host)
    base = ".workbuddy-ai" if host == "workbuddy" else ".codex"
    return pathlib.Path.home() / base / "intelalloc-image"


def config_path(runtime_host: str = "unknown") -> pathlib.Path:
    return config_dir(runtime_host) / "config.json"


def auth_path() -> pathlib.Path:
    return pathlib.Path.home() / ".codex" / "auth.json"


def codex_config_path() -> pathlib.Path:
    return pathlib.Path.home() / ".codex" / "config.toml"


def workbuddy_models_path() -> pathlib.Path:
    return pathlib.Path.home() / ".workbuddy-ai" / "models.json"


def history_path(runtime_host: str = "unknown") -> pathlib.Path:
    return config_dir(runtime_host) / "history.json"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def monotonic_seconds() -> float:
    return time.perf_counter()


def load_json(path: pathlib.Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def save_json_private(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_config(runtime_host: str = "unknown") -> Dict[str, Any]:
    cfg = load_json(config_path(runtime_host), {})
    if not isinstance(cfg, dict):
        return {}
    return cfg


def string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


AUTOMATIC_KEY_SOURCES = {"codex-auth", "codex-config", "workbuddy-model"}


def stored_api_key_origin(cfg: Dict[str, Any]) -> str:
    if not string_value(cfg.get("api_key")):
        return ""
    origin = string_value(cfg.get("api_key_origin"))
    return origin or "manual"


def stored_automatic_key_matches_runtime(cfg: Dict[str, Any], runtime: Dict[str, str]) -> bool:
    """Only reuse an automatically saved key for the exact runtime that produced it."""
    if stored_api_key_origin(cfg) not in AUTOMATIC_KEY_SOURCES:
        return False
    stored_host = normalized_runtime_host(cfg.get("api_key_runtime_host"))
    stored_model = normalized_model_id(string_value(cfg.get("api_key_runtime_model")))
    return bool(
        stored_host
        and stored_model
        and stored_host == runtime.get("host")
        and stored_model == normalized_model_id(runtime.get("model", ""))
    )


def save_automatic_api_key(cfg: Dict[str, Any], automatic: Dict[str, str]) -> None:
    """Persist the first eligible host credential as the skill's local key."""
    cfg["api_key"] = automatic["api_key"]
    cfg["api_key_origin"] = automatic["source"]
    cfg["api_key_runtime_host"] = automatic["host"]
    cfg["api_key_runtime_model"] = automatic["model"]
    cfg["api_key_saved_at"] = now_iso()
    save_json_private(config_path(automatic["host"]), cfg)


def load_codex_auth_api_key() -> str:
    auth = load_json(auth_path(), {})
    if not isinstance(auth, dict):
        return ""
    return string_value(auth.get("OPENAI_API_KEY"))


def load_codex_config_string(key: str) -> str:
    """Read one quoted root-level Codex TOML string."""
    path = codex_config_path()
    if not path.exists():
        return ""
    pattern = re.compile(
        r"^\s*{0}\s*=\s*(?:\"([^\"]*)\"|'([^']*)')(?:\s*#.*)?$".format(re.escape(key))
    )
    try:
        section = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            table = re.fullmatch(r"\[([^\[\]\r\n]+)\]\s*(?:#.*)?", stripped)
            if table:
                section = table.group(1).strip()
                continue
            if stripped.startswith("["):
                return ""
            if section:
                continue
            match = pattern.match(line)
            if match:
                return string_value(match.group(1) if match.group(1) is not None else match.group(2))
    except (OSError, UnicodeError):
        pass
    return ""


def load_codex_config_bearer_token() -> str:
    """Read the first non-empty quoted bearer token from the whole Codex TOML file."""
    path = codex_config_path()
    if not path.exists():
        return ""
    pattern = re.compile(
        r"^\s*experimental_bearer_token\s*=\s*(?:\"([^\"]*)\"|'([^']*)')(?:\s*#.*)?$"
    )
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            value = string_value(match.group(1) if match.group(1) is not None else match.group(2))
            if value:
                return value
    except (OSError, UnicodeError):
        pass
    return ""


def load_codex_config_model() -> str:
    return load_codex_config_string("model")


def normalized_model_id(value: str) -> str:
    value = value.strip().lower()
    for separator in (":", "/"):
        if separator in value:
            value = value.rsplit(separator, 1)[-1]
    return value


def is_gpt_model(value: str) -> bool:
    model = normalized_model_id(value)
    return model == "gpt" or model.startswith("gpt-")


def normalized_runtime_host(value: Any) -> str:
    value = string_value(value).lower()
    return value if value in {"codex", "workbuddy"} else ""


def resolve_runtime_context(args: argparse.Namespace) -> Dict[str, str]:
    explicit_host = getattr(args, "runtime_host", None) or os.environ.get("INTELALLOC_RUNTIME_HOST")
    host = normalized_runtime_host(explicit_host)
    if explicit_host:
        host_source = "cli" if getattr(args, "runtime_host", None) else "environment"
        if not host:
            host_source = "invalid"
    elif os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_THREAD_ID"):
        host = "codex"
        host_source = "codex-environment"
    elif (
        os.environ.get("WORKBUDDY_SESSION_ID")
        or os.environ.get("WORKBUDDY_MODEL")
        or os.environ.get("WORKBUDDY_CURRENT_MODEL")
        or os.environ.get("CODEBUDDY_SESSION_ID")
        or os.environ.get("CODEBUDDY_MODEL")
        or os.environ.get("CODEBUDDY_CURRENT_MODEL")
    ):
        host = "workbuddy"
        host_source = "workbuddy-environment"
    else:
        host_source = "none"

    runtime_model = getattr(args, "runtime_model", None)
    model_source = "cli" if runtime_model else ""
    if not runtime_model:
        runtime_model = os.environ.get("INTELALLOC_RUNTIME_MODEL")
        model_source = "environment" if runtime_model else ""
    if not runtime_model and host == "codex":
        runtime_model = os.environ.get("CODEX_MODEL") or os.environ.get("CODEX_CURRENT_MODEL")
        model_source = "codex-environment" if runtime_model else ""
    if not runtime_model and host == "workbuddy":
        runtime_model = (
            os.environ.get("WORKBUDDY_MODEL")
            or os.environ.get("WORKBUDDY_CURRENT_MODEL")
            or os.environ.get("CODEBUDDY_MODEL")
            or os.environ.get("CODEBUDDY_CURRENT_MODEL")
        )
        model_source = "workbuddy-environment" if runtime_model else ""
    if not runtime_model and host == "codex":
        runtime_model = load_codex_config_model()
        model_source = "codex-config" if runtime_model else ""
    runtime_model = string_value(runtime_model)
    if not model_source:
        model_source = "none"
    return {
        "host": host or "unknown",
        "host_source": host_source,
        "model": runtime_model,
        "model_source": model_source,
        "model_is_gpt": "true" if is_gpt_model(runtime_model) else "false",
    }


def load_workbuddy_model_api_key(runtime_model: str) -> Tuple[str, str]:
    models = load_json(workbuddy_models_path(), [])
    if not isinstance(models, list):
        return "", "models-invalid"
    expected = normalized_model_id(runtime_model)
    for item in models:
        if not isinstance(item, dict):
            continue
        identifiers = (string_value(item.get("id")), string_value(item.get("name")))
        if any(normalized_model_id(identifier) == expected for identifier in identifiers if identifier):
            key = string_value(item.get("apiKey"))
            return key, "model-matched" if key else "model-key-missing"
    return "", "model-not-found"


def resolve_automatic_api_key(
    args: argparse.Namespace, runtime: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    runtime = runtime or resolve_runtime_context(args)
    result = dict(runtime)
    result.update({"api_key": "", "source": "none", "reason": "", "match": "not-checked"})
    if runtime["host"] == "unknown":
        result["reason"] = "runtime-host-unknown"
        return result
    if not runtime["model"]:
        result["reason"] = "runtime-model-unknown"
        return result
    if runtime["model_is_gpt"] != "true":
        result["reason"] = "runtime-model-not-gpt"
        return result
    if runtime["host"] == "codex":
        auth_key = load_codex_auth_api_key()
        if auth_key:
            result["api_key"] = auth_key
            result["source"] = "codex-auth"
            result["match"] = "auth-file"
            result["reason"] = "key-available"
            return result
        result["api_key"] = load_codex_config_bearer_token()
        result["source"] = "codex-config"
        result["match"] = "config-file" if result["api_key"] else "config-key-missing"
        result["reason"] = "key-available" if result["api_key"] else "codex-config-key-missing"
        return result
    key, match_reason = load_workbuddy_model_api_key(runtime["model"])
    result["api_key"] = key
    result["source"] = "workbuddy-model"
    result["match"] = match_reason
    result["reason"] = "key-available" if key else match_reason
    return result


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return value[:2] + "***"
    return value[:4] + "..." + value[-4:]


def normalize_size(value: Optional[str]) -> str:
    value = (value or DEFAULT_SIZE).strip()
    if value == "auto":
        return value
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", value)
    if not match:
        raise CliError(
            "Unsupported size: {0}. Use auto or WIDTHxHEIGHT with positive integer dimensions.".format(value)
        )
    width, height = (int(match.group(1)), int(match.group(2)))
    if width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE:
        raise CliError("Unsupported size: {0}. Each edge must be at most {1}px.".format(value, MAX_IMAGE_EDGE))
    if width % 16 or height % 16:
        raise CliError("Unsupported size: {0}. Width and height must be multiples of 16px.".format(value))
    longer, shorter = max(width, height), min(width, height)
    if longer > shorter * MAX_IMAGE_ASPECT_RATIO:
        raise CliError("Unsupported size: {0}. The aspect ratio must not exceed 3:1.".format(value))
    pixels = width * height
    if not MIN_IMAGE_PIXELS <= pixels <= MAX_IMAGE_PIXELS:
        raise CliError(
            "Unsupported size: {0}. Total pixels must be between {1} and {2}.".format(
                value, MIN_IMAGE_PIXELS, MAX_IMAGE_PIXELS
            )
        )
    return "{0}x{1}".format(width, height)


def normalize_quality(value: Optional[str]) -> str:
    value = (value or DEFAULT_QUALITY).strip()
    if value not in SUPPORTED_QUALITIES:
        raise CliError(
            "Unsupported quality: {0}. Supported qualities: {1}".format(
                value, ", ".join(sorted(SUPPORTED_QUALITIES))
            )
        )
    return value


def normalize_endpoint(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise CliError("Invalid {0}: endpoint must be a plain http:// or https:// URL.".format(name))
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        value = value[1:-1].strip()
    markdown = re.fullmatch(r"\[([^\]\r\n]+)\]\((https?://[^()\s]+)\)", value)
    if markdown:
        value = markdown.group(2)
    if not value or "\\" in value or "`" in value or any(char.isspace() for char in value):
        raise CliError("Invalid {0}: endpoint must be a plain http:// or https:// URL.".format(name))
    try:
        parsed = urllib.parse.urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise CliError("Invalid {0}: endpoint must contain a valid hostname and port.".format(name)) from exc
    if parsed.scheme.lower() not in SUPPORTED_ENDPOINT_SCHEMES or not parsed.netloc or not hostname:
        raise CliError("Invalid {0}: endpoint must be a plain http:// or https:// URL with a hostname.".format(name))
    if parsed.username is not None or parsed.password is not None:
        raise CliError("Invalid {0}: endpoint must not contain embedded credentials.".format(name))
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise CliError("Invalid {0}: endpoint contains control characters.".format(name))
    if any(marker in value for marker in ("[", "]", "(", ")")):
        raise CliError("Invalid {0}: endpoint must not contain unresolved Markdown syntax.".format(name))
    return value


def normalize_configured_endpoints(cfg: Dict[str, Any]) -> bool:
    changed = False
    for key, label in (("endpoint", "generation endpoint"), ("edits_endpoint", "edit endpoint")):
        if key not in cfg:
            continue
        normalized = normalize_endpoint(cfg[key], label)
        if cfg[key] != normalized:
            cfg[key] = normalized
            changed = True
    return changed


def normalize_bounded_integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise CliError("Unsupported {0}: {1}. Use an integer from {2} to {3}.".format(name, value, minimum, maximum))
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise CliError("Unsupported {0}: {1}. Use an integer from {2} to {3}.".format(name, value, minimum, maximum)) from exc
    if number < minimum or number > maximum:
        raise CliError("Unsupported {0}: {1}. Use an integer from {2} to {3}.".format(name, number, minimum, maximum))
    return number


def normalize_partial_images(value: Any) -> int:
    return normalize_bounded_integer(value, "partial_images", min(SUPPORTED_PARTIAL_IMAGE_COUNTS), max(SUPPORTED_PARTIAL_IMAGE_COUNTS))


def normalize_n(value: Any) -> int:
    return normalize_bounded_integer(value, "n", MIN_OUTPUT_IMAGES, MAX_OUTPUT_IMAGES)


def normalize_background(value: Optional[str]) -> str:
    value = (value or DEFAULT_BACKGROUND).strip().lower()
    if value not in SUPPORTED_BACKGROUNDS:
        raise CliError(
            "Unsupported background: {0}. Supported backgrounds: {1}".format(
                value, ", ".join(sorted(SUPPORTED_BACKGROUNDS))
            )
        )
    return value


def normalize_output_format(value: Optional[str]) -> str:
    value = (value or DEFAULT_OUTPUT_FORMAT).strip().lower()
    if value not in SUPPORTED_OUTPUT_FORMATS:
        raise CliError(
            "Unsupported output format: {0}. Supported formats: {1}".format(
                value, ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
            )
        )
    return value


def validate_output_options(background: str, output_format: str) -> None:
    if background == "transparent" and output_format == "jpeg":
        raise CliError("Transparent background requires output format png or webp; jpeg is not supported.")


def normalize_edit_protocol(value: Optional[str]) -> str:
    value = (value or DEFAULT_EDIT_PROTOCOL).strip().lower()
    if value not in SUPPORTED_EDIT_PROTOCOLS:
        raise CliError(
            "Unsupported edit protocol: {0}. Supported protocols: {1}".format(
                value, ", ".join(sorted(SUPPORTED_EDIT_PROTOCOLS))
            )
        )
    return value


def normalize_persistent_model(value: Optional[str]) -> str:
    if value is None:
        value = DEFAULT_MODEL
    elif not isinstance(value, str):
        raise CliError(
            "Unsupported persistent model: {0}. Supported models: {1}".format(
                value, ", ".join(sorted(PERSISTENT_MODELS))
            )
        )
    else:
        value = value.strip() or DEFAULT_MODEL
    if value not in PERSISTENT_MODELS:
        raise CliError(
            "Unsupported persistent model: {0}. Supported models: {1}".format(
                value, ", ".join(sorted(PERSISTENT_MODELS))
            )
        )
    return value


def validate_model_quality(model: str, quality: str) -> None:
    if model == GPT_IMAGE_2_MODEL and quality in GPT_IMAGE_2_UNSUPPORTED_QUALITIES:
        raise CliError(
            "Unsupported quality for GPT Image 2: {0}. GPT Image 2 supports: auto, low, medium, high.".format(
                quality
            )
        )


def migration_complete(cfg: Dict[str, Any], key: str) -> bool:
    return cfg.get(key) == GPT_IMAGE_2_5_MIGRATION_VERSION


def migrate_gpt_image_2_5_defaults(cfg: Dict[str, Any], runtime_host: str) -> bool:
    """Migrate legacy built-in defaults once without overriding later explicit choices."""
    changed = False
    if not migration_complete(cfg, MODEL_MIGRATION_KEY):
        if string_value(cfg.get("model")) == "gpt-image-2":
            cfg["model"] = DEFAULT_MODEL
        cfg[MODEL_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
        changed = True
    if not migration_complete(cfg, SIZE_MIGRATION_KEY):
        if string_value(cfg.get("default_size")) == "2048x1152":
            cfg["default_size"] = DEFAULT_SIZE
        cfg[SIZE_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
        changed = True
    if not migration_complete(cfg, QUALITY_MIGRATION_KEY):
        if string_value(cfg.get("default_quality")) == "medium":
            cfg["default_quality"] = DEFAULT_QUALITY
        cfg[QUALITY_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
        changed = True
    if changed:
        save_json_private(config_path(runtime_host), cfg)
    return changed


def resolve_configured_value(
    args: argparse.Namespace, argument_name: str, cfg: Dict[str, Any], config_name: str, default: Any
) -> Any:
    value = getattr(args, argument_name, None)
    if value is not None:
        return value
    value = cfg.get(config_name)
    return default if value is None else value


def resolve_endpoint_value(
    args: argparse.Namespace, argument_name: str, cfg: Dict[str, Any], config_name: str, default: str, label: str
) -> str:
    override = getattr(args, argument_name, None)
    if override is not None:
        return normalize_endpoint(override, label)
    value = cfg.get(config_name, default)
    return normalize_endpoint(default if value is None else value, label)


def resolve_settings(args: argparse.Namespace, require_key: bool) -> Dict[str, Any]:
    runtime = resolve_runtime_context(args)
    cfg = load_config(runtime["host"])
    if normalize_configured_endpoints(cfg):
        save_json_private(config_path(runtime["host"]), cfg)
    if require_key:
        migrate_gpt_image_2_5_defaults(cfg, runtime["host"])
    configured_candidates = (
        getattr(args, "api_key", None),
        os.environ.get("INTELALLOC_API_KEY"),
        cfg.get("api_key"),
    )
    has_configured_key = any(string_value(candidate) for candidate in configured_candidates)
    if has_configured_key:
        automatic = dict(runtime)
        automatic.update(
            {
                "api_key": "",
                "source": "none",
                "reason": "configured-key-present",
                "match": "not-checked",
            }
        )
    else:
        automatic = resolve_automatic_api_key(args, runtime)
    stored_origin = stored_api_key_origin(cfg)
    stored_automatic_matches = stored_automatic_key_matches_runtime(cfg, automatic)
    configured_key = string_value(cfg.get("api_key"))
    candidates = (
        ("cli", getattr(args, "api_key", None)),
        ("environment", os.environ.get("INTELALLOC_API_KEY")),
        ("config", configured_key),
        (automatic["source"], automatic["api_key"]),
    )
    api_key = ""
    api_key_source = "none"
    for source, candidate in candidates:
        if candidate is None:
            continue
        candidate = candidate.strip() if isinstance(candidate, str) else str(candidate).strip()
        if candidate:
            api_key = candidate
            api_key_source = source
            break
    automatic_key_persisted = stored_origin in AUTOMATIC_KEY_SOURCES
    if require_key and api_key_source in AUTOMATIC_KEY_SOURCES:
        # Only an eligible host credential is adopted. CLI and environment keys stay request-scoped.
        save_automatic_api_key(cfg, automatic)
        automatic_key_persisted = True
    settings = {
        "api_key": str(api_key).strip(),
        "api_key_source": api_key_source,
        "storage_host": storage_host_name(runtime["host"]),
        "runtime_host": automatic["host"],
        "runtime_host_source": automatic["host_source"],
        "runtime_model": automatic["model"],
        "runtime_model_source": automatic["model_source"],
        "runtime_model_is_gpt": automatic["model_is_gpt"],
        "automatic_api_key_configured": "true" if automatic["api_key"] else "false",
        "automatic_api_key_source": automatic["source"],
        "automatic_api_key_match": automatic["match"],
        "automatic_api_key_reason": automatic["reason"],
        "automatic_api_key_persisted": "true" if automatic_key_persisted else "false",
        "stored_automatic_key_matches_runtime": "true" if stored_automatic_matches else "false",
        "stored_api_key_origin": stored_origin,
        "stored_api_key_runtime_host": string_value(cfg.get("api_key_runtime_host")),
        "stored_api_key_runtime_model": string_value(cfg.get("api_key_runtime_model")),
        "endpoint": resolve_endpoint_value(
            args, "endpoint", cfg, "endpoint", DEFAULT_GENERATIONS_ENDPOINT, "generation endpoint"
        ),
        "edits_endpoint": resolve_endpoint_value(
            args, "edits_endpoint", cfg, "edits_endpoint", DEFAULT_EDITS_ENDPOINT, "edit endpoint"
        ),
        "model": (
            str(getattr(args, "model", None)).strip()
            if getattr(args, "model", None)
            else normalize_persistent_model(cfg.get("model"))
        ),
        "user_agent": str(getattr(args, "user_agent", None) or cfg.get("user_agent") or build_default_user_agent()).strip(),
        "default_size": normalize_size(resolve_configured_value(args, "size", cfg, "default_size", DEFAULT_SIZE)),
        "default_quality": normalize_quality(
            resolve_configured_value(args, "quality", cfg, "default_quality", DEFAULT_QUALITY)
        ),
        "partial_images": normalize_partial_images(
            resolve_configured_value(args, "partial_images", cfg, "default_partial_images", DEFAULT_PARTIAL_IMAGES)
        ),
        "background": normalize_background(
            resolve_configured_value(args, "background", cfg, "default_background", DEFAULT_BACKGROUND)
        ),
        "output_format": normalize_output_format(
            resolve_configured_value(args, "output_format", cfg, "default_output_format", DEFAULT_OUTPUT_FORMAT)
        ),
        "n": normalize_n(resolve_configured_value(args, "n", cfg, "default_n", DEFAULT_N)),
        "edit_protocol": normalize_edit_protocol(
            getattr(args, "edit_protocol", None) or cfg.get("edit_protocol") or DEFAULT_EDIT_PROTOCOL
        ),
    }
    if require_key and not settings["api_key"]:
        raise CliError(
            "IntelAlloc GPT-series model API key is not configured. Configure an IntelAlloc GPT-series model API key: "
            "python scripts/intelalloc_image.py configure --api-key <key>"
        )
    if (
        require_key
        and settings["api_key_source"] in {"cli", "environment", "config"}
        and settings["automatic_api_key_reason"] != "configured-key-present"
    ):
        if settings["automatic_api_key_reason"] != "key-available":
            print(
                "WARNING=当前宿主或模型未确认可使用自动凭据；请确保手动 API key 属于 GPT 系列模型。",
                file=sys.stderr,
            )
    if not settings["endpoint"]:
        settings["endpoint"] = DEFAULT_GENERATIONS_ENDPOINT
    if not settings["edits_endpoint"]:
        settings["edits_endpoint"] = DEFAULT_EDITS_ENDPOINT
    if not settings["model"]:
        settings["model"] = DEFAULT_MODEL
    if not settings["user_agent"]:
        settings["user_agent"] = build_default_user_agent()
    validate_model_quality(settings["model"], settings["default_quality"])
    validate_output_options(settings["background"], settings["output_format"])
    return settings


def renderable_path(path: pathlib.Path) -> str:
    return path.resolve().as_posix()


def directory_link(path: pathlib.Path) -> str:
    display = renderable_path(path)
    target = "<" + display.replace(">", "%3E") + ">" if any(char.isspace() for char in display) else display
    return "[{0}]({1})".format(display, target)


def ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_image(path: pathlib.Path, image_bytes: bytes) -> pathlib.Path:
    if not image_bytes:
        raise CliError("No image bytes were returned by the API.")
    ensure_parent(path)
    with path.open("wb") as f:
        f.write(image_bytes)
    return path.resolve()


def indexed_output_path(path: pathlib.Path, index: int, total: int) -> pathlib.Path:
    if total == 1:
        return path
    return path.with_name("{0}-{1:03d}{2}".format(path.stem, index, path.suffix))


def save_images(path: pathlib.Path, images: Sequence[bytes]) -> List[pathlib.Path]:
    if not images:
        raise CliError("No image bytes were returned by the API.")
    total = len(images)
    return [save_image(indexed_output_path(path, index, total), image) for index, image in enumerate(images, start=1)]


def default_output_dir(runtime_host: str = "unknown") -> pathlib.Path:
    output_root = pathlib.Path.home() / "Pictures" / "IntelAlloc"
    host = str(runtime_host).strip().lower()
    if host == "workbuddy":
        return output_root / "WorkBuddy"
    if host == "codex":
        return output_root / "Codex"
    return output_root


def output_extension(output_format: str) -> str:
    return "." + ("jpeg" if output_format == "jpeg" else output_format)


def with_output_extension(path: pathlib.Path, output_format: str) -> pathlib.Path:
    return path.with_suffix(output_extension(output_format))


def unique_output_name(kind: str, output_format: str = DEFAULT_OUTPUT_FORMAT) -> str:
    timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return "intelalloc-{0}-{1}-{2}{3}".format(kind, timestamp, uuid.uuid4().hex[:8], output_extension(output_format))


def resolve_output_path(
    args: argparse.Namespace, kind: str, runtime_host: str, output_format: str = DEFAULT_OUTPUT_FORMAT
) -> pathlib.Path:
    if getattr(args, "output", None):
        requested = pathlib.Path(args.output).expanduser()
        output = with_output_extension(requested, output_format)
        expected_extension = output_extension(output_format)
        if requested.suffix and requested.suffix.lower() != expected_extension:
            print(
                "WARNING=显式输出路径的扩展名 {0} 与输出格式 {1} 不一致；文件将保存为 {2}。".format(
                    requested.suffix, output_format, output
                ),
                file=sys.stderr,
            )
        return output
    if getattr(args, "output_dir", None):
        return pathlib.Path(args.output_dir).expanduser() / unique_output_name(kind, output_format)
    return default_output_dir(runtime_host) / unique_output_name(kind, output_format)


def resolve_batch_output_dir(args: argparse.Namespace, runtime_host: str) -> pathlib.Path:
    if getattr(args, "output_dir", None):
        return pathlib.Path(args.output_dir).expanduser()
    timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return default_output_dir(runtime_host) / "batch-{0}-{1}".format(timestamp, uuid.uuid4().hex[:8])


def response_error_text(response: urllib.error.HTTPError) -> str:
    try:
        raw = response.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    if not raw:
        return str(response)
    return raw


def is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in {408, 409, 425, 429, 500, 503, 504, 524}
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ssl.SSLError, ConnectionError)):
        return True
    if isinstance(exc, CliError):
        msg = str(exc).lower()
        return "upstream" in msg or "stream disconnected" in msg or "temporarily" in msg
    return False


def retry_delay(attempt: int) -> float:
    return min(8.0, 1.0 * (2 ** max(0, attempt - 1))) + random.random() * 0.25


def request_with_retries(fn):
    last_exc: Optional[BaseException] = None
    for attempt in range(MAX_RETRY_COUNT + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - user-facing CLI wraps expected network errors
            last_exc = exc
            if attempt >= MAX_RETRY_COUNT or not is_retryable_exception(exc):
                break
            print("RETRY={0}/{1} reason={2}".format(attempt + 1, MAX_RETRY_COUNT, str(exc)), file=sys.stderr)
            time.sleep(retry_delay(attempt + 1))
    if isinstance(last_exc, ApiResponseError):
        raise last_exc
    if isinstance(last_exc, CliError):
        raise last_exc
    if isinstance(last_exc, urllib.error.HTTPError):
        raise ApiResponseError(response_error_text(last_exc), status=last_exc.code)
    raise CliError(str(last_exc) if last_exc else "Request failed.")


def timed_api_request(fn):
    started_at = now_iso()
    started = monotonic_seconds()
    print("REQUEST_STARTED_AT=" + started_at, file=sys.stderr)
    try:
        return request_with_retries(fn)
    finally:
        finished_at = now_iso()
        elapsed = monotonic_seconds() - started
        print("REQUEST_FINISHED_AT=" + finished_at, file=sys.stderr)
        print("REQUEST_ELAPSED_SECONDS={0:.3f}".format(elapsed), file=sys.stderr)


def open_request(req: urllib.request.Request):
    return urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS)


def request_headers(settings: Dict[str, str], content_type: str, accept: str = "text/event-stream") -> Dict[str, str]:
    return {
        "Authorization": "Bearer " + settings["api_key"],
        "Content-Type": content_type,
        "Accept": accept,
        "Cache-Control": "no-cache",
        "User-Agent": settings["user_agent"],
    }


def build_generation_body(prompt: str, settings: Dict[str, Any], stream: bool = True) -> bytes:
    body = {
        "model": settings["model"],
        "prompt": prompt,
        "n": settings.get("n", DEFAULT_N),
        "size": settings["default_size"],
        "quality": settings["default_quality"],
        "output_format": settings.get("output_format", DEFAULT_OUTPUT_FORMAT),
        "stream": stream,
        "partial_images": settings.get("partial_images", DEFAULT_PARTIAL_IMAGES),
        "background": settings.get("background", DEFAULT_BACKGROUND),
    }
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def request_generation(prompt: str, settings: Dict[str, Any]) -> List[bytes]:
    endpoint = normalize_endpoint(settings["endpoint"], "generation endpoint")

    def once() -> List[bytes]:
        body = build_generation_body(prompt, settings, stream=True)
        req = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers=request_headers(settings, "application/json; charset=utf-8"),
        )
        with open_request(req) as response:
            return read_image_response(response)

    return timed_api_request(once)


def guess_mime(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(str(path))[0]
    return mime or "application/octet-stream"


def maybe_optimize_image(path: pathlib.Path, force: bool, allow_optimization: bool = True) -> UploadImage:
    original_bytes = path.stat().st_size
    original = UploadImage(
        source_path=path,
        upload_path=path,
        filename=path.name,
        content_type=guess_mime(path),
        optimized=False,
        original_bytes=original_bytes,
        upload_bytes=original_bytes,
    )
    if not allow_optimization or (not force and original_bytes < UPLOAD_OPTIMIZE_MIN_BYTES):
        return original
    try:
        from PIL import Image, ImageOps  # type: ignore
    except Exception:
        return original
    tmp_path: Optional[pathlib.Path] = None
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", getattr(Image, "BICUBIC", 3))
            img.thumbnail((UPLOAD_OPTIMIZE_MAX_EDGE, UPLOAD_OPTIMIZE_MAX_EDGE), resample)
            has_alpha = "A" in img.getbands()
            if has_alpha:
                # A JPEG optimization would flatten transparency and change edit semantics.
                return original
            img = img.convert("RGB")
            tmp = tempfile.NamedTemporaryFile(prefix="intelalloc-upload-", suffix=".jpg", delete=False)
            tmp_path = pathlib.Path(tmp.name)
            tmp.close()
            img.save(tmp_path, "JPEG", quality=UPLOAD_OPTIMIZE_JPEG_QUALITY, optimize=True)
        upload_bytes = tmp_path.stat().st_size
        if upload_bytes >= original_bytes:
            tmp_path.unlink(missing_ok=True)
            tmp_path = None
            return original
        return UploadImage(
            source_path=path,
            upload_path=tmp_path,
            filename=path.with_suffix(".jpg").name,
            content_type="image/jpeg",
            optimized=True,
            original_bytes=original_bytes,
            upload_bytes=upload_bytes,
            cleanup=True,
        )
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        return original


def prepare_upload_images(inputs: Sequence[pathlib.Path], allow_optimization: bool = True) -> List[UploadImage]:
    force = len(inputs) > 1
    uploads: List[UploadImage] = []
    try:
        for path in inputs:
            uploads.append(maybe_optimize_image(path, force=force, allow_optimization=allow_optimization))
    except Exception:
        cleanup_upload_images(uploads)
        raise
    optimized_count = sum(1 for item in uploads if item.optimized)
    total_original = sum(item.original_bytes for item in uploads)
    total_upload = sum(item.upload_bytes for item in uploads)
    if uploads:
        print(
            "UPLOAD_IMAGES={0} OPTIMIZED={1} ORIGINAL_BYTES={2} UPLOAD_BYTES={3}".format(
                len(uploads), optimized_count, total_original, total_upload
            ),
            file=sys.stderr,
        )
        if len(inputs) > 1 and not allow_optimization:
            print("UPLOAD_OPTIMIZATION=disabled_for_multipart", file=sys.stderr)
        elif len(inputs) > 1 and optimized_count == 0:
            print("UPLOAD_OPTIMIZATION=skipped_or_unavailable", file=sys.stderr)
    return uploads


def cleanup_upload_images(uploads: Sequence[UploadImage]) -> None:
    for item in uploads:
        if item.cleanup:
            try:
                item.upload_path.unlink(missing_ok=True)
            except OSError:
                pass


def upload_data_url(upload: UploadImage) -> str:
    with upload.upload_path.open("rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return "data:{0};base64,{1}".format(upload.content_type or "application/octet-stream", encoded)


def build_json_edit_body(prompt: str, uploads: Sequence[UploadImage], settings: Dict[str, Any]) -> bytes:
    body = {
        "model": settings["model"],
        "prompt": prompt,
        "n": settings.get("n", DEFAULT_N),
        "size": settings["default_size"],
        "quality": settings["default_quality"],
        "output_format": settings.get("output_format", DEFAULT_OUTPUT_FORMAT),
        "stream": True,
        "partial_images": settings.get("partial_images", DEFAULT_PARTIAL_IMAGES),
        "background": settings.get("background", DEFAULT_BACKGROUND),
        "images": [{"image_url": upload_data_url(upload)} for upload in uploads],
    }
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def write_field(parts: List[bytes], boundary: str, name: str, value: str) -> None:
    parts.append(("--" + boundary + "\r\n").encode("utf-8"))
    parts.append(('Content-Disposition: form-data; name="{0}"\r\n\r\n'.format(name)).encode("utf-8"))
    parts.append(str(value).encode("utf-8"))
    parts.append(b"\r\n")


def sanitize_upload_filename(filename: str) -> str:
    """Return a header-safe ASCII basename without changing the local file."""
    basename = re.split(r"[/\\]+", str(filename))[-1]
    basename = unicodedata.normalize("NFKD", basename)
    suffix_match = re.search(r"(\.(?:png|jpg|jpeg|webp))$", basename, re.IGNORECASE)
    suffix = suffix_match.group(1).lower() if suffix_match else ""
    stem = basename[: -len(suffix)] if suffix else basename
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return (safe_stem or "image") + suffix


def write_file(parts: List[bytes], boundary: str, name: str, upload: UploadImage) -> None:
    safe_filename = sanitize_upload_filename(upload.filename)
    parts.append(("--" + boundary + "\r\n").encode("utf-8"))
    parts.append(
        (
            'Content-Disposition: form-data; name="{0}"; filename="{1}"\r\n'
            "Content-Type: {2}\r\n\r\n"
        ).format(name, safe_filename, upload.content_type).encode("ascii")
    )
    with upload.upload_path.open("rb") as f:
        parts.append(f.read())
    parts.append(b"\r\n")


def build_multipart(prompt: str, uploads: Sequence[UploadImage], settings: Dict[str, Any]) -> Tuple[bytes, str]:
    boundary = "----IntelAllocImage" + uuid.uuid4().hex
    parts: List[bytes] = []
    write_field(parts, boundary, "model", settings["model"])
    write_field(parts, boundary, "prompt", prompt)
    write_field(parts, boundary, "n", str(settings.get("n", DEFAULT_N)))
    write_field(parts, boundary, "size", settings["default_size"])
    write_field(parts, boundary, "quality", settings["default_quality"])
    write_field(parts, boundary, "output_format", settings.get("output_format", DEFAULT_OUTPUT_FORMAT))
    write_field(parts, boundary, "stream", "true")
    write_field(parts, boundary, "partial_images", str(settings.get("partial_images", DEFAULT_PARTIAL_IMAGES)))
    write_field(parts, boundary, "background", settings.get("background", DEFAULT_BACKGROUND))
    for upload in uploads:
        write_file(parts, boundary, "image[]", upload)
    parts.append(("--" + boundary + "--\r\n").encode("utf-8"))
    return b"".join(parts), boundary


def request_edit(prompt: str, inputs: Sequence[pathlib.Path], settings: Dict[str, Any]) -> List[bytes]:
    if not inputs:
        raise CliError("Edit requires at least one input image.")
    if len(inputs) > MAX_INPUT_IMAGES:
        raise CliError("Edit supports at most {0} input images; got {1}.".format(MAX_INPUT_IMAGES, len(inputs)))
    endpoint = normalize_endpoint(settings["edits_endpoint"], "edit endpoint")
    allow_optimization = settings.get("edit_protocol") == "json"
    uploads = prepare_upload_images(inputs, allow_optimization=allow_optimization)

    def once() -> List[bytes]:
        if settings["edit_protocol"] == "json":
            body = build_json_edit_body(prompt, uploads, settings)
            content_type = "application/json; charset=utf-8"
        else:
            body, boundary = build_multipart(prompt, uploads, settings)
            content_type = "multipart/form-data; boundary=" + boundary
        req = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers=request_headers(settings, content_type),
        )
        with open_request(req) as response:
            return read_image_response(response)

    try:
        return timed_api_request(once)
    finally:
        cleanup_upload_images(uploads)


def read_image_response(response) -> List[bytes]:
    content_type = response.headers.get("Content-Type", "")
    raw = response.read()
    text = raw.decode("utf-8", errors="replace")
    if "text/event-stream" in content_type.lower() or looks_like_event_stream(text):
        return read_streamed_images(text)
    return read_images_from_json(text)


def looks_like_event_stream(text: str) -> bool:
    trimmed = (text or "").lstrip()
    return trimmed.startswith("event:") or trimmed.startswith("data:")


def read_streamed_images(text: str) -> List[bytes]:
    event_lines: List[str] = []
    final_values: List[str] = []

    def collect(values: Sequence[str]) -> None:
        final_values.extend(values)

    for line in text.splitlines():
        if line == "":
            values = process_event_data_values("\n".join(event_lines))
            event_lines = []
            collect(values)
            continue
        if line.lower().startswith("data:"):
            event_lines.append(line[5:].lstrip())
    collect(process_event_data_values("\n".join(event_lines)))
    if final_values:
        return [decode_base64_image(value) for value in final_values]
    raise CliError("Stream ended without a final image.")


def read_streamed_image(text: str) -> bytes:
    """Keep the legacy single-image helper for callers outside the CLI."""
    return read_streamed_images(text)[0]


def process_event_data(data_text: str) -> Optional[str]:
    values = process_event_data_values(data_text)
    return values[0] if values else None


def process_event_data_values(data_text: str) -> List[str]:
    data_text = (data_text or "").strip()
    if not data_text or data_text == "[DONE]":
        return []
    try:
        payload = json.loads(data_text)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    event_type = str(payload.get("type") or "")
    if "failed" in event_type.lower() or "error" in event_type.lower():
        raise ApiResponseError(data_text)
    if "partial" in event_type.lower():
        return []
    values = extract_base64_values(payload, deduplicate=False)
    if values and (not event_type or "complete" in event_type.lower() or "completed" in event_type.lower()):
        return values
    return []


def read_images_from_json(text: str) -> List[bytes]:
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise CliError("Response was not valid JSON and not an event stream: " + str(exc)) from exc
    values = extract_base64_values(payload, deduplicate=False)
    if not values:
        if isinstance(payload, dict) and ("error" in payload or "message" in payload or "detail" in payload):
            raise ApiResponseError(text)
        raise CliError("Response did not contain an image base64 field.")
    return [decode_base64_image(value) for value in values]


def read_image_from_json(text: str) -> bytes:
    """Keep the legacy single-image helper for callers outside the CLI."""
    return read_images_from_json(text)[0]


def decode_base64_image(value: str) -> bytes:
    value = re.sub(r"^data:image/[^;]+;base64,", "", value.strip())
    try:
        return base64.b64decode(value, validate=False)
    except Exception as exc:
        raise CliError("Image base64 could not be decoded: " + str(exc)) from exc


def extract_base64(payload: Any) -> Optional[str]:
    values = extract_base64_values(payload)
    return values[0] if values else None


def extract_base64_values(payload: Any, deduplicate: bool = True) -> List[str]:
    values: List[str] = []
    seen = set()

    def add(value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            return
        if deduplicate:
            if value in seen:
                return
            seen.add(value)
        values.append(value)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            # Partial preview payloads are intentionally excluded. Only final image fields
            # should reach the save/display path.
            for key in ("b64_json", "image", "image_b64", "image_base64", "result"):
                add(value.get(key))
            data = value.get("data")
            if isinstance(data, list):
                for item in data:
                    visit(item)
            elif isinstance(data, dict):
                visit(data)
            output = value.get("output")
            if isinstance(output, list):
                for item in output:
                    visit(item)
            response = value.get("response")
            if isinstance(response, dict):
                visit(response)
            content = value.get("content")
            if isinstance(content, list):
                for item in content:
                    visit(item)

    visit(payload)
    return values


def extract_error_message(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        for key in ("message", "detail"):
            value = payload.get(key)
            if value:
                return str(value)
        error = payload.get("error")
        if isinstance(error, dict):
            parts = []
            for key in ("code", "type", "message"):
                value = error.get(key)
                if value:
                    parts.append(str(value))
            if parts:
                return "\n".join(parts)
        if error:
            return str(error)
    return None


def collect_dir_images(path: pathlib.Path, recursive: bool) -> List[pathlib.Path]:
    if not path.exists() or not path.is_dir():
        raise CliError("Input directory does not exist: " + str(path))
    iterator: Iterable[pathlib.Path] = path.rglob("*") if recursive else path.iterdir()
    files = [
        p.resolve()
        for p in iterator
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=lambda p: str(p).lower())


def resolve_inputs(args: argparse.Namespace, runtime_host: str) -> List[pathlib.Path]:
    inputs: List[pathlib.Path] = []
    for value in getattr(args, "inputs", None) or []:
        path = pathlib.Path(value).expanduser()
        if not path.exists() or not path.is_file():
            raise CliError("Input image does not exist: " + str(path))
        inputs.append(path.resolve())
    if getattr(args, "input_dir", None):
        dir_images = collect_dir_images(pathlib.Path(args.input_dir).expanduser(), bool(getattr(args, "recursive", False)))
        limit = getattr(args, "limit", None)
        if limit is not None:
            dir_images = dir_images[:limit]
        inputs.extend(dir_images)
    if getattr(args, "from_last", False):
        last = get_last_output_path(runtime_host)
        if not last:
            raise CliError("No last output is recorded. Specify --input instead.")
        if not last.exists():
            raise CliError("Last output no longer exists: " + str(last))
        inputs.append(last.resolve())
    unique: List[pathlib.Path] = []
    seen = set()
    for path in inputs:
        key = os.path.normcase(str(path))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    if len(unique) > MAX_INPUT_IMAGES:
        raise CliError(
            "Edit found {0} input images, but the maximum is {1}. Reduce inputs or pass --limit 16 for directory input.".format(
                len(unique), MAX_INPUT_IMAGES
            )
        )
    return unique


def get_last_output_path(runtime_host: str = "unknown") -> Optional[pathlib.Path]:
    history = load_json(history_path(runtime_host), {})
    if not isinstance(history, dict):
        return None
    value = history.get("last_output")
    if not value:
        return None
    return pathlib.Path(str(value)).expanduser()


def load_history(runtime_host: str = "unknown") -> Dict[str, Any]:
    history = load_json(history_path(runtime_host), {"last_output": "", "items": []})
    if not isinstance(history, dict):
        history = {"last_output": "", "items": []}
    if not isinstance(history.get("items"), list):
        history["items"] = []
    return history


def add_history(item: Dict[str, Any], outputs: Sequence[pathlib.Path], runtime_host: str) -> None:
    history = load_history(runtime_host)
    items = history["items"]
    items.insert(0, item)
    del items[HISTORY_LIMIT:]
    if outputs:
        history["last_output"] = str(outputs[-1].resolve())
    save_json_private(history_path(runtime_host), history)


def save_history_state(history: Dict[str, Any], outputs: Sequence[pathlib.Path], runtime_host: str) -> None:
    if outputs:
        history["last_output"] = str(outputs[-1].resolve())
    save_json_private(history_path(runtime_host), history)


def start_history_item(item: Dict[str, Any], runtime_host: str) -> Dict[str, Any]:
    history = load_history(runtime_host)
    history["items"].insert(0, item)
    del history["items"][HISTORY_LIMIT:]
    save_history_state(history, [], runtime_host)
    return history


def redact_history_error(exc: BaseException, limit: int = 1000) -> str:
    text = redact_sensitive_text(str(exc).strip())
    return text[:limit] or exc.__class__.__name__


def redact_sensitive_text(text: str) -> str:
    """Redact API keys and bearer tokens before user-visible output or history writes."""
    text = re.sub(r"(?i)sk-[A-Za-z0-9][A-Za-z0-9._~+/=-]{7,}", "[REDACTED_API_KEY]", text)
    return re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)


def build_history_item(kind: str, prompt: str, size: str, quality: str, outputs: Sequence[pathlib.Path], inputs: Sequence[pathlib.Path]) -> Dict[str, Any]:
    return {
        "id": _dt.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "type": kind,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "outputs": [str(p.resolve()) for p in outputs],
        "output": str(outputs[-1].resolve()) if outputs else "",
        "inputs": [str(p.resolve()) for p in inputs],
        "created_at": now_iso(),
    }


def print_saved(path: pathlib.Path) -> None:
    resolved = path.resolve()
    print("SAVED_IMAGE=" + str(resolved))
    print("DISPLAY_IMAGE=" + renderable_path(resolved))
    print("SAVED_DIRECTORY=" + str(resolved.parent))
    print("DISPLAY_DIRECTORY=" + renderable_path(resolved.parent))
    print("DISPLAY_DIRECTORY_LINK=" + directory_link(resolved.parent))


def print_saved_many(paths: Sequence[pathlib.Path]) -> None:
    saved = [str(p.resolve()) for p in paths]
    display = [renderable_path(p) for p in paths]
    print("SAVED_IMAGES=" + json.dumps(saved, ensure_ascii=False))
    print("DISPLAY_IMAGES=" + json.dumps(display, ensure_ascii=False))
    if paths:
        directory = paths[0].resolve().parent
        print("SAVED_DIRECTORY=" + str(directory))
        print("DISPLAY_DIRECTORY=" + renderable_path(directory))
        print("DISPLAY_DIRECTORY_LINK=" + directory_link(directory))


def print_request_options(settings: Dict[str, Any]) -> None:
    print("REQUEST_MODEL=" + settings["model"], file=sys.stderr)
    print("REQUEST_SIZE=" + settings["default_size"], file=sys.stderr)
    print("REQUEST_QUALITY=" + settings["default_quality"], file=sys.stderr)
    print("REQUEST_PARTIAL_IMAGES=" + str(settings.get("partial_images", DEFAULT_PARTIAL_IMAGES)), file=sys.stderr)
    print("REQUEST_BACKGROUND=" + settings.get("background", DEFAULT_BACKGROUND), file=sys.stderr)
    print("REQUEST_OUTPUT_FORMAT=" + settings.get("output_format", DEFAULT_OUTPUT_FORMAT), file=sys.stderr)
    print("REQUEST_N=" + str(settings.get("n", DEFAULT_N)), file=sys.stderr)


def command_configure(args: argparse.Namespace) -> int:
    runtime = resolve_runtime_context(args)
    cfg = dict(load_config(runtime["host"]))
    target_endpoint = resolve_endpoint_value(
        args, "endpoint", cfg, "endpoint", DEFAULT_GENERATIONS_ENDPOINT, "generation endpoint"
    )
    target_edits_endpoint = resolve_endpoint_value(
        args, "edits_endpoint", cfg, "edits_endpoint", DEFAULT_EDITS_ENDPOINT, "edit endpoint"
    )
    target_model = (
        normalize_persistent_model(args.model)
        if args.model is not None
        else normalize_persistent_model(cfg.get("model"))
    )
    target_quality = normalize_quality(
        args.default_quality if args.default_quality is not None else cfg.get("default_quality") or DEFAULT_QUALITY
    )
    target_partial_images = normalize_partial_images(
        resolve_configured_value(args, "default_partial_images", cfg, "default_partial_images", DEFAULT_PARTIAL_IMAGES)
    )
    target_background = normalize_background(
        resolve_configured_value(args, "default_background", cfg, "default_background", DEFAULT_BACKGROUND)
    )
    target_output_format = normalize_output_format(
        resolve_configured_value(args, "default_output_format", cfg, "default_output_format", DEFAULT_OUTPUT_FORMAT)
    )
    target_n = normalize_n(resolve_configured_value(args, "default_n", cfg, "default_n", DEFAULT_N))
    validate_model_quality(target_model, target_quality)
    validate_output_options(target_background, target_output_format)
    if args.api_key is not None:
        cfg["api_key"] = args.api_key.strip()
        cfg["api_key_origin"] = "manual" if cfg["api_key"] else ""
        cfg.pop("api_key_runtime_host", None)
        cfg.pop("api_key_runtime_model", None)
        cfg.pop("api_key_saved_at", None)
    if args.default_size is not None:
        cfg["default_size"] = normalize_size(args.default_size)
        cfg[SIZE_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
    if args.default_quality is not None:
        cfg["default_quality"] = target_quality
        cfg[QUALITY_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
    if args.default_partial_images is not None:
        cfg["default_partial_images"] = target_partial_images
    if args.default_background is not None:
        cfg["default_background"] = target_background
    if args.default_output_format is not None:
        cfg["default_output_format"] = target_output_format
    if args.default_n is not None:
        cfg["default_n"] = target_n
    cfg["endpoint"] = target_endpoint
    cfg["edits_endpoint"] = target_edits_endpoint
    if args.model is not None:
        cfg["model"] = target_model
        cfg[MODEL_MIGRATION_KEY] = GPT_IMAGE_2_5_MIGRATION_VERSION
    if args.user_agent is not None:
        cfg["user_agent"] = args.user_agent.strip() or build_default_user_agent()
    if args.edit_protocol is not None:
        cfg["edit_protocol"] = normalize_edit_protocol(args.edit_protocol)
    cfg.setdefault("endpoint", DEFAULT_GENERATIONS_ENDPOINT)
    cfg.setdefault("edits_endpoint", DEFAULT_EDITS_ENDPOINT)
    cfg.setdefault("model", DEFAULT_MODEL)
    cfg.setdefault("user_agent", build_default_user_agent())
    cfg.setdefault("default_size", DEFAULT_SIZE)
    cfg.setdefault("default_quality", DEFAULT_QUALITY)
    cfg.setdefault("default_partial_images", DEFAULT_PARTIAL_IMAGES)
    cfg.setdefault("default_background", DEFAULT_BACKGROUND)
    cfg.setdefault("default_output_format", DEFAULT_OUTPUT_FORMAT)
    cfg.setdefault("default_n", DEFAULT_N)
    cfg.setdefault("edit_protocol", DEFAULT_EDIT_PROTOCOL)
    save_json_private(config_path(runtime["host"]), cfg)
    print("CONFIG_PATH=" + str(config_path(runtime["host"])))
    print("API_KEY_CONFIGURED=" + ("true" if cfg.get("api_key") else "false"))
    print("DEFAULT_SIZE=" + cfg.get("default_size", DEFAULT_SIZE))
    print("DEFAULT_QUALITY=" + cfg.get("default_quality", DEFAULT_QUALITY))
    print("DEFAULT_PARTIAL_IMAGES=" + str(cfg.get("default_partial_images", DEFAULT_PARTIAL_IMAGES)))
    print("DEFAULT_BACKGROUND=" + cfg.get("default_background", DEFAULT_BACKGROUND))
    print("DEFAULT_OUTPUT_FORMAT=" + cfg.get("default_output_format", DEFAULT_OUTPUT_FORMAT))
    print("DEFAULT_N=" + str(cfg.get("default_n", DEFAULT_N)))
    print("EDIT_PROTOCOL=" + cfg.get("edit_protocol", DEFAULT_EDIT_PROTOCOL))
    print("MODEL=" + cfg.get("model", DEFAULT_MODEL))
    print("ENDPOINT=" + cfg.get("endpoint", DEFAULT_GENERATIONS_ENDPOINT))
    print("EDITS_ENDPOINT=" + cfg.get("edits_endpoint", DEFAULT_EDITS_ENDPOINT))
    return 0


def command_show_config(args: argparse.Namespace) -> int:
    settings = resolve_settings(args, require_key=False)
    print("STORAGE_HOST=" + settings["storage_host"])
    print("CONFIG_PATH=" + str(config_path(settings["runtime_host"])))
    print("HISTORY_PATH=" + str(history_path(settings["runtime_host"])))
    print("DEFAULT_OUTPUT_DIRECTORY=" + str(default_output_dir(settings["runtime_host"])))
    print("CODEX_AUTH_PATH=" + str(auth_path()))
    print("WORKBUDDY_MODELS_PATH=" + str(workbuddy_models_path()))
    print("RUNTIME_HOST=" + settings["runtime_host"])
    print("RUNTIME_HOST_SOURCE=" + settings["runtime_host_source"])
    print("RUNTIME_MODEL=" + settings["runtime_model"])
    print("RUNTIME_MODEL_SOURCE=" + settings["runtime_model_source"])
    print("RUNTIME_MODEL_IS_GPT=" + settings["runtime_model_is_gpt"])
    print("AUTOMATIC_API_KEY_CONFIGURED=" + settings["automatic_api_key_configured"])
    print("AUTOMATIC_API_KEY_SOURCE=" + settings["automatic_api_key_source"])
    print("AUTOMATIC_API_KEY_MATCH=" + settings["automatic_api_key_match"])
    print("AUTOMATIC_API_KEY_REASON=" + settings["automatic_api_key_reason"])
    print("AUTOMATIC_API_KEY_PERSISTED=" + settings["automatic_api_key_persisted"])
    print("STORED_AUTOMATIC_KEY_MATCHES_RUNTIME=" + settings["stored_automatic_key_matches_runtime"])
    print("STORED_API_KEY_ORIGIN=" + settings["stored_api_key_origin"])
    print("STORED_API_KEY_RUNTIME_HOST=" + settings["stored_api_key_runtime_host"])
    print("STORED_API_KEY_RUNTIME_MODEL=" + settings["stored_api_key_runtime_model"])
    print("API_KEY_CONFIGURED=" + ("true" if bool(settings["api_key"]) else "false"))
    print("API_KEY_MASKED=" + mask_key(settings["api_key"]))
    print("API_KEY_SOURCE=" + settings["api_key_source"])
    print("MODEL=" + settings["model"])
    print("USER_AGENT=" + settings["user_agent"])
    print("ENDPOINT=" + settings["endpoint"])
    print("EDITS_ENDPOINT=" + settings["edits_endpoint"])
    print("DEFAULT_SIZE=" + settings["default_size"])
    print("DEFAULT_QUALITY=" + settings["default_quality"])
    print("DEFAULT_PARTIAL_IMAGES=" + str(settings["partial_images"]))
    print("DEFAULT_BACKGROUND=" + settings["background"])
    print("DEFAULT_OUTPUT_FORMAT=" + settings["output_format"])
    print("DEFAULT_N=" + str(settings["n"]))
    print("EDIT_PROTOCOL=" + settings["edit_protocol"])
    return 0


def command_generate(args: argparse.Namespace) -> int:
    settings = resolve_settings(args, require_key=True)
    prompt = require_prompt(args.prompt)
    output = resolve_output_path(args, "generate", settings["runtime_host"], settings["output_format"])
    print_request_options(settings)
    images = request_generation(prompt, settings)
    saved = save_images(output, images)
    add_history(
        build_history_item("generate", prompt, settings["default_size"], settings["default_quality"], saved, []),
        saved, settings["runtime_host"],
    )
    print_saved(saved[0]) if len(saved) == 1 else print_saved_many(saved)
    return 0


def command_edit(args: argparse.Namespace) -> int:
    settings = resolve_settings(args, require_key=True)
    prompt = require_prompt(args.prompt)
    inputs = resolve_inputs(args, settings["runtime_host"])
    if not inputs:
        raise CliError("Edit requires --input, --input-dir, or --from-last.")
    output = resolve_output_path(args, "edit", settings["runtime_host"], settings["output_format"])
    print_request_options(settings)
    images = request_edit(prompt, inputs, settings)
    saved = save_images(output, images)
    add_history(
        build_history_item("edit", prompt, settings["default_size"], settings["default_quality"], saved, inputs),
        saved, settings["runtime_host"],
    )
    print("INPUT_IMAGES=" + json.dumps([str(p) for p in inputs], ensure_ascii=False))
    print_saved(saved[0]) if len(saved) == 1 else print_saved_many(saved)
    return 0


def output_name_for(
    input_path: pathlib.Path, index: int, output_format: str, variant: int = 1, variant_total: int = 1
) -> str:
    stem = input_path.stem or "image"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "image"
    if variant_total == 1:
        return "{0}-{1:03d}{2}".format(safe, index, output_extension(output_format))
    return "{0}-{1:03d}-{2:03d}{3}".format(safe, index, variant, output_extension(output_format))


def command_batch_edit(args: argparse.Namespace) -> int:
    settings = resolve_settings(args, require_key=True)
    prompt = require_prompt(args.prompt)
    input_dir = pathlib.Path(args.input_dir).expanduser()
    inputs = collect_dir_images(input_dir, bool(args.recursive))
    if args.limit is not None:
        inputs = inputs[: args.limit]
    if not inputs:
        raise CliError("No supported input images found in: " + str(input_dir))
    output_dir = resolve_batch_output_dir(args, settings["runtime_host"])
    print_request_options(settings)
    outputs: List[pathlib.Path] = []
    batch_item = build_history_item(
        "batch-edit", prompt, settings["default_size"], settings["default_quality"], outputs, inputs
    )
    batch_item.update(
        {
            "status": "running",
            "completed_items": [],
            "failed_items": [],
            "started_at": now_iso(),
            "finished_at": "",
        }
    )
    history = start_history_item(batch_item, settings["runtime_host"])
    try:
        for index, input_path in enumerate(inputs, start=1):
            try:
                images = request_edit(prompt, [input_path], settings)
                item_outputs: List[pathlib.Path] = []
                for variant, image in enumerate(images, start=1):
                    item_outputs.append(
                        save_image(
                            output_dir
                            / output_name_for(input_path, index, settings["output_format"], variant, len(images)),
                            image,
                        )
                    )
            except Exception as exc:
                batch_item["status"] = "partial"
                batch_item["failed_items"].append(
                    {"input": str(input_path), "error": redact_history_error(exc)}
                )
                batch_item["outputs"] = [str(path.resolve()) for path in outputs]
                batch_item["output"] = str(outputs[-1].resolve()) if outputs else ""
                batch_item["finished_at"] = now_iso()
                save_history_state(history, outputs, settings["runtime_host"])
                raise
            outputs.extend(item_outputs)
            batch_item["completed_items"].append(
                {"input": str(input_path), "outputs": [str(path.resolve()) for path in item_outputs]}
            )
            batch_item["outputs"] = [str(path.resolve()) for path in outputs]
            batch_item["output"] = str(outputs[-1].resolve()) if outputs else ""
            save_history_state(history, outputs, settings["runtime_host"])
            print(
                "BATCH_ITEM={0}/{1} INPUT={2} OUTPUTS={3}".format(
                    index, len(inputs), input_path, json.dumps([str(path) for path in item_outputs], ensure_ascii=False)
                ),
                file=sys.stderr,
            )
    except Exception:
        raise
    batch_item["status"] = "succeeded"
    batch_item["finished_at"] = now_iso()
    save_history_state(history, outputs, settings["runtime_host"])
    print_saved_many(outputs)
    return 0


def command_last(args: argparse.Namespace) -> int:
    runtime = resolve_runtime_context(args)
    last = get_last_output_path(runtime["host"])
    if not last:
        print("LAST_OUTPUT=")
        return 1
    print("LAST_OUTPUT=" + str(last))
    print("DISPLAY_IMAGE=" + renderable_path(last))
    print("SAVED_DIRECTORY=" + str(last.parent.resolve()))
    print("DISPLAY_DIRECTORY=" + renderable_path(last.parent))
    print("DISPLAY_DIRECTORY_LINK=" + directory_link(last.parent))
    print("EXISTS=" + ("true" if last.exists() else "false"))
    return 0 if last.exists() else 1


def command_history(args: argparse.Namespace) -> int:
    runtime = resolve_runtime_context(args)
    history = load_history(runtime["host"])
    items = history.get("items", [])[: args.limit]
    print(json.dumps({"last_output": history.get("last_output", ""), "items": items}, ensure_ascii=False, indent=2))
    return 0


def command_help(args: argparse.Namespace) -> int:
    """Print static user guidance without reading or changing local state."""
    print(HELP_TEXT)
    return 0


def require_prompt(prompt: Optional[str]) -> str:
    prompt = (prompt or "").strip()
    if not prompt:
        raise CliError("Prompt is required.")
    return prompt


def add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime-host", choices=("codex", "workbuddy"), help=argparse.SUPPRESS)
    parser.add_argument("--runtime-model", help=argparse.SUPPRESS)


def add_common_request_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help=argparse.SUPPRESS)
    parser.add_argument("--endpoint", help=argparse.SUPPRESS)
    parser.add_argument("--edits-endpoint", help=argparse.SUPPRESS)
    parser.add_argument("--model", help=argparse.SUPPRESS)
    add_runtime_options(parser)
    parser.add_argument("--user-agent", help="Override the HTTP User-Agent for this request.")
    parser.add_argument("--size", help="Override image size with auto or WIDTHxHEIGHT for this request.")
    parser.add_argument("--quality", choices=sorted(SUPPORTED_QUALITIES), help="Override image quality for this request.")
    parser.add_argument("--partial-images", type=int, choices=sorted(SUPPORTED_PARTIAL_IMAGE_COUNTS))
    parser.add_argument("--background", choices=sorted(SUPPORTED_BACKGROUNDS))
    parser.add_argument("--output-format", choices=sorted(SUPPORTED_OUTPUT_FORMATS))
    parser.add_argument("--n", type=int, choices=range(MIN_OUTPUT_IMAGES, MAX_OUTPUT_IMAGES + 1))


def add_edit_protocol_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--edit-protocol",
        choices=sorted(SUPPORTED_EDIT_PROTOCOLS),
        help="Choose the edit request protocol: json (default) or multipart.",
    )


def add_single_output_options(parser: argparse.ArgumentParser) -> None:
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", help="Save to this image file path.")
    output.add_argument("--output-dir", help="Save a generated filename in this directory.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and edit images through the IntelAlloc API.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("help", help="Show common image settings and commands.")
    p.set_defaults(func=command_help)

    p = sub.add_parser("configure", help="Save local API key and defaults.")
    p.add_argument("--api-key")
    p.add_argument("--default-size", help="Save auto or a WIDTHxHEIGHT default size.")
    p.add_argument("--default-quality", choices=sorted(SUPPORTED_QUALITIES))
    p.add_argument("--default-partial-images", type=int, choices=sorted(SUPPORTED_PARTIAL_IMAGE_COUNTS))
    p.add_argument("--default-background", choices=sorted(SUPPORTED_BACKGROUNDS))
    p.add_argument("--default-output-format", choices=sorted(SUPPORTED_OUTPUT_FORMATS))
    p.add_argument("--default-n", type=int, choices=range(MIN_OUTPUT_IMAGES, MAX_OUTPUT_IMAGES + 1))
    p.add_argument("--endpoint")
    p.add_argument("--edits-endpoint")
    p.add_argument("--model", choices=sorted(PERSISTENT_MODELS))
    p.add_argument("--user-agent")
    add_edit_protocol_option(p)
    add_runtime_options(p)
    p.set_defaults(func=command_configure)

    p = sub.add_parser("show-config", help="Show resolved configuration without leaking the full API key.")
    add_common_request_options(p)
    add_edit_protocol_option(p)
    p.set_defaults(func=command_show_config)

    p = sub.add_parser("generate", help="Generate one image from text.")
    add_common_request_options(p)
    p.add_argument("--prompt", required=True)
    add_single_output_options(p)
    p.set_defaults(func=command_generate)

    p = sub.add_parser("edit", help="Edit using one or more input images.")
    add_common_request_options(p)
    add_edit_protocol_option(p)
    p.add_argument("--prompt", required=True)
    p.add_argument("--input", dest="inputs", action="append")
    p.add_argument("--input-dir")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument("--from-last", action="store_true")
    add_single_output_options(p)
    p.set_defaults(func=command_edit)

    p = sub.add_parser("batch-edit", help="Edit every supported image in a directory.")
    add_common_request_options(p)
    add_edit_protocol_option(p)
    p.add_argument("--prompt", required=True)
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=command_batch_edit)

    p = sub.add_parser("last", help="Show the most recent generated/edited output path.")
    add_runtime_options(p)
    p.set_defaults(func=command_last)

    p = sub.add_parser("history", help="Show recent generation/edit history.")
    p.add_argument("--limit", type=int, default=20)
    add_runtime_options(p)
    p.set_defaults(func=command_history)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if getattr(args, "limit", None) is not None and args.limit <= 0:
            raise CliError("--limit must be positive.")
        return int(args.func(args))
    except ApiResponseError as exc:
        if exc.status is not None:
            print("HTTP {0}".format(exc.status), file=sys.stderr)
        print("接口返回错误如下：", file=sys.stderr)
        print(redact_sensitive_text(exc.body), file=sys.stderr)
        if exc.status == 502:
            print("建议稍后再试。", file=sys.stderr)
        return 2
    except CliError as exc:
        print("ERROR=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
