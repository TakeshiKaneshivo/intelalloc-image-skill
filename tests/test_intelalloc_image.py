import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import types
import urllib.error
import unittest
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).parents[1] / "skills" / "intelalloc-image" / "scripts" / "intelalloc_image.py"
SPEC = importlib.util.spec_from_file_location("intelalloc_image", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def request_args(host=None, model=None):
    return argparse.Namespace(runtime_host=host, runtime_model=model)


class RuntimeCredentialTests(unittest.TestCase):
    def test_workbuddy_matches_current_model_id(self):
        with tempfile.TemporaryDirectory() as directory:
            models_path = pathlib.Path(directory) / "models.json"
            models_path.write_text(
                json.dumps(
                    [
                        {"id": "glm-5.2", "name": "glm-5.2", "apiKey": "glm-key"},
                        {"id": "gpt-5.6-luna", "name": "gpt-5.6-luna", "apiKey": "luna-key"},
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "workbuddy_models_path", return_value=models_path), mock.patch.dict(
                MODULE.os.environ, {}, clear=True
            ):
                result = MODULE.resolve_automatic_api_key(request_args("workbuddy", "gpt-5.6-luna"))

        self.assertEqual(result["api_key"], "luna-key")
        self.assertEqual(result["source"], "workbuddy-model")
        self.assertEqual(result["match"], "model-matched")
        self.assertEqual(result["reason"], "key-available")

    def test_workbuddy_lookup_reports_missing_or_invalid_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            models_path = pathlib.Path(directory) / "models.json"
            with mock.patch.object(MODULE, "workbuddy_models_path", return_value=models_path):
                key, reason = MODULE.load_workbuddy_model_api_key("gpt-5.6-luna")
                self.assertEqual((key, reason), ("", "model-not-found"))

                models_path.write_text("{not json", encoding="utf-8")
                key, reason = MODULE.load_workbuddy_model_api_key("gpt-5.6-luna")
                self.assertEqual((key, reason), ("", "model-not-found"))

                models_path.write_text(json.dumps({"models": []}), encoding="utf-8")
                key, reason = MODULE.load_workbuddy_model_api_key("gpt-5.6-luna")
                self.assertEqual((key, reason), ("", "models-invalid"))

                models_path.write_text(json.dumps([{"id": "gpt-5.6-luna"}]), encoding="utf-8")
                key, reason = MODULE.load_workbuddy_model_api_key("gpt-5.6-luna")
                self.assertEqual((key, reason), ("", "model-key-missing"))

    def test_unknown_runtime_does_not_read_models(self):
        with mock.patch.object(MODULE, "load_workbuddy_model_api_key") as load_key, mock.patch.dict(
            MODULE.os.environ, {}, clear=True
        ):
            result = MODULE.resolve_automatic_api_key(request_args())

        load_key.assert_not_called()
        self.assertEqual(result["host"], "unknown")
        self.assertEqual(result["reason"], "runtime-host-unknown")
        self.assertEqual(result["match"], "not-checked")

    def test_codebuddy_runtime_variables_are_supported(self):
        with mock.patch.object(MODULE, "load_workbuddy_model_api_key", return_value=("luna-key", "model-matched")), mock.patch.dict(
            MODULE.os.environ,
            {"CODEBUDDY_SESSION_ID": "session", "CODEBUDDY_MODEL": "custom-local:gpt-5.6-luna"},
            clear=True,
        ):
            result = MODULE.resolve_automatic_api_key(request_args())

        self.assertEqual(result["host"], "workbuddy")
        self.assertEqual(result["model"], "custom-local:gpt-5.6-luna")
        self.assertEqual(result["model_source"], "workbuddy-environment")
        self.assertEqual(result["api_key"], "luna-key")

    def test_non_gpt_workbuddy_model_does_not_read_models(self):
        with mock.patch.object(MODULE, "load_workbuddy_model_api_key") as load_key, mock.patch.dict(
            MODULE.os.environ, {}, clear=True
        ):
            result = MODULE.resolve_automatic_api_key(request_args("workbuddy", "glm-5.2"))

        load_key.assert_not_called()
        self.assertEqual(result["reason"], "runtime-model-not-gpt")
        self.assertEqual(result["match"], "not-checked")

    def test_codex_uses_auth_for_gpt_runtime(self):
        with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value="codex-key"), mock.patch.dict(
            MODULE.os.environ, {}, clear=True
        ):
            result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-5.6-terra"))

        self.assertEqual(result["api_key"], "codex-key")
        self.assertEqual(result["source"], "codex-auth")
        self.assertEqual(result["match"], "auth-file")

    def test_codex_uses_config_bearer_token_when_auth_key_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = pathlib.Path(directory) / "config.toml"
            config_path.write_text(
                "model = 'gpt-6.1-sol'\n"
                "\n"
                "[model_providers.custom]\n"
                "name = 'IntelAlloc'\n"
                "experimental_bearer_token = '  sk-config-key  ' # Codex token\n",
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                MODULE, "codex_config_path", return_value=config_path
            ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "sk-config-key")
        self.assertEqual(result["source"], "codex-config")
        self.assertEqual(result["match"], "config-file")
        self.assertEqual(result["reason"], "key-available")

    def test_codex_uses_root_level_bearer_token_as_compatibility_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = pathlib.Path(directory) / "config.toml"
            config_path.write_text(
                "experimental_bearer_token = \"  sk-root-key  \" # legacy root field\n",
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                MODULE, "codex_config_path", return_value=config_path
            ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "sk-root-key")
        self.assertEqual(result["source"], "codex-config")
        self.assertEqual(result["match"], "config-file")

    def test_codex_reads_bearer_tokens_in_any_provider_section(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = pathlib.Path(directory) / "config.toml"
            config_path.write_text(
                "[model_providers.other]\nexperimental_bearer_token = 'sk-other-key'\n",
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                MODULE, "codex_config_path", return_value=config_path
            ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "sk-other-key")
        self.assertEqual(result["source"], "codex-config")
        self.assertEqual(result["match"], "config-file")
        self.assertEqual(result["reason"], "key-available")

    def test_codex_uses_first_non_empty_bearer_token_in_file_order(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = pathlib.Path(directory) / "config.toml"
            config_path.write_text(
                "[first]\n"
                "experimental_bearer_token = ''\n"
                "[second]\n"
                "experimental_bearer_token = 'sk-first-valid-key'\n"
                "[third]\n"
                "experimental_bearer_token = 'sk-later-key'\n",
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                MODULE, "codex_config_path", return_value=config_path
            ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "sk-first-valid-key")

    def test_codex_auth_key_takes_precedence_over_config_bearer_token(self):
        with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value="auth-key"), mock.patch.object(
            MODULE, "load_codex_config_bearer_token"
        ) as load_config_key, mock.patch.dict(MODULE.os.environ, {}, clear=True):
            result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "auth-key")
        self.assertEqual(result["source"], "codex-auth")
        self.assertEqual(result["match"], "auth-file")
        load_config_key.assert_not_called()

    def test_codex_config_bearer_token_missing_or_invalid_is_safe(self):
        cases = [
            None,
            "",
            "experimental_bearer_token = 123\n",
            "not valid toml\n",
            "[credentials]\nexperimental_bearer_token = 123\n",
        ]
        for content in cases:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    config_path = pathlib.Path(directory) / "config.toml"
                    if content is not None:
                        config_path.write_text(content, encoding="utf-8")
                    with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                        MODULE, "codex_config_path", return_value=config_path
                    ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                        result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

                self.assertEqual(result["api_key"], "")
                self.assertEqual(result["source"], "codex-config")
                self.assertEqual(result["match"], "config-key-missing")
                self.assertEqual(result["reason"], "codex-config-key-missing")

        with tempfile.TemporaryDirectory() as directory:
            config_path = pathlib.Path(directory) / "config.toml"
            config_path.write_bytes(b'experimental_bearer_token = "\xff"\n')
            with mock.patch.object(MODULE, "load_codex_auth_api_key", return_value=""), mock.patch.object(
                MODULE, "codex_config_path", return_value=config_path
            ), mock.patch.dict(MODULE.os.environ, {}, clear=True):
                result = MODULE.resolve_automatic_api_key(request_args("codex", "gpt-6.1-sol"))

        self.assertEqual(result["api_key"], "")
        self.assertEqual(result["source"], "codex-config")
        self.assertEqual(result["match"], "config-key-missing")
        self.assertEqual(result["reason"], "codex-config-key-missing")

    def test_codex_non_gpt_runtime_does_not_read_auth_or_config(self):
        with mock.patch.object(MODULE, "load_codex_auth_api_key") as load_auth, mock.patch.object(
            MODULE, "load_codex_config_bearer_token"
        ) as load_config, mock.patch.dict(MODULE.os.environ, {}, clear=True):
            result = MODULE.resolve_automatic_api_key(request_args("codex", "claude-4"))

        load_auth.assert_not_called()
        load_config.assert_not_called()
        self.assertEqual(result["reason"], "runtime-model-not-gpt")
        self.assertEqual(result["match"], "not-checked")

    def test_codex_unknown_runtime_model_does_not_read_auth_or_config(self):
        with mock.patch.object(MODULE, "load_codex_auth_api_key") as load_auth, mock.patch.object(
            MODULE, "load_codex_config_bearer_token"
        ) as load_config, mock.patch.object(MODULE, "load_codex_config_model", return_value=""), mock.patch.dict(
            MODULE.os.environ, {}, clear=True
        ):
            result = MODULE.resolve_automatic_api_key(request_args("codex", None))

        load_auth.assert_not_called()
        load_config.assert_not_called()
        self.assertEqual(result["reason"], "runtime-model-unknown")


class KeySelectionTests(unittest.TestCase):
    def test_saved_automatic_config_takes_precedence_over_current_model(self):
        cfg = {
            "api_key": "old-key",
            "api_key_origin": "workbuddy-model",
            "api_key_runtime_host": "workbuddy",
            "api_key_runtime_model": "gpt-old",
        }
        automatic = {
            "api_key": "new-key",
            "source": "workbuddy-model",
            "reason": "key-available",
            "match": "model-matched",
            "host": "workbuddy",
            "model": "gpt-5.6-luna",
            "host_source": "cli",
            "model_source": "cli",
            "model_is_gpt": "true",
        }
        with mock.patch.object(MODULE, "load_config", return_value=cfg), mock.patch.object(
            MODULE, "resolve_automatic_api_key", return_value=automatic
        ) as resolve_auto, mock.patch.object(MODULE, "save_automatic_api_key") as save_key, mock.patch.object(
            MODULE, "save_json_private"
        ):
            settings = MODULE.resolve_settings(request_args("workbuddy", "gpt-5.6-luna"), require_key=True)

        self.assertEqual(settings["api_key"], "old-key")
        self.assertEqual(settings["api_key_source"], "config")
        self.assertEqual(settings["stored_automatic_key_matches_runtime"], "false")
        resolve_auto.assert_not_called()
        save_key.assert_not_called()

    def test_saved_automatic_config_is_preferred_when_model_matches(self):
        cfg = {
            "api_key": "saved-key",
            "api_key_origin": "workbuddy-model",
            "api_key_runtime_host": "workbuddy",
            "api_key_runtime_model": "gpt-5.6-luna",
        }
        automatic = {
            "api_key": "current-key",
            "source": "workbuddy-model",
            "reason": "key-available",
            "match": "model-matched",
            "host": "workbuddy",
            "model": "gpt-5.6-luna",
            "host_source": "cli",
            "model_source": "cli",
            "model_is_gpt": "true",
        }
        with mock.patch.object(MODULE, "load_config", return_value=cfg), mock.patch.object(
            MODULE, "resolve_automatic_api_key", return_value=automatic
        ) as resolve_auto, mock.patch.object(MODULE, "save_automatic_api_key") as save_key, mock.patch.object(
            MODULE, "save_json_private"
        ):
            settings = MODULE.resolve_settings(request_args("workbuddy", "gpt-5.6-luna"), require_key=True)

        self.assertEqual(settings["api_key"], "saved-key")
        self.assertEqual(settings["stored_automatic_key_matches_runtime"], "true")
        resolve_auto.assert_not_called()
        save_key.assert_not_called()

    def test_saved_automatic_config_is_reused_when_current_lookup_fails(self):
        cfg = {
            "api_key": "saved-key",
            "api_key_origin": "workbuddy-model",
            "api_key_runtime_host": "workbuddy",
            "api_key_runtime_model": "gpt-5.6-luna",
        }
        automatic = {
            "api_key": "",
            "source": "workbuddy-model",
            "reason": "model-not-found",
            "match": "model-not-found",
            "host": "workbuddy",
            "model": "gpt-5.6-luna",
            "host_source": "cli",
            "model_source": "cli",
            "model_is_gpt": "true",
        }
        with mock.patch.object(MODULE, "load_config", return_value=cfg), mock.patch.object(
            MODULE, "resolve_automatic_api_key", return_value=automatic
        ) as resolve_auto, mock.patch.object(MODULE, "save_automatic_api_key") as save_key, mock.patch.object(
            MODULE, "save_json_private"
        ):
            settings = MODULE.resolve_settings(request_args("workbuddy", "gpt-5.6-luna"), require_key=True)

        self.assertEqual(settings["api_key"], "saved-key")
        self.assertEqual(settings["api_key_source"], "config")
        self.assertEqual(settings["stored_automatic_key_matches_runtime"], "true")
        resolve_auto.assert_not_called()
        save_key.assert_not_called()

    def test_manual_configured_key_keeps_precedence(self):
        cfg = {"api_key": "manual-key", "api_key_origin": "manual"}
        automatic = {
            "api_key": "automatic-key",
            "source": "workbuddy-model",
            "reason": "key-available",
            "match": "model-matched",
            "host": "workbuddy",
            "model": "gpt-5.6-luna",
            "host_source": "cli",
            "model_source": "cli",
            "model_is_gpt": "true",
        }
        with mock.patch.object(MODULE, "load_config", return_value=cfg), mock.patch.object(
            MODULE, "resolve_automatic_api_key", return_value=automatic
        ) as resolve_auto, mock.patch.object(MODULE, "save_automatic_api_key") as save_key, mock.patch.object(
            MODULE, "save_json_private"
        ):
            settings = MODULE.resolve_settings(request_args(), require_key=True)

        self.assertEqual(settings["api_key"], "manual-key")
        self.assertEqual(settings["api_key_source"], "config")
        resolve_auto.assert_not_called()
        save_key.assert_not_called()

    def test_codex_config_automatic_key_is_persisted(self):
        cfg = {}
        automatic = {
            "api_key": "config-key",
            "source": "codex-config",
            "reason": "key-available",
            "match": "config-file",
            "host": "codex",
            "model": "gpt-6.1-sol",
            "host_source": "cli",
            "model_source": "cli",
            "model_is_gpt": "true",
        }
        with mock.patch.object(MODULE, "load_config", return_value=cfg), mock.patch.object(
            MODULE, "resolve_automatic_api_key", return_value=automatic
        ), mock.patch.object(MODULE, "save_automatic_api_key") as save_key, mock.patch.object(
            MODULE, "save_json_private"
        ):
            settings = MODULE.resolve_settings(request_args("codex", "gpt-6.1-sol"), require_key=True)

        self.assertEqual(settings["api_key"], "config-key")
        self.assertEqual(settings["api_key_source"], "codex-config")
        self.assertEqual(settings["automatic_api_key_persisted"], "true")
        save_key.assert_called_once_with(cfg, automatic)

    def test_codex_config_key_persistence_and_show_config_source(self):
        parser = MODULE.build_parser()
        token = "sk-config-key"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            codex_dir = pathlib.Path(directory) / ".codex"
            codex_dir.mkdir(parents=True)
            (codex_dir / "config.toml").write_text(
                "model = 'gpt-6.1-sol'\n"
                "\n"
                "[model_providers.custom]\n"
                "experimental_bearer_token = '" + token + "'\n",
                encoding="utf-8",
            )
            generate_args = parser.parse_args(
                [
                    "generate",
                    "--runtime-host",
                    "codex",
                    "--runtime-model",
                    "gpt-6.1-sol",
                    "--prompt",
                    "test",
                ]
            )
            settings = MODULE.resolve_settings(generate_args, require_key=True)
            self.assertEqual(settings["api_key_source"], "codex-config")
            self.assertEqual(settings["automatic_api_key_persisted"], "true")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    MODULE.command_show_config(
                        parser.parse_args(
                            ["show-config", "--runtime-host", "codex", "--runtime-model", "gpt-6.1-sol"]
                        )
                    ),
                    0,
                )

        self.assertIn("STORED_API_KEY_ORIGIN=codex-config", output.getvalue())
        self.assertIn("API_KEY_SOURCE=config", output.getvalue())
        self.assertNotIn(token, output.getvalue())


class RuntimeArgumentTests(unittest.TestCase):
    def test_help_reports_host_specific_default_outputs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(MODULE.command_help(argparse.Namespace()), 0)

        help_text = output.getvalue()
        self.assertIn("Codex: saves under ~/Pictures/IntelAlloc/Codex", help_text)
        self.assertIn("WorkBuddy: saves under ~/Pictures/IntelAlloc/WorkBuddy", help_text)
        self.assertIn("Unknown host: keeps ~/Pictures/IntelAlloc", help_text)

    def test_help_reports_labeled_sizes_and_model_characteristics(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(MODULE.command_help(argparse.Namespace()), 0)

        help_text = output.getvalue()
        expected_presets = (
            "1536x1024 - 横图 / Landscape",
            "1024x1536 - 竖图 / Portrait",
            "1024x1024 - 方图 / Square",
            "2048x1152 - 高清横图 / HD Landscape",
            "1152x2048 - 高清竖图 / HD Portrait",
            "2048x2048 - 高清方图 / HD Square",
            "3840x2160 - 4K 横图 / 4K Landscape",
            "2160x3840 - 4K 竖图 / 4K Portrait",
        )
        for preset in expected_presets:
            with self.subTest(preset=preset):
                self.assertIn(preset, help_text)
        self.assertIn("GPT Image 2: compatibility fallback; no xhigh or max / 兼容备选；不支持 xhigh 或 max", help_text)
        self.assertIn("GPT Image 2.5 Flare: fast, for everyday generation / 速度快，适合日常生成", help_text)
        self.assertIn(
            "GPT Image 2.5 Sunburst: higher-quality generation and editing / 面向更高质量生成与编辑", help_text
        )

    def test_all_stateful_commands_accept_workbuddy_runtime_arguments(self):
        parser = MODULE.build_parser()
        commands = (
            ("configure", ["--api-key", "manual-key"]),
            ("show-config", []),
            ("generate", ["--prompt", "test"]),
            ("edit", ["--prompt", "test", "--input", "image.png"]),
            ("batch-edit", ["--prompt", "test", "--input-dir", "images"]),
            ("last", []),
            ("history", []),
        )
        for command, required_args in commands:
            with self.subTest(command=command):
                args = parser.parse_args(
                    [
                        command,
                        "--runtime-host",
                        "workbuddy",
                        "--runtime-model",
                        "gpt-5.6-luna",
                        *required_args,
                    ]
                )
                self.assertEqual(args.runtime_host, "workbuddy")
                self.assertEqual(args.runtime_model, "gpt-5.6-luna")


class HostStateIsolationTests(unittest.TestCase):
    def test_workbuddy_paths_are_macos_home_relative(self):
        mac_home = pathlib.PurePosixPath("/Users/tester")
        with mock.patch.object(MODULE.pathlib.Path, "home", return_value=mac_home), mock.patch.object(
            MODULE.platform, "system", return_value="Darwin"
        ):
            self.assertEqual(
                MODULE.config_path("workbuddy"),
                pathlib.PurePosixPath("/Users/tester/.workbuddy-ai/intelalloc-image/config.json"),
            )
            self.assertEqual(
                MODULE.history_path("workbuddy"),
                pathlib.PurePosixPath("/Users/tester/.workbuddy-ai/intelalloc-image/history.json"),
            )
            self.assertEqual(
                MODULE.workbuddy_models_path(), pathlib.PurePosixPath("/Users/tester/.workbuddy-ai/models.json")
            )
            self.assertEqual(
                MODULE.default_output_dir("workbuddy"),
                pathlib.PurePosixPath("/Users/tester/Pictures/IntelAlloc/WorkBuddy"),
            )

    def test_paths_and_default_outputs_are_host_specific(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            self.assertEqual(
                MODULE.config_path("codex"),
                pathlib.Path(directory) / ".codex" / "intelalloc-image" / "config.json",
            )
            self.assertEqual(
                MODULE.history_path("workbuddy"),
                pathlib.Path(directory) / ".workbuddy-ai" / "intelalloc-image" / "history.json",
            )
            self.assertEqual(
                MODULE.default_output_dir("codex"),
                pathlib.Path(directory) / "Pictures" / "IntelAlloc" / "Codex",
            )
            self.assertEqual(
                MODULE.default_output_dir("workbuddy"),
                pathlib.Path(directory) / "Pictures" / "IntelAlloc" / "WorkBuddy",
            )
            self.assertEqual(MODULE.config_path("unknown"), MODULE.config_path("codex"))
            self.assertEqual(
                MODULE.default_output_dir("unknown"), pathlib.Path(directory) / "Pictures" / "IntelAlloc"
            )

    def test_configure_keeps_codex_and_workbuddy_configs_separate(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            codex_args = parser.parse_args(
                ["configure", "--runtime-host", "codex", "--api-key", "codex-key"]
            )
            workbuddy_args = parser.parse_args(
                ["configure", "--runtime-host", "workbuddy", "--api-key", "workbuddy-key"]
            )
            self.assertEqual(MODULE.command_configure(codex_args), 0)
            self.assertEqual(MODULE.command_configure(workbuddy_args), 0)
            self.assertEqual(MODULE.load_config("codex")["api_key"], "codex-key")
            self.assertEqual(MODULE.load_config("workbuddy")["api_key"], "workbuddy-key")

    def test_history_and_from_last_do_not_cross_hosts(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            codex_image = pathlib.Path(directory) / "codex.png"
            workbuddy_image = pathlib.Path(directory) / "workbuddy.png"
            codex_image.touch()
            workbuddy_image.touch()
            MODULE.add_history({"type": "generate"}, [codex_image], "codex")
            MODULE.add_history({"type": "generate"}, [workbuddy_image], "workbuddy")

            self.assertEqual(MODULE.get_last_output_path("codex"), codex_image.resolve())
            self.assertEqual(MODULE.get_last_output_path("workbuddy"), workbuddy_image.resolve())
            args = argparse.Namespace(inputs=[], input_dir=None, recursive=False, limit=None, from_last=True)
            self.assertEqual(MODULE.resolve_inputs(args, "workbuddy"), [workbuddy_image.resolve()])

    def test_explicit_output_paths_are_not_rewritten(self):
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            explicit_file = MODULE.resolve_output_path(
                argparse.Namespace(output="D:/out/result.png", output_dir=None), "generate", "workbuddy"
            )
        explicit_directory = MODULE.resolve_output_path(
            argparse.Namespace(output=None, output_dir="D:/out"), "generate", "codex"
        )
        self.assertEqual(explicit_file, pathlib.Path("D:/out/result.png"))
        self.assertEqual(explicit_directory.parent, pathlib.Path("D:/out"))
        self.assertEqual(warning.getvalue(), "")


class ImageModelAndParameterTests(unittest.TestCase):
    def test_gpt_image_2_5_defaults_and_qualities(self):
        self.assertEqual(MODULE.DEFAULT_MODEL, "gpt-image-2.5-flare")
        self.assertEqual(MODULE.DEFAULT_SIZE, "auto")
        self.assertEqual(MODULE.DEFAULT_QUALITY, "auto")
        self.assertEqual(MODULE.DEFAULT_PARTIAL_IMAGES, 3)
        self.assertEqual(MODULE.DEFAULT_BACKGROUND, "auto")
        self.assertEqual(MODULE.DEFAULT_OUTPUT_FORMAT, "png")
        self.assertEqual(MODULE.DEFAULT_N, 1)
        self.assertEqual(MODULE.normalize_size(None), "auto")
        for quality in ("auto", "low", "medium", "high", "xhigh", "max"):
            with self.subTest(quality=quality):
                self.assertEqual(MODULE.normalize_quality(quality), quality)

    def test_gpt_image_2_5_parameter_validation(self):
        for value in (0, 1, 2, 3):
            self.assertEqual(MODULE.normalize_partial_images(value), value)
        for value in ("auto", "opaque", "transparent"):
            self.assertEqual(MODULE.normalize_background(value), value)
        for value in ("png", "jpeg", "webp"):
            self.assertEqual(MODULE.normalize_output_format(value), value)
        for value in (1, 3, 10):
            self.assertEqual(MODULE.normalize_n(value), value)
        with self.assertRaises(MODULE.CliError):
            MODULE.normalize_partial_images(4)
        with self.assertRaises(MODULE.CliError):
            MODULE.normalize_n(0)
        with self.assertRaises(MODULE.CliError):
            MODULE.normalize_output_format("gif")
        with self.assertRaises(MODULE.CliError):
            MODULE.validate_output_options("transparent", "jpeg")

    def test_endpoint_normalization_accepts_plain_and_exact_markdown_urls(self):
        endpoint = "https://example.test/v1/images/generations"
        self.assertEqual(MODULE.normalize_endpoint(endpoint, "endpoint"), endpoint)
        self.assertEqual(MODULE.normalize_endpoint("`" + endpoint + "`", "endpoint"), endpoint)
        self.assertEqual(MODULE.normalize_endpoint("[" + endpoint + "](" + endpoint + ")", "endpoint"), endpoint)
        self.assertEqual(MODULE.normalize_endpoint("[generation API](" + endpoint + ")", "endpoint"), endpoint)

        invalid_values = (
            "",
            "ftp://example.test/images",
            "https://",
            "https\\://example.test/images",
            "https://bad host/images",
            "https://user:password@example.test/images",
            "[https://example.test/images]",
        )
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(MODULE.CliError):
                    MODULE.normalize_endpoint(value, "endpoint")

    def test_configure_normalizes_markdown_endpoints_and_reports_them(self):
        parser = MODULE.build_parser()
        generation = "https://example.test/v1/images/generations"
        edits = "https://example.test/v1/images/edits"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            args = parser.parse_args(
                [
                    "configure",
                    "--runtime-host",
                    "codex",
                    "--endpoint",
                    "[generation API](" + generation + ")",
                    "--edits-endpoint",
                    "[edit API](" + edits + ")",
                ]
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(MODULE.command_configure(args), 0)

            cfg = MODULE.load_config("codex")
            self.assertEqual(cfg["endpoint"], generation)
            self.assertEqual(cfg["edits_endpoint"], edits)
            self.assertIn("ENDPOINT=" + generation, output.getvalue())
            self.assertIn("EDITS_ENDPOINT=" + edits, output.getvalue())

    def test_legacy_markdown_endpoints_are_repaired_when_read(self):
        parser = MODULE.build_parser()
        generation = "https://example.test/v1/images/generations"
        edits = "https://example.test/v1/images/edits"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            MODULE.save_json_private(
                MODULE.config_path("codex"),
                {
                    "endpoint": "[generation API](" + generation + ")",
                    "edits_endpoint": "[edit API](" + edits + ")",
                },
            )
            args = parser.parse_args(["show-config", "--runtime-host", "codex"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(MODULE.command_show_config(args), 0)

            cfg = MODULE.load_config("codex")
            self.assertEqual(cfg["endpoint"], generation)
            self.assertEqual(cfg["edits_endpoint"], edits)
            self.assertIn("ENDPOINT=" + generation, output.getvalue())
            self.assertIn("EDITS_ENDPOINT=" + edits, output.getvalue())

    def test_invalid_endpoint_does_not_overwrite_existing_configuration(self):
        parser = MODULE.build_parser()
        original = {
            "endpoint": "https://example.test/v1/images/generations",
            "edits_endpoint": "https://example.test/v1/images/edits",
        }
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            MODULE.save_json_private(MODULE.config_path("codex"), original)
            args = parser.parse_args(
                ["configure", "--runtime-host", "codex", "--endpoint", "https://bad host/v1/images"]
            )
            with self.assertRaises(MODULE.CliError):
                MODULE.command_configure(args)
            self.assertEqual(MODULE.load_config("codex"), original)

            invalid_cfg = dict(original)
            invalid_cfg["edits_endpoint"] = "[unresolved markdown"
            MODULE.save_json_private(MODULE.config_path("codex"), invalid_cfg)
            read_args = parser.parse_args(["show-config", "--runtime-host", "codex"])
            with self.assertRaises(MODULE.CliError):
                MODULE.command_show_config(read_args)
            self.assertEqual(MODULE.load_config("codex"), invalid_cfg)

    def test_invalid_request_endpoint_is_rejected_before_network_call(self):
        generation_settings = {
            "api_key": "test-key",
            "endpoint": "https://bad host/v1/images/generations",
            "model": "gpt-image-2.5-flare",
            "default_size": "auto",
            "default_quality": "auto",
            "user_agent": "test-agent",
        }
        with mock.patch.object(MODULE, "open_request") as open_request:
            with self.assertRaises(MODULE.CliError):
                MODULE.request_generation("test", generation_settings)
        open_request.assert_not_called()

        with tempfile.TemporaryDirectory() as directory:
            image_path = pathlib.Path(directory) / "input.png"
            image_path.write_bytes(b"input")
            edit_settings = {
                "api_key": "test-key",
                "edits_endpoint": "https\\://example.test/v1/images/edits",
                "model": "gpt-image-2.5-flare",
                "default_size": "auto",
                "default_quality": "auto",
                "edit_protocol": "json",
                "user_agent": "test-agent",
            }
            with mock.patch.object(MODULE, "open_request") as open_request:
                with self.assertRaises(MODULE.CliError):
                    MODULE.request_edit("test", [image_path], edit_settings)
            open_request.assert_not_called()

    def test_persistent_model_validation_allows_only_public_models(self):
        for model in MODULE.PERSISTENT_MODELS:
            with self.subTest(model=model):
                self.assertEqual(MODULE.normalize_persistent_model(model), model)
        with self.assertRaises(MODULE.CliError):
            MODULE.normalize_persistent_model("gpt-image-2.5-flare-2026-09-01")

    def test_invalid_persisted_model_blocks_configure_without_writing(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            original = {"model": "legacy-model", "default_quality": "high"}
            MODULE.save_json_private(MODULE.config_path("codex"), original)
            args = parser.parse_args(["configure", "--runtime-host", "codex", "--api-key", "new-key"])
            with self.assertRaises(MODULE.CliError):
                MODULE.command_configure(args)
            self.assertEqual(MODULE.load_config("codex"), original)

    def test_invalid_persisted_model_blocks_generate_before_request(self):
        parser = MODULE.build_parser()
        config = {
            "api_key": "test-key",
            "model": "legacy-model",
            MODULE.MODEL_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.SIZE_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.QUALITY_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
        }
        args = parser.parse_args(["generate", "--runtime-host", "codex", "--prompt", "test"])
        with mock.patch.object(MODULE, "load_config", return_value=dict(config)), mock.patch.object(
            MODULE, "request_generation"
        ) as request:
            with self.assertRaises(MODULE.CliError):
                MODULE.command_generate(args)
            request.assert_not_called()

    def test_valid_model_override_repairs_invalid_persisted_model(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            MODULE.save_json_private(
                MODULE.config_path("codex"), {"model": "legacy-model", "default_quality": "high"}
            )
            args = parser.parse_args(
                ["configure", "--runtime-host", "codex", "--model", "gpt-image-2.5-flare"]
            )
            self.assertEqual(MODULE.command_configure(args), 0)
            self.assertEqual(MODULE.load_config("codex")["model"], "gpt-image-2.5-flare")

    def test_gpt_image_2_rejects_xhigh_and_max(self):
        for quality in ("auto", "low", "medium", "high"):
            with self.subTest(quality=quality):
                MODULE.validate_model_quality("gpt-image-2", quality)
        for quality in ("xhigh", "max"):
            with self.subTest(quality=quality):
                with self.assertRaises(MODULE.CliError):
                    MODULE.validate_model_quality("gpt-image-2", quality)

    def test_custom_size_validation(self):
        for size in ("auto", "1024x640", "1536x864", "2048x1152", "3840x2160"):
            with self.subTest(size=size):
                self.assertEqual(MODULE.normalize_size(size), size)

        invalid_sizes = (
            "1024",
            "0x1024",
            "1025x1024",
            "4096x1024",
            "1024x512",
            "3840x1024",
            "1024x1024x1",
        )
        for size in invalid_sizes:
            with self.subTest(size=size):
                with self.assertRaises(MODULE.CliError):
                    MODULE.normalize_size(size)

    def test_parser_accepts_custom_request_and_default_sizes(self):
        parser = MODULE.build_parser()
        request_args = parser.parse_args(
            [
                "generate",
                "--prompt",
                "test",
                "--size",
                "1536x864",
                "--quality",
                "xhigh",
                "--partial-images",
                "1",
                "--background",
                "transparent",
                "--output-format",
                "webp",
                "--n",
                "3",
            ]
        )
        config_args = parser.parse_args(
            [
                "configure",
                "--default-size",
                "auto",
                "--default-quality",
                "max",
                "--default-partial-images",
                "3",
                "--default-background",
                "opaque",
                "--default-output-format",
                "jpeg",
                "--default-n",
                "2",
            ]
        )
        edit_args = parser.parse_args(
            ["edit", "--prompt", "test", "--input", "input.png", "--edit-protocol", "multipart"]
        )
        self.assertEqual(request_args.size, "1536x864")
        self.assertEqual(request_args.quality, "xhigh")
        self.assertEqual(request_args.partial_images, 1)
        self.assertEqual(request_args.background, "transparent")
        self.assertEqual(request_args.output_format, "webp")
        self.assertEqual(request_args.n, 3)
        self.assertEqual(config_args.default_size, "auto")
        self.assertEqual(config_args.default_quality, "max")
        self.assertEqual(config_args.default_partial_images, 3)
        self.assertEqual(config_args.default_background, "opaque")
        self.assertEqual(config_args.default_output_format, "jpeg")
        self.assertEqual(config_args.default_n, 2)
        self.assertEqual(edit_args.edit_protocol, "multipart")

    def test_edit_protocol_normalization_and_default(self):
        self.assertEqual(MODULE.DEFAULT_EDIT_PROTOCOL, "json")
        self.assertEqual(MODULE.normalize_edit_protocol(None), "json")
        self.assertEqual(MODULE.normalize_edit_protocol("JSON"), "json")
        self.assertEqual(MODULE.normalize_edit_protocol("multipart"), "multipart")
        with self.assertRaises(MODULE.CliError):
            MODULE.normalize_edit_protocol("xml")

    def test_generation_and_edit_payloads_preserve_gpt_image_2_5_parameters(self):
        settings = {
            "model": "gpt-image-2.5-sunburst",
            "default_size": "1536x864",
            "default_quality": "max",
            "partial_images": 3,
            "background": "transparent",
            "output_format": "webp",
            "n": 3,
        }
        body = json.loads(MODULE.build_generation_body("test prompt", settings).decode("utf-8"))
        self.assertEqual(body["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(body["size"], "1536x864")
        self.assertEqual(body["quality"], "max")
        self.assertEqual(body["partial_images"], 3)
        self.assertEqual(body["background"], "transparent")
        self.assertEqual(body["output_format"], "webp")
        self.assertEqual(body["n"], 3)

        with tempfile.TemporaryDirectory() as directory:
            image_path = pathlib.Path(directory) / "input.png"
            image_path.write_bytes(b"input")
            upload = MODULE.UploadImage(
                source_path=image_path,
                upload_path=image_path,
                filename="input.png",
                content_type="image/png",
                optimized=False,
                original_bytes=5,
                upload_bytes=5,
            )
            multipart, _ = MODULE.build_multipart("test prompt", [upload], settings)
            json_body = json.loads(MODULE.build_json_edit_body("test prompt", [upload], settings).decode("utf-8"))

        self.assertIn(b'gpt-image-2.5-sunburst', multipart)
        self.assertIn(b'1536x864', multipart)
        self.assertIn(b'max', multipart)
        self.assertIn(b'webp', multipart)
        self.assertIn(b'partial_images', multipart)
        self.assertIn(b'\r\n3\r\n', multipart)
        self.assertIn(b'transparent', multipart)
        self.assertEqual(json_body["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(json_body["size"], "1536x864")
        self.assertEqual(json_body["quality"], "max")
        self.assertEqual(json_body["partial_images"], 3)
        self.assertEqual(json_body["background"], "transparent")
        self.assertEqual(json_body["output_format"], "webp")
        self.assertEqual(json_body["n"], 3)
        self.assertEqual(json_body["images"][0]["image_url"], "data:image/png;base64,aW5wdXQ=")

    def test_multipart_filename_is_safe_without_changing_upload_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = pathlib.Path(directory) / "original.png"
            image_path.write_bytes(b"original-bytes")
            upload = MODULE.UploadImage(
                source_path=image_path,
                upload_path=image_path,
                filename='resume 1(\"final\")\n.png',
                content_type="image/png",
                optimized=False,
                original_bytes=len(b"original-bytes"),
                upload_bytes=len(b"original-bytes"),
            )
            body, _ = MODULE.build_multipart(
                "test prompt",
                [upload],
                {"model": "gpt-image-2.5-flare", "default_size": "auto", "default_quality": "auto"},
            )

        self.assertEqual(MODULE.sanitize_upload_filename("../照片\\测试.png"), "image.png")
        self.assertIn(b'filename="resume_1_final.png"', body)
        self.assertNotIn(b"\n.png", body)
        self.assertIn(b"original-bytes", body)

    def test_multipart_upload_preparation_preserves_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in ("one.png", "two.png"):
                path = pathlib.Path(directory) / name
                path.write_bytes(b"original")
                paths.append(path)
            uploads = MODULE.prepare_upload_images(paths, allow_optimization=False)

        self.assertEqual([upload.upload_path for upload in uploads], paths)
        self.assertEqual([upload.optimized for upload in uploads], [False, False])
        self.assertEqual([upload.content_type for upload in uploads], ["image/png", "image/png"])

    def test_request_edit_disables_optimization_for_multipart(self):
        path = pathlib.Path("input.png")
        settings = {"edit_protocol": "multipart", "edits_endpoint": "https://example.test/v1/images/edits"}
        with mock.patch.object(MODULE, "prepare_upload_images", return_value=[]) as prepare_uploads, mock.patch.object(
            MODULE, "timed_api_request", return_value=[b"result"]
        ) as timed_request:
            self.assertEqual(MODULE.request_edit("test", [path], settings), [b"result"])
        prepare_uploads.assert_called_once_with([path], allow_optimization=False)
        timed_request.assert_called_once()

    def test_transparent_images_are_not_jpeg_optimized(self):
        class FakeImage:
            mode = "RGBA"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def getbands(self):
                return ("R", "G", "B", "A")

            def thumbnail(self, size, resample):
                pass

        fake_image_module = types.ModuleType("PIL.Image")
        fake_image_module.open = lambda path: FakeImage()
        fake_image_module.Resampling = types.SimpleNamespace(LANCZOS=1)
        fake_image_module.BICUBIC = 1
        fake_image_ops = types.ModuleType("PIL.ImageOps")
        fake_image_ops.exif_transpose = lambda image: image
        fake_pil = types.ModuleType("PIL")
        fake_pil.Image = fake_image_module
        fake_pil.ImageOps = fake_image_ops

        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            sys.modules,
            {"PIL": fake_pil, "PIL.Image": fake_image_module, "PIL.ImageOps": fake_image_ops},
        ):
            path = pathlib.Path(directory) / "transparent.png"
            path.write_bytes(b"transparent")
            upload = MODULE.maybe_optimize_image(path, force=True)

        self.assertFalse(upload.optimized)
        self.assertEqual(upload.upload_path, path)
        self.assertEqual(upload.content_type, "image/png")

    def test_edit_protocol_config_precedence(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            configure_args = parser.parse_args(
                ["configure", "--runtime-host", "codex", "--edit-protocol", "multipart"]
            )
            self.assertEqual(MODULE.command_configure(configure_args), 0)
            self.assertEqual(MODULE.load_config("codex")["edit_protocol"], "multipart")

            persisted_args = parser.parse_args(
                ["edit", "--runtime-host", "codex", "--prompt", "test", "--input", "input.png"]
            )
            persisted = MODULE.resolve_settings(persisted_args, require_key=False)
            self.assertEqual(persisted["edit_protocol"], "multipart")

            override_args = parser.parse_args(
                [
                    "edit",
                    "--runtime-host",
                    "codex",
                    "--edit-protocol",
                    "json",
                    "--prompt",
                    "test",
                    "--input",
                    "input.png",
                ]
            )
            override = MODULE.resolve_settings(override_args, require_key=False)
            self.assertEqual(override["edit_protocol"], "json")

    def test_image_parameter_config_precedence(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            configure_args = parser.parse_args(
                [
                    "configure",
                    "--runtime-host",
                    "codex",
                    "--default-partial-images",
                    "1",
                    "--default-background",
                    "opaque",
                    "--default-output-format",
                    "webp",
                    "--default-n",
                    "2",
                ]
            )
            self.assertEqual(MODULE.command_configure(configure_args), 0)

            persisted_args = parser.parse_args(["generate", "--runtime-host", "codex", "--prompt", "test"])
            persisted = MODULE.resolve_settings(persisted_args, require_key=False)
            self.assertEqual(persisted["partial_images"], 1)
            self.assertEqual(persisted["background"], "opaque")
            self.assertEqual(persisted["output_format"], "webp")
            self.assertEqual(persisted["n"], 2)

            override_args = parser.parse_args(
                [
                    "generate",
                    "--runtime-host",
                    "codex",
                    "--partial-images",
                    "3",
                    "--background",
                    "transparent",
                    "--output-format",
                    "png",
                    "--n",
                    "4",
                    "--prompt",
                    "test",
                ]
            )
            override = MODULE.resolve_settings(override_args, require_key=False)
            self.assertEqual(override["partial_images"], 3)
            self.assertEqual(override["background"], "transparent")
            self.assertEqual(override["output_format"], "png")
            self.assertEqual(override["n"], 4)

    def test_json_and_stream_responses_return_all_final_images(self):
        json_images = MODULE.read_images_from_json(
            json.dumps(
                {
                    "data": [
                        {"partial_image_b64": "cGFydGlhbA=="},
                        {"b64_json": "aA=="},
                        {"b64_json": "aA=="},
                        {"b64_json": "aQ=="},
                    ]
                }
            )
        )
        self.assertEqual(json_images, [b"h", b"h", b"i"])

        stream = "\n".join(
            [
                'event: response.image_generation_call.partial_image',
                'data: {"type":"response.image_generation_call.partial_image","partial_image_b64":"cGFydGlhbA=="}',
                "",
                'event: response.completed',
                'data: {"type":"response.completed","response":{"output":[{"result":"Zmlyc3Q="},{"result":"Zmlyc3Q="},{"result":"c2Vjb25k"}]}}',
                "",
            ]
        )
        self.assertEqual(MODULE.read_streamed_images(stream), [b"first", b"first", b"second"])

    def test_multi_output_paths_and_format_extensions(self):
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            rewritten = MODULE.resolve_output_path(
                argparse.Namespace(output="/tmp/result.png", output_dir=None), "generate", "codex", "webp"
            )
        self.assertEqual(rewritten, pathlib.Path("/tmp/result.webp"))
        self.assertIn("扩展名 .png 与输出格式 webp 不一致", warning.getvalue())
        self.assertIn("/tmp/result.webp", warning.getvalue())

        matching_warning = io.StringIO()
        with contextlib.redirect_stderr(matching_warning):
            matching = MODULE.resolve_output_path(
                argparse.Namespace(output="/tmp/result.webp", output_dir=None), "generate", "codex", "webp"
            )
        self.assertEqual(matching, pathlib.Path("/tmp/result.webp"))
        self.assertEqual(matching_warning.getvalue(), "")

        automatic_warning = io.StringIO()
        with contextlib.redirect_stderr(automatic_warning):
            automatic = MODULE.resolve_output_path(
                argparse.Namespace(output=None, output_dir="/tmp/results"), "generate", "codex", "webp"
            )
        self.assertEqual(automatic.suffix, ".webp")
        self.assertEqual(automatic_warning.getvalue(), "")
        base = pathlib.Path("/tmp/result.png")
        self.assertEqual(MODULE.indexed_output_path(base, 1, 3), pathlib.Path("/tmp/result-001.png"))
        self.assertEqual(MODULE.indexed_output_path(base, 3, 3), pathlib.Path("/tmp/result-003.png"))
        self.assertEqual(MODULE.output_name_for(pathlib.Path("source.png"), 2, "webp"), "source-002.webp")
        self.assertEqual(
            MODULE.output_name_for(pathlib.Path("source.png"), 2, "jpeg", 3, 3), "source-002-003.jpeg"
        )

    def test_save_images_writes_all_variants_with_sequence_suffixes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory) / "result.webp"
            saved = MODULE.save_images(base, [b"one", b"two", b"three"])
            self.assertEqual(
                saved,
                [
                    (pathlib.Path(directory) / "result-001.webp").resolve(),
                    (pathlib.Path(directory) / "result-002.webp").resolve(),
                    (pathlib.Path(directory) / "result-003.webp").resolve(),
                ],
            )
            self.assertEqual([path.read_bytes() for path in saved], [b"one", b"two", b"three"])

    def test_http_400_does_not_trigger_multipart_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = pathlib.Path(directory) / "input.png"
            image_path.write_bytes(b"input")
            settings = {
                "api_key": "test-key",
                "model": "gpt-image-2.5-flare",
                "default_size": "auto",
                "default_quality": "auto",
                "edit_protocol": "json",
                "edits_endpoint": "https://example.test/v1/images/edits",
                "user_agent": "test-agent",
            }
            error = urllib.error.HTTPError(
                settings["edits_endpoint"],
                400,
                "Bad Request",
                {},
                io.BytesIO(b'{"error":{"message":"Bad Request"}}'),
            )
            with mock.patch.object(MODULE, "open_request", side_effect=error) as open_request:
                with self.assertRaises(MODULE.ApiResponseError):
                    MODULE.request_edit("test", [image_path], settings)
            self.assertEqual(open_request.call_count, 1)

    def test_batch_history_is_saved_incrementally_and_marks_partial_failure(self):
        parser = MODULE.build_parser()
        settings = {
            "runtime_host": "codex",
            "model": "gpt-image-2.5-flare",
            "default_size": "auto",
            "default_quality": "auto",
            "partial_images": 3,
            "background": "auto",
            "output_format": "png",
            "n": 1,
        }
        with tempfile.TemporaryDirectory() as home, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(home)
        ), tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
            first = pathlib.Path(input_dir) / "first.png"
            second = pathlib.Path(input_dir) / "second.png"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            args = parser.parse_args(
                [
                    "batch-edit",
                    "--prompt",
                    "test",
                    "--input-dir",
                    input_dir,
                    "--output-dir",
                    output_dir,
                ]
            )

            observed_statuses = []

            def request_side_effect(prompt, inputs, resolved_settings):
                observed_statuses.append(MODULE.load_history("codex")["items"][0]["status"])
                if inputs[0] == first.resolve():
                    return [b"edited-first"]
                raise MODULE.ApiResponseError("upstream key=sk-test-secret", status=400)

            with mock.patch.object(MODULE, "resolve_settings", return_value=settings), mock.patch.object(
                MODULE, "request_edit", side_effect=request_side_effect
            ):
                with self.assertRaises(MODULE.ApiResponseError):
                    MODULE.command_batch_edit(args)

            history = MODULE.load_history("codex")
            item = history["items"][0]
            self.assertEqual(observed_statuses, ["running", "running"])
            self.assertEqual(item["status"], "partial")
            self.assertEqual(len(item["completed_items"]), 1)
            self.assertEqual(len(item["failed_items"]), 1)
            self.assertEqual(item["outputs"], [str((pathlib.Path(output_dir) / "first-001.png").resolve())])
            self.assertEqual(history["last_output"], item["outputs"][0])
            self.assertNotIn("sk-test-secret", json.dumps(item))

    def test_api_error_redaction_preserves_non_secret_text(self):
        body = 'message=failed key=sk-proj-abc.DEF_123~xyz Authorization: Bearer sk-live-secret'
        redacted = MODULE.redact_sensitive_text(body)
        self.assertEqual(
            redacted,
            "message=failed key=[REDACTED_API_KEY] Authorization: Bearer [REDACTED]",
        )

    def test_batch_history_is_marked_succeeded_after_all_items(self):
        parser = MODULE.build_parser()
        settings = {
            "runtime_host": "codex",
            "model": "gpt-image-2.5-flare",
            "default_size": "auto",
            "default_quality": "auto",
            "partial_images": 3,
            "background": "auto",
            "output_format": "png",
            "n": 1,
        }
        with tempfile.TemporaryDirectory() as home, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(home)
        ), tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
            source = pathlib.Path(input_dir) / "source.png"
            source.write_bytes(b"source")
            args = parser.parse_args(
                ["batch-edit", "--prompt", "test", "--input-dir", input_dir, "--output-dir", output_dir]
            )
            with mock.patch.object(MODULE, "resolve_settings", return_value=settings), mock.patch.object(
                MODULE, "request_edit", return_value=[b"edited"]
            ):
                self.assertEqual(MODULE.command_batch_edit(args), 0)

            item = MODULE.load_history("codex")["items"][0]
            self.assertEqual(item["status"], "succeeded")
            self.assertEqual(len(item["completed_items"]), 1)
            self.assertEqual(item["failed_items"], [])

    def test_request_metadata_includes_model(self):
        output = io.StringIO()
        settings = {
            "model": "gpt-image-2.5-flare",
            "default_size": "auto",
            "default_quality": "auto",
        }
        with contextlib.redirect_stderr(output):
            MODULE.print_request_options(settings)

        self.assertIn("REQUEST_MODEL=gpt-image-2.5-flare", output.getvalue())
        self.assertIn("REQUEST_SIZE=auto", output.getvalue())
        self.assertIn("REQUEST_QUALITY=auto", output.getvalue())
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "REQUEST_MODEL=gpt-image-2.5-flare",
                "REQUEST_SIZE=auto",
                "REQUEST_QUALITY=auto",
                "REQUEST_PARTIAL_IMAGES=3",
                "REQUEST_BACKGROUND=auto",
                "REQUEST_OUTPUT_FORMAT=png",
                "REQUEST_N=1",
            ],
        )

    def test_legacy_defaults_migrate_once(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            cfg = {
                "model": "gpt-image-2",
                "default_size": "2048x1152",
                "default_quality": "medium",
            }
            self.assertTrue(MODULE.migrate_gpt_image_2_5_defaults(cfg, "codex"))
            self.assertEqual(cfg["model"], "gpt-image-2.5-flare")
            self.assertEqual(cfg["default_size"], "auto")
            self.assertEqual(cfg["default_quality"], "auto")
            self.assertFalse(MODULE.migrate_gpt_image_2_5_defaults(cfg, "codex"))

    def test_explicit_post_upgrade_model_choice_is_not_migrated_again(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            MODULE.save_json_private(
                MODULE.config_path("codex"),
                {"model": "gpt-image-2", "default_size": "2048x1152", "default_quality": "medium"},
            )
            args = parser.parse_args(["configure", "--runtime-host", "codex", "--model", "gpt-image-2"])
            self.assertEqual(MODULE.command_configure(args), 0)
            cfg = MODULE.load_config("codex")
            MODULE.migrate_gpt_image_2_5_defaults(cfg, "codex")
            self.assertEqual(cfg["model"], "gpt-image-2")
            self.assertEqual(cfg["default_size"], "auto")
            self.assertEqual(cfg["default_quality"], "auto")

    def test_incompatible_model_and_quality_do_not_partially_update_config(self):
        parser = MODULE.build_parser()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.pathlib.Path, "home", return_value=pathlib.Path(directory)
        ):
            original = {"model": "gpt-image-2.5-flare", "default_quality": "max"}
            MODULE.save_json_private(MODULE.config_path("codex"), original)
            args = parser.parse_args(
                [
                    "configure",
                    "--runtime-host",
                    "codex",
                    "--model",
                    "gpt-image-2",
                    "--default-quality",
                    "max",
                ]
            )
            with self.assertRaises(MODULE.CliError):
                MODULE.command_configure(args)
            self.assertEqual(MODULE.load_config("codex"), original)

    def test_image_2_incompatible_quality_is_rejected_before_request(self):
        parser = MODULE.build_parser()
        config = {
            "api_key": "test-key",
            "model": "gpt-image-2",
            "default_quality": "xhigh",
            MODULE.MODEL_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.SIZE_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.QUALITY_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
        }
        commands = (
            ("generate", ["generate", "--prompt", "test"], "request_generation"),
            ("edit", ["edit", "--prompt", "test", "--input", "input.png"], "request_edit"),
            ("batch-edit", ["batch-edit", "--prompt", "test", "--input-dir", "inputs"], "request_edit"),
        )
        for name, argv, request_name in commands:
            with self.subTest(command=name), mock.patch.object(MODULE, "load_config", return_value=dict(config)), mock.patch.object(
                MODULE, request_name
            ) as request:
                args = parser.parse_args(argv)
                with self.assertRaises(MODULE.CliError):
                    args.func(args)
                request.assert_not_called()

    def test_hidden_request_model_override_does_not_change_saved_model(self):
        parser = MODULE.build_parser()
        config = {
            "api_key": "test-key",
            "model": "gpt-image-2.5-flare",
            MODULE.MODEL_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.SIZE_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.QUALITY_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
        }
        args = parser.parse_args(["generate", "--prompt", "test", "--model", "diagnostic-model"])
        with mock.patch.object(MODULE, "load_config", return_value=config):
            settings = MODULE.resolve_settings(args, require_key=True)
        self.assertEqual(settings["model"], "diagnostic-model")
        self.assertEqual(config["model"], "gpt-image-2.5-flare")

    def test_model_api_error_does_not_change_saved_model_or_retry_with_fallback(self):
        parser = MODULE.build_parser()
        config = {
            "api_key": "test-key",
            "model": "gpt-image-2.5-flare",
            MODULE.MODEL_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.SIZE_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
            MODULE.QUALITY_MIGRATION_KEY: MODULE.GPT_IMAGE_2_5_MIGRATION_VERSION,
        }
        args = parser.parse_args(["generate", "--prompt", "test", "--model", "unavailable-model"])
        with mock.patch.object(MODULE, "load_config", return_value=config), mock.patch.object(
            MODULE, "request_generation", side_effect=MODULE.ApiResponseError("unknown model", status=400)
        ) as request:
            with self.assertRaises(MODULE.ApiResponseError):
                MODULE.command_generate(args)
        self.assertEqual(config["model"], "gpt-image-2.5-flare")
        request.assert_called_once()
        self.assertEqual(request.call_args.args[1]["model"], "unavailable-model")


if __name__ == "__main__":
    unittest.main()
