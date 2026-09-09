import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
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
        explicit_file = MODULE.resolve_output_path(
            argparse.Namespace(output="D:/out/result.png", output_dir=None), "generate", "workbuddy"
        )
        explicit_directory = MODULE.resolve_output_path(
            argparse.Namespace(output=None, output_dir="D:/out"), "generate", "codex"
        )
        self.assertEqual(explicit_file, pathlib.Path("D:/out/result.png"))
        self.assertEqual(explicit_directory.parent, pathlib.Path("D:/out"))


class ImageModelAndParameterTests(unittest.TestCase):
    def test_gpt_image_2_5_defaults_and_qualities(self):
        self.assertEqual(MODULE.DEFAULT_MODEL, "gpt-image-2.5-flare")
        self.assertEqual(MODULE.DEFAULT_SIZE, "auto")
        self.assertEqual(MODULE.DEFAULT_QUALITY, "auto")
        self.assertEqual(MODULE.normalize_size(None), "auto")
        for quality in ("auto", "low", "medium", "high", "xhigh", "max"):
            with self.subTest(quality=quality):
                self.assertEqual(MODULE.normalize_quality(quality), quality)

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
            ["generate", "--prompt", "test", "--size", "1536x864", "--quality", "xhigh"]
        )
        config_args = parser.parse_args(["configure", "--default-size", "auto", "--default-quality", "max"])
        self.assertEqual(request_args.size, "1536x864")
        self.assertEqual(request_args.quality, "xhigh")
        self.assertEqual(config_args.default_size, "auto")
        self.assertEqual(config_args.default_quality, "max")

    def test_generation_and_edit_payloads_preserve_gpt_image_2_5_parameters(self):
        settings = {
            "model": "gpt-image-2.5-sunburst",
            "default_size": "1536x864",
            "default_quality": "max",
        }
        body = json.loads(MODULE.build_generation_body("test prompt", settings).decode("utf-8"))
        self.assertEqual(body["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(body["size"], "1536x864")
        self.assertEqual(body["quality"], "max")

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

        self.assertIn(b'gpt-image-2.5-sunburst', multipart)
        self.assertIn(b'1536x864', multipart)
        self.assertIn(b'max', multipart)

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
