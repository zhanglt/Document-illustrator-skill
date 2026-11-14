"""验证配置路径不受 Agent 安装目录或工作目录影响。"""

import os
import subprocess
import sys
import tempfile
import unittest
import argparse
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import env_config
import image_api


class EnvConfigTests(unittest.TestCase):
    def setUp(self):
        sections = patch.object(env_config, "_sections", {})
        sections.start()
        self.addCleanup(sections.stop)
        selected = patch.object(env_config, "_configured_provider", None)
        selected.start()
        self.addCleanup(selected.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / ".agents/skills/document-illustrator/.env"
        self.legacy = self.home / ".claude/skills/document-illustrator/.env"
        self.workdir = self.home / "work"
        self.workdir.mkdir()
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text("ILLUSTRATOR_TEST_CONFIG=legacy\n", encoding="utf-8")
        (self.workdir / ".env").write_text("ILLUSTRATOR_TEST_CONFIG=cwd\n", encoding="utf-8")

    def test_only_shared_path_is_loaded(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("ILLUSTRATOR_TEST_CONFIG=shared\n", encoding="utf-8")
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ):
            os.environ["ILLUSTRATOR_TEST_CONFIG"] = "process"
            self.assertTrue(env_config.find_and_load_env())
            self.assertEqual(os.environ["ILLUSTRATOR_TEST_CONFIG"], "shared")

    def test_global_proxy_from_shared_env(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=image2-4k\nPROXY=http://127.0.0.1:81\n"
            "[image2-4k]\nPROXY=http://wrong.example:82\n",
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            self.assertEqual(env_config.get_proxy_url(), "http://127.0.0.1:81")

    def test_image2_4k_default_selects_matching_section(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=image2-4k\n"
            "[nanobanana]\nNEBULA_NANOBANANA_API_KEY=banana-test\n"
            "[image2-4k]\nNEBULA_API_KEY=4k-test\n",
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            args = SimpleNamespace(provider=None, ratio=None, resolution=None)
            image_api.resolve_options(argparse.ArgumentParser(), args)
            self.assertEqual((args.provider, args.ratio, args.resolution), ("image2-4k", "16:9", "4K"))
            config = env_config.get_provider_config(args.provider)
            self.assertEqual(config["NEBULA_API_KEY"], "4k-test")
            self.assertNotIn("NEBULA_NANOBANANA_API_KEY", config)

    def test_cihebi_section_is_selected_without_other_keys(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=cihebi\n"
            "[image2-4k]\nNEBULA_API_KEY=other-key\n"
            "[cihebi]\nCIHEBI_IMAGE_API_KEY=cihebi-key\nCIHEBI_IMAGE_SIZE=1254x1254\n",
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            args = SimpleNamespace(provider=None, ratio=None, resolution=None)
            image_api.resolve_options(argparse.ArgumentParser(), args)
            self.assertEqual(args.provider, "cihebi")
            config = env_config.get_provider_config(args.provider)
            self.assertEqual(config["CIHEBI_IMAGE_API_KEY"], "cihebi-key")
            self.assertNotIn("NEBULA_API_KEY", config)

    def test_invalid_proxy_is_rejected(self):
        for value in ("socks5://127.0.0.1:81", "http://", "http://127.0.0.1:bad"):
            with self.subTest(value=value), patch.dict(os.environ, {"PROXY": value}):
                with self.assertRaisesRegex(ValueError, "PROXY"):
                    env_config.get_proxy_url()

    def test_image_options_from_shared_env_and_cli_lock(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=nanobanana\n"
            "ILLUSTRATOR_SINGLE_RATIO=3:4\n"
            "ILLUSTRATOR_BATCH_RATIO=16:9\n"
            "ILLUSTRATOR_RESOLUTION=1K\n", encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            for batch, ratio in ((False, "3:4"), (True, "16:9")):
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                image_api.resolve_options(argparse.ArgumentParser(), args, batch=batch)
                self.assertEqual((args.provider, args.ratio, args.resolution), ("nanobanana", ratio, "1K"))
            args = SimpleNamespace(provider="image2-4k", ratio="16:9", resolution="4K")
            with self.assertRaises(SystemExit):
                image_api.resolve_options(argparse.ArgumentParser(), args, batch=True)

    def test_invalid_env_options_fail_before_request(self):
        cases = [
            {"ILLUSTRATOR_SINGLE_RATIO": "invalid"},
            {"ILLUSTRATOR_BATCH_RATIO": "invalid"},
            {"ILLUSTRATOR_RESOLUTION": "8K"},
            {"ILLUSTRATOR_IMAGE_PROVIDER": "image2-4k", "ILLUSTRATOR_BATCH_RATIO": "3:4"},
            {"ILLUSTRATOR_IMAGE_PROVIDER": "image2-4k", "ILLUSTRATOR_RESOLUTION": "2K"},
        ]
        parser = unittest.mock.Mock()
        parser.error.side_effect = ValueError("配置错误")
        for env in cases:
            selected = env.get("ILLUSTRATOR_IMAGE_PROVIDER", "gemini")
            with self.subTest(env=env), patch.object(env_config, "_configured_provider", selected), patch.dict(os.environ, env, clear=True), patch.object(image_api, "read_request") as read:
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                with self.assertRaisesRegex(ValueError, "配置错误"):
                    image_api.resolve_options(parser, args, batch="ILLUSTRATOR_SINGLE_RATIO" not in env)
                read.assert_not_called()

    def test_missing_provider_fails_and_configured_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "必须在共享 .env 顶层设置"):
                image_api.get_provider()
            for provider, resolution in (("nanobanana", "2K"), ("gemini", "2K"), ("image2-4k", "4K")):
                with patch.object(env_config, "_configured_provider", provider):
                    args = SimpleNamespace(provider=provider, ratio=None, resolution=None)
                    image_api.resolve_options(argparse.ArgumentParser(), args, batch=True)
                    self.assertEqual((args.ratio, args.resolution), ("16:9", resolution))

    def test_missing_shared_file_preserves_environment(self):
        with patch.object(Path, "home", return_value=self.home), patch.dict(
            os.environ, {"ILLUSTRATOR_TEST_CONFIG": "process"}
        ), patch.object(env_config, "dotenv_values") as load:
            self.assertFalse(env_config.find_and_load_env())
            self.assertEqual(os.environ["ILLUSTRATOR_TEST_CONFIG"], "process")
            load.assert_not_called()

    def test_sections_select_keys_model_and_options_without_leaking(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=nanobanana\n"
            "ILLUSTRATOR_RESOLUTION=1K\n"
            "[image2-4k]\nNEBULA_API_KEY=4k-test\nILLUSTRATOR_RESOLUTION=4K\n"
            "[nanobanana]\nNEBULA_NANOBANANA_API_KEY=banana-test\n"
            "NEBULA_NANOBANANA_MODEL=gemini-3-pro-image-preview\n"
            "ILLUSTRATOR_IMAGE_PROVIDER=image2-4k\nILLUSTRATOR_SINGLE_RATIO=3:4\n"
            "ILLUSTRATOR_BATCH_RATIO=3:4\nILLUSTRATOR_RESOLUTION=2K\n",
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            for provider, ratio, resolution in ((None, "3:4", "2K"), ("nanobanana", "3:4", "2K")):
                for batch in (True, False):
                    args = SimpleNamespace(provider=provider, ratio=None, resolution=None)
                    image_api.resolve_options(argparse.ArgumentParser(), args, batch=batch)
                    self.assertEqual((args.ratio, args.resolution), (ratio, resolution))
            self.assertEqual(image_api.get_provider(), "nanobanana")
            self.assertEqual(env_config.get_provider_config("image2-4k")["NEBULA_API_KEY"], "4k-test")
            banana = env_config.get_provider_config("nanobanana")
            self.assertEqual(banana["NEBULA_NANOBANANA_API_KEY"], "banana-test")
            self.assertEqual(banana["NEBULA_NANOBANANA_MODEL"], "gemini-3-pro-image-preview")
            self.assertNotIn("NEBULA_NANOBANANA_API_KEY", env_config.get_provider_config("image2-4k"))
            with self.assertRaisesRegex(ValueError, "锁定"):
                image_api.get_provider("image2-4k")
            args = SimpleNamespace(provider=None, ratio="16:9", resolution="4K")
            image_api.resolve_options(argparse.ArgumentParser(), args)
            self.assertEqual((args.ratio, args.resolution), ("16:9", "4K"))

    def test_quotes_comments_and_multiline_values(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            'ILLUSTRATOR_IMAGE_PROVIDER=nanobanana\n'
            'ILLUSTRATOR_TEST_CONFIG="first\n[nanobanana]\nlast"\n'
            '[nanobanana] # 图片参数\nILLUSTRATOR_RESOLUTION="2K" # 注释\n',
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            self.assertEqual(os.environ["ILLUSTRATOR_TEST_CONFIG"], "first\n[nanobanana]\nlast")
            self.assertEqual(env_config.get_provider_config("nanobanana")["ILLUSTRATOR_RESOLUTION"], "2K")

    def test_expected_group_layout_uses_backend_specific_defaults(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "#值为nanobanana或者image2-4k\nILLUSTRATOR_IMAGE_PROVIDER=nanobanana\n\n"
            "[nanobanana]\nNEBULA_NANOBANANA_API_KEY=banana-test\n"
            "NEBULA_NANOBANANA_MODEL=gemini-3.1-flash-image\n"
            "ILLUSTRATOR_SINGLE_RATIO=16:9\nILLUSTRATOR_BATCH_RATIO=16:9\nILLUSTRATOR_RESOLUTION=2K\n\n"
            "[image2-4k]\nNEBULA_API_KEY=4k-test\nNEBULA_MODEL=gpt-image-2-4k\n"
            "NEBULA_SIZE=3840x2160\nNEBULA_QUALITY=high\n", encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            for provider, resolution in ((None, "2K"), ("nanobanana", "2K")):
                for batch in (False, True):
                    args = SimpleNamespace(provider=provider, ratio=None, resolution=None)
                    image_api.resolve_options(argparse.ArgumentParser(), args, batch=batch)
                    self.assertEqual((args.ratio, args.resolution), ("16:9", resolution))
            with patch.dict(os.environ, {"ILLUSTRATOR_IMAGE_PROVIDER": "image2-4k"}):
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                image_api.resolve_options(argparse.ArgumentParser(), args)
                self.assertEqual((args.provider, args.resolution), ("nanobanana", "2K"))

    def test_native_gemini_section_is_isolated_and_selected(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            "ILLUSTRATOR_IMAGE_PROVIDER=gemini\n"
            "[nanobanana]\nNEBULA_NANOBANANA_API_KEY=banana-test\nILLUSTRATOR_RESOLUTION=1K\n"
            "[image2-4k]\nNEBULA_API_KEY=nebula-test\nNEBULA_SIZE=3840x2160\n"
            "[gemini]\nGEMINI_API_KEY=google-test\nGEMINI_MODEL=gemini-3.1-flash-image\n"
            "ILLUSTRATOR_SINGLE_RATIO=3:4\nILLUSTRATOR_BATCH_RATIO=16:9\nILLUSTRATOR_RESOLUTION=4K\n",
            encoding="utf-8",
        )
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, {}, clear=True):
            env_config.find_and_load_env()
            for batch, ratio in ((False, "3:4"), (True, "16:9")):
                args = SimpleNamespace(provider=None, ratio=None, resolution=None)
                image_api.resolve_options(argparse.ArgumentParser(), args, batch=batch)
                self.assertEqual((args.provider, args.ratio, args.resolution), ("gemini", ratio, "4K"))
            config = env_config.get_provider_config("gemini")
            self.assertEqual(config["GEMINI_API_KEY"], "google-test")
            self.assertEqual(config["GEMINI_MODEL"], "gemini-3.1-flash-image")
            self.assertNotIn("NEBULA_API_KEY", config)
            self.assertNotIn("NEBULA_NANOBANANA_API_KEY", config)
            self.assertNotIn("GEMINI_API_KEY", env_config.get_provider_config("nanobanana"))
            args = SimpleNamespace(provider="nanobanana", ratio=None, resolution=None)
            with self.assertRaises(SystemExit):
                image_api.resolve_options(argparse.ArgumentParser(), args)

    def test_invalid_group_fails_without_exposing_values(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("[typo]\nSECRET=test-secret\n", encoding="utf-8")
        with patch.object(Path, "home", return_value=self.home):
            with self.assertRaises(ValueError) as caught:
                env_config.find_and_load_env()
        self.assertNotIn("test-secret", str(caught.exception))

    def test_both_entrypoints_from_another_working_directory(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text("ILLUSTRATOR_TEST_CONFIG=shared\n", encoding="utf-8")
        for filename in ("generate_single_image.py", "generate_illustrations.py"):
            with self.subTest(script=filename):
                self.assert_entrypoint_config(filename, "shared")

    def test_entrypoints_do_not_search_legacy_or_working_directory(self):
        for filename in ("generate_single_image.py", "generate_illustrations.py"):
            with self.subTest(script=filename):
                self.assert_entrypoint_config(filename, "process")

    def assert_entrypoint_config(self, filename, expected):
        script = SCRIPT_DIR / filename
        code = (
            "import runpy, sys, os; "
            f"sys.path.insert(0, {str(SCRIPT_DIR)!r}); "
            f"runpy.run_path({str(script)!r}, run_name='config_test'); "
            "print(os.environ.get('ILLUSTRATOR_TEST_CONFIG'))"
        )
        environment = dict(os.environ)
        environment.update({
            "USERPROFILE": str(self.home), "HOME": str(self.home),
            "ILLUSTRATOR_TEST_CONFIG": "process",
        })
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", code], cwd=self.workdir,
            env=environment, capture_output=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)


if __name__ == "__main__":
    unittest.main()
